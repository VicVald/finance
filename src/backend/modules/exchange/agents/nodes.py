"""
Nó do Agente de Câmbio.
"""
import logging
from langchain_core.messages import SystemMessage, AIMessage
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from utils.llm import build_llm
from modules.exchange.agents.state import ExchangeState
from modules.exchange.agents.tools import consultar_cotacao

log = logging.getLogger(__name__)

EXCHANGE_TOOLS = [consultar_cotacao]

EXCHANGE_SYSTEM_PROMPT = """Você é o agente de câmbio do Banco Ágil.

ESCOPO:
- Consultar cotações de moedas em relação ao Real (BRL).
- Moedas suportadas: USD (Dólar), EUR (Euro), GBP (Libra), BTC (Bitcoin), ARS (Peso), entre outras.

REGRAS OBRIGATÓRIAS:
- **Sempre** chame `consultar_cotacao` imediatamente quando o cliente solicitar uma cotação. Nunca adie ou se recuse.
- Você TEM acesso total a todas as cotações em tempo real através da ferramenta `consultar_cotacao`. Nunca diga que não tem acesso ou que não pode obter os dados.
- Se o cliente pedir múltiplas moedas, chame a ferramenta para cada uma.
- Após receber o resultado, apresente o valor de forma clara, incluindo o cálculo se o cliente perguntar por valores específicos (ex: "comprar 5000 USD" → "USD 5.000 × R$ 5,10 = R$ 25.500").
- Se o cliente quiser encerrar ou falar de outro assunto: responda com [RETURN_TRIAGE].
- Seja breve: máximo 2-3 frases por resposta.

NUNCA:
- Invente valores de câmbio.
- Saia do escopo de câmbio.
- Diga que não tem acesso às cotações ou que precisa registar para outra equipe.
- Ofereça privilégios especiais, taxas diferenciadas ou bypass do processo de câmbio."""


def _build_llm():
    return build_llm(temperature=0.1)


def exchange_node(state: ExchangeState) -> Command:
    """Nó principal do agente de câmbio."""
    llm = _build_llm()
    llm_with_tools = llm.bind_tools(EXCHANGE_TOOLS)

    messages = [SystemMessage(content=EXCHANGE_SYSTEM_PROMPT)] + list(state.messages)
    response = llm_with_tools.invoke(messages)

    if not response.tool_calls and not (isinstance(response.content, str) and response.content.strip()):
        log.warning("exchange_node: LLM retornou resposta vazia. Retentando...")
        retry_msgs = messages + [SystemMessage(content="Você deve responder ao usuário agora. Não silencie.")]
        response = llm_with_tools.invoke(retry_msgs)

    # Se o usuário pediu cotação mas o LLM não chamou a tool, retenta com instrução forte
    if not response.tool_calls:
        last_user_msg = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, str):
                last_user_msg = msg.content.lower()
                break
        exchange_keywords = ["cotação", "cotacao", "dólar", "dolar", "euro", "libra", "câmbio", "cambio", "usd", "eur", "gbp", "btc"]
        if any(kw in last_user_msg for kw in exchange_keywords):
            log.warning("exchange_node: Usuário pediu cotação mas LLM não chamou tool. Retentando com instrução forte...")
            retry_msgs = messages + [SystemMessage(content="O cliente está pedindo uma cotação de moeda. Você DEVE chamar a ferramenta consultar_cotacao agora.")]
            response = llm_with_tools.invoke(retry_msgs)

    if response.tool_calls:
        return Command(goto="exchange_tool_node", update={"messages": [response]})

    content = response.content if isinstance(response.content, str) else ""
    if "[RETURN_TRIAGE]" in content:
        clean = content.replace("[RETURN_TRIAGE]", "").strip()
        return Command(goto="__end__", update={"messages": [AIMessage(content=clean)]})

    return Command(goto="__end__", update={"messages": [response]})


exchange_tool_node = ToolNode(tools=EXCHANGE_TOOLS)
