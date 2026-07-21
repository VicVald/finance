"""
Ferramentas do Agente de Câmbio.
"""
import asyncio
import logging
from langchain_core.tools import tool
from modules.exchange.services import get_cotacao, ExchangeServiceUnavailableError

log = logging.getLogger(__name__)


@tool
def consultar_cotacao(moeda: str) -> str:
    """
    Consulta a cotação de uma moeda em relação ao Real Brasileiro (BRL).
    Aceita: USD (Dólar), EUR (Euro), GBP (Libra), BTC (Bitcoin), ARS (Peso Argentino), etc.

    Args:
        moeda: Código da moeda (ex: "USD", "EUR", "GBP", "BTC")

    Returns:
        String formatada com os valores de compra, venda e a fonte dos dados.
    """
    try:
        result = asyncio.run(get_cotacao(moeda.upper()))
        variacao = ""
        if result.variacao_pct is not None:
            sinal = "+" if result.variacao_pct >= 0 else ""
            variacao = f" | Variação: {sinal}{result.variacao_pct:.2f}%"
        return (
            f"Cotação {result.moeda_nome} ({result.moeda_codigo}/BRL):\n"
            f"• Compra: R$ {result.valor_compra:,.4f}\n"
            f"• Venda:  R$ {result.valor_venda:,.4f}{variacao}\n"
            f"• Fonte: {result.fonte} | {result.timestamp.strftime('%d/%m/%Y %H:%M UTC')}"
        )
    except ExchangeServiceUnavailableError as e:
        return str(e)
    except Exception as e:
        log.error(f"Erro inesperado ao consultar cotação de {moeda}: {e}")
        return "Serviço de câmbio temporariamente indisponível. Tente novamente em instantes."


