"""
Endpoint SSE para streaming de respostas dos agentes LangGraph.

Rotas:
  POST /api/v1/agent/stream  → envia mensagem e recebe tokens em streaming
  POST /api/v1/agent/resume  → retoma o grafo após interrupt() (ex: oferta de entrevista)
"""
import json
import logging
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from core.auth.routes import get_current_user
from core.agents.router_agent.graph import compiled_router_graph
from core.agents.router_agent.state import RouterState

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None  # None → nova thread (UUID gerado automaticamente)


class ResumeRequest(BaseModel):
    thread_id: str
    resume_value: str | bool | dict  # resposta após interrupt()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _sse_event(event_type: str, data: dict | str) -> dict:
    return {"event": event_type, "data": json.dumps(data, ensure_ascii=False)}


# ─── Gerador de eventos SSE ───────────────────────────────────────────────────

async def _stream_agent(
    message: str,
    thread_id: str,
    current_user: dict,
) -> AsyncIterator[dict]:
    """
    Processa uma mensagem no grafo e emite eventos SSE:
      - token: chunk de texto do LLM
      - interrupt: grafo pausou aguardando resposta do usuário
      - done: fim do processamento
      - error: erro inesperado
    """
    from langchain_core.messages import HumanMessage, AIMessageChunk

    config = _make_config(thread_id)

    # Recupera ou inicializa o estado da thread
    try:
        snapshot = compiled_router_graph.get_state(config)
        current_state = snapshot.values if snapshot.values else {}
    except Exception:
        current_state = {}

    # Injeta dados do usuário autenticado no estado inicial se ainda não autenticado
    initial_update = {
        "messages": [HumanMessage(content=message)],
        "thread_id": thread_id,
        "current_user_cpf_hash": current_user["cpf_hash"],
    }

    triage_buffer = ""

    try:
        async for event in compiled_router_graph.astream_events(
            initial_update,
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            data = event.get("data", {})
            node_name = event.get("metadata", {}).get("langgraph_node", "")

            # ── Token de texto do LLM ────────────────────────────────────────
            if kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    content = chunk.content

                    if node_name == "triage_node":
                        triage_buffer += content
                    else:
                        # Se havíamos acumulado texto do triage sem handoff, emite agora
                        if triage_buffer:
                            if "HANDOFF" not in triage_buffer:
                                yield _sse_event("token", {"content": triage_buffer})
                            triage_buffer = ""

                        clean_content = content.replace("[RETURN_TRIAGE]", "")
                        if clean_content:
                            yield _sse_event("token", {"content": clean_content})

        # Ao final do stream, libera o buffer do triage se não continha handoff
        if triage_buffer and "HANDOFF" not in triage_buffer:
            yield _sse_event("token", {"content": triage_buffer})

        # ── Após o loop: inspeciona estado para detectar interrupt pendente ──
        # Subgraphs pausam o astream_events sem exception — o interrupt fica
        # registrado em get_state().tasks com a lista de interrupts.
        interrupt_emitted = False
        try:
            final_snapshot = compiled_router_graph.get_state(config)
            if final_snapshot and final_snapshot.tasks:
                for task in final_snapshot.tasks:
                    if task.interrupts:
                        for intr in task.interrupts:
                            val = intr.value if hasattr(intr, "value") else intr
                            if isinstance(val, dict):
                                yield _sse_event("interrupt", {
                                    "message": val.get("message", ""),
                                    "type": val.get("type", ""),
                                })
                                interrupt_emitted = True
            final_state = final_snapshot.values if final_snapshot and final_snapshot.values else {}
            is_ended = final_state.get("is_conversation_ended", False)
        except Exception:
            is_ended = False

        yield _sse_event("done", {"thread_id": thread_id, "is_conversation_ended": is_ended})

    except Exception as e:
        log.error(f"Erro no streaming do agente [thread={thread_id}]: {e}", exc_info=True)
        # Fallback: tenta detectar interrupt mesmo em caso de exceção
        try:
            final_snapshot = compiled_router_graph.get_state(config)
            if final_snapshot and final_snapshot.tasks:
                for task in final_snapshot.tasks:
                    if task.interrupts:
                        for intr in task.interrupts:
                            val = intr.value if hasattr(intr, "value") else intr
                            if isinstance(val, dict):
                                yield _sse_event("interrupt", {
                                    "message": val.get("message", ""),
                                    "type": val.get("type", ""),
                                })
            is_ended = False
            yield _sse_event("done", {"thread_id": thread_id, "is_conversation_ended": is_ended})
        except Exception:
            yield _sse_event("error", {"message": "Erro interno. Tente novamente."})


async def _stream_resume(
    thread_id: str,
    resume_value: str | bool | dict,
) -> AsyncIterator[dict]:
    """
    Retoma o grafo após interrupt() usando Command(resume=...) e emite tokens SSE.
    """
    from langchain_core.messages import AIMessageChunk
    from langgraph.types import Command

    config = _make_config(thread_id)

    try:
        async for event in compiled_router_graph.astream_events(
            Command(resume=resume_value),
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            data = event.get("data", {})

            if kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    clean_content = chunk.content.replace("[RETURN_TRIAGE]", "")
                    if clean_content:
                        yield _sse_event("token", {"content": clean_content})

        # Verifica interrupt pendente após resume (ex: segundo interrupt no fluxo)
        try:
            final_snapshot = compiled_router_graph.get_state(config)
            if final_snapshot and final_snapshot.tasks:
                for task in final_snapshot.tasks:
                    if task.interrupts:
                        for intr in task.interrupts:
                            val = intr.value if hasattr(intr, "value") else intr
                            if isinstance(val, dict):
                                yield _sse_event("interrupt", {
                                    "message": val.get("message", ""),
                                    "type": val.get("type", ""),
                                })
            final_state = final_snapshot.values if final_snapshot and final_snapshot.values else {}
            is_ended = final_state.get("is_conversation_ended", False)
        except Exception:
            is_ended = False

        yield _sse_event("done", {"thread_id": thread_id, "is_conversation_ended": is_ended})

    except Exception as e:
        log.error(f"Erro no resume [thread={thread_id}]: {e}", exc_info=True)
        yield _sse_event("error", {"message": "Erro ao retomar conversa."})


# ─── Rotas ────────────────────────────────────────────────────────────────────

@router.post("/stream")
async def stream_agent(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Recebe uma mensagem do cliente e retorna a resposta do agente via SSE (streaming de tokens).

    O `thread_id` identifica a conversa. Se não fornecido, uma nova thread é criada.
    Retorna:
      - event: token    → data: {"content": "..."}
      - event: interrupt → data: {"message": "...", "type": "..."}
      - event: done     → data: {"thread_id": "..."}
      - event: error    → data: {"message": "..."}
    """
    thread_id = req.thread_id or str(uuid.uuid4())

    return EventSourceResponse(
        _stream_agent(
            message=req.message,
            thread_id=thread_id,
            current_user=current_user,
        ),
        media_type="text/event-stream",
    )


@router.post("/resume")
async def resume_agent(
    req: ResumeRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Retoma o grafo após um interrupt() — ex: cliente aceitou ou recusou entrevista.

    O `resume_value` é injetado via Command(resume=...) no astream_events.
    Retorna o mesmo formato SSE do endpoint /stream.
    """
    return EventSourceResponse(
        _stream_resume(
            thread_id=req.thread_id,
            resume_value=req.resume_value,
        ),
        media_type="text/event-stream",
    )
