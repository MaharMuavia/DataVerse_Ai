import pytest

from app.api import routes
from app.core import llm as llm_module


@pytest.mark.asyncio
async def test_delete_session_clears_memory_and_workflow_cache(monkeypatch):
    class MemoryStore:
        def __init__(self):
            self.sessions = {"session-1": {"state": "active"}}

    memory_store = MemoryStore()
    cleared = {}

    monkeypatch.setattr(
        "app.memory.conversation_memory.get_memory_store",
        lambda: memory_store,
    )
    monkeypatch.setattr(
        routes,
        "clear_workflow_session",
        lambda session_id: cleared.setdefault("session_id", session_id),
    )

    result = await routes.delete_session("session-1")

    assert result["deleted"] is True
    assert result["session_id"] == "session-1"
    assert "session-1" not in memory_store.sessions
    assert cleared["session_id"] == "session-1"


@pytest.mark.asyncio
async def test_get_llm_initializes_with_openai_when_anthropic_unset(monkeypatch):
    llm_module.reset_llm()

    monkeypatch.setattr(llm_module.settings, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(llm_module.settings, "OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(llm_module.settings, "OPENAI_API_BASE", None)
    monkeypatch.setattr(llm_module.settings, "OPENAI_CHAT_MODEL", "gpt-5.2")

    llm_client = await llm_module.get_llm()

    assert llm_client is not None
    assert hasattr(llm_client, "ainvoke")

    llm_module.reset_llm()
