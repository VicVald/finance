from typing import Annotated, Optional
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class CreditState(BaseModel):
    """Estado local do subgraph de crédito."""

    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # Dados do cliente (injetados pelo router no handoff)
    cliente_cpf_hash: Optional[str] = None
    cliente_nome: Optional[str] = None
    limite_atual: Optional[float] = None
    score_atual: Optional[int] = None

    # Controle de solicitação de aumento
    solicitacao_pendente: Optional[float] = None
    ultimo_status_solicitacao: Optional[str] = None  # "aprovado" | "rejeitado"

    # Sinaliza que o cliente aceitou fazer a entrevista (após interrupt)
    aceite_entrevista: Optional[bool] = None

    # Indica se a entrevista foi solicitada pelo fluxo (human-in-the-loop track)
    pediu_entrevista: Optional[bool] = None
