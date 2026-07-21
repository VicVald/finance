"""
TDD — Testes de persistência de limite de crédito e direcionamento de triagem.
"""
import sys
import os
import csv
from unittest.mock import patch, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from langchain_core.messages import AIMessage


MOCK_CLIENTES_CSV = (
    "cpf_hash,cpf_mask,nome,data_nascimento,limite_atual,score,email,senha\n"
    "HASH_JOAO,111.XXX.XXX-11,João Silva,15/05/1990,5000.0,779,joao@agil.com,senha123\n"
    "HASH_PEDRO,333.XXX.XXX-33,Pedro Santos,03/03/1995,500.0,300,pedro@agil.com,senha789\n"
)

MOCK_SCORE_LIMITE_CSV = (
    "score_minimo,score_maximo,limite_maximo\n"
    "0,300,500.0\n"
    "301,500,2000.0\n"
    "501,700,5000.0\n"
    "701,850,10000.0\n"
    "851,1000,25000.0\n"
)


class TestCreditLimitPersistence:
    """Testa a atualização de limite em clientes.csv quando uma solicitação é aprovada."""

    def test_atualizar_limite_cliente_success(self, tmp_path):
        from modules.credit.services import atualizar_limite_cliente
        from core.config import settings

        csv_file = tmp_path / "clientes.csv"
        csv_file.write_text(MOCK_CLIENTES_CSV, encoding="utf-8")

        with patch.object(settings, "CLIENTES_CSV", csv_file):
            result = atualizar_limite_cliente(cpf_hash="HASH_JOAO", novo_limite=7000.0)

        assert result is True

        # Verifica se o arquivo foi atualizado
        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert reader[0]["cpf_hash"] == "HASH_JOAO"
            assert float(reader[0]["limite_atual"]) == 7000.0

    def test_solicitar_aumento_limite_updates_csv_on_approval(self, tmp_path):
        from modules.credit.agents.credit_agent.tools import solicitar_aumento_limite
        from core.config import settings

        clientes_file = tmp_path / "clientes.csv"
        clientes_file.write_text(MOCK_CLIENTES_CSV, encoding="utf-8")

        score_limite_file = tmp_path / "score_limite.csv"
        score_limite_file.write_text(MOCK_SCORE_LIMITE_CSV, encoding="utf-8")

        solicitacoes_file = tmp_path / "solicitacoes.csv"

        with patch.object(settings, "CLIENTES_CSV", clientes_file), \
             patch.object(settings, "SCORE_LIMITE_CSV", score_limite_file), \
             patch.object(settings, "SOLICITACOES_AUMENTO_CSV", solicitacoes_file):
            res = solicitar_aumento_limite.invoke({"cpf_hash": "HASH_JOAO", "novo_limite": 7000.0})

        assert res["status"] == "aprovado"

        # Verifica se clientes.csv reflete o novo limite de 7000.0
        with open(clientes_file, mode="r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert float(reader[0]["limite_atual"]) == 7000.0

    def test_solicitar_aumento_limite_does_not_update_csv_on_rejection(self, tmp_path):
        from modules.credit.agents.credit_agent.tools import solicitar_aumento_limite
        from core.config import settings

        clientes_file = tmp_path / "clientes.csv"
        clientes_file.write_text(MOCK_CLIENTES_CSV, encoding="utf-8")

        score_limite_file = tmp_path / "score_limite.csv"
        score_limite_file.write_text(MOCK_SCORE_LIMITE_CSV, encoding="utf-8")

        solicitacoes_file = tmp_path / "solicitacoes.csv"

        with patch.object(settings, "CLIENTES_CSV", clientes_file), \
             patch.object(settings, "SCORE_LIMITE_CSV", score_limite_file), \
             patch.object(settings, "SOLICITACOES_AUMENTO_CSV", solicitacoes_file):
            res = solicitar_aumento_limite.invoke({"cpf_hash": "HASH_PEDRO", "novo_limite": 5000.0})

        assert res["status"] == "rejeitado"

        # Limite do Pedro deve permanecer 500.0
        with open(clientes_file, mode="r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert float(reader[1]["limite_atual"]) == 500.0


class TestTriageHandoffRules:
    """Testa se mensagens de solicitação de crédito são direcionadas para [HANDOFF:credit]."""

    @patch("core.agents.router_agent.nodes._build_llm")
    def test_triage_routes_credit_request_to_credit_subgraph(self, mock_build_llm):
        from core.agents.router_agent.nodes import triage_node
        from core.agents.router_agent.state import RouterState

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
            authenticated_cpf_hash="HASH_JOAO",
            cliente_nome="João Silva",
            active_agent="triage",
        )

        res = triage_node(state)
        assert res.goto == "credit_subgraph"
        assert res.update["active_agent"] == "credit"
