"""
TDD — Boundary: Fórmula de cálculo de score do Agente de Entrevista de Crédito.

Fórmula (DESAFIO.md):
  score = (renda_mensal / (despesas + 1)) * peso_renda
        + peso_emprego[tipo_emprego]
        + peso_dependentes[num_dependentes]
        + peso_dividas[tem_dividas]

  clampado entre 0 e 1000.

Pesos:
  peso_renda = 30
  peso_emprego = {"formal": 300, "autônomo": 200, "desempregado": 0}
  peso_dependentes = {0: 100, 1: 80, 2: 60, "3+": 30}
  peso_dividas = {"sim": -100, "não": 100}
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest


def get_score_formula_fn():
    from modules.credit.services import calcular_score_entrevista
    return calcular_score_entrevista


class TestScoreFormula:
    """Testa a fórmula de score da entrevista de crédito."""

    def test_perfect_profile_capped_at_1000(self):
        """Perfil excelente não ultrapassa 1000."""
        fn = get_score_formula_fn()
        # renda 20000, despesas 100, formal, 0 dependentes, sem dívidas
        score = fn(
            renda_mensal=20000.0,
            tipo_emprego="formal",
            despesas_fixas=100.0,
            num_dependentes=0,
            tem_dividas=False,
        )
        assert score <= 1000
        assert score >= 900  # deve ser muito alto

    def test_worst_profile_floored_at_0(self):
        """Perfil ruim não fica negativo."""
        fn = get_score_formula_fn()
        score = fn(
            renda_mensal=0.0,
            tipo_emprego="desempregado",
            despesas_fixas=10000.0,
            num_dependentes=5,  # usa "3+"
            tem_dividas=True,
        )
        assert score >= 0

    def test_formal_employment_beats_autonomo(self):
        """Emprego formal deve resultar em score maior que autônomo com mesmos dados."""
        fn = get_score_formula_fn()
        base = dict(renda_mensal=5000.0, despesas_fixas=1000.0, num_dependentes=1, tem_dividas=False)
        score_formal = fn(tipo_emprego="formal", **base)
        score_autonomo = fn(tipo_emprego="autônomo", **base)
        assert score_formal > score_autonomo

    def test_dividas_penalizes_score(self):
        """Ter dívidas deve reduzir o score em 200 pontos vs não ter."""
        fn = get_score_formula_fn()
        base = dict(renda_mensal=5000.0, tipo_emprego="formal", despesas_fixas=1000.0, num_dependentes=0)
        score_sem_divida = fn(tem_dividas=False, **base)
        score_com_divida = fn(tem_dividas=True, **base)
        assert score_sem_divida - score_com_divida == 200  # 100 - (-100) = 200

    def test_three_or_more_dependents_uses_3_plus_weight(self):
        """3 ou mais dependentes usa peso_dependentes["3+"] = 30."""
        fn = get_score_formula_fn()
        base = dict(renda_mensal=3000.0, tipo_emprego="formal", despesas_fixas=500.0, tem_dividas=False)
        score_3dep = fn(num_dependentes=3, **base)
        score_5dep = fn(num_dependentes=5, **base)
        # Ambos devem ter o mesmo peso (30) para dependentes
        assert score_3dep == score_5dep

    @pytest.mark.parametrize("renda,despesas,tipo,dependentes,dividas,min_score,max_score", [
        (5000, 1000, "formal", 0, False, 550, 700),
        (2000, 500, "autônomo", 2, True, 200, 400),
        (1500, 1000, "desempregado", 1, False, 100, 250),
    ])
    def test_typical_profiles_in_expected_range(
        self, renda, despesas, tipo, dependentes, dividas, min_score, max_score
    ):
        """Perfis típicos devem cair dentro dos intervalos esperados."""
        fn = get_score_formula_fn()
        score = fn(
            renda_mensal=float(renda),
            tipo_emprego=tipo,
            despesas_fixas=float(despesas),
            num_dependentes=dependentes,
            tem_dividas=dividas,
        )
        assert min_score <= score <= max_score, f"score={score} fora do intervalo [{min_score}, {max_score}]"
