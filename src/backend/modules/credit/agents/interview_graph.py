"""
Interview Subgraph — compilado sem checkpointer próprio.
O checkpointer é do grafo raiz (Router).
"""
from typing import Annotated, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from modules.credit.agents.interview_state import InterviewState
from modules.credit.agents.interview_nodes import interview_node, interview_tool_node


class InterviewInputSchema(BaseModel):
    """
    Schema de entrada que mapeia campos do RouterState para o InterviewState.
    O LangGraph usa este schema para injetar dados do grafo pai no subgraph.
    """
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    # authenticated_cpf_hash no router → cpf_hash no subgraph
    authenticated_cpf_hash: Optional[str] = None
    cliente_nome: Optional[str] = None


def _setup_interview_node(state: InterviewState) -> dict:
    """Mapeia campos herdados do RouterState para o InterviewState local."""
    update = {}
    # authenticated_cpf_hash chega via InterviewInputSchema e é copiado para cpf_hash
    if not state.cpf_hash and hasattr(state, "authenticated_cpf_hash"):
        update["cpf_hash"] = getattr(state, "authenticated_cpf_hash", None)
    return update


def build_interview_graph():
    builder = StateGraph(InterviewState, input=InterviewInputSchema)

    builder.add_node("setup_node", _setup_interview_node)
    builder.add_node("interview_node", interview_node)
    builder.add_node("interview_tool_node", interview_tool_node)

    builder.add_edge(START, "setup_node")
    builder.add_edge("setup_node", "interview_node")
    builder.add_edge("interview_tool_node", "interview_node")

    return builder.compile()


compiled_interview_graph = build_interview_graph()
