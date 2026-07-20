"""Testes unitários para a suíte de avaliações (/evals)."""

import sys
import os
from pathlib import Path
import pytest

# Insere backend e src no PYTHONPATH
SRC_DIR = Path(__file__).parent.parent
BACKEND_DIR = SRC_DIR / "backend"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evals.models import SimpleTestCase, AIBattlePersona, EvalRunReport, JudgeVerdict, ConversationTurn
from evals.simple_eval import load_simple_dataset
from evals.ai_battle import load_ai_battle_persona
from evals.reporter import save_eval_report


class TestEvalsStructure:
    """Testa a integridade de dados e modelos da suíte de evals."""

    def test_load_simple_datasets(self):
        """Valida se todos os datasets YAML de /simple são carregados corretamente."""
        simple_dir = SRC_DIR / "evals" / "datasets" / "simple"
        files = list(simple_dir.glob("*.yaml"))
        assert len(files) >= 3, "Devem existir pelo menos 3 datasets YAML em /simple"

        for f in files:
            tc = load_simple_dataset(f)
            assert isinstance(tc, SimpleTestCase)
            assert tc.dataset_name
            assert len(tc.steps) > 0

    def test_load_ai_battle_personas(self):
        """Valida se todas as personas YAML de /ai-battle são carregadas corretamente."""
        ai_battle_dir = SRC_DIR / "evals" / "datasets" / "ai_battle"
        files = list(ai_battle_dir.glob("*.yaml"))
        assert len(files) >= 3, "Devem existir pelo menos 3 personas YAML em /ai-battle"

        for f in files:
            persona = load_ai_battle_persona(f)
            assert isinstance(persona, AIBattlePersona)
            assert persona.persona_name
            assert persona.max_turns > 0
            assert persona.attacker_prompt

    def test_reporter_saves_json_and_md(self, tmp_path):
        """Valida a persistência dos relatórios de histórico em formato JSON e Markdown."""
        report = EvalRunReport(
            run_id="test-run-123",
            timestamp="2026-07-20T15:00:00Z",
            eval_type="simple",
            dataset_name="Teste de Unidade",
            turns=[
                ConversationTurn(turn=1, speaker="user", message="Olá"),
                ConversationTurn(turn=1, speaker="bot", message="Bem-vindo!", active_agent="triage"),
            ],
            verdict=JudgeVerdict(
                passed=True,
                score=1.0,
                reasoning="Atendimento impecável",
                detected_violations=[],
            ),
        )

        json_p, md_p = save_eval_report(report, history_dir=tmp_path)

        assert json_p.exists()
        assert md_p.exists()
        assert json_p.suffix == ".json"
        assert md_p.suffix == ".md"

        content_md = md_p.read_text(encoding="utf-8")
        assert "✅ PASSOU" in content_md
        assert "Teste de Unidade" in content_md

    def test_pre_authenticate_thread_helper(self):
        """Valida que o helper de pré-autenticação atualiza o estado corretamente."""
        import uuid
        from evals.auth_helper import pre_authenticate_thread
        from core.agents.router_agent.graph import compiled_router_graph

        thread_id = f"test-auth-helper-{uuid.uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}

        success = pre_authenticate_thread(config, "11111111111")
        assert success is True

        snapshot = compiled_router_graph.get_state(config)
        state_values = snapshot.values if snapshot.values else {}
        assert state_values.get("is_authenticated") is True
        assert state_values.get("cliente_nome") == "João Silva"

    def test_authenticated_thread_config_fixture(self, authenticated_thread_config):
        """Valida que a fixture authenticated_thread_config fornece um estado autenticado."""
        from core.agents.router_agent.graph import compiled_router_graph

        snapshot = compiled_router_graph.get_state(authenticated_thread_config)
        state_values = snapshot.values if snapshot.values else {}
        assert state_values.get("is_authenticated") is True
        assert state_values.get("cliente_nome") == "João Silva"
