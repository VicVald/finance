"""
Ferramentas do Router Agent:
  - authenticate_client: valida CPF + data de nascimento contra clientes.csv
  - end_conversation: encerra a conversa de forma controlada

A função _authenticate_client_logic é separada para permitir testes unitários
sem depender do decorator @tool do LangGraph.
"""
import csv
import logging
from langchain_core.tools import tool
from utils.pii import hash_cpf
from core.config import settings

log = logging.getLogger(__name__)


def _normalize_date(date_str: str) -> str | None:
    """
    Tenta parsear a data em múltiplos formatos e normaliza para DD/MM/AAAA.
    Retorna None se nenhum formato reconhecer a entrada.
    """
    from datetime import datetime
    # Formatos aceitos (sempre interpretados como dia/mês/ano)
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return None


def _authenticate_client_logic(cpf: str, data_nascimento: str) -> dict:
    """
    Lógica pura de autenticação — sem LangGraph, testável isoladamente.

    Retorna:
      {"authenticated": True, "cpf_hash": ..., "nome": ..., ...} se válido
      {"authenticated": False} se inválido ou CSV ausente
    """
    try:
        # Mascara básica para log (mantém apenas os últimos dois caracteres se possível)
        masked_cpf = f"***.***.***-{cpf[-2:]}" if len(cpf) >= 2 else "***.***.***-**"

        # Normaliza a data de nascimento para o formato padrão DD/MM/AAAA
        dob_normalized = _normalize_date(data_nascimento)
        if not dob_normalized:
            log.warning(f"Formato de data inválido recebido: '{data_nascimento}' — não foi possível normalizar.")
            dob_normalized = data_nascimento.strip()

        log.debug(f"Iniciando autenticação para CPF: {masked_cpf} | Data Nasc (normalizada): {dob_normalized}")

        cpf_hash = hash_cpf(cpf)
        if not settings.CLIENTES_CSV.exists():
            log.warning("clientes.csv não encontrado")
            return {"authenticated": False}

        with open(settings.CLIENTES_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["cpf_hash"].strip() == cpf_hash:
                    dob_csv = row["data_nascimento"].strip()
                    if dob_csv == dob_normalized:
                        log.debug(f"Usuário encontrado e autenticado com sucesso: {row['nome']}")
                        return {
                            "authenticated": True,
                            "cpf_hash": cpf_hash,
                            "nome": row["nome"],
                            "limite_atual": float(row["limite_atual"]),
                            "score": int(row["score"]),
                        }
                    else:
                        log.debug(f"CPF encontrado mas data incorreta. Esperado: {dob_csv} | Recebido: {dob_normalized}")
                        return {"authenticated": False}

        # CPF não encontrado
        return {"authenticated": False}

    except FileNotFoundError:
        log.error("clientes.csv não encontrado (FileNotFoundError)")
        return {"authenticated": False}
    except Exception as e:
        log.error(f"Erro inesperado na autenticação: {e}")
        return {"authenticated": False}



@tool
def authenticate_client(cpf: str, data_nascimento: str) -> dict:
    """
    Autentica o cliente bancário usando CPF e data de nascimento.

    Args:
        cpf: CPF do cliente (pode conter formatação: "123.456.789-00")
        data_nascimento: Data de nascimento no formato "DD/MM/AAAA"

    Returns:
        dict com {"authenticated": bool, ...dados do cliente se autenticado}
    """
    return _authenticate_client_logic(cpf, data_nascimento)


@tool
def end_conversation() -> str:
    """
    Encerra a conversa de forma amigável.
    Deve ser chamada quando o cliente solicitar o fim do atendimento
    ou após 3 tentativas falhas de autenticação.

    Returns:
        Mensagem de encerramento para exibir ao cliente.
    """
    return "encerrar"


@tool
def transfer_to_credit() -> str:
    """
    Transfere o atendimento para o especialista de crédito, responsável por consultar limites, score e processar aumentos de limite de crédito.
    """
    return "handoff_credit"


@tool
def transfer_to_exchange() -> str:
    """
    Transfere o atendimento para o especialista de câmbio, responsável por cotações de moedas estrangeiras.
    """
    return "handoff_exchange"


@tool
def transfer_to_interview() -> str:
    """
    Transfere o atendimento para a entrevista de crédito e score.
    """
    return "handoff_interview"
