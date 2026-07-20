"""
TDD — Boundary: Fallback da AwesomeAPI quando BrasilAPI falha.
Testa:
  - BrasilAPI responde OK → usa BrasilAPI
  - BrasilAPI falha (timeout/HTTP error/JSON inválido) → fallback AwesomeAPI
  - Ambas falham → ExchangeServiceUnavailableError
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock


def get_service():
    from modules.exchange.services import get_cotacao, ExchangeServiceUnavailableError
    return get_cotacao, ExchangeServiceUnavailableError


BRASIL_API_RESPONSE = [
    {
        "paridadeCompra": 1,
        "paridadeVenda": 1,
        "cotacaoCompra": 5.7123,
        "cotacaoVenda": 5.7129,
        "dataHoraCotacao": "2026-07-19 13:05:00.0",
        "tipoBoletim": "Fechamento",
        "codigoMoeda": "USD",
        "nomeFormatado": "Dólar dos EUA",
    }
]

AWESOME_API_RESPONSE = {
    "USDBRL": {
        "code": "USD",
        "codein": "BRL",
        "name": "Dólar Americano/Real Brasileiro",
        "high": "5.7200",
        "low": "5.6900",
        "varBid": "0.0150",
        "pctChange": "0.26",
        "bid": "5.7100",
        "ask": "5.7150",
        "timestamp": "1721390400",
        "create_date": "2026-07-19 13:00:00",
    }
}


class TestExchangeFallback:
    """Testa a lógica de fallback entre BrasilAPI e AwesomeAPI."""

    def test_brasilapi_success_uses_brasilapi(self):
        """Quando BrasilAPI retorna OK, usa BrasilAPI como fonte."""
        get_cotacao, _ = get_service()

        async def run():
            with patch("modules.exchange.services._fetch_brasilapi", new=AsyncMock(return_value=BRASIL_API_RESPONSE)), \
                 patch("modules.exchange.services._fetch_awesomeapi", new=AsyncMock(side_effect=Exception("não deve chamar"))):
                return await get_cotacao("USD")

        result = asyncio.run(run())
        assert result.fonte == "brasilapi"
        assert result.moeda_codigo == "USD"
        assert abs(result.valor_compra - 5.7123) < 0.001

    def test_brasilapi_failure_triggers_awesomeapi_fallback(self):
        """Quando BrasilAPI falha, AwesomeAPI é usada como fallback."""
        get_cotacao, _ = get_service()

        async def run():
            with patch("modules.exchange.services._fetch_brasilapi", new=AsyncMock(side_effect=Exception("timeout"))), \
                 patch("modules.exchange.services._fetch_awesomeapi", new=AsyncMock(return_value=AWESOME_API_RESPONSE)):
                return await get_cotacao("USD")

        result = asyncio.run(run())
        assert result.fonte == "awesomeapi"
        assert result.moeda_codigo == "USD"
        assert abs(result.valor_compra - 5.71) < 0.001

    def test_both_apis_fail_raises_unavailable_error(self):
        """Quando ambas falham, ExchangeServiceUnavailableError é lançada."""
        get_cotacao, ExchangeServiceUnavailableError = get_service()

        async def run():
            with patch("modules.exchange.services._fetch_brasilapi", new=AsyncMock(side_effect=Exception("timeout"))), \
                 patch("modules.exchange.services._fetch_awesomeapi", new=AsyncMock(side_effect=Exception("connection error"))):
                return await get_cotacao("USD")

        with pytest.raises(ExchangeServiceUnavailableError):
            asyncio.run(run())

    def test_brasilapi_invalid_json_triggers_fallback(self):
        """JSON inválido / moeda ausente na BrasilAPI também aciona o fallback."""
        get_cotacao, _ = get_service()

        async def run():
            # Retorna lista sem a moeda solicitada
            with patch("modules.exchange.services._fetch_brasilapi", new=AsyncMock(return_value=[])), \
                 patch("modules.exchange.services._fetch_awesomeapi", new=AsyncMock(return_value=AWESOME_API_RESPONSE)):
                return await get_cotacao("USD")

        result = asyncio.run(run())
        assert result.fonte == "awesomeapi"
