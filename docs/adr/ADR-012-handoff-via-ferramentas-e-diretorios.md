# ADR-012: Handoff via Ferramentas de Grafo e Reorganização de Diretórios

**Status:** Aceito  
**Data:** 2026-07-21  
**Decididores:** Victor  

---

## Contexto

Previamente, a transição entre múltiplos agentes especializados (handoff) era realizada de forma baseada em tags textuais específicas retornadas nas mensagens da IA (ex: `[HANDOFF:credit]`). Isso exigia que o orquestrador (Router) realizasse varredura de strings e gerenciasse manualmente a transição de grafos de forma reativa a tokens de texto. 

Além disso, para melhorar a legibilidade e manutenibilidade do código, foi requisitado que os agentes especializados fossem organizados em pastas individuais semelhantes ao `router_agent` localizado em `core/agents/router_agent`.

---

## Decisão

1. **Handoff Baseado em Ferramentas (Tools)**:
   Substituímos o mapeamento de string textuais por ferramentas de handoff explícitas no padrão LangGraph:
   - `transfer_to_credit` (Triador → Agente de Crédito)
   - `transfer_to_exchange` (Triador → Agente de Câmbio)
   - `transfer_to_interview` (Triador/Agente de Crédito → Agente de Entrevista)
   - `transfer_to_triage` (Qualquer especialista → Triador)

   Estas ferramentas retornam objetos `Command(goto=..., update=...)` no padrão LangGraph para direcionar o fluxo de controle de forma nativa.

2. **Reorganização dos Agentes em Subdiretórios**:
   Organizamos os agentes em pastas próprias contendo arquivos correspondentes aos seus grafos, nós, estados e ferramentas específicas:
   - `modules/credit/agents/credit_agent/`
   - `modules/credit/agents/interview_agent/`
   - `modules/exchange/agents/exchange_agent/`

---

## Alternativas Consideradas

| Opção | Motivo de Rejeição |
|-------|-------------------|
| Manter tags textuais | Menos robusto e acoplado a parsing de strings do LLM. |
| Estrutura flat de subgraphs | Dificulta a separação de responsabilidades em times e legibilidade do código. |

---

## Consequências

**Positivas:**
- Handoff robusto e transparente usando ferramentas estruturadas com esquemas definidos.
- Separação total de responsabilidades em subpastas individuais.
- Testabilidade mais isolada de cada agente.

**Negativas:**
- Necessidade de atualizar referências de imports em múltiplos arquivos de teste e configurações.

---

## Referências

- [AGENTS.md](../../AGENTS.md)
- [ADR-001: Arquitetura Geral de Agentes](./ADR-001-arquitetura-geral-de-agentes.md)
- [ADR-002: Orquestração e Handoff](./ADR-002-orquestracao-e-handoff.md)
