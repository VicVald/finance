"""
Grafo raiz do Router Agent (orquestrador principal).

Topologia:
  START → triage_node → [credit_subgraph | exchange_subgraph | interview_subgraph | END]
  Subgraphs → triage_node (retorno pós-handoff)

Compilado com MemorySaver para persistência de estado por thread_id.
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from core.agents.router_agent.state import RouterState
from core.agents.router_agent.nodes import triage_node


def build_router_graph():
    """Constrói e retorna o grafo raiz compilado."""
    from modules.credit.agents.graph import compiled_credit_graph
    from modules.credit.agents.interview_graph import compiled_interview_graph
    from modules.exchange.agents.graph import compiled_exchange_graph

    builder = StateGraph(RouterState)

    # Nó de triagem (LLM + tools)
    builder.add_node("triage_node", triage_node)

    # Subgraphs como nós do grafo raiz
    builder.add_node("credit_subgraph", compiled_credit_graph)
    builder.add_node("interview_subgraph", compiled_interview_graph)
    builder.add_node("exchange_subgraph", compiled_exchange_graph)

    # Ponto de entrada
    builder.add_edge(START, "triage_node")

    # Retorno dos subgraphs para o triage
    builder.add_edge("credit_subgraph", "triage_node")
    builder.add_edge("interview_subgraph", "triage_node")
    builder.add_edge("exchange_subgraph", "triage_node")

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# Instância singleton — criada uma vez ao importar o módulo
compiled_router_graph = build_router_graph()
