import pytest
from types import SimpleNamespace

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


@pytest.mark.asyncio
async def test_readiness_is_degraded_but_200_when_optional_db_and_redis_are_absent(monkeypatch):
    import json
    from app import main

    monkeypatch.setattr(main.db_base, "get_engine", lambda: None)
    monkeypatch.setattr(main, "redis_async", None)
    monkeypatch.setattr(main.settings, "REDIS_URL", None)

    response = await main.health_ready()
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["status"] == "degraded"
    assert payload["checks"]["database"]["status"] == "unconfigured"
    assert payload["checks"]["redis"]["status"] == "unconfigured"


@pytest.mark.asyncio
async def test_rate_limiter_enforces_local_fallback_when_redis_fails(monkeypatch):
    from starlette.responses import Response
    from app.core import middleware

    middleware._LOCAL_WINDOWS.clear()
    monkeypatch.setattr(middleware.settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(middleware.settings, "RATE_LIMIT_REQUESTS", 1)
    monkeypatch.setattr(middleware.settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(middleware.settings, "RATE_LIMIT_PATH_PREFIX", "/api")
    monkeypatch.setattr(middleware, "_get_rate_limit_client", lambda: (_ for _ in ()).throw(RuntimeError("redis down")))

    request = SimpleNamespace(
        url=SimpleNamespace(path="/api/stream/query"),
        headers={},
        client=SimpleNamespace(host="127.0.0.1"),
    )

    async def call_next(_request):
        return Response("ok")

    first = await middleware.redis_rate_limit_middleware(request, call_next)
    second = await middleware.redis_rate_limit_middleware(request, call_next)

    assert first.status_code == 200
    assert second.status_code == 429
