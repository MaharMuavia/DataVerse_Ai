"""DeepAnalyze as the preferred agentic engine.

DataVerse's deterministic pipeline computes every number; the LLM layer only
reasons and narrates. These tests pin the wiring that makes DeepAnalyze
(https://github.com/ruc-datalab/DeepAnalyze) the preferred provider when it is
configured, with graceful fallback and zero impact on computed facts.
"""
from __future__ import annotations

import asyncio

import httpx
import pytest

from app.core.config import settings
from app.services.deepanalyze_client import DeepAnalyzeClient
from app.services.llm_provider import LLMProvider


def test_deepanalyze_is_preferred_when_selected(monkeypatch):
    monkeypatch.setattr(settings, "DEEPANALYZE_LOCAL_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    provider = LLMProvider(provider="deepanalyze")
    order = provider.configured_order()
    assert order[0] == "deepanalyze"
    # Other configured providers stay available as fallbacks.
    assert "openai" in order


def test_deepanalyze_absent_without_configuration(monkeypatch):
    monkeypatch.setattr(settings, "DEEPANALYZE_LOCAL_BASE_URL", None)
    monkeypatch.setattr(settings, "DEEPANALYZE_API_KEY", None)
    monkeypatch.setattr(settings, "DEEPANALYZE_API_BASE", None)
    provider = LLMProvider(provider="auto")
    assert "deepanalyze" not in provider.configured_order()


def test_client_speaks_openai_chat_protocol(monkeypatch):
    """The client must call {base}/chat/completions with the configured model."""
    captured: dict = {}

    async def mock_post(self, url, json=None, headers=None):
        captured["url"] = url
        captured["model"] = json["model"]
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "DeepAnalyze says hi"}}]},
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    client = DeepAnalyzeClient(local_base_url="http://127.0.0.1:9999/v1", model="deepanalyze-8b")
    result = asyncio.run(client.generate("summarize the computed facts"))
    assert result == "DeepAnalyze says hi"
    assert captured["url"] == "http://127.0.0.1:9999/v1/chat/completions"
    assert captured["model"] == "deepanalyze-8b"


def test_client_returns_none_on_server_failure(monkeypatch):
    """Provider failures must degrade to deterministic mode, never crash."""

    async def mock_post(self, url, json=None, headers=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    client = DeepAnalyzeClient(local_base_url="http://127.0.0.1:9999/v1")
    assert asyncio.run(client.generate("hello")) is None
