"""
Pytest configuration and fixtures for Banco Ágil tests.
"""

import os
# Ensure API keys are present for client instantiation in CI/CD environments
os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "dummy_openrouter_api_key_for_testing")
os.environ["LANGSMITH_TRACING"] = "false"

import pytest
import sys
from pathlib import Path
import asyncio
import uuid

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_api_key: mark test as requiring a real OpenRouter API key"
    )

def pytest_runtest_setup(item):
    if any(mark.name == "requires_api_key" for mark in item.iter_markers()):
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        # If the key is empty or contains 'dummy', skip the test
        if not api_key or "dummy" in api_key.lower():
            pytest.skip("Test skipped because a real OPENROUTER_API_KEY is not configured.")

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
