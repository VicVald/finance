"""
Credit Subgraph — compilado sem checkpointer próprio.
O checkpointer é do grafo raiz (Router).
"""
from langgraph.graph import StateGraph, START, END

from modules.credit.agents.state import CreditState
from modules.credit.agents.nodes import credit_node, credit_tool_node


def build_credit_graph():
    builder = StateGraph(CreditState)

    builder.add_node("credit_node", credit_node)
    builder.add_node("credit_tool_node", credit_tool_node)

    builder.add_edge(START, "credit_node")
    builder.add_edge("credit_tool_node", "credit_node")

    return builder.compile()


compiled_credit_graph = build_credit_graph()
