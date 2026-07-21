"""
Nós do Router Graph.

Estrutura do grafo raiz:
  START → triage_node ↔ tool_node
  triage_node → credit_subgraph | exchange_subgraph | END
"""
import logging
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from utils.llm import build_llm
from core.agents.router_agent.state import RouterState
from core.agents.router_agent.tools import (
    authenticate_client,
    end_conversation,
    transfer_to_credit,
    transfer_to_exchange,
    transfer_to_interview,
)

log = logging.getLogger(__name__)

# ─── LLM ──────────────────────────────────────────────────────────────────────

def _build_llm():
    return build_llm(temperature=0.2)


TRIAGE_TOOLS = [
    authenticate_client,
    end_conversation,
    transfer_to_credit,
    transfer_to_exchange,
    transfer_to_interview,
]

SYSTEM_PROMPT = """Você é o assistente virtual do Banco Ágil. Seja objetivo e respeitoso.

Sua função é autenticar o cliente e direcioná-lo ao serviço correto.

FLUXO DE AUTENTICAÇÃO:
1. Cumprimente brevemente e solicite o CPF.
2. Solicite a data de nascimento EXPLICITAMENTE no formato DD/MM/AAAA (ex: 15/05/1990).
3. Ao chamar `authenticate_client`, passe a data EXATAMENTE como o cliente informou, no formato DD/MM/AAAA. Nunca inverta dia e mês.
4. Se autenticado: avise explicitamente que a autenticação foi realizada com sucesso e pergunte qual é a intenção/necessidade do usuário. Somente após a resposta dele, direcione para o serviço (crédito ou câmbio).
5. Se falhar: informe e solicite nova tentativa (máximo 3 tentativas total).
6. Na 3ª falha: chame `end_conversation` e encerre gentilmente.

DIRECIONAMENTO (após autenticação):
- Qualquer menção a crédito, limite de crédito, aumento de limite ou consulta de limite/score → chame a ferramenta `transfer_to_credit`
- Câmbio/cotação → chame a ferramenta `transfer_to_exchange`
- Apenas se o cliente pedir EXPLICITAMENTE a "entrevista de crédito" ou "entrevista de score" → chame a ferramenta `transfer_to_interview`
- Encerramento solicitado → chame `end_conversation`
- **Ao chamar ferramentas de transferência (`transfer_to_credit`, `transfer_to_interview`, `transfer_to_exchange`), retorne APENAS a chamada da ferramenta sem texto descritivo adicional de transferência.**

REGRAS:
- Não repita saudações desnecessariamente.
- Não informe detalhes técnicos internos ao cliente.
- Seja breve. Máximo 2-3 frases por resposta.
- Nunca atue fora do escopo de triagem e autenticação.
- Nunca ofereça privilégios especiais, descontos ou bypass de processos de segurança. O cliente deve seguir os fluxos normais."""


AUTHENTICATED_SYSTEM_PROMPT = """Você é o assistente virtual do Banco Ágil.

O CLIENTE JÁ ESTÁ AUTENTICADO NO SISTEMA.
Nome do Cliente: {cliente_nome}
Agente Ativo Atual: {active_agent}

REGRAS OBRIGATÓRIAS:
1. NUNCA solicite CPF, data de nascimento ou qualquer dado de autenticação. O cliente JÁ está autenticado.
2. Sua função é classificar a intenção do cliente a cada mensagem e direcioná-lo IMEDIATAMENTE chamando a ferramenta de transferência correspondente:
   - Se o cliente mencionar crédito, limite, aumento de limite OU se for continuidade/saudação do atendimento atual de crédito (`active_agent` == 'credit') → chame `transfer_to_credit`.
   - Se o cliente mencionar câmbio, cotação, moedas (dólar, euro, etc.) OU se for continuidade/saudação do atendimento atual de câmbio (`active_agent` == 'exchange') → chame `transfer_to_exchange`.
   - Se o cliente pedir explicitamente a "entrevista de crédito" ou "entrevista de score" OU se a entrevista já estiver em andamento (`active_agent` == 'interview') → chame `transfer_to_interview`.
   - Se o cliente solicitar o encerramento do atendimento → chame `end_conversation`.
3. Ao chamar ferramentas de transferência (`transfer_to_credit`, `transfer_to_exchange`, `transfer_to_interview`), retorne APENAS a chamada da ferramenta sem texto adicional."""


# ─── Nós ──────────────────────────────────────────────────────────────────────

def triage_node(state: RouterState) -> Command:
    """
    Nó principal do router. Gerencia autenticação e handoff dinâmico por intenção.
    Retorna Command para direcionar o fluxo do grafo.
    """
    log.debug(f"[RouterAgent] Entrando no triage_node. Authenticated: {state.is_authenticated}, Active agent: {state.active_agent}")

    # ── Intercepção de aceite de entrevista vindo do credit_node ─────────────
    if state.aceite_entrevista:
        log.debug("[RouterAgent] Aceite de entrevista detectado. Iniciando entrevista.")
        return Command(
            goto="interview_subgraph",
            update={
                "active_agent": "interview",
                "aceite_entrevista": None,
            },
        )

    # ── Intercepção de resposta do assistente (evita loops infinitos) ────
    if state.messages:
        from langchain_core.messages import AIMessage as _AIM
        last_msg = state.messages[-1]
        if isinstance(last_msg, _AIM) and not last_msg.tool_calls:
            log.debug("[RouterAgent] Última mensagem é AIMessage. Retornando ao usuário e pausando grafo.")
            return Command(goto="__end__", update={})

    llm = _build_llm()
    llm_with_tools = llm.bind_tools(TRIAGE_TOOLS)

    # Verifica limite de tentativas antes de chamar o LLM
    if state.auth_attempts >= 3 and not state.is_authenticated:
        from langchain_core.messages import AIMessage
        error_msg = AIMessage(content="Acesso bloqueado após 3 tentativas inválidas de autenticação. Por razões de segurança, esta conversa foi encerrada.")
        return Command(
            goto="__end__",
            update={
                "messages": [error_msg],
                "is_conversation_ended": True,
                "active_agent": "end"
            },
        )

    if state.is_authenticated:
        sys_prompt = AUTHENTICATED_SYSTEM_PROMPT.format(
            cliente_nome=state.cliente_nome or "Cliente",
            active_agent=state.active_agent or "triage",
        )
    else:
        sys_prompt = SYSTEM_PROMPT

    messages = [SystemMessage(content=sys_prompt)] + list(state.messages)
    response = llm_with_tools.invoke(messages)

    if not response.tool_calls and not (isinstance(response.content, str) and response.content.strip()):
        log.warning("triage_node: LLM retornou resposta vazia. Retentando...")
        retry_msgs = messages + [SystemMessage(content="Você deve responder ao usuário agora. Não silencie.")]
        response = llm_with_tools.invoke(retry_msgs)

    # Se cliente está autenticado e o LLM não chamou tool, mantém no subgrafo ativo (se houver)
    if not response.tool_calls and state.is_authenticated and state.active_agent in ("credit", "exchange", "interview"):
        target_subgraph = f"{state.active_agent}_subgraph"
        log.debug(f"[RouterAgent] Cliente autenticado sem tool_call explícita. Mantendo em {target_subgraph}.")
        return Command(goto=target_subgraph, update={})

    # ── Processa tool calls ──────────────────────────────────────────────────
    if response.tool_calls:
        tool_messages = []
        is_valid_auth = False
        auth_result = None
        end_conv = False

        for tc in response.tool_calls:
            tname = tc.get("name")
            targs = tc.get("args", {})
            tcall_id = tc.get("id")

            if tname == "authenticate_client":
                from core.agents.router_agent.tools import _authenticate_client_logic
                result = _authenticate_client_logic(**targs)
                tool_msg = ToolMessage(
                    content=str(result),
                    tool_call_id=tcall_id,
                )
                tool_messages.append(tool_msg)

                if (result.get("authenticated")
                        and (state.current_user_cpf_hash is None or result.get("cpf_hash") == state.current_user_cpf_hash)):
                    is_valid_auth = True
                    auth_result = result
                else:
                    auth_result = result

            elif tname == "end_conversation":
                tool_msg = ToolMessage(
                    content="Conversa encerrada.",
                    tool_call_id=tcall_id,
                )
                tool_messages.append(tool_msg)
                end_conv = True

            elif tname == "transfer_to_credit":
                tool_msg = ToolMessage(
                    content="Handoff realizado com sucesso. (INSTRUÇÃO INTERNA: assuma o atendimento imediatamente ajudando o usuário. NÃO mencione que ele foi transferido. NÃO confirme a transferência.)",
                    tool_call_id=tcall_id,
                )
                clean_response = type(response)(content="", tool_calls=response.tool_calls, id=getattr(response, "id", None))
                return Command(
                    goto="credit_subgraph",
                    update={
                        "messages": [clean_response, tool_msg],
                        "active_agent": "credit",
                    },
                )

            elif tname == "transfer_to_exchange":
                tool_msg = ToolMessage(
                    content="Handoff realizado com sucesso. (INSTRUÇÃO INTERNA: assuma o atendimento imediatamente ajudando o usuário. NÃO mencione que ele foi transferido. NÃO confirme a transferência.)",
                    tool_call_id=tcall_id,
                )
                clean_response = type(response)(content="", tool_calls=response.tool_calls, id=getattr(response, "id", None))
                return Command(
                    goto="exchange_subgraph",
                    update={
                        "messages": [clean_response, tool_msg],
                        "active_agent": "exchange",
                    },
                )

            elif tname == "transfer_to_interview":
                tool_msg = ToolMessage(
                    content="Handoff realizado com sucesso. (INSTRUÇÃO INTERNA: assuma o atendimento imediatamente ajudando o usuário. NÃO mencione que ele foi transferido. NÃO confirme a transferência.)",
                    tool_call_id=tcall_id,
                )
                clean_response = type(response)(content="", tool_calls=response.tool_calls, id=getattr(response, "id", None))
                return Command(
                    goto="interview_subgraph",
                    update={
                        "messages": [clean_response, tool_msg],
                        "active_agent": "interview",
                    },
                )

            else:
                # Unsupported tool generated by the LLM
                tool_msg = ToolMessage(
                    content=f"Error: Tool {tname} not supported in triage.",
                    tool_call_id=tcall_id,
                )
                tool_messages.append(tool_msg)

        if end_conv:
            return Command(
                goto="__end__",
                update={
                    "messages": [response] + tool_messages,
                    "is_conversation_ended": True,
                    "active_agent": "end",
                },
            )

        if auth_result is not None:
            if is_valid_auth:
                update = {
                    "messages": [response] + tool_messages,
                    "is_authenticated": True,
                    "authenticated_cpf_hash": auth_result["cpf_hash"],
                    "cliente_nome": auth_result["nome"],
                    "cliente_limite_atual": auth_result["limite_atual"],
                    "cliente_score_atual": auth_result["score"],
                }
                return Command(goto="triage_node", update=update)
            else:
                new_attempts = state.auth_attempts + 1
                if new_attempts >= 3:
                    from langchain_core.messages import AIMessage
                    error_msg = AIMessage(content="Acesso bloqueado após 3 tentativas inválidas de autenticação. Por razões de segurança, esta conversa foi encerrada.")
                    update = {
                        "messages": [response] + tool_messages + [error_msg],
                        "auth_attempts": new_attempts,
                        "is_conversation_ended": True,
                        "active_agent": "end",
                    }
                    return Command(goto="__end__", update=update)
                update = {
                    "messages": [response] + tool_messages,
                    "auth_attempts": new_attempts,
                }
                return Command(goto="triage_node", update=update)

    # Resposta normal (triagem em andamento)
    return Command(
        goto="__end__",
        update={"messages": [response]},
    )


# ToolNode executado automaticamente quando triage_node emite tool_calls
router_tool_node = ToolNode(tools=TRIAGE_TOOLS)
