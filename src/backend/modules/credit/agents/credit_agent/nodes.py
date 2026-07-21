"""
Nós do Credit Subgraph.

Fluxo:
  credit_node → [tool_node] → credit_node → ... → END
  Quando status="rejeitado" → interrupt() → resume com aceite_entrevista
"""
import logging
from langchain_core.messages import SystemMessage, AIMessage
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from utils.llm import build_llm
from modules.credit.agents.credit_agent.state import CreditState
from modules.credit.agents.credit_agent.tools import (
    consultar_limite,
    solicitar_aumento_limite,
)

log = logging.getLogger(__name__)

CREDIT_TOOLS = [consultar_limite, solicitar_aumento_limite]

CREDIT_SYSTEM_PROMPT = """Você é o especialista de crédito do Banco Ágil. Seja direto e preciso.

ESCOPO:
- Consultar limite de crédito atual do cliente.
- Processar solicitações de aumento de limite.
- Informar sobre resultado (aprovado/rejeitado) e próximos passos.

COMPORTAMENTO OBRIGATÓRIO:
- **Sempre que o cliente solicitar aumento de limite ou informar um novo valor desejado, você DEVE chamar a ferramenta `solicitar_aumento_limite` imediatamente.** Nunca diga que enviará para análise manual, nem ofereça entrevista antes de chamar a ferramenta.
- Use sempre o `cpf_hash` do cliente autenticado nas chamadas de ferramenta.
- Se o retorno da ferramenta for aprovado: confirme com clareza ao cliente que o limite foi aumentado com sucesso para o novo valor.
- Se o retorno da ferramenta for rejeitado: informe o motivo brevemente e ofereça a entrevista de score para recalcular os dados.
- Seja breve: máximo 3 frases por resposta.
- Nunca invente dados de limite ou score.
- Nunca ofereça privilégios especiais, aprovações sem análise ou bypass do processo de crédito.

FERRAMENTAS DISPONÍVEIS:
- consultar_limite(cpf_hash): retorna o limite atual
- solicitar_aumento_limite(cpf_hash, novo_limite): processa o pedido"""


def _build_llm():
    return build_llm(temperature=0.1)


def credit_node(state: CreditState) -> Command:
    """Nó principal do agente de crédito."""
    llm = _build_llm()
    llm_with_tools = llm.bind_tools(CREDIT_TOOLS)

    # Injeta o cpf_hash disponível no estado para contexto do LLM
    system_content = CREDIT_SYSTEM_PROMPT
    if state.cliente_cpf_hash:
        system_content += f"\n\nCliente autenticado — cpf_hash: {state.cliente_cpf_hash}"
    if state.cliente_nome:
        system_content += f"\nNome: {state.cliente_nome}"

    messages = [SystemMessage(content=system_content)] + list(state.messages)
    response = llm_with_tools.invoke(messages)

    if not response.tool_calls and not (isinstance(response.content, str) and response.content.strip()):
        log.warning("credit_node: LLM retornou resposta vazia. Retentando...")
        retry_msgs = messages + [SystemMessage(content="Você deve responder ao usuário agora. Não silencie.")]
        response = llm_with_tools.invoke(retry_msgs)

    # ── Tool calls ────────────────────────────────────────────────────────────
    if response.tool_calls:
        return Command(goto="credit_tool_node", update={"messages": [response]})

    # ── Retorno para triagem ──────────────────────────────────────────────────
    content = response.content if isinstance(response.content, str) else ""
    if "[RETURN_TRIAGE]" in content:
        clean = content.replace("[RETURN_TRIAGE]", "").strip()
        return Command(
            goto="__end__",
            update={
                "messages": [AIMessage(content=clean)],
                "active_agent": "triage",
            },
        )

    # ── Verifica se acabou de registrar rejeição → usar interrupt ────────────
    # O LLM já processou a tool de solicitação; verificamos o último ToolMessage
    last_rejection = _check_last_rejection(state)
    log.debug(f'last_rejection={last_rejection}, aceite={state.aceite_entrevista}, msgs={[type(m).__name__ for m in state.messages]}')
    if last_rejection and not state.aceite_entrevista:
        # Pausa o grafo e aguarda decisão do usuário (aceitar entrevista ou não)
        user_response = interrupt(
            value={
                "type": "interview_offer",
                "message": (
                    "Infelizmente seu score atual não permite esse limite. "
                    "Gostaria de fazer uma entrevista de crédito para tentar "
                    "melhorar seu score?"
                ),
            }
        )
        # Após resume: user_response contém a decisão
        aceite = _parse_aceite(user_response)
        if aceite:
            # Sinaliza ao triage via estado para rotear para interview_subgraph
            return Command(
                goto="__end__",
                update={
                    "messages": [AIMessage(content="Iniciando a entrevista de crédito.")],
                    "aceite_entrevista": True,
                    "ultimo_status_solicitacao": "rejected_offer_accepted",
                },
            )
        else:
            return Command(
                goto="__end__",
                update={
                    "messages": [response],
                    "aceite_entrevista": False,
                },
            )

    return Command(goto="__end__", update={"messages": [response]})


def _check_last_rejection(state: CreditState) -> bool:
    """Verifica se a última tool retornou status='rejeitado' por insuficiência de score."""
    from langchain_core.messages import ToolMessage
    for msg in reversed(list(state.messages)):
        if isinstance(msg, ToolMessage):
            try:
                import ast
                data = ast.literal_eval(msg.content)
                if data.get("status") == "rejeitado":
                    motivo = str(data.get("motivo", "")).lower()
                    if "maior que" in motivo or "invalido" in data.get("status", ""):
                        return False
                    return True
            except Exception:
                pass
            break
    return False


def _parse_aceite(response: str | dict | bool) -> bool:
    """Interpreta a resposta do usuário após o interrupt."""
    if isinstance(response, bool):
        return response
    if isinstance(response, dict):
        return response.get("aceite", False)
    text = str(response).lower()
    positivo = ["sim", "yes", "quero", "aceito", "ok", "pode", "vamos", "s", "1"]
    return any(p in text for p in positivo)


# ToolNode para executar as tools do agente de crédito
credit_tool_node = ToolNode(tools=CREDIT_TOOLS)
