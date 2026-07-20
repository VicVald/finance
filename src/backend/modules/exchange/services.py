"""
Serviço de câmbio: BrasilAPI (primária) + AwesomeAPI (fallback).

Modelo unificado CotacaoResult abstrai as diferenças entre as APIs.
Usa httpx.AsyncClient com timeout de 5s.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
import httpx

from core.config import settings

log = logging.getLogger(__name__)


class ExchangeServiceUnavailableError(Exception):
    """Levantada quando ambas as APIs de câmbio falham."""
    pass


class CotacaoResult(BaseModel):
    """Modelo unificado de cotação de moeda."""
    moeda_codigo: str
    moeda_nome: str
    valor_compra: float
    valor_venda: float
    timestamp: datetime
    fonte: str  # "brasilapi" ou "awesomeapi"
    variacao_pct: Optional[float] = None


# ─── Fetchers ─────────────────────────────────────────────────────────────────

async def _fetch_brasilapi(moeda: str) -> list[dict]:
    """Busca cotação na BrasilAPI (dados do BACEN)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"https://brasilapi.com.br/api/taxas-cambio/v1/{today}"
    async with httpx.AsyncClient(timeout=settings.EXCHANGE_TIMEOUT_SECONDS) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def _fetch_awesomeapi(moeda: str) -> dict:
    """Busca cotação na AwesomeAPI."""
    par = f"{moeda.upper()}-BRL"
    url = f"https://economia.awesomeapi.com.br/json/last/{par}"
    async with httpx.AsyncClient(timeout=settings.EXCHANGE_TIMEOUT_SECONDS) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


# ─── Parsers ──────────────────────────────────────────────────────────────────

def parse_brasilapi(data: list[dict], moeda: str) -> CotacaoResult:
    moeda_upper = moeda.upper()
    entry = next((d for d in data if d.get("codigoMoeda") == moeda_upper), None)
    if not entry:
        raise ValueError(f"Moeda {moeda_upper} não encontrada na BrasilAPI")
    if not entry.get("cotacaoCompra"):
        raise ValueError(f"Cotação de compra ausente para {moeda_upper} na BrasilAPI")
    return CotacaoResult(
        moeda_codigo=entry["codigoMoeda"],
        moeda_nome=entry["nomeFormatado"],
        valor_compra=float(entry["cotacaoCompra"]),
        valor_venda=float(entry["cotacaoVenda"]),
        timestamp=datetime.strptime(entry["dataHoraCotacao"], "%Y-%m-%d %H:%M:%S.%f"),
        fonte="brasilapi",
        variacao_pct=None,
    )


def parse_awesomeapi(data: dict, moeda: str) -> CotacaoResult:
    par_key = f"{moeda.upper()}BRL"
    entry = data.get(par_key)
    if not entry:
        raise ValueError(f"Par {par_key} não encontrado na AwesomeAPI")
    return CotacaoResult(
        moeda_codigo=moeda.upper(),
        moeda_nome=entry["name"].split("/")[0],
        valor_compra=float(entry["bid"]),
        valor_venda=float(entry["ask"]),
        timestamp=datetime.fromtimestamp(int(entry["timestamp"]), tz=timezone.utc),
        fonte="awesomeapi",
        variacao_pct=float(entry["pctChange"]) if entry.get("pctChange") else None,
    )


# ─── Serviço principal com fallback ──────────────────────────────────────────

async def get_cotacao(moeda: str) -> CotacaoResult:
    """
    Obtém cotação de uma moeda contra BRL.
    Tenta BrasilAPI primeiro; fallback automático para AwesomeAPI.

    Raises:
        ExchangeServiceUnavailableError: se ambas as APIs falharem.
    """
    # 1. Tentativa com BrasilAPI
    try:
        data = await _fetch_brasilapi(moeda)
        return parse_brasilapi(data, moeda)
    except Exception as e:
        log.warning(f"BrasilAPI falhou para {moeda}: {e}")

    # 2. Fallback: AwesomeAPI
    try:
        data = await _fetch_awesomeapi(moeda)
        return parse_awesomeapi(data, moeda)
    except Exception as e:
        log.error(f"AwesomeAPI também falhou para {moeda}: {e}")

    # 3. Ambas falharam
    raise ExchangeServiceUnavailableError(
        f"Não foi possível obter a cotação de {moeda.upper()}. "
        "Tente novamente em instantes."
    )
