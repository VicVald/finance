"""CLI Runner principal para a suíte de avaliações (/evals).

Uso:
  python -m src.evals.runner --type simple
  python -m src.evals.runner --type ai_battle
  python -m src.evals.runner --type all
"""

import sys
import os
import argparse
import asyncio
import logging
from pathlib import Path

# Adiciona o diretório src ao sys.path para importações relativas e absolutas do backend
SRC_DIR = Path(__file__).parent.parent
BACKEND_DIR = SRC_DIR / "backend"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evals.simple_eval import run_simple_eval
from evals.ai_battle import run_ai_battle_eval
from evals.reporter import save_eval_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("evals.runner")

DATASETS_DIR = Path(__file__).parent / "datasets"


async def main():
    parser = argparse.ArgumentParser(description="Runner da Suíte de Avaliações (/evals) - Banco Ágil")
    parser.add_argument(
        "--type",
        choices=["simple", "ai_battle", "all"],
        default="all",
        help="Tipo de avaliação a ser executada (simple, ai_battle ou all)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Caminho ou nome específico do arquivo YAML do dataset (opcional)",
    )
    parser.add_argument(
        "--history-dir",
        type=str,
        default=None,
        help="Diretório customizado para salvar o histórico",
    )

    args = parser.parse_args()

    eval_tasks = []

    # Processar avaliações /simple
    if args.type in ["simple", "all"]:
        simple_dir = DATASETS_DIR / "simple"
        if args.dataset and ("simple" in args.dataset or args.type == "simple"):
            files = [Path(args.dataset)]
        else:
            files = list(simple_dir.glob("*.yaml")) if simple_dir.exists() else []

        for f in files:
            eval_tasks.append(("simple", f))

    # Processar avaliações /ai-battle
    if args.type in ["ai_battle", "all"]:
        ai_battle_dir = DATASETS_DIR / "ai_battle"
        if args.dataset and ("ai_battle" in args.dataset or args.type == "ai_battle"):
            files = [Path(args.dataset)]
        else:
            files = list(ai_battle_dir.glob("*.yaml")) if ai_battle_dir.exists() else []

        for f in files:
            eval_tasks.append(("ai_battle", f))

    if not eval_tasks:
        log.warning("Nenhum arquivo de dataset YAML foi encontrado para execução.")
        return

    print(f"\n🚀 Iniciando a Suíte de Avaliações ({len(eval_tasks)} cenário(s))\n" + "=" * 60)

    reports = []
    for eval_type, filepath in eval_tasks:
        print(f"\n▶ Executando [{eval_type.upper()}] arquivo: {filepath.name}...")
        try:
            if eval_type == "simple":
                report = await run_simple_eval(filepath)
            else:
                report = await run_ai_battle_eval(filepath)

            history_dir = args.history_dir or (Path(__file__).parent / "history")
            json_p, md_p = save_eval_report(report, history_dir=history_dir)

            reports.append(report)
            status_symbol = "✅ PASSOU" if report.verdict.passed else "❌ FALHOU"
            print(f"  Resultado: {status_symbol} (Nota: {report.verdict.score * 100:.1f}%)")
            print(f"  Relatório JSON: {json_p}")
            print(f"  Relatório MD:   {md_p}")

        except Exception as e:
            log.error(f"Erro durante a execução de {filepath.name}: {e}", exc_info=True)

    print("\n" + "=" * 60)
    passed_count = sum(1 for r in reports if r.verdict.passed)
    print(f"📊 Resumo Final: {passed_count}/{len(reports)} avaliações passaram com sucesso.\n")


if __name__ == "__main__":
    asyncio.run(main())
