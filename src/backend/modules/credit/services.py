"""
Serviços de negócio do módulo de crédito:
  - check_score_allows_limit: valida se score permite o limite solicitado
  - calcular_score_entrevista: fórmula de score da entrevista financeira
  - solicitar_aumento: registra e avalia pedido no CSV
  - atualizar_score_cliente: atualiza score após entrevista
"""
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from core.config import settings

log = logging.getLogger(__name__)


# ─── Score e Limite ───────────────────────────────────────────────────────────

def check_score_allows_limit(score: int, novo_limite: float) -> bool:
    """
    Verifica se o score do cliente permite o novo limite solicitado.
    Lê as faixas de score_limite.csv.

    Returns:
        True se aprovado, False se rejeitado.
    """
    try:
        with open(settings.SCORE_LIMITE_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                s_min = int(row["score_minimo"])
                s_max = int(row["score_maximo"])
                lim_max = float(row["limite_maximo"])
                if s_min <= score <= s_max:
                    return novo_limite <= lim_max
    except Exception as e:
        log.error(f"Erro ao ler score_limite.csv: {e}")
    return False


# ─── Fórmula de Score da Entrevista ──────────────────────────────────────────

PESO_RENDA = 30
PESO_EMPREGO = {
    "formal": 300,
    "autônomo": 200,
    "desempregado": 0,
}
PESO_DEPENDENTES = {
    0: 100,
    1: 80,
    2: 60,
}
PESO_DEPENDENTES_3MAIS = 30

PESO_DIVIDAS = {
    True: -100,   # tem dívidas
    False: 100,   # sem dívidas
}


def calcular_score_entrevista(
    renda_mensal: float,
    tipo_emprego: Literal["formal", "autônomo", "desempregado"],
    despesas_fixas: float,
    num_dependentes: int,
    tem_dividas: bool,
) -> int:
    """
    Calcula novo score de crédito com base nos dados da entrevista financeira.
    Score é clampado entre 0 e 1000.
    """
    p_emprego = PESO_EMPREGO.get(tipo_emprego, 0)
    p_dep = PESO_DEPENDENTES.get(num_dependentes, PESO_DEPENDENTES_3MAIS)
    p_dividas = PESO_DIVIDAS.get(tem_dividas, 0)
    p_renda = (renda_mensal / (despesas_fixas + 1)) * PESO_RENDA

    raw_score = p_renda + p_emprego + p_dep + p_dividas
    return max(0, min(1000, int(raw_score)))


# ─── Persistência de Solicitações ────────────────────────────────────────────

def registrar_solicitacao_aumento(
    cpf_hash: str,
    limite_atual: float,
    novo_limite_solicitado: float,
    status: Literal["aprovado", "rejeitado", "pendente"],
) -> dict:
    """
    Registra uma solicitação de aumento de limite no CSV.
    Cria o arquivo com cabeçalho se não existir.
    """
    csv_path = settings.SOLICITACOES_AUMENTO_CSV
    fieldnames = [
        "cpf_cliente",
        "data_hora_solicitacao",
        "limite_atual",
        "novo_limite_solicitado",
        "status_pedido",
    ]

    row = {
        "cpf_cliente": cpf_hash,
        "data_hora_solicitacao": datetime.now(timezone.utc).isoformat(),
        "limite_atual": limite_atual,
        "novo_limite_solicitado": novo_limite_solicitado,
        "status_pedido": status,
    }

    try:
        file_exists = csv_path.exists() and csv_path.stat().st_size > 0
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception as e:
        log.error(f"Erro ao registrar solicitação: {e}")

    return row


def atualizar_score_cliente(cpf_hash: str, novo_score: int) -> bool:
    """
    Atualiza o score do cliente no clientes.csv.
    Faz leitura completa, modifica e reescreve o arquivo.

    Returns:
        True se atualizado com sucesso, False caso contrário.
    """
    csv_path = settings.CLIENTES_CSV
    try:
        rows = []
        updated = False
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row["cpf_hash"] == cpf_hash:
                    row["score"] = str(novo_score)
                    updated = True
                rows.append(row)

        if updated:
            with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

        return updated
    except Exception as e:
        log.error(f"Erro ao atualizar score: {e}")
        return False
