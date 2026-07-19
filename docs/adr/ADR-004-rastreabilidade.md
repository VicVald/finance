# ADR-004: Rastreabilidade (LangSmith + CSV por Evento)

**Status:** Aceito  
**Data:** 2026-07-19  
**Decididores:** Victor  

---

## Contexto

O sistema precisa de rastreabilidade para fins de auditoria, depuração e demonstração do desafio técnico. Dois mecanismos são requeridos:
1. **LangSmith** — rastreamento de traces de LLM (runs, spans, tokens)
2. **CSV local** — log de eventos de alto nível para auditoria de fluxo de negócio

---

## Decisão

### LangSmith

**Configuração:**
- Ativado via variáveis de ambiente no `.env`:
  ```
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_API_KEY=<chave>
  LANGCHAIN_PROJECT=banco-agil
  ```
- Cada invocação do grafo raiz gera automaticamente um **run** no LangSmith com o `thread_id` como metadado
- O `session_id` é passado como `metadata` no `config` da invocação para agrupar runs por mensagem

**Tagging de Agentes:**
```python
config = {
    "configurable": {"thread_id": thread_id},
    "metadata": {
        "session_id": session_id,
        "active_agent": active_agent,
        "thread_id": thread_id,
    },
    "tags": [active_agent, "banco-agil"]
}
```

### CSV de Rastreabilidade de Eventos

**Arquivo:** `src/backend/data/trace_eventos.csv`

**Estratégia:** Append por evento (uma linha por evento de negócio relevante)

**Schema:**

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `timestamp` | ISO 8601 | Momento do evento |
| `thread_id` | UUID | Identificador da conversa |
| `session_id` | UUID | Identificador da mensagem |
| `agent` | string | Agente ativo no momento do evento |
| `tipo_evento` | string | Tipo do evento (ver tabela abaixo) |
| `payload_resumido` | string (JSON) | Dados relevantes do evento (CPF mascarado, valores, status) |

**Tipos de Evento:**

| `tipo_evento` | Quando é registrado |
|---------------|---------------------|
| `CONVERSA_INICIADA` | Chat aberto pelo usuário |
| `AUTH_TENTATIVA` | Usuário fornece CPF + data de nascimento |
| `AUTH_SUCESSO` | Autenticação bem-sucedida |
| `AUTH_FALHA` | Autenticação falhou (com contador de tentativas) |
| `AUTH_BLOQUEIO` | Terceira falha consecutiva, conversa encerrada |
| `HANDOFF` | Transição entre agentes |
| `MENSAGEM_ENVIADA` | Cada mensagem do usuário |
| `MENSAGEM_RECEBIDA` | Cada resposta do agente |
| `SOLICITACAO_CREDITO` | Pedido de aumento de limite registrado |
| `SCORE_ATUALIZADO` | Score recalculado após entrevista |
| `COTACAO_CONSULTADA` | Consulta de câmbio realizada |
| `CONVERSA_ENCERRADA` | Encerramento pelo agente ou usuário |

**Implementação:**

```python
# utils/tracer.py
import csv, json
from pathlib import Path
from datetime import datetime, timezone

TRACE_CSV_PATH = Path("src/backend/data/trace_eventos.csv")

def log_event(thread_id: str, session_id: str, agent: str, 
              tipo_evento: str, payload: dict):
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thread_id": thread_id,
        "session_id": session_id,
        "agent": agent,
        "tipo_evento": tipo_evento,
        "payload_resumido": json.dumps(payload, ensure_ascii=False)
    }
    write_header = not TRACE_CSV_PATH.exists()
    with open(TRACE_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)
```

### Relação entre Sessão e Thread

```
Thread (conversa)
 ├── session_id_1 → agent: "triage"     → mensagem 1
 ├── session_id_2 → agent: "triage"     → mensagem 2 (autenticação)
 ├── session_id_3 → agent: "credit"     → após handoff
 ├── session_id_4 → agent: "credit"     → consulta de limite
 └── session_id_5 → agent: "exchange"   → após handoff
```

---

## Alternativas Consideradas

| Opção | Motivo de Rejeição |
|-------|-------------------|
| Apenas LangSmith | LangSmith rastreia runs de LLM, não eventos de negócio (handoffs, auth, score) |
| Batch no encerramento | Perde dados se a sessão cair ou o usuário fechar o navegador |
| Banco de dados SQLite | Overhead de schema e migração desnecessário para o escopo do desafio |

---

## Consequências

**Positivas:**
- Rastreabilidade dupla: granularidade técnica (LangSmith) + granularidade de negócio (CSV)
- O CSV é human-readable e pode ser aberto diretamente em Excel/Google Sheets para demonstração
- Append thread-safe com lock de arquivo para evitar corrompimento em sessões paralelas
- LangSmith agrupa por `tags` e `metadata`, permitindo filtrar por agente no dashboard

**Negativas:**
- Dois mecanismos de rastreabilidade para manter sincronizados
- O CSV de eventos cresce indefinidamente (sem rotação automática — aceitável para testes)
- LangSmith requer chave de API externa

---

## Referências

- [ADR-003: Gerenciamento de Estado](./ADR-003-gerenciamento-de-estado.md)
- [ADR-005: Segurança e PII](./ADR-005-seguranca-e-pii.md)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
