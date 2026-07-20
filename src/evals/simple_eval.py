"""Executor para avaliações do tipo /simple (cenários direcionados)."""

import uuid
import yaml
import logging
from datetime import datetime, timezone
from pathlib import Path
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from core.agents.router_agent.graph import compiled_router_graph
from evals.models import SimpleTestCase, ConversationTurn, EvalRunReport
from evals.judge import evaluate_conversation
from evals.auth_helper import pre_authenticate_thread

log = logging.getLogger(__name__)


def load_simple_dataset(filepath: str | Path) -> SimpleTestCase:
    """Carrega um dataset YAML do modo /simple e valida com Pydantic."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return SimpleTestCase(**data)


async def run_simple_eval(dataset_path: str | Path) -> EvalRunReport:
    """Executa a suíte simples para um dataset YAML e retorna o relatório final."""
    dataset = load_simple_dataset(dataset_path)
    thread_id = f"eval-simple-{uuid.uuid4()}"
    
    # Adicionado metadado de rastreamento (LangSmith tracing)
    workflow_name = f"simple_{dataset.dataset_name.lower().replace(' ', '_')}"
    config = {
        "configurable": {"thread_id": thread_id},
        "metadata": {"eval_workflow": workflow_name}
    }

    turns: list[ConversationTurn] = []
    turn_counter = 1

    log.info(f"Iniciando /simple eval: {dataset.dataset_name} (thread_id: {thread_id})")

    if dataset.pre_authenticate:
        pre_authenticate_thread(config, dataset.user_cpf)

    for step in dataset.steps:
        # Registrar turno do usuário
        turns.append(ConversationTurn(
            turn=turn_counter,
            speaker="user",
            message=step.user_message,
        ))

        # Invocação do grafo — detecta interrupts pendentes e faz resume
        snapshot = compiled_router_graph.get_state(config)
        pending_interrupts = bool(
            snapshot and snapshot.tasks
            and any(task.interrupts for task in snapshot.tasks)
        )

        if pending_interrupts:
            async for _ in compiled_router_graph.astream_events(
                Command(
                    resume=step.user_message,
                    update={"messages": [HumanMessage(content=step.user_message)]},
                ),
                config=config, version="v2",
            ):
                pass
        else:
            state_input = {
                "messages": [HumanMessage(content=step.user_message)],
                "thread_id": thread_id,
            }
            async for _ in compiled_router_graph.astream_events(state_input, config=config, version="v2"):
                pass

        # Obter estado pós-execução
        snapshot = compiled_router_graph.get_state(config)
        state_values = snapshot.values if snapshot.values else {}
        messages = state_values.get("messages", [])
        active_agent = state_values.get("active_agent", "triage")

        # Captura última resposta da IA — busca o último AIMessage com texto real
        bot_response = "Sem resposta"
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
                bot_response = msg.content
                break

        turns.append(ConversationTurn(
            turn=turn_counter,
            speaker="bot",
            message=bot_response,
            active_agent=active_agent,
        ))

        turn_counter += 1

    # Invocação do LLM Judge com metadados de rastreamento
    log.info(f"Submetendo /simple '{dataset.dataset_name}' ao LLM Judge...")
    verdict = evaluate_conversation(
        dataset_name=dataset.dataset_name,
        description=dataset.description,
        target_objective=f"Executar passos e direcionar para {dataset.expected_final_agent or 'agente adequado'}",
        criteria=dataset.criteria,
        prohibited_outcomes=[],
        turns=turns,
        eval_workflow=f"{workflow_name}_judge",
    )

    run_id = f"simple-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    return EvalRunReport(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        eval_type="simple",
        dataset_name=dataset.dataset_name,
        turns=turns,
        verdict=verdict,
    )
