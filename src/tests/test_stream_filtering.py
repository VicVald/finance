"""
Testes unitários para filtragem de handoff tags no streaming SSE das rotas do agente.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest


def filter_triage_buffer(buffer: str) -> str | None:
    """Helper de teste que espelha a lógica de descarte de handoff tags do streaming."""
    if "HANDOFF" in buffer or "[HANDOFF:" in buffer:
        return None
    return buffer


class TestStreamFiltering:
    """Testa a supressão de mensagens de handoff do streaming."""

    def test_handoff_tag_is_suppressed(self):
        buf1 = "[HANDOFF:credit]"
        buf2 = "[Código interno: HANDOFF:credit]"
        buf3 = "Vou encaminhar você. [HANDOFF:credit]"

        assert filter_triage_buffer(buf1) is None
        assert filter_triage_buffer(buf2) is None
        assert filter_triage_buffer(buf3) is None

    def test_normal_triage_message_is_preserved(self):
        msg = "Autenticação realizada com sucesso. Qual é a sua intenção hoje?"
        assert filter_triage_buffer(msg) == msg
