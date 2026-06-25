"""LLM answer composition: grounded, with deterministic fallback."""
import asyncio

from app.core.config import settings
from app.services.session_service import session_service


class _FakeLLM:
    def __init__(self, configured=True, text="Total sales were $15,930, led by Product A."):
        self._configured = configured
        self._text = text

    def is_configured(self):
        return self._configured

    async def generate(self, prompt, system_prompt=None, json_mode=False):
        return self._text


def test_uses_llm_answer_when_available(monkeypatch):
    monkeypatch.setattr(settings, "USE_LLM_NARRATION", True)
    facts = {"business_metrics": {"total_revenue": 15930}}
    out = asyncio.run(
        session_service._compose_chat_answer("total sales", facts, "Total sales are 15930.", provider=_FakeLLM())
    )
    assert "15,930" in out and out != "Total sales are 15930."


def test_falls_back_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "USE_LLM_NARRATION", True)
    out = asyncio.run(
        session_service._compose_chat_answer("q", {}, "DET", provider=_FakeLLM(configured=False))
    )
    assert out == "DET"


def test_falls_back_when_llm_blank(monkeypatch):
    monkeypatch.setattr(settings, "USE_LLM_NARRATION", True)
    out = asyncio.run(
        session_service._compose_chat_answer("q", {}, "DET", provider=_FakeLLM(text="   "))
    )
    assert out == "DET"


def test_respects_narration_disabled(monkeypatch):
    monkeypatch.setattr(settings, "USE_LLM_NARRATION", False)
    out = asyncio.run(
        session_service._compose_chat_answer("q", {}, "DET", provider=_FakeLLM(text="should not be used"))
    )
    assert out == "DET"
