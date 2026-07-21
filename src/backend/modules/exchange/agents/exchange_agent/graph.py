"""
Exchange Subgraph — compilado sem checkpointer próprio.
"""
from langgraph.graph import StateGraph, START, END

from modules.exchange.agents.exchange_agent.state import ExchangeState
from modules.exchange.agents.exchange_agent.nodes import exchange_node, exchange_tool_node


def build_exchange_graph():
    builder = StateGraph(ExchangeState)

    builder.add_node("exchange_node", exchange_node)
    builder.add_node("exchange_tool_node", exchange_tool_node)

    builder.add_edge(START, "exchange_node")
    builder.add_edge("exchange_tool_node", "exchange_node")

    return builder.compile()


compiled_exchange_graph = build_exchange_graph()
