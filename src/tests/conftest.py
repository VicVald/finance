"""
Pytest configuration and fixtures for Banco Ágil tests.
"""

import pytest
import sys
from pathlib import Path
import asyncio
import uuid

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def thread_id():
    """Generate a unique thread ID for each test."""
    return str(uuid.uuid4())


@pytest.fixture
def thread_config(thread_id):
    """Fixture providing a test thread configuration."""
    return {"configurable": {"thread_id": thread_id}}


@pytest.fixture
def authenticated_thread_config(thread_config):
    """Fixture que fornece uma configuração de thread já autenticada com João Silva."""
    from core.agents.router_agent.graph import compiled_router_graph
    state_values = {
        "is_authenticated": True,
        "authenticated_cpf_hash": "e491adad6a27ca8e5dd9ebc05a670178e4c01e7572e0bfe9557fe7a6f96c048a", # João Silva
        "cliente_nome": "João Silva",
        "cliente_limite_atual": 5000.0,
        "cliente_score_atual": 800,
        "auth_attempts": 0,
    }
    compiled_router_graph.update_state(thread_config, state_values)
    return thread_config
