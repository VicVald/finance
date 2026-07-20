"""Auxiliar de autenticação para simular usuário registrado no grafo durante avaliações."""

import csv
import logging
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from utils.pii import hash_cpf
from core.config import settings
from core.agents.router_agent.graph import compiled_router_graph

log = logging.getLogger(__name__)


def pre_authenticate_thread(thread_config: dict, cpf: str) -> bool:
    """Configura o estado do grafo para um usuário pré-autenticado com base no CPF."""
    try:
        clean_cpf = cpf.replace(".", "").replace("-", "").strip()
        hashed = hash_cpf(clean_cpf)

        if not settings.CLIENTES_CSV.exists():
            log.error(f"clientes.csv não encontrado no caminho: {settings.CLIENTES_CSV}")
            return False

        with open(settings.CLIENTES_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["cpf_hash"].strip() == hashed:
                    # Cria a simulação do histórico de mensagens de autenticação para o LLM ver que está logado
                    mock_tool_call_id = "call_auth_mock_123"
                    mock_messages = [
                        HumanMessage(content=f"Quero me identificar. Meu CPF é {cpf}."),
                        AIMessage(
                            content="",
                            tool_calls=[{
                                "name": "authenticate_client",
                                "args": {"cpf": cpf, "data_nascimento": row["data_nascimento"]},
                                "id": mock_tool_call_id
                            }]
                        ),
                        ToolMessage(
                            content=str({
                                "authenticated": True,
                                "cpf_hash": hashed,
                                "nome": row["nome"],
                                "limite_atual": float(row["limite_atual"]),
                                "score": int(row["score"]),
                            }),
                            tool_call_id=mock_tool_call_id,
                            name="authenticate_client"
                        ),
                        AIMessage(content="Autenticação realizada com sucesso. Como posso te ajudar hoje?")
                    ]

                    state_values = {
                        "is_authenticated": True,
                        "authenticated_cpf_hash": hashed,
                        "cliente_nome": row["nome"],
                        "cliente_limite_atual": float(row["limite_atual"]),
                        "cliente_score_atual": int(row["score"]),
                        "auth_attempts": 0,
                        "messages": mock_messages
                    }
                    compiled_router_graph.update_state(thread_config, state_values)
                    log.info(f"Thread pré-autenticada com sucesso para o usuário: {row['nome']}")
                    return True

        log.warning(f"CPF {cpf} (hash: {hashed}) não encontrado no clientes.csv.")
        return False
    except Exception as e:
        log.error(f"Erro ao tentar pré-autenticar a thread: {e}")
        return False
