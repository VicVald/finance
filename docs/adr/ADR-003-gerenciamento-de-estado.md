# ADR-003: Gerenciamento de Estado (Pydantic BaseModel + MemorySaver)

**Status:** Aceito  
**Data:** 2026-07-19  
**Decididores:** Victor  

---

## Contexto

O LangGraph requer um esquema de estado para cada grafo. O projeto tem dois níveis de estado:
1. **Estado Global** do router (orquestrador)
2. **Estado Local** de cada subgraph de domínio

Precisamos de validação de dados, documentação clara de campos e compatibilidade com o serializer do LangGraph.

---

## Decisão

### Pydantic BaseModel para Todos os Estados

Em vez do `TypedDict` padrão do LangGraph, usamos **Pydantic `BaseModel`** para todos os estados.

> **Nota técnica:** O LangGraph aceita Pydantic v2 `BaseModel` diretamente como schema de estado a partir da versão 0.2.x. O reducer padrão é substituição total do campo, salvo quando anotado com `Annotated[list, add_messages]`.

### Estado Global do Router

```python
# core/agents/router_agent/state.py
from pydantic import BaseModel, Field
from typing import Literal, Optional
from langchain_core.messages import BaseMessage

class AuthState(BaseModel):
    is_authenticated: bool = False
    auth_attempts: int = 0           # máximo 3 tentativas
    authenticated_cpf_hash: Optional[str] = None  # hash SHA-256 com salt

class RouterState(BaseModel):
    messages: list[BaseMessage] = Field(default_factory=list)
    
    # Controle de agente ativo
    active_agent: Literal["triage", "credit", "interview", "exchange", "end"] = "triage"
    
    # Autenticação
    auth: AuthState = Field(default_factory=AuthState)
    
    # Controle de sessão/encerramento
    is_conversation_ended: bool = False
    
    # IDs de rastreabilidade
    session_id: str = ""    # uma mensagem = uma session
    thread_id: str = ""     # uma conversa = uma thread
    
    # Snapshot dos estados dos subgraphs (preservados no handoff)
    credit_state_snapshot: Optional[dict] = None
    exchange_state_snapshot: Optional[dict] = None
    interview_state_snapshot: Optional[dict] = None
```

### Estado Local de Cada Subgraph

Cada domínio define seu próprio `BaseModel`:

```python
# modules/credit/agents/state.py
class CreditState(BaseModel):
    messages: list[BaseMessage] = Field(default_factory=list)
    cliente_cpf_hash: Optional[str] = None
    limite_atual: Optional[float] = None
    score_atual: Optional[int] = None
    solicitacao_pendente: Optional[float] = None  # novo limite desejado

# modules/exchange/agents/state.py
class ExchangeState(BaseModel):
    messages: list[BaseMessage] = Field(default_factory=list)
    ultima_moeda_consultada: Optional[str] = None
    ultima_cotacao: Optional[dict] = None
    api_fonte: Optional[Literal["brasilapi", "awesomeapi"]] = None
```

### Persistência: MemorySaver

- Usa-se `MemorySaver` do LangGraph como checkpointer do grafo raiz
- **Sem persistência em disco:** ao reiniciar a aplicação, todos os estados são perdidos
- Adequado para o ambiente de testes do desafio
- Para promover para produção, basta trocar por `SqliteSaver` ou `PostgresSaver` sem alterar a lógica de grafos

### Modelo de Sessão e Thread

| Conceito | Escopo | Geração do ID |
|----------|--------|---------------|
| `thread_id` | Uma conversa completa (do início ao encerramento) | UUID gerado ao abrir o chat ou ao "reiniciar conversa" |
| `session_id` | Uma mensagem individual dentro da thread | UUID gerado a cada mensagem enviada |

> Assim: `1 thread → N sessions`, `1 session → 1 agent ativo`

O `thread_id` é o identificador usado no `config` do LangGraph:
```python
config = {"configurable": {"thread_id": thread_id}}
graph.invoke(state, config=config)
```

---

## Alternativas Consideradas

| Opção | Motivo de Rejeição |
|-------|-------------------|
| `TypedDict` padrão do LangGraph | Sem validação de dados; documentação inferida apenas por anotações de tipo |
| Estado único global compartilhado | Acoplamento entre domínios; dificulta isolamento de testes |
| PostgresSaver | Overhead desnecessário para ambiente de testes; sem ganho demonstrável no desafio |

---

## Consequências

**Positivas:**
- Validação automática de campos com Pydantic (ex: `auth_attempts` nunca negativo)
- Documentação dos campos via `Field(description=...)` acessível via schema JSON
- Estado de cada domínio é completamente encapsulado e independente
- Fácil snapshot/restore do estado de subgraphs durante handoffs

**Negativas:**
- Pydantic BaseModel como estado LangGraph requer atenção ao modo de serialização (`.model_dump()` para persistência)
- `MemorySaver` perde todos os estados ao reiniciar o processo Streamlit

---

## Referências

- [ADR-002: Orquestração e Handoff](./ADR-002-orquestracao-e-handoff.md)
- [LangGraph State Management](https://langchain-ai.github.io/langgraph/concepts/low_level/#state)
- [LangGraph Pydantic State](https://langchain-ai.github.io/langgraph/how-tos/state-model/)
