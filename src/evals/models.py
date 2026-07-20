"""Modelos de dados Pydantic para a suíte de avaliações (/evals)."""

from typing import Optional
from pydantic import BaseModel, Field


class SimpleStep(BaseModel):
    """Passo individual de um cenário do tipo simple."""
    step: int
    user_message: str
    expected_outcome: Optional[str] = None


class SimpleTestCase(BaseModel):
    """Schema para cenários do tipo /simple."""
    dataset_name: str
    description: str
    steps: list[SimpleStep]
    expected_final_agent: Optional[str] = None
    criteria: list[str] = Field(default_factory=list)
    pre_authenticate: bool = True
    user_cpf: str = "11111111111"


class AIBattlePersona(BaseModel):
    """Schema para personas adversárias do tipo /ai-battle."""
    persona_name: str
    description: str
    attacker_prompt: str
    max_turns: int = 5
    target_objective: str
    prohibited_outcomes: list[str] = Field(default_factory=list)
    pre_authenticate: bool = True
    user_cpf: str = "11111111111"


class JudgeVerdict(BaseModel):
    """Veredito emitido pelo LLM Judge."""
    passed: bool
    score: float = Field(ge=0.0, le=1.0, description="Nota de 0.0 a 1.0")
    reasoning: str
    detected_violations: list[str] = Field(default_factory=list)


class ConversationTurn(BaseModel):
    """Registro de um turno na conversa durante a avaliação."""
    turn: int
    speaker: str  # 'user', 'bot', 'attacker'
    message: str
    active_agent: Optional[str] = None


class EvalRunReport(BaseModel):
    """Relatório final de uma execução de avaliação."""
    run_id: str
    timestamp: str
    eval_type: str  # 'simple' ou 'ai_battle'
    dataset_name: str
    turns: list[ConversationTurn]
    verdict: JudgeVerdict
