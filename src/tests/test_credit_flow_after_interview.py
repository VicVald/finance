"""
TDD — Testes do fluxo de crédito pós-entrevista e prevenção de handoff incorreto.
"""
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from langchain_core.messages import AIMessage, HumanMessage


class TestCreditFlowFixes:
    """Testa se o router força handoff para credit e se a IA pergunta por aumento pós-entrevista."""

    @patch("core.agents.router_agent.nodes._build_llm")
    def test_router_forces_credit_subgraph_even_if_llm_says_interview(self, mock_build_llm):
        """Mesmo que a IA do router mencione entrevista, a rota de crédito deve ser acionada."""
        from core.agents.router_agent.nodes import triage_node
        from core.agents.router_agent.state import RouterState

        mock_llm = mock_build_llm.return_value
        mock_llm.bind_tools.return_value.invoke.return_value = AIMessage(
            content="Vou direcioná-lo para a entrevista. [HANDOFF:interview]"
        )

        state = RouterState(
            is_authenticated=True,
            authenticated_cpf_hash="HASH_123",
            cliente_nome="João",
            active_agent="triage",
        )

        res = triage_node(state)
        # Deve ir para credit_subgraph, não interview_subgraph
        assert res.goto == "credit_subgraph"
        assert res.update["active_agent"] == "credit"

    @patch("modules.credit.agents.nodes._build_llm")
    def test_credit_node_asks_for_limit_increase_after_interview_done(self, mock_build_llm):
        """Após [INTERVIEW_DONE], o nó de crédito deve pedir proativamente a solicitação de aumento de limite."""
        from modules.credit.agents.nodes import credit_node
        from modules.credit.agents.state import CreditState

        mock_llm = mock_build_llm.return_value
        mock_llm.bind_tools.return_value.invoke.return_value = AIMessage(
            content="Seu novo score é 899. Gostaria de solicitar um aumento de limite de crédito agora?"
        )

        history = [
            HumanMessage(content="quero aumentar meu limite"),
            AIMessage(content="Entrevista concluída. [INTERVIEW_DONE]"),
        ]
        state = CreditState(
            messages=history,
            cliente_cpf_hash="HASH_123",
            cliente_nome="João",
            score_atual=899,
            limite_atual=5000.0,
        )

        res = credit_node(state)
        assert res.goto == "__end__"
        assert "aumento de limite" in res.update["messages"][0].content.lower()
