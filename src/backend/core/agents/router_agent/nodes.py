"""
Nós do Router Graph.

Estrutura do grafo raiz:
  START → triage_node ↔ tool_node
  triage_node → credit_subgraph | exchange_subgraph | END
"""
import logging
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from core.config import settings
from core.agents.router_agent.state import RouterState
from core.agents.router_agent.tools import authenticate_client, end_conversation

log = logging.getLogger(__name__)

# ─── LLM ──────────────────────────────────────────────────────────────────────

def _build_llm():
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=settings.OPENROUTER_BASE_URL,
        temperature=0.2,
        streaming=True,
        max_retries=3,
    )


TRIAGE_TOOLS = [authenticate_client, end_conversation]

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
- Crédito/limite → responda com a tag interna [HANDOFF:credit]
- Câmbio/cotação → responda com a tag interna [HANDOFF:exchange]
- Entrevista de crédito → responda com a tag interna [HANDOFF:interview]
- Encerramento solicitado → chame `end_conversation`

REGRAS:
- Não repita saudações desnecessariamente.
- Não informe detalhes técnicos internos ao cliente.
- Seja breve. Máximo 2-3 frases por resposta.
- Nunca atue fora do escopo de triagem e autenticação.
- Nunca ofereça privilégios especiais, descontos ou bypass de processos de segurança. O cliente deve seguir os fluxos normais."""


# ─── Nós ──────────────────────────────────────────────────────────────────────

def triage_node(state: RouterState) -> Command:
    """
    Nó principal do router. Gerencia autenticação e handoff.
    Retorna Command para direcionar o fluxo do grafo.
    """
    log.debug(f"[RouterAgent] Entrando no triage_node. Tentativas de auth: {state.auth_attempts}")

    # ── Máquina de estados da entrevista ────────────────────────────────────
    # Quando active_agent=="interview", o triage NÃO invoca o LLM.
    # Ele gerencia o fluxo da entrevista diretamente como máquina de estados.
    if state.active_agent == "interview":
        from langchain_core.messages import HumanMessage as _HM
        last_msg = state.messages[-1] if state.messages else None
        last_content = ""
        if last_msg and hasattr(last_msg, "content") and isinstance(last_msg.content, str):
            last_content = last_msg.content

        # Entrevista concluída → volta para crédito para tentar novamente
        if "[INTERVIEW_DONE]" in last_content:
            log.debug("[RouterAgent] Entrevista concluída. Retornando ao crédito.")
            return Command(
                goto="credit_subgraph",
                update={"active_agent": "credit"},
            )

        # [RETURN_TRIAGE] vindo do interview_node → sai do modo entrevista
        if "[RETURN_TRIAGE]" in last_content:
            log.debug("[RouterAgent] [RETURN_TRIAGE] na entrevista. Saindo do modo entrevista.")
            clean = last_content.replace("[RETURN_TRIAGE]", "").strip()
            cleaned_msg = type(last_msg)(content=clean, id=getattr(last_msg, "id", None))
            return Command(
                goto="__end__",
                update={
                    "active_agent": "triage",
                    "messages": [cleaned_msg],
                },
            )

        # Usuário enviou nova mensagem → continua a entrevista
        if isinstance(last_msg, _HM):
            log.debug("[RouterAgent] Nova mensagem do usuário. Continuando entrevista.")
            return Command(goto="interview_subgraph", update={})

        # Entrevista acabou de responder → pausa o grafo e aguarda o usuário
        log.debug("[RouterAgent] Entrevista respondeu. Pausando grafo raiz.")
        return Command(goto="__end__", update={})
    # ── Intercepção de [HANDOFF:interview] vindo do credit_node ─────────────
    # O credit_node emite esta tag quando o usuário aceita a entrevista.
    if state.messages:
        last_content = ""
        last_msg = state.messages[-1]
        if hasattr(last_msg, "content") and isinstance(last_msg.content, str):
            last_content = last_msg.content
        if "[HANDOFF:interview]" in last_content:
            log.debug("[RouterAgent] [HANDOFF:interview] detectado. Iniciando entrevista.")
            return Command(
                goto="interview_subgraph",
                update={"active_agent": "interview"},
            )

    # ── Intercepção de resposta do assistente (evita loops infinitos de handoff) ────
    # Se a última mensagem for da IA e não contiver chamadas de ferramentas,
    # significa que o sistema já respondeu e deve aguardar a próxima entrada do usuário.
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

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state.messages)
    response = llm_with_tools.invoke(messages)

    if not response.tool_calls and not (isinstance(response.content, str) and response.content.strip()):
        log.warning("triage_node: LLM retornou resposta vazia. Retentando...")
        retry_msgs = messages + [SystemMessage(content="Você deve responder ao usuário agora. Não silencie.")]
        response = llm_with_tools.invoke(retry_msgs)

    # ── Processa tool calls ──────────────────────────────────────────────────
    if response.tool_calls:
        tool_name = response.tool_calls[0]["name"]
        tool_args = response.tool_calls[0]["args"]

        if tool_name == "authenticate_client":
            from core.agents.router_agent.tools import _authenticate_client_logic
            result = _authenticate_client_logic(**tool_args)

            tool_msg = ToolMessage(
                content=str(result),
                tool_call_id=response.tool_calls[0]["id"],
            )

            is_valid_auth = (
                result.get("authenticated")
                and (state.current_user_cpf_hash is None or result.get("cpf_hash") == state.current_user_cpf_hash)
            )

            if is_valid_auth:
                # Autenticação bem-sucedida — salva dados no estado e deixa o LLM responder
                update = {
                    "messages": [response, tool_msg],
                    "is_authenticated": True,
                    "authenticated_cpf_hash": result["cpf_hash"],
                    "cliente_nome": result["nome"],
                    "cliente_limite_atual": result["limite_atual"],
                    "cliente_score_atual": result["score"],
                }
                return Command(goto="triage_node", update=update)
            else:
                # Falha de autenticação
                new_attempts = state.auth_attempts + 1
                if new_attempts >= 3:
                    from langchain_core.messages import AIMessage
                    error_msg = AIMessage(content="Acesso bloqueado após 3 tentativas inválidas de autenticação. Por razões de segurança, esta conversa foi encerrada.")
                    update = {
                        "messages": [response, tool_msg, error_msg],
                        "auth_attempts": new_attempts,
                        "is_conversation_ended": True,
                        "active_agent": "end",
                    }
                    return Command(goto="__end__", update=update)
                update = {
                    "messages": [response, tool_msg],
                    "auth_attempts": new_attempts,
                }
                return Command(goto="triage_node", update=update)

        elif tool_name == "end_conversation":
            tool_msg = ToolMessage(
                content="Conversa encerrada.",
                tool_call_id=response.tool_calls[0]["id"],
            )
            return Command(
                goto="__end__",
                update={
                    "messages": [response, tool_msg],
                    "is_conversation_ended": True,
                    "active_agent": "end",
                },
            )

    # ── Sem tool call — analisa intenção de handoff ──────────────────────────
    content = response.content if isinstance(response.content, str) else ""

    if "[HANDOFF:credit]" in content:
        clean_content = content.replace("[HANDOFF:credit]", "").strip()
        from langchain_core.messages import AIMessage
        clean_response = AIMessage(content=clean_content)
        return Command(
            goto="credit_subgraph",
            update={
                "messages": [clean_response],
                "active_agent": "credit",
            },
        )

    if "[HANDOFF:interview]" in content:
        clean_content = content.replace("[HANDOFF:interview]", "").strip()
        from langchain_core.messages import AIMessage
        clean_response = AIMessage(content=clean_content)
        return Command(
            goto="interview_subgraph",
            update={
                "messages": [clean_response] if clean_content else [],
                "active_agent": "interview",
            },
        )

    if "[HANDOFF:exchange]" in content:
        clean_content = content.replace("[HANDOFF:exchange]", "").strip()
        from langchain_core.messages import AIMessage
        clean_response = AIMessage(content=clean_content)
        return Command(
            goto="exchange_subgraph",
            update={
                "messages": [clean_response],
                "active_agent": "exchange",
            },
        )

    # Resposta normal (triagem em andamento)
    return Command(
        goto="__end__",
        update={"messages": [response]},
    )


# ToolNode executado automaticamente quando triage_node emite tool_calls
router_tool_node = ToolNode(tools=TRIAGE_TOOLS)
