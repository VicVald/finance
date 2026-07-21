"""
TDD — Boundary: Regra de score para aprovação/rejeição de aumento de limite.
Testa os limites da tabela score_limite.csv:
  score 0-300   → limite máx 500
  score 301-500 → limite máx 2000
  score 501-700 → limite máx 5000
  score 701-850 → limite máx 10000
  score 851-1000 → limite máx 25000
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from unittest.mock import patch, mock_open

MOCK_SCORE_LIMITE_CSV = (
    "score_minimo,score_maximo,limite_maximo\n"
    "0,300,500.0\n"
    "301,500,2000.0\n"
    "501,700,5000.0\n"
    "701,850,10000.0\n"
    "851,1000,25000.0\n"
)


def get_check_score_fn():
    from modules.credit.services import check_score_allows_limit
    return check_score_allows_limit


class TestScoreLimitRule:
    """Testa a regra de aprovação de limite baseada no score."""

    @pytest.mark.parametrize("score,limite_solicitado,expected", [
        # Aprovações (dentro do limite para o score)
        (800, 5000.0, True),    # score 701-850, limite máx 10000 → aprovado
        (950, 20000.0, True),   # score 851-1000, limite máx 25000 → aprovado
        (300, 500.0, True),     # score 0-300, limite máx 500 → aprovado (exato)
        (301, 2000.0, True),    # score 301-500, limite máx 2000 → aprovado (exato)
        # Rejeições (acima do limite para o score)
        (450, 5000.0, False),   # score 301-500, limite máx 2000 → rejeitado
        (300, 501.0, False),    # score 0-300, limite máx 500 → rejeitado (1 acima)
        (800, 15000.0, False),  # score 701-850, limite máx 10000 → rejeitado
        (850, 25001.0, False),  # score 851-1000, limite máx 25000 → rejeitado (1 acima)
    ])
    def test_score_limit_rule(self, score: int, limite_solicitado: float, expected: bool):
        fn = get_check_score_fn()
        with patch("builtins.open", mock_open(read_data=MOCK_SCORE_LIMITE_CSV)):
            result = fn(score=score, novo_limite=limite_solicitado)
        assert result == expected, (
            f"score={score}, limite={limite_solicitado}: esperado {expected}, obtido {result}"
        )

    def test_score_below_minimum_is_rejected(self):
        """Score 0 pode solicitar no máximo 500."""
        fn = get_check_score_fn()
        with patch("builtins.open", mock_open(read_data=MOCK_SCORE_LIMITE_CSV)):
            assert fn(score=0, novo_limite=500.0) is True
            assert fn(score=0, novo_limite=500.01) is False

    def test_max_score_allows_max_limit(self):
        """Score 1000 pode solicitar até 25000."""
        fn = get_check_score_fn()
        with patch("builtins.open", mock_open(read_data=MOCK_SCORE_LIMITE_CSV)):
            assert fn(score=1000, novo_limite=25000.0) is True
            assert fn(score=1000, novo_limite=25000.01) is False


class TestCreditStateBridge:
    """Testa se o estado do Router é mapeado corretamente para o CreditState."""

    def test_setup_credit_node_maps_fields(self):
        from modules.credit.agents.graph import _setup_credit_node
        from modules.credit.agents.state import CreditState

        # Simulando o estado inicial recebido pelo setup_node
        class MockState:
            def __init__(self):
                self.cliente_cpf_hash = None
                self.limite_atual = None
                self.score_atual = None
                self.authenticated_cpf_hash = "HASH_CPF"
                self.cliente_limite_atual = 1000.0
                self.cliente_score_atual = 300

        state = MockState()
        update = _setup_credit_node(state)

        assert update["cliente_cpf_hash"] == "HASH_CPF"
        assert update["limite_atual"] == 1000.0
        assert update["score_atual"] == 300

