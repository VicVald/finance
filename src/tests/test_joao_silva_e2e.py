"""
Teste de Integração End-to-End para o fluxo de João Silva.
"""
import sys
import os
import csv
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from core.agents.router_agent.graph import compiled_router_graph
from core.agents.router_agent.state import RouterState
from langchain_core.messages import HumanMessage


MOCK_CLIENTES_CSV = (
    "cpf_hash,cpf_mask,nome,data_nascimento,limite_atual,score,email,senha\n"
    "97b377bbeda9673230ba3fdc477c423916cac65f0a5861c217ee5f19c5fb639d,111.XXX.XXX-11,João Silva,15/05/1990,5000.0,1000,joao@agil.com,senha123\n"
)

MOCK_SCORE_LIMITE_CSV = (
    "score_minimo,score_maximo,limite_maximo\n"
    "0,300,500.0\n"
    "301,500,2000.0\n"
    "501,700,5000.0\n"
    "701,850,10000.0\n"
    "851,1000,25000.0\n"
)


class TestJoaoSilvaE2E:
    """Valida o fluxo completo de alteração de limite de João Silva."""

    def test_joao_silva_limit_increase_approved_and_persisted(self, tmp_path):
        from core.config import settings

        clientes_file = tmp_path / "clientes.csv"
        clientes_file.write_text(MOCK_CLIENTES_CSV, encoding="utf-8")

        score_limite_file = tmp_path / "score_limite.csv"
        score_limite_file.write_text(MOCK_SCORE_LIMITE_CSV, encoding="utf-8")

        solicitacoes_file = tmp_path / "solicitacoes.csv"

        thread_config = {"configurable": {"thread_id": "test_joao_e2e_1"}}

        with patch.object(settings, "CLIENTES_CSV", clientes_file), \
             patch.object(settings, "SCORE_LIMITE_CSV", score_limite_file), \
             patch.object(settings, "SOLICITACOES_AUMENTO_CSV", solicitacoes_file):

            # Step 1: Autenticação
            init_state = {
                "messages": [HumanMessage(content="11111111111 e 15/05/1990")],
            }
            res_auth = compiled_router_graph.invoke(init_state, config=thread_config)
            assert res_auth.get("is_authenticated") is True
            assert res_auth.get("cliente_nome") == "João Silva"

            # Step 2: Solicitar aumento de limite para 5500
            inc_state = {
                "messages": [HumanMessage(content="Quero aumentar meu limite para 5500")],
            }
            res_inc = compiled_router_graph.invoke(inc_state, config=thread_config)

            # O resultado final deve ser o nó final (não interview_subgraph)
            last_msg = res_inc["messages"][-1].content
            assert "5500" in last_msg or "5.500" in last_msg or "aprovad" in last_msg.lower() or "sucesso" in last_msg.lower()

            # O clientes.csv deve ter sido atualizado para 5500.0
            with open(clientes_file, mode="r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                assert float(reader[0]["limite_atual"]) == 5500.0

    def test_joao_silva_limit_increase_lower_than_current(self, tmp_path):
        from core.config import settings

        clientes_file = tmp_path / "clientes.csv"
        clientes_file.write_text(MOCK_CLIENTES_CSV, encoding="utf-8")

        score_limite_file = tmp_path / "score_limite.csv"
        score_limite_file.write_text(MOCK_SCORE_LIMITE_CSV, encoding="utf-8")

        solicitacoes_file = tmp_path / "solicitacoes.csv"

        thread_config = {"configurable": {"thread_id": "test_joao_e2e_2"}}

        with patch.object(settings, "CLIENTES_CSV", clientes_file), \
             patch.object(settings, "SCORE_LIMITE_CSV", score_limite_file), \
             patch.object(settings, "SOLICITACOES_AUMENTO_CSV", solicitacoes_file):

            # Step 1: Autenticação
            init_state = {
                "messages": [HumanMessage(content="11111111111 e 15/05/1990")],
            }
            compiled_router_graph.invoke(init_state, config=thread_config)

            # Step 2: Pedir limite menor (550)
            inc_state = {
                "messages": [HumanMessage(content="Quero aumentar meu limite para 550")],
            }
            res_inc = compiled_router_graph.invoke(inc_state, config=thread_config)

            # Não deve ter acionado o interrupt de entrevista!
            state_snapshot = compiled_router_graph.get_state(thread_config)
            has_interrupts = False
            if state_snapshot.tasks:
                for t in state_snapshot.tasks:
                    if t.interrupts:
                        has_interrupts = True

            assert has_interrupts is False, "Não deveria disparar entrevista para valor menor que o limite atual"
