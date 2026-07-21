"""
Ferramentas do Agente de Crédito:
  - consultar_limite: retorna o limite atual do cliente
  - solicitar_aumento_limite: avalia e registra pedido de aumento
"""
import logging
from langchain_core.tools import tool
from modules.credit.services import (
    check_score_allows_limit,
    registrar_solicitacao_aumento,
    atualizar_limite_cliente,
)
from core.config import settings
import csv

log = logging.getLogger(__name__)


def _get_cliente_data(cpf_hash: str) -> dict | None:
    """Busca dados do cliente no CSV pelo hash do CPF."""
    try:
        with open(settings.CLIENTES_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["cpf_hash"].strip() == cpf_hash.strip():
                    return {
                        "nome": row["nome"],
                        "limite_atual": float(row["limite_atual"]),
                        "score": int(row["score"]),
                    }
    except Exception as e:
        log.error(f"Erro ao buscar cliente: {e}")
    return None


@tool
def consultar_limite(cpf_hash: str) -> str:
    """
    Consulta o limite de crédito atual do cliente autenticado.

    Args:
        cpf_hash: Hash do CPF do cliente (disponível no estado autenticado)

    Returns:
        String com o limite atual formatado em BRL.
    """
    dados = _get_cliente_data(cpf_hash)
    if not dados:
        return "Não foi possível consultar o limite. Tente novamente."
    return (
        f"Olá, {dados['nome']}! Seu limite de crédito atual é "
        f"R$ {dados['limite_atual']:,.2f}."
    )


@tool
def solicitar_aumento_limite(cpf_hash: str, novo_limite: float) -> dict:
    """
    Solicita um aumento no limite de crédito do cliente.
    Avalia automaticamente com base no score e registra no CSV.

    Args:
        cpf_hash: Hash do CPF do cliente
        novo_limite: Novo limite desejado em BRL

    Returns:
        dict com status ("aprovado" | "rejeitado"), limite_atual, novo_limite, score
    """
    dados = _get_cliente_data(cpf_hash)
    if not dados:
        return {"status": "erro", "mensagem": "Cliente não encontrado."}

    limite_atual = dados["limite_atual"]
    score = dados["score"]

    if novo_limite <= limite_atual:
        return {
            "status": "invalido",
            "motivo": f"O novo limite solicitado (R$ {novo_limite:,.2f}) deve ser maior que seu limite atual (R$ {limite_atual:,.2f}).",
            "limite_atual": limite_atual,
            "novo_limite_solicitado": novo_limite,
            "score": score,
        }

    aprovado = check_score_allows_limit(score=score, novo_limite=novo_limite)
    status = "aprovado" if aprovado else "rejeitado"

    if aprovado:
        atualizar_limite_cliente(cpf_hash=cpf_hash, novo_limite=novo_limite)

    registrar_solicitacao_aumento(
        cpf_hash=cpf_hash,
        limite_atual=limite_atual,
        novo_limite_solicitado=novo_limite,
        status=status,
    )

    return {
        "status": status,
        "limite_atual": limite_atual,
        "novo_limite_solicitado": novo_limite,
        "score": score,
    }


@tool
def transfer_to_triage() -> str:
    """
    Transfere o atendimento de volta para a triagem geral (router) se o cliente quiser falar de outro assunto ou encerrar a conversa.
    """
    return "handoff_triage"
