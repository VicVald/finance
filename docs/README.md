# /docs — Architecture Decision Records (ADRs)

Este diretório contém as decisões de arquitetura do **Banco Ágil**, documentadas no formato [MADR (Markdown ADR)](https://adr.github.io/madr/).

---

## Índice

| ADR | Título | Status |
|-----|--------|--------|
| [ADR-001](./ADR-001-arquitetura-geral-de-agentes.md) | Arquitetura Geral de Agentes | ✅ Aceito |
| [ADR-002](./ADR-002-orquestracao-e-handoff.md) | Orquestração e Handoff (Router + Subgraphs) | ✅ Aceito |
| [ADR-003](./ADR-003-gerenciamento-de-estado.md) | Gerenciamento de Estado (Pydantic + MemorySaver) | ✅ Aceito |
| [ADR-004](./ADR-004-rastreabilidade.md) | Rastreabilidade (LangSmith + CSV por Evento) | ✅ Aceito |
| [ADR-005](./ADR-005-seguranca-e-pii.md) | Segurança e PII (SHA-256 + Middleware) | ✅ Aceito |
| [ADR-006](./ADR-006-interface-streamlit.md) | Interface Streamlit do Banco Ágil | ✅ Aceito |
| [ADR-007](./ADR-007-agente-de-cambio.md) | Agente de Câmbio (BrasilAPI + AwesomeAPI Fallback) | ✅ Aceito |
| [ADR-008](./ADR-008-autenticacao-jwt.md) | Autenticação JWT com Access e Refresh Token | ✅ Aceito |

---

## Diagrama de Dependências entre ADRs

```
ADR-001 (Arquitetura Geral)
├── ADR-002 (Orquestração/Handoff)
│   └── ADR-003 (Gerenciamento de Estado)
├── ADR-004 (Rastreabilidade)
│   └── ADR-005 (Segurança/PII)
├── ADR-006 (Interface Streamlit)
├── ADR-007 (Agente de Câmbio)
└── ADR-008 (Autenticação JWT)
```

---

## Convenções

- **Status:** `Aceito` | `Proposto` | `Depreciado` | `Substituído por ADR-XXX`
- Cada ADR inclui: Contexto → Decisão → Alternativas → Consequências
- Código de exemplo nas ADRs é **pseudocódigo de referência** — a implementação real pode diferir em detalhes
