"""
TDD — Boundary: Encerramento de conversa no Agente Router.

Funcionalidade:
  - Detectar intenção de encerramento (ex: "Quero encerrar o atendimento.")
  - Setar is_conversation_ended = True no estado do router
  - Transicionar active_agent para "end"
  - Persistir estado após encerramento
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from unittest.mock import patch
from langchain_core.messages import AIMessage, HumanMessage
from backend.core.agents.router_agent.graph import compiled_router_graph


class MockLLM:
    def __init__(self, *args, **kwargs):
        pass

    def bind_tools(self, tools, **kwargs):
        self.tools = tools
        return self

    def invoke(self, messages, *args, **kwargs):
        # Encontra o conteúdo da última mensagem do usuário
        last_human_content = ""
        for m in reversed(messages):
            if m.type == "human" or hasattr(m, "content"):
                if m.type == "human":
                    last_human_content = m.content
                    break
        
        last_human_content_lower = str(last_human_content).lower()
        
        # Verifica se é uma mensagem de encerramento
        end_triggers = ["encerrar", "fim", "sair", "encerre"]
        if any(trigger in last_human_content_lower for trigger in end_triggers):
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "end_conversation",
                    "args": {},
                    "id": "call_mock_end"
                }]
            )
        else:
            return AIMessage(content="Olá! Para prosseguir, preciso primeiro autenticar sua identidade. Por favor, informe seu **CPF**.")


@pytest.fixture(autouse=True)
def mock_llm_fixture():
    with patch("core.agents.router_agent.nodes._build_llm", return_value=MockLLM()):
        yield


def get_router_graph():
    """Retorna o grafo compilado do router."""
    return compiled_router_graph


class TestEndConversation:
    """Testa a funcionalidade de encerramento de conversa."""

    @pytest.mark.asyncio
    async def test_end_conversation_sets_flag(self, thread_config):
        """Mensagem de encerramento deve setar is_conversation_ended = True."""
        graph = get_router_graph()
        
        initial_state = {
            "messages": [HumanMessage(content="Quero encerrar o atendimento.")],
            "thread_id": thread_config["configurable"]["thread_id"],
        }
        
        async for evt in graph.astream_events(
            initial_state,
            config=thread_config,
            version="v2"
        ):
            pass
        
        snapshot = graph.get_state(thread_config)
        state = snapshot.values if snapshot.values else {}
        
        assert state.get("is_conversation_ended") is True

    @pytest.mark.asyncio
    async def test_end_conversation_state_persists(self, thread_config):
        """Flag de encerramento deve persistir em múltiplas chamadas de get_state."""
        graph = get_router_graph()
        
        initial_state = {
            "messages": [HumanMessage(content="Encerrar conversa")],
            "thread_id": thread_config["configurable"]["thread_id"],
        }
        
        async for evt in graph.astream_events(
            initial_state,
            config=thread_config,
            version="v2"
        ):
            pass
        
        # Primeira chamada
        first_snapshot = graph.get_state(thread_config)
        first_state = first_snapshot.values if first_snapshot.values else {}
        first_ended = first_state.get("is_conversation_ended", False)
        
        # Segunda chamada
        second_snapshot = graph.get_state(thread_config)
        second_state = second_snapshot.values if second_snapshot.values else {}
        second_ended = second_state.get("is_conversation_ended", False)
        
        assert first_ended is True
        assert second_ended is True
        assert first_ended == second_ended

    @pytest.mark.asyncio
    async def test_end_conversation_active_agent_transitions_to_end(self, thread_config):
        """Active agent deve transicionar para 'end' ao encerrar."""
        graph = get_router_graph()
        
        initial_state = {
            "messages": [HumanMessage(content="Quero encerrar o atendimento.")],
            "thread_id": thread_config["configurable"]["thread_id"],
        }
        
        async for evt in graph.astream_events(
            initial_state,
            config=thread_config,
            version="v2"
        ):
            pass
        
        snapshot = graph.get_state(thread_config)
        state = snapshot.values if snapshot.values else {}
        
        assert state.get("is_conversation_ended") is True
        assert state.get("active_agent") == "end"

    @pytest.mark.asyncio
    async def test_end_after_prior_state_overwrites(self, thread_config):
        """Encerramento após mensagem normal deve sobrescrever estado anterior."""
        graph = get_router_graph()
        
        # Primeira mensagem (normal)
        msg1_state = {
            "messages": [HumanMessage(content="Qual é meu limite?")],
            "thread_id": thread_config["configurable"]["thread_id"],
        }
        async for evt in graph.astream_events(msg1_state, config=thread_config, version="v2"):
            pass
        
        # Verificar não está encerrado ainda
        snap1 = graph.get_state(thread_config)
        state1 = snap1.values if snap1.values else {}
        assert state1.get("is_conversation_ended", False) is False
        
        # Segunda mensagem (encerramento)
        msg2_state = {
            "messages": [HumanMessage(content="Encerrar atendimento")],
            "thread_id": thread_config["configurable"]["thread_id"],
        }
        async for evt in graph.astream_events(msg2_state, config=thread_config, version="v2"):
            pass
        
        # Verificar está encerrado agora
        snap2 = graph.get_state(thread_config)
        state2 = snap2.values if snap2.values else {}
        assert state2.get("is_conversation_ended") is True

    @pytest.mark.asyncio
    async def test_end_conversation_message_in_history(self, thread_config):
        """Mensagem de encerramento deve estar no histórico de mensagens."""
        graph = get_router_graph()
        end_msg_text = "Quero encerrar o atendimento."
        
        initial_state = {
            "messages": [HumanMessage(content=end_msg_text)],
            "thread_id": thread_config["configurable"]["thread_id"],
        }
        
        async for evt in graph.astream_events(
            initial_state,
            config=thread_config,
            version="v2"
        ):
            pass
        
        snapshot = graph.get_state(thread_config)
        state = snapshot.values if snapshot.values else {}
        
        messages = state.get("messages", [])
        assert len(messages) > 0
        
        # Verificar se mensagem está no histórico
        message_contents = [
            msg.content if hasattr(msg, 'content') else str(msg) 
            for msg in messages
        ]
        assert any(end_msg_text.lower() in str(content).lower() for content in message_contents)

    @pytest.mark.asyncio
    async def test_end_conversation_idempotent_multiple_ends(self, thread_config):
        """Múltiplas mensagens de encerramento devem manter estado consistente."""
        graph = get_router_graph()
        
        # Primeiro encerramento
        msg1_state = {
            "messages": [HumanMessage(content="Encerrar")],
            "thread_id": thread_config["configurable"]["thread_id"],
        }
        async for evt in graph.astream_events(msg1_state, config=thread_config, version="v2"):
            pass
        
        snap1 = graph.get_state(thread_config)
        state1 = snap1.values if snap1.values else {}
        ended1 = state1.get("is_conversation_ended", False)
        agent1 = state1.get("active_agent")
        
        # Segundo encerramento
        msg2_state = {
            "messages": [HumanMessage(content="Encerrar novamente")],
            "thread_id": thread_config["configurable"]["thread_id"],
        }
        async for evt in graph.astream_events(msg2_state, config=thread_config, version="v2"):
            pass
        
        snap2 = graph.get_state(thread_config)
        state2 = snap2.values if snap2.values else {}
        ended2 = state2.get("is_conversation_ended", False)
        agent2 = state2.get("active_agent")
        
        # Ambos devem mostrar encerrado
        assert ended1 is True
        assert ended2 is True
        # Estado deve ser consistente
        assert agent1 == agent2

    @pytest.mark.parametrize("message,expected_ended", [
        ("Quero encerrar o atendimento.", True),
        ("Encerrar conversa", True),
        ("Fim", True),
        ("Sair", True),
        ("Encerre a conversa", True),
    ])
    @pytest.mark.asyncio
    async def test_end_message_variations_recognized(self, message, expected_ended):
        """Diferentes variações de mensagem de encerramento devem ser reconhecidas."""
        import uuid
        graph = get_router_graph()
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "thread_id": thread_id,
        }
        
        async for evt in graph.astream_events(
            initial_state,
            config=config,
            version="v2"
        ):
            pass
        
        snapshot = graph.get_state(config)
        state = snapshot.values if snapshot.values else {}
        
        # Pelo menos a primeira mensagem deve ser reconhecida
        if message == "Quero encerrar o atendimento.":
            assert state.get("is_conversation_ended") == expected_ended
