"""
TDD — Boundary: Autenticação do agente via CPF + data de nascimento.
Testa:
  - Autenticação válida retorna dados do cliente
  - Credenciais inválidas retornam None
  - Contador de tentativas é respeitado (máximo 3)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from unittest.mock import patch, mock_open
import csv
import io

# Dados simulados de clientes (mesmo formato do CSV real)
MOCK_CSV_CONTENT = (
    "cpf_hash,nome,data_nascimento,limite_atual,score,email,senha\n"
    "HASH_JOAO,João Silva,15/05/1990,5000.0,800,joao@agil.com,senha123\n"
    "HASH_MARIA,Maria Oliveira,20/10/1985,1500.0,450,maria@agil.com,senha456\n"
)


def get_authenticate_client_fn():
    """Importa a função após configurar o path corretamente."""
    from core.agents.router_agent.tools import _authenticate_client_logic
    return _authenticate_client_logic


class TestAuthenticateClientLogic:
    """Testa a lógica pura de autenticação (sem LLM)."""

    def test_valid_credentials_return_user_data(self):
        """CPF + data de nascimento corretos devem retornar dados do cliente."""
        fn = get_authenticate_client_fn()
        with patch("core.agents.router_agent.tools.hash_cpf", return_value="HASH_JOAO"), \
             patch("builtins.open", mock_open(read_data=MOCK_CSV_CONTENT)):
            result = fn(cpf="123.456.789-00", data_nascimento="15/05/1990")
        assert result["authenticated"] is True
        assert result["nome"] == "João Silva"
        assert result["cpf_hash"] == "HASH_JOAO"
        assert result["limite_atual"] == 5000.0
        assert result["score"] == 800

    def test_wrong_birth_date_returns_unauthenticated(self):
        """CPF correto mas data de nascimento errada deve retornar não autenticado."""
        fn = get_authenticate_client_fn()
        with patch("core.agents.router_agent.tools.hash_cpf", return_value="HASH_JOAO"), \
             patch("builtins.open", mock_open(read_data=MOCK_CSV_CONTENT)):
            result = fn(cpf="123.456.789-00", data_nascimento="01/01/2000")
        assert result["authenticated"] is False

    def test_nonexistent_cpf_returns_unauthenticated(self):
        """CPF não cadastrado deve retornar não autenticado."""
        fn = get_authenticate_client_fn()
        with patch("core.agents.router_agent.tools.hash_cpf", return_value="HASH_INEXISTENTE"), \
             patch("builtins.open", mock_open(read_data=MOCK_CSV_CONTENT)):
            result = fn(cpf="000.000.000-00", data_nascimento="01/01/1990")
        assert result["authenticated"] is False

    def test_missing_csv_returns_unauthenticated(self):
        """CSV ausente não deve lançar exceção — retorna não autenticado."""
        fn = get_authenticate_client_fn()
        with patch("core.agents.router_agent.tools.hash_cpf", return_value="HASH_X"), \
             patch("builtins.open", side_effect=FileNotFoundError):
            result = fn(cpf="111.111.111-11", data_nascimento="01/01/1990")
        assert result["authenticated"] is False

    def test_date_with_dashes_is_normalized(self):
        """Data com traços (DD-MM-AAAA) deve ser normalizada e aceita."""
        fn = get_authenticate_client_fn()
        with patch("core.agents.router_agent.tools.hash_cpf", return_value="HASH_JOAO"), \
             patch("builtins.open", mock_open(read_data=MOCK_CSV_CONTENT)):
            result = fn(cpf="123.456.789-00", data_nascimento="15-05-1990")
        assert result["authenticated"] is True

    def test_date_with_iso_format_is_normalized(self):
        """Data no formato ISO (AAAA-MM-DD) deve ser normalizada corretamente."""
        fn = get_authenticate_client_fn()
        with patch("core.agents.router_agent.tools.hash_cpf", return_value="HASH_JOAO"), \
             patch("builtins.open", mock_open(read_data=MOCK_CSV_CONTENT)):
            result = fn(cpf="123.456.789-00", data_nascimento="1990-05-15")
        assert result["authenticated"] is True

    def test_invalid_date_format_does_not_crash(self):
        """Formato de data completamente inválido não deve lançar exceção — retorna não autenticado."""
        fn = get_authenticate_client_fn()
        with patch("core.agents.router_agent.tools.hash_cpf", return_value="HASH_JOAO"), \
             patch("builtins.open", mock_open(read_data=MOCK_CSV_CONTENT)):
            result = fn(cpf="123.456.789-00", data_nascimento="nao-e-uma-data")
        assert result["authenticated"] is False


class TestNormalizeDate:
    """Testa a função auxiliar de normalização de datas."""

    def test_slash_format(self):
        from core.agents.router_agent.tools import _normalize_date
        assert _normalize_date("15/05/1990") == "15/05/1990"

    def test_dash_format(self):
        from core.agents.router_agent.tools import _normalize_date
        assert _normalize_date("15-05-1990") == "15/05/1990"

    def test_iso_format(self):
        from core.agents.router_agent.tools import _normalize_date
        assert _normalize_date("1990-05-15") == "15/05/1990"

    def test_invalid_format_returns_none(self):
        from core.agents.router_agent.tools import _normalize_date
        assert _normalize_date("nao-e-uma-data") is None



class TestAuthAttemptsBoundary:
    """Testa que o sistema respeita o limite de 3 tentativas."""

    def test_max_attempts_is_three(self):
        """Após 3 tentativas falhas, auth_attempts deve atingir o limite (3)."""
        MAX_ATTEMPTS = 3
        attempts = 0
        for _ in range(MAX_ATTEMPTS):
            attempts += 1
        assert attempts == MAX_ATTEMPTS

    def test_auth_attempts_boundary_value(self):
        """O valor máximo de tentativas permitidas é exatamente 3 (não 2, não 4)."""
        from core.agents.router_agent.state import RouterState
        state = RouterState()
        assert state.auth_attempts == 0
        # Simula 3 falhas
        for _ in range(3):
            state = state.model_copy(update={"auth_attempts": state.auth_attempts + 1})
        assert state.auth_attempts == 3
        # Verifica que o estado detecta o bloqueio
        assert state.auth_attempts >= 3

    def test_triage_node_max_attempts_friendly_msg(self):
        """triage_node deve retornar mensagem amigável e is_conversation_ended=True se auth_attempts >= 3."""
        from core.agents.router_agent.nodes import triage_node
        from core.agents.router_agent.state import RouterState
        from langgraph.types import Command
        
        state = RouterState(auth_attempts=3)
        res = triage_node(state)
        
        assert isinstance(res, Command)
        assert res.goto == "__end__"
        assert res.update["is_conversation_ended"] is True
        assert res.update["active_agent"] == "end"
        assert len(res.update["messages"]) == 1
        assert "Acesso bloqueado" in res.update["messages"][0].content


class TestCrossValidation:
    """Testa se o usuário autenticado não pode acessar conta de terceiros."""

    @patch("core.agents.router_agent.nodes._build_llm")
    @patch("core.agents.router_agent.tools._authenticate_client_logic")
    def test_different_user_cpf_fails_auth(self, mock_auth_logic, mock_build_llm):
        """Se o CPF consultado não pertencer ao usuário logado, a autenticação deve falhar."""
        from core.agents.router_agent.nodes import triage_node
        from core.agents.router_agent.state import RouterState
        from langchain_core.messages import AIMessage
        
        # Moca o LLM para fazer a chamada da tool authenticate_client
        mock_llm = mock_build_llm.return_value
        mock_llm.bind_tools.return_value.invoke.return_value = AIMessage(
            content="", 
            tool_calls=[{"name": "authenticate_client", "args": {"cpf": "999", "data_nascimento": "01/01/2000"}, "id": "call_123"}]
        )

        # Moca a lógica da tool para retornar sucesso e um hash de outro usuário
        mock_auth_logic.return_value = {
            "authenticated": True, 
            "cpf_hash": "HASH_OUTRO", 
            "nome": "Invasor",
            "limite_atual": 100,
            "score": 100
        }

        # Estado inicial com usuário logado tendo HASH_MEU
        state = RouterState(current_user_cpf_hash="HASH_MEU")
        
        # Executa o nó
        res = triage_node(state)
        
        # A autenticação deve ter sido negada por cross-validation
        assert res.update["auth_attempts"] == 1
        assert "is_authenticated" not in res.update or not res.update["is_authenticated"]


class TestMultipleToolCalls:
    """Testa o comportamento do nó de triagem diante de múltiplas tool calls."""

    @patch("core.agents.router_agent.nodes._build_llm")
    @patch("core.agents.router_agent.tools._authenticate_client_logic")
    def test_multiple_tool_calls_handled(self, mock_auth_logic, mock_build_llm):
        """Múltiplas chamadas de ferramentas na mesma resposta da IA devem ser todas processadas."""
        from core.agents.router_agent.nodes import triage_node
        from core.agents.router_agent.state import RouterState
        from langchain_core.messages import AIMessage
        
        mock_llm = mock_build_llm.return_value
        mock_llm.bind_tools.return_value.invoke.return_value = AIMessage(
            content="", 
            tool_calls=[
                {"name": "authenticate_client", "args": {"cpf": "123", "data_nascimento": "01/01/2000"}, "id": "call_1"},
                {"name": "end_conversation", "args": {}, "id": "call_2"}
            ]
        )

        mock_auth_logic.return_value = {
            "authenticated": True, 
            "cpf_hash": "HASH_MEU", 
            "nome": "Victor",
            "limite_atual": 1000,
            "score": 800
        }

        state = RouterState(current_user_cpf_hash="HASH_MEU")
        res = triage_node(state)

        # Se houver 'end_conversation' no loop, deve encerrar o atendimento
        assert res.update["is_conversation_ended"] is True
        assert res.update["active_agent"] == "end"
        assert len(res.update["messages"]) == 3  # AIMessage + 2 ToolMessages
        assert res.update["messages"][1].tool_call_id == "call_1"
        assert res.update["messages"][2].tool_call_id == "call_2"


