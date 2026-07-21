"""
Credit Subgraph — compilado sem checkpointer próprio.
O checkpointer é do grafo raiz (Router).
"""
from typing import Annotated, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from modules.credit.agents.credit_agent.state import CreditState
from modules.credit.agents.credit_agent.nodes import credit_node, credit_tool_node


class CreditInputSchema(BaseModel):
    """
    Schema de entrada para mapear campos do RouterState para o CreditState do subgraph.
    """
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    authenticated_cpf_hash: Optional[str] = None
    cliente_nome: Optional[str] = None
    cliente_limite_atual: Optional[float] = None
    cliente_score_atual: Optional[int] = None
    entrevista_concluida: bool = False


def _setup_credit_node(state: CreditState) -> dict:
    """Mapeia campos herdados do RouterState para o CreditState local."""
    update = {}
    if not state.cliente_cpf_hash and getattr(state, "authenticated_cpf_hash", None):
        update["cliente_cpf_hash"] = getattr(state, "authenticated_cpf_hash", None)
    if state.limite_atual is None and getattr(state, "cliente_limite_atual", None) is not None:
        update["limite_atual"] = getattr(state, "cliente_limite_atual", None)
    
    # Sempre atualiza o score_atual para ter a versão mais recente após a entrevista
    parent_score = getattr(state, "cliente_score_atual", None)
    if parent_score is not None:
        update["score_atual"] = parent_score
        
    # Mapeia se a entrevista foi concluída
    parent_interview_done = getattr(state, "entrevista_concluida", False)
    if parent_interview_done:
        update["entrevista_concluida"] = parent_interview_done
        
    return update


def build_credit_graph():
    builder = StateGraph(CreditState, input=CreditInputSchema)

    builder.add_node("setup_node", _setup_credit_node)
    builder.add_node("credit_node", credit_node)
    builder.add_node("credit_tool_node", credit_tool_node)

    builder.add_edge(START, "setup_node")
    builder.add_edge("setup_node", "credit_node")
    builder.add_edge("credit_tool_node", "credit_node")

    return builder.compile()


compiled_credit_graph = build_credit_graph()
