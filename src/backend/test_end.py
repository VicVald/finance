import asyncio
from core.agents.router_agent.graph import compiled_router_graph

async def main():
    config = {"configurable": {"thread_id": "test_end_1"}}
    # Mock human saying they want to end
    async for evt in compiled_router_graph.astream_events(
        {"messages": [("user", "Quero encerrar o atendimento.")]}, 
        config, 
        version="v2"
    ):
        pass
    snap = compiled_router_graph.get_state(config)
    print("final state:", snap.values.get("is_conversation_ended"))

asyncio.run(main())
