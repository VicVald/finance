from typing import Annotated, Literal, Optional
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class ExchangeState(BaseModel):
    """Estado local do subgraph de câmbio."""

    messages: Annotated[list, add_messages] = Field(default_factory=list)

    ultima_moeda_consultada: Optional[str] = None
    ultima_cotacao: Optional[dict] = None
    api_fonte: Optional[Literal["brasilapi", "awesomeapi"]] = None

    # Campo bridge para handoff reverso (retorno à triagem)
    active_agent: Optional[str] = None
