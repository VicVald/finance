"""
TDD — Teste de Classificação Dinâmica de Intenção e Roteamento Pós-Autenticação.
Garante que:
1. Cliente autenticado NUNCA receba pedido de CPF/autenticação.
2. Troca de assunto (ex: Crédito -> Câmbio) funcione via triage_node.
3. Mensagens contínuas/saudações mantêm o agente ativo atual.
"""
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from core.agents.router_agent.nodes import triage_node
from core.agents.router_agent.state import RouterState


class TestDynamicIntentionRouting:
    """Testa se o triage_node classifica a intenção de clientes autenticados sem pedir reautenticação."""

    @patch("core.agents.router_agent.nodes._build_llm")
    def test_authenticated_user_asking_exchange_while_in_credit_switches_to_exchange(self, mock_build_llm):
        """Cliente autenticado em crédito pede cotação -> triage_node redireciona para exchange_subgraph."""
        mock_llm = mock_build_llm.return_value
        mock_llm.bind_tools.return_value.invoke.return_value = AIMessage(
            content="",
            tool_calls=[{
                "name": "transfer_to_exchange",
                "args": {},
                "id": "call_transfer_exchange"
            }]
        )

        state = RouterState(
            is_authenticated=True,
            authenticated_cpf_hash="HASH_123",
            cliente_nome="João",
            active_agent="credit",
            messages=[
                HumanMessage(content="Qual a cotação do dólar hoje?"),
            ]
        )

        res = triage_node(state)
        assert res.goto == "exchange_subgraph"
        assert res.update["active_agent"] == "exchange"

    @patch("core.agents.router_agent.nodes._build_llm")
    def test_authenticated_user_asking_credit_while_in_exchange_switches_to_credit(self, mock_build_llm):
        """Cliente autenticado em câmbio pede crédito -> triage_node redireciona para credit_subgraph."""
        mock_llm = mock_build_llm.return_value
        mock_llm.bind_tools.return_value.invoke.return_value = AIMessage(
            content="",
            tool_calls=[{
                "name": "transfer_to_credit",
                "args": {},
                "id": "call_transfer_credit"
            }]
        )

        state = RouterState(
            is_authenticated=True,
            authenticated_cpf_hash="HASH_123",
            cliente_nome="João",
            active_agent="exchange",
            messages=[
                HumanMessage(content="Quero aumentar meu limite de crédito"),
            ]
        )

        res = triage_node(state)
        assert res.goto == "credit_subgraph"
        assert res.update["active_agent"] == "credit"

    @patch("core.agents.router_agent.nodes._build_llm")
    def test_authenticated_user_greeting_maintains_active_agent(self, mock_build_llm):
        """Cliente autenticado enviando saudação em crédito -> triage_node direciona para credit_subgraph."""
        mock_llm = mock_build_llm.return_value
        mock_llm.bind_tools.return_value.invoke.return_value = AIMessage(
            content="",
            tool_calls=[{
                "name": "transfer_to_credit",
                "args": {},
                "id": "call_transfer_credit"
            }]
        )

        state = RouterState(
            is_authenticated=True,
            authenticated_cpf_hash="HASH_123",
            cliente_nome="João",
            active_agent="credit",
            messages=[
                HumanMessage(content="bom dia"),
            ]
        )

        res = triage_node(state)
        assert res.goto == "credit_subgraph"
        assert res.update["active_agent"] == "credit"
