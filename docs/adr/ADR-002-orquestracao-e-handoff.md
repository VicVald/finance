# ADR-002: Orquestração e Handoff (Router + Subgraphs)

**Status:** Aceito  
**Data:** 2026-07-19  
**Decididores:** Victor  

---

## Contexto

O sistema possui múltiplos agentes especializados que precisam trocar o controle da conversa de forma fluida, sem que o cliente perceba a transição. O estado de cada agente deve ser preservado durante handoffs — se o cliente voltar a um agente anterior, seu contexto deve estar intacto.

---

## Decisão

### Padrão de Orquestração: Grafo Raiz com Subgraphs Compilados

O router é implementado como um **grafo raiz LangGraph** que contém, como nós, **subgraphs compilados** de cada domínio de agente.

```
RouterGraph (grafo raiz)
├── node: triage_node          ← lógica de autenticação
├── node: credit_subgraph      ← CreditGraph compilado
├── node: interview_subgraph   ← InterviewGraph compilado
├── node: exchange_subgraph    ← ExchangeGraph compilado
└── node: end_node             ← ferramenta de encerramento
```

### Mecanismo de Handoff

1. **O router analisa cada mensagem** antes de encaminhar ao agente ativo, verificando se há **intenção de mudança de domínio**.
2. Se detectar intenção de mudança:
   - Preserva o estado do agente atual (congelado no estado do router)
   - Atualiza `active_agent` no estado global
   - Encaminha a mensagem para o novo subgraph
3. Se não houver mudança:
   - Encaminha diretamente ao subgraph do `active_agent` corrente

### Regras de Handoff

| De | Para | Gatilho |
|----|------|---------|
| Router (triage) | Crédito | Intenção de consultar/alterar limite |
| Router (triage) | Câmbio | Intenção de cotação de moeda |
| Crédito | Entrevista de Crédito | Solicitação rejeitada + aceite via botão na UI ("Gostaria de fazer a entrevista") |
| Entrevista de Crédito | Crédito | Entrevista concluída |
| Qualquer | Encerramento | Intenção explícita de encerrar |

### Transparência para o Cliente

Os handoffs são **implícitos**: os agentes não informam ao cliente que estão "transferindo". A experiência é de um único assistente com múltiplas habilidades.

### Ferramenta de Encerramento

O router expõe uma `end_conversation_tool` que:
- Seta `is_conversation_ended = True` no estado global
- Registra o evento no CSV de rastreabilidade
- Encerra o loop do grafo (`END`)

---

## Estrutura de Cada Subgraph

Cada módulo (`credit`, `exchange`) implementa internamente:

```
modules/<domain>/
├── agents/
│   ├── graph.py        # Definição do StateGraph do domínio
│   ├── nodes.py        # Funções de nó (chamadas ao LLM + ferramentas)
│   └── state.py        # Pydantic BaseModel do estado local
├── models.py           # Modelos de domínio (entidades)
└── services.py         # Lógica de negócio (CSV, APIs externas)
```

---

## Alternativas Consideradas

| Opção | Motivo de Rejeição |
|-------|-------------------|
| Cada agente como grafo independente chamado via `invoke` | Perde o contexto da thread; não há checkpointing compartilhado |
| Router flat (todos os nós no mesmo grafo) | Acoplamento total; impossível isolar estado por domínio |

---

## Consequências

**Positivas:**
- Estado de cada domínio é completamente encapsulado e reutilizável
- O router pode ser testado independentemente dos subgraphs
- Fácil adição de novos agentes (novo módulo + novo nó no router)
- Compatível com streaming nativo do LangGraph

**Negativas:**
- Subgraphs compilados têm limitações em algumas versões do LangGraph (ex: streaming de eventos internos requer `astream_events`)
- A lógica de detecção de intenção no router adiciona uma chamada de LLM extra por mensagem

---

## Referências

- [ADR-001: Arquitetura Geral](./ADR-001-arquitetura-geral-de-agentes.md)
- [ADR-003: Gerenciamento de Estado](./ADR-003-gerenciamento-de-estado.md)
- [LangGraph Subgraphs](https://langchain-ai.github.io/langgraph/how-tos/subgraph/)
