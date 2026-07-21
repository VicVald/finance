"""
Nós do Subgraph de Entrevista de Crédito.

Fluxo conversacional:
  1. LLM apresenta todos os campos necessários de uma vez.
  2. Extrai respostas parciais do histórico e atualiza o estado progressivamente.
  3. Quando todos os campos estão preenchidos → calcula score via tool.
  4. Atualiza clientes.csv e retorna ao subgraph de crédito.
"""
import json
import logging
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from utils.llm import build_llm
from modules.credit.agents.interview_state import InterviewState
from modules.credit.services import calcular_score_entrevista, atualizar_score_cliente

log = logging.getLogger(__name__)


# ─── Tool de cálculo de score ─────────────────────────────────────────────────

@tool
def calcular_e_salvar_score(
    cpf_hash: str,
    renda_mensal: float,
    tipo_emprego: str,
    despesas_fixas: float,
    num_dependentes: int,
    tem_dividas: bool,
) -> dict:
    """
    Calcula o novo score de crédito com base nos dados financeiros e atualiza o banco de dados.

    Args:
        cpf_hash: Hash do CPF do cliente
        renda_mensal: Renda mensal em BRL
        tipo_emprego: "formal", "autônomo" ou "desempregado"
        despesas_fixas: Total de despesas fixas mensais em BRL
        num_dependentes: Número de dependentes
        tem_dividas: True se possui dívidas ativas, False caso contrário

    Returns:
        dict com novo_score e confirmação de atualização
    """
    novo_score = calcular_score_entrevista(
        renda_mensal=renda_mensal,
        tipo_emprego=tipo_emprego,
        despesas_fixas=despesas_fixas,
        num_dependentes=num_dependentes,
        tem_dividas=tem_dividas,
    )
    atualizado = atualizar_score_cliente(cpf_hash=cpf_hash, novo_score=novo_score)
    return {
        "novo_score": novo_score,
        "atualizado": atualizado,
    }


INTERVIEW_TOOLS = [calcular_e_salvar_score]

INTERVIEW_SYSTEM_PROMPT = """Você é o agente de entrevista de crédito do Banco Ágil.

Sua função é coletar dados financeiros do cliente para recalcular o score de crédito.

INÍCIO DA ENTREVISTA:
Ao iniciar a entrevista, apresente de uma vez todos os dados necessários que o cliente precisará inserir:
1. Renda mensal bruta (em R$)
2. Tipo de emprego: formal, autônomo ou desempregado
3. Despesas fixas mensais (em R$)
4. Número de dependentes
5. Possui dívidas ativas? (sim/não)

Sugira proativamente que o cliente comece informando algum dos campos (ex: "Para começar, qual é a sua renda mensal bruta?").

COMPORTAMENTO:
- O cliente pode responder um campo por vez ou vários de uma vez.
- À medida que receber respostas, confirme os dados coletados e peça os que faltam.
- Quando todos os 5 campos estiverem coletados, chame a tool `calcular_e_salvar_score`.
- Após o cálculo, informe o novo score e diga que o cliente será redirecionado para crédito.
- **O cliente pode corrigir/alterar valores já informados anteriormente.** Atualize seu entendimento e continue perguntando os campos faltantes.
- Se o cliente quiser encerrar ou falar de outro assunto (ex: câmbio): responda com [RETURN_TRIAGE] no final da mensagem.
- Seja direto: máximo 3 frases por resposta.

NUNCA:
- Invente dados financeiros.
- Saia do escopo da entrevista.
- Ofereça privilégios especiais, descontos ou garantias de aprovação de crédito."""


def _build_llm():
    return build_llm(temperature=0.1)


def interview_node(state: InterviewState) -> Command:
    """Nó principal do agente de entrevista."""
    llm = _build_llm()
    llm_with_tools = llm.bind_tools(INTERVIEW_TOOLS)

    system_content = INTERVIEW_SYSTEM_PROMPT
    if state.cpf_hash:
        system_content += f"\n\nCliente — cpf_hash: {state.cpf_hash}"
    if state.cliente_nome:
        system_content += f"\nNome: {state.cliente_nome}"

    # Injeta contexto dos dados já coletados
    collected = _get_collected_summary(state)
    if collected:
        system_content += f"\n\nDados já coletados: {collected}"

    messages = [SystemMessage(content=system_content)] + list(state.messages[-6:])
    response = llm_with_tools.invoke(messages)

    if not response.tool_calls and not (isinstance(response.content, str) and response.content.strip()):
        log.warning("interview_node: LLM retornou resposta vazia. Retentando...")
        retry_msgs = messages + [SystemMessage(content="Você deve responder ao usuário agora. Não silencie.")]
        response = llm_with_tools.invoke(retry_msgs)

    # Tool call → calcular score
    if response.tool_calls:
        return Command(goto="interview_tool_node", update={"messages": [response]})

    # Verifica se entrevista foi concluída (score calculado no histórico)
    novo_score = _extract_novo_score(state)
    if novo_score is not None:
        # Sinaliza ao triage (via tag na mensagem) que a entrevista terminou
        done_content = response.content if isinstance(response.content, str) else ""
        done_msg = AIMessage(content=done_content + " [INTERVIEW_DONE]")
        return Command(
            goto="__end__",
            update={
                "messages": [done_msg],
                "novo_score": novo_score,
                "entrevista_concluida": True,
            },
        )

    return Command(goto="__end__", update={"messages": [response]})


def _get_collected_summary(state: InterviewState) -> str:
    """Retorna string com dados já coletados para contextualizar o LLM."""
    parts = []
    if state.renda_mensal is not None:
        parts.append(f"renda_mensal=R${state.renda_mensal:,.2f}")
    if state.tipo_emprego is not None:
        parts.append(f"tipo_emprego={state.tipo_emprego}")
    if state.despesas_fixas is not None:
        parts.append(f"despesas_fixas=R${state.despesas_fixas:,.2f}")
    if state.num_dependentes is not None:
        parts.append(f"num_dependentes={state.num_dependentes}")
    if state.tem_dividas is not None:
        parts.append(f"tem_dividas={'sim' if state.tem_dividas else 'não'}")
    return ", ".join(parts)


def _extract_novo_score(state: InterviewState) -> int | None:
    """Extrai o novo score da última ToolMessage (se existir)."""
    from langchain_core.messages import ToolMessage
    for msg in reversed(list(state.messages)):
        if isinstance(msg, ToolMessage):
            try:
                import ast
                data = ast.literal_eval(msg.content)
                if "novo_score" in data:
                    return int(data["novo_score"])
            except Exception:
                pass
            break
    return None


# ToolNode para executar calcular_e_salvar_score
interview_tool_node = ToolNode(tools=INTERVIEW_TOOLS)
