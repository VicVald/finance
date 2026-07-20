"""Utilitário de geração de relatórios e persistência em /history."""

import json
from pathlib import Path
from evals.models import EvalRunReport


DEFAULT_HISTORY_DIR = Path(__file__).parent / "history"


def save_eval_report(report: EvalRunReport, history_dir: Path | str = DEFAULT_HISTORY_DIR) -> tuple[Path, Path]:
    """Salva os arquivos .json e .md na pasta de histórico e retorna os caminhos criados."""
    history_path = Path(history_dir)
    history_path.mkdir(parents=True, exist_ok=True)

    base_filename = f"{report.timestamp.replace(':', '').replace('-', '').split('.')[0]}_{report.eval_type}_{report.dataset_name.replace(' ', '_').lower()}"
    json_path = history_path / f"{base_filename}.json"
    md_path = history_path / f"{base_filename}.md"

    # 1. Salvar JSON completo
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))

    # 2. Gerar Relatório Markdown
    status_emoji = "✅ PASSOU" if report.verdict.passed else "❌ FALHOU"
    score_pct = f"{report.verdict.score * 100:.1f}%"

    md_lines = [
        f"# Relatório de Avaliação: {report.dataset_name}",
        "",
        f"- **Status:** {status_emoji}",
        f"- **Nota:** {score_pct}",
        f"- **Tipo:** `{report.eval_type}`",
        f"- **Timestamp:** {report.timestamp}",
        f"- **Run ID:** `{report.run_id}`",
        "",
        "---",
        "",
        "## Parecer do LLM Judge",
        "",
        f"**Justificativa:**",
        f"{report.verdict.reasoning}",
        "",
    ]

    if report.verdict.detected_violations:
        md_lines.extend([
            "**Violações Detectadas:**",
            *(f"- ⚠️ {v}" for v in report.verdict.detected_violations),
            "",
        ])

    md_lines.extend([
        "---",
        "",
        "## Transcrição da Conversa",
        "",
        "| Turno | Emissor | Agente Ativo | Mensagem |",
        "|-------|---------|--------------|----------|",
    ])

    for t in report.turns:
        speaker_fmt = f"**{t.speaker.upper()}**"
        agent_fmt = f"`{t.active_agent}`" if t.active_agent else "-"
        msg_fmt = t.message.replace("\n", "<br>")
        md_lines.append(f"| {t.turn} | {speaker_fmt} | {agent_fmt} | {msg_fmt} |")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    return json_path, md_path
