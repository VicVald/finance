# ADR-007: Agente de Câmbio — BrasilAPI + AwesomeAPI com Fallback

**Status:** Aceito  
**Data:** 2026-07-19  
**Decididores:** Victor  

---

## Contexto

O Agente de Câmbio precisa consultar cotações de moedas em tempo real. O desafio exige pelo menos duas fontes de dados distintas, com tratativa de falha e normalização dos dados em um modelo unificado.

---

## Decisão

### APIs Utilizadas

| Prioridade | API | Base URL | Autenticação |
|-----------|-----|----------|-------------|
| 1 (primária) | BrasilAPI | `https://brasilapi.com.br/api/taxas-cambio/v1` | Sem autenticação |
| 2 (fallback) | AwesomeAPI | `https://economia.awesomeapi.com.br/json/last` | Sem autenticação |

**Critério de Ativação do Fallback:**
- Timeout > 5 segundos
- HTTP status != 2xx
- JSON inválido ou campo esperado ausente
- Exceção de rede (`ConnectionError`, `Timeout`)

### Mapeamento de Moedas

Ambas as APIs usam códigos de par de moeda diferentes. O serviço de câmbio abstrai essa diferença:

| Moeda solicitada | BrasilAPI (`from`) | AwesomeAPI (par) |
|------------------|--------------------|------------------|
| Dólar (USD) | `USD` | `USD-BRL` |
| Euro (EUR) | `EUR` | `EUR-BRL` |
| Libra (GBP) | `GBP` | `GBP-BRL` |
| Bitcoin (BTC) | — (não suporta) | `BTC-BRL` |

### Modelo de Dados Unificado

```python
# modules/exchange/models.py
from pydantic import BaseModel
from datetime import datetime

class CotacaoResult(BaseModel):
    moeda_codigo: str           # Ex: "USD"
    moeda_nome: str             # Ex: "Dólar Americano"
    valor_compra: float         # Em BRL
    valor_venda: float          # Em BRL
    timestamp: datetime         # Momento da consulta
    fonte: str                  # "brasilapi" ou "awesomeapi"
    variacao_pct: float | None  # Variação percentual (quando disponível)
```

### Tratamento de Dados por API

**BrasilAPI (`/api/taxas-cambio/v1/{data}`):**

> ⚠️ A BrasilAPI de taxas de câmbio retorna dados do Banco Central com 1 dia de defasagem. Para cotação em tempo real, deve-se usar a data de hoje e verificar se o campo `cotacaoCompra` está presente.

```python
# Resposta esperada (array)
[
  {
    "paridadeCompra": 1,
    "paridadeVenda": 1,
    "cotacaoCompra": 5.7123,
    "cotacaoVenda": 5.7129,
    "dataHoraCotacao": "2026-07-18 13:05:00.0",
    "tipoBoletim": "Fechamento",
    "codigoMoeda": "USD",
    "nomeFormatado": "Dólar dos EUA"
  }
]
```

**Parsing BrasilAPI → CotacaoResult:**
```python
def parse_brasilapi(data: list[dict], moeda: str) -> CotacaoResult:
    entry = next((d for d in data if d["codigoMoeda"] == moeda), None)
    if not entry:
        raise ValueError(f"Moeda {moeda} não encontrada na BrasilAPI")
    return CotacaoResult(
        moeda_codigo=entry["codigoMoeda"],
        moeda_nome=entry["nomeFormatado"],
        valor_compra=float(entry["cotacaoCompra"]),
        valor_venda=float(entry["cotacaoVenda"]),
        timestamp=datetime.strptime(entry["dataHoraCotacao"], "%Y-%m-%d %H:%M:%S.%f"),
        fonte="brasilapi",
        variacao_pct=None
    )
```

**AwesomeAPI (`/json/last/{par}`):**

```python
# Resposta esperada (dict com chave = par sem hífen)
{
  "USDBRL": {
    "code": "USD",
    "codein": "BRL",
    "name": "Dólar Americano/Real Brasileiro",
    "high": "5.7200",
    "low": "5.6900",
    "varBid": "0.0150",
    "pctChange": "0.26",
    "bid": "5.7100",   # compra
    "ask": "5.7150",   # venda
    "timestamp": "1721390400",
    "create_date": "2026-07-19 13:00:00"
  }
}
```

**Parsing AwesomeAPI → CotacaoResult:**
```python
def parse_awesomeapi(data: dict, moeda: str) -> CotacaoResult:
    par_key = f"{moeda}BRL"
    entry = data.get(par_key)
    if not entry:
        raise ValueError(f"Par {par_key} não encontrado na AwesomeAPI")
    return CotacaoResult(
        moeda_codigo=moeda,
        moeda_nome=entry["name"].split("/")[0],
        valor_compra=float(entry["bid"]),
        valor_venda=float(entry["ask"]),
        timestamp=datetime.fromtimestamp(int(entry["timestamp"])),
        fonte="awesomeapi",
        variacao_pct=float(entry["pctChange"]) if entry.get("pctChange") else None
    )
```

### Fluxo de Chamada com Fallback

```python
# modules/exchange/services.py
async def get_cotacao(moeda: str) -> CotacaoResult:
    # 1. Tentativa com BrasilAPI
    try:
        data = await _fetch_brasilapi(moeda)
        return parse_brasilapi(data, moeda)
    except Exception as e_brasil:
        log.warning(f"BrasilAPI falhou para {moeda}: {e_brasil}")
    
    # 2. Fallback: AwesomeAPI
    try:
        data = await _fetch_awesomeapi(moeda)
        return parse_awesomeapi(data, moeda)
    except Exception as e_awesome:
        log.error(f"AwesomeAPI também falhou para {moeda}: {e_awesome}")
    
    # 3. Ambas falharam
    raise ExchangeServiceUnavailableError(
        f"Não foi possível obter cotação para {moeda}. "
        "Tente novamente em instantes."
    )
```

### Detecção Automática de Moeda pelo Agente

O agente de câmbio usa o LLM para extrair a moeda da mensagem do usuário antes de chamar a ferramenta:

```python
# Ferramenta LangGraph do agente de câmbio
@tool
async def consultar_cotacao(moeda: str) -> str:
    """
    Consulta a cotação de uma moeda em relação ao Real (BRL).
    Aceita: USD, EUR, GBP, BTC, ARS, etc.
    """
    try:
        result = await get_cotacao(moeda.upper())
        return (
            f"Cotação do {result.moeda_nome} ({result.moeda_codigo}):\n"
            f"• Compra: R$ {result.valor_compra:.4f}\n"
            f"• Venda:  R$ {result.valor_venda:.4f}\n"
            f"• Fonte: {result.fonte} | {result.timestamp.strftime('%d/%m/%Y %H:%M')}"
        )
    except ExchangeServiceUnavailableError as e:
        return str(e)
```

---

## Alternativas Consideradas

| Opção | Motivo de Rejeição |
|-------|-------------------|
| Apenas uma API | Sem resiliência; ponto único de falha |
| Tavily / SerpAPI | Dependência de chave de API paga; overhead de web scraping para dado estruturado |
| Yahoo Finance API | API não-oficial; quebras frequentes |
| Cache de cotação | Fora do escopo para demo; cotação deve ser sempre em tempo real |

---

## Consequências

**Positivas:**
- Zero dependência de chave de API para ambas as fontes (BrasilAPI e AwesomeAPI são públicas)
- Modelo unificado `CotacaoResult` desacopla a lógica do agente dos detalhes de cada API
- Fallback automático transparente para o usuário
- Suporte fácil a novas moedas (adicionar ao mapeamento)

**Negativas:**
- BrasilAPI de câmbio usa dados do BACEN com defasagem de ~1 dia útil (não é cotação em tempo real de mercado)
- AwesomeAPI é free tier sem SLA garantido
- Moedas exóticas podem não estar disponíveis em ambas as APIs simultaneamente

---

## Referências

- [ADR-002: Orquestração e Handoff](./ADR-002-orquestracao-e-handoff.md)
- [BrasilAPI - Taxas de Câmbio](https://brasilapi.com.br/docs#tag/Taxas-de-Câmbio)
- [AwesomeAPI - Economia](https://docs.awesomeapi.com.br/api-de-moedas)
