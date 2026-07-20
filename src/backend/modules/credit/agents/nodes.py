"""
Nós do Credit Subgraph.

Fluxo:
  credit_node → [tool_node] → credit_node → ... → END
  Quando status="rejeitado" → interrupt() → resume com aceite_entrevista
"""
import logging
from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from core.config import settings
from modules.credit.agents.state import CreditState
from modules.credit.agents.tools import consultar_limite, solicitar_aumento_limite

log = logging.getLogger(__name__)

CREDIT_TOOLS = [consultar_limite, solicitar_aumento_limite]

CREDIT_SYSTEM_PROMPT = """Você é o especialista de crédito do Banco Ágil. Seja direto e preciso.

ESCOPO:
- Consultar limite de crédito atual do cliente.
- Processar solicitações de aumento de limite.
- Informar sobre resultado (aprovado/rejeitado) e próximos passos.

COMPORTAMENTO:
- Use sempre o cpf_hash do cliente autenticado nas tools.
- Se o pedido for rejeitado: informe o motivo brevemente e ofereça a entrevista de score.
- Se o cliente quiser encerrar ou falar de outro assunto: responda com [RETURN_TRIAGE].
- Seja breve: máximo 3 frases por resposta.
- Nunca invente dados de limite ou score.

FERRAMENTAS DISPONÍVEIS:
- consultar_limite(cpf_hash): retorna o limite atual
- solicitar_aumento_limite(cpf_hash, novo_limite): processa o pedido"""


def _build_llm():
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=settings.OPENROUTER_BASE_URL,
        temperature=0.1,
        streaming=True,
        max_retries=3,
    )


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

    # ── Tool calls ────────────────────────────────────────────────────────────
    if response.tool_calls:
        return Command(goto="credit_tool_node", update={"messages": [response]})

    # ── Retorno para triagem ──────────────────────────────────────────────────
    content = response.content if isinstance(response.content, str) else ""
    if "[RETURN_TRIAGE]" in content:
        clean = content.replace("[RETURN_TRIAGE]", "").strip()
        return Command(goto="__end__", update={"messages": [AIMessage(content=clean)]})

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
            # Sinaliza ao triage via tag para rotear para interview_subgraph
            return Command(
                goto="__end__",
                update={
                    "messages": [AIMessage(content="[HANDOFF:interview]")],
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
    """Verifica se a última tool retornou status='rejeitado'."""
    from langchain_core.messages import ToolMessage
    for msg in reversed(list(state.messages)):
        if isinstance(msg, ToolMessage):
            try:
                import ast
                data = ast.literal_eval(msg.content)
                return data.get("status") == "rejeitado"
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
