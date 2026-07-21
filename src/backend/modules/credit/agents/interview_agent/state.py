from typing import Annotated, Literal, Optional
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class InterviewState(BaseModel):
    """Estado local do subgraph de entrevista de crédito."""

    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # Dados do cliente (herdados do router via handoff)
    cpf_hash: Optional[str] = None
    cliente_nome: Optional[str] = None
    # Campo bridge: RouterState.authenticated_cpf_hash → InterviewState.cpf_hash
    authenticated_cpf_hash: Optional[str] = None

    # Dados financeiros coletados na entrevista
    renda_mensal: Optional[float] = None
    tipo_emprego: Optional[Literal["formal", "autônomo", "desempregado"]] = None
    despesas_fixas: Optional[float] = None
    num_dependentes: Optional[int] = None
    tem_dividas: Optional[bool] = None

    # Resultado
    novo_score: Optional[int] = None
    entrevista_concluida: bool = False
