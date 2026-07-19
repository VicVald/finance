# ADR-001: Arquitetura Geral de Agentes do Banco Ágil

**Status:** Aceito  
**Data:** 2026-07-19  
**Decididores:** Victor  

---

## Contexto

O Banco Ágil requer um sistema de atendimento ao cliente baseado em múltiplos agentes de IA especializados, cada um com escopo e responsabilidades bem definidas, conforme descrito no DESAFIO.md. A aplicação precisa ser testável, rastreável e demonstrável através de uma interface Streamlit.

---

## Decisão

Adotamos **LangGraph + LangChain** como framework principal para a construção e orquestração dos agentes, com as seguintes camadas:

### Agentes do Sistema

| Agente | Localização | Responsabilidade |
|--------|-------------|------------------|
| Router | `src/backend/core/agents/router_agent/` | Autenticação, handoff entre agentes, encerramento |
| Crédito | `src/backend/modules/credit/agents/` | Consulta de limite, solicitação de aumento |
| Entrevista de Crédito | `src/backend/modules/credit/agents/` | Entrevista financeira, recálculo de score |
| Câmbio | `src/backend/modules/exchange/agents/` | Consulta de cotação (BrasilAPI + AwesomeAPI) |

### Stack Técnica

- **Framework de Agentes:** LangGraph (grafo principal + subgraphs)
- **LLM Provider:** OpenRouter (modelo configurável via `.env`)
- **Interface:** Streamlit (`src/ui/`)
- **Dados:** CSVs locais em `src/backend/data/`
- **Rastreabilidade:** LangSmith (traces) + CSV de eventos (append por evento)

### Estrutura de Diretórios dos Agentes

```
src/backend/
├── core/
│   └── agents/
│       └── router_agent/       # Grafo raiz + orquestrador
├── modules/
│   ├── credit/
│   │   ├── agents/             # credit_agent + interview_agent
│   │   ├── models.py           # Pydantic models do domínio
│   │   └── services.py         # Lógica de negócio (CSV, score)
│   └── exchange/
│       ├── agents/             # exchange_agent
│       └── services.py         # Clientes BrasilAPI + AwesomeAPI
└── utils/
    └── pii.py                  # Utilitário central de masking PII
```

---

## Alternativas Consideradas

| Opção | Motivo de Rejeição |
|-------|-------------------|
| Google ADK | Menor ecossistema Python; sem suporte nativo a subgraphs |
| CrewAI | Paradigma de "crew" não mapeia bem para handoff dinâmico em runtime |
| LlamaIndex Workflows | Mais adequado para RAG, menos maduro para orquestração de múltiplos agentes |
| Implementação própria | Reinventar checkpointing, streaming e state management sem ganho para o projeto |

---

## Consequências

**Positivas:**
- LangGraph tem suporte nativo a subgraphs compilados com estado isolado por domínio
- Integração nativa com LangSmith para rastreabilidade sem configuração adicional
- Streaming de respostas suportado nativamente (`.stream()`, `.astream_events()`)
- Comunidade ativa e documentação extensa

**Negativas:**
- LangGraph tem curva de aprendizado mais íngreme que soluções mais simples
- Depende de API externa (OpenRouter) para o LLM; sem fallback local

---

## Referências

- [DESAFIO.md](../DESAFIO.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [ADR-002: Orquestração e Handoff](./ADR-002-orquestracao-e-handoff.md)
