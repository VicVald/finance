"""
TDD — Teste de encerramento de entrevista sem redirecionamento imediato para triagem/autenticação.
"""
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from modules.credit.agents.interview_agent.nodes import interview_node
from modules.credit.agents.interview_agent.state import InterviewState


def test_interview_node_ends_graph_on_completion():
    """Valida se o interview_node retorna goto='__end__' e active_agent='triage' após conclusão."""
    # Simula estado onde a ToolMessage com novo_score está presente
    state = InterviewState(
        cpf_hash="HASH_123",
        cliente_nome="João",
        messages=[
            ToolMessage(
                content='{"novo_score": 850, "atualizado": true}',
                tool_call_id="call_score_1"
            )
        ]
    )

    with patch("modules.credit.agents.interview_agent.nodes._build_llm") as mock_llm:
        mock_instance = mock_llm.return_value
        mock_instance.bind_tools.return_value.invoke.return_value = AIMessage(
            content="Sua entrevista foi concluída com sucesso! Seu novo score é 850."
        )

        res = interview_node(state)

        assert res.goto == "__end__"
        assert res.update["active_agent"] == "triage"
        assert res.update["entrevista_concluida"] is True
        assert res.update["novo_score"] == 850
