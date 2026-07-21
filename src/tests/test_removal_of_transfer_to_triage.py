"""
TDD — Testes para garantir a remoção de transfer_to_triage de todos os agentes especialistas.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest


def test_transfer_to_triage_not_in_credit_tools():
    """Garante que transfer_to_triage não está na lista de tools do agente de crédito."""
    from modules.credit.agents.credit_agent.nodes import CREDIT_TOOLS
    tool_names = [t.name for t in CREDIT_TOOLS]
    assert "transfer_to_triage" not in tool_names


def test_transfer_to_triage_not_in_exchange_tools():
    """Garante que transfer_to_triage não está na lista de tools do agente de câmbio."""
    from modules.exchange.agents.exchange_agent.nodes import EXCHANGE_TOOLS
    tool_names = [t.name for t in EXCHANGE_TOOLS]
    assert "transfer_to_triage" not in tool_names


def test_transfer_to_triage_not_in_interview_tools():
    """Garante que transfer_to_triage não está na lista de tools do agente de entrevista."""
    from modules.credit.agents.interview_agent.nodes import INTERVIEW_TOOLS
    tool_names = [t.name for t in INTERVIEW_TOOLS]
    assert "transfer_to_triage" not in tool_names
