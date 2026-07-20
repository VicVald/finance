"""
Nó do Agente de Câmbio.
"""
import logging
from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from core.config import settings
from modules.exchange.agents.state import ExchangeState
from modules.exchange.agents.tools import consultar_cotacao

log = logging.getLogger(__name__)

EXCHANGE_TOOLS = [consultar_cotacao]

EXCHANGE_SYSTEM_PROMPT = """Você é o agente de câmbio do Banco Ágil.

ESCOPO:
- Consultar cotações de moedas em relação ao Real (BRL).
- Moedas suportadas: USD (Dólar), EUR (Euro), GBP (Libra), BTC (Bitcoin), ARS (Peso), entre outras.

COMPORTAMENTO:
- Identifique a moeda na mensagem do cliente e chame `consultar_cotacao`.
- Apresente o resultado de forma clara e objetiva.
- Se o cliente quiser encerrar ou falar de outro assunto: responda com [RETURN_TRIAGE].
- Seja breve: máximo 2-3 frases por resposta.

NUNCA:
- Invente valores de câmbio.
- Saia do escopo de câmbio."""


def _build_llm():
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=settings.OPENROUTER_BASE_URL,
        temperature=0.1,
        streaming=True,
        max_retries=3,
    )


def exchange_node(state: ExchangeState) -> Command:
    """Nó principal do agente de câmbio."""
    llm = _build_llm()
    llm_with_tools = llm.bind_tools(EXCHANGE_TOOLS)

    messages = [SystemMessage(content=EXCHANGE_SYSTEM_PROMPT)] + list(state.messages)
    response = llm_with_tools.invoke(messages)

    if response.tool_calls:
        return Command(goto="exchange_tool_node", update={"messages": [response]})

    content = response.content if isinstance(response.content, str) else ""
    if "[RETURN_TRIAGE]" in content:
        clean = content.replace("[RETURN_TRIAGE]", "").strip()
        return Command(goto="__end__", update={"messages": [AIMessage(content=clean)]})

    return Command(goto="__end__", update={"messages": [response]})


exchange_tool_node = ToolNode(tools=EXCHANGE_TOOLS)
