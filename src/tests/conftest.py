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
