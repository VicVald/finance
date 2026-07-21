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

---

## Consequências

**Positivas:**
- Rastreabilidade dupla: granularidade técnica (LangSmith)
- Append thread-safe com lock de arquivo para evitar corrompimento em sessões paralelas
- LangSmith agrupa por `tags` e `metadata`, permitindo filtrar por agente no dashboard

**Negativas:**
- LangSmith requer chave de API externa

---

## Referências

- [ADR-003: Gerenciamento de Estado](./ADR-003-gerenciamento-de-estado.md)
- [ADR-005: Segurança e PII](./ADR-005-seguranca-e-pii.md)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
