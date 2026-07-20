from typing import Annotated, Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class RouterState(BaseModel):
    """Estado global do grafo raiz (Router/Triagem)."""

    # Histórico de mensagens (reducer add_messages mantém append semântico)
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # Controle de agente ativo
    active_agent: Literal["triage", "credit", "interview", "exchange", "end"] = "triage"

    # Autenticação do cliente bancário (via CPF + data de nascimento)
    is_authenticated: bool = False
    auth_attempts: int = 0  # máximo 3 tentativas antes de encerrar
    authenticated_cpf_hash: Optional[str] = None
    current_user_cpf_hash: Optional[str] = None


    # Dados do cliente autenticado (para passar aos subgraphs)
    cliente_nome: Optional[str] = None
    cliente_limite_atual: Optional[float] = None
    cliente_score_atual: Optional[int] = None

    # Controle de sessão
    is_conversation_ended: bool = False
    thread_id: str = ""
