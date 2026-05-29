from __future__ import annotations

import asyncio

from agents.orchestrator import orchestrator_node
from config.llm_providers import ModelRouter
from graph.routing import route_after_orchestrator
from graph.state import DEFAULT_STATE


def test_route_after_orchestrator_prefers_anomaly_with_dataset():
    state = dict(DEFAULT_STATE)
    state["dataset_path"] = "session_storage/demo/dataset.parquet"
    state["agent_plan"] = ["data_analyst", "visualizer"]

    next_node = route_after_orchestrator(state)
    assert next_node == "anomaly_detector"


def test_route_after_orchestrator_without_plan_goes_to_clarifier():
    state = dict(DEFAULT_STATE)
    state["agent_plan"] = []

    next_node = route_after_orchestrator(state)
    assert next_node == "clarifier"


def test_orchestrator_retries_then_succeeds(monkeypatch):
    calls = {"count": 0}

    async def fake_call(self, agent_name, messages, **kwargs):  # noqa: ARG001
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("transient failure")
        return '{"agent_plan": ["data_analyst", "insight_generator"], "reasoning": "ok"}'

    monkeypatch.setattr(ModelRouter, "call", fake_call)

    state = dict(DEFAULT_STATE)
    state["user_message"] = "Analyze sales trend"
    state["dataset_metadata"] = {"columns": ["sales"], "shape": {"rows": 10, "columns": 1}}

    result = asyncio.run(orchestrator_node(state))

    assert calls["count"] == 3
    assert result["agent_plan"] == ["data_analyst", "insight_generator"]
    assert result["current_agent"] == "orchestrator"
    assert result["error"] is None


def test_model_router_fallback_switches_provider(monkeypatch):
    call_order = []

    async def fake_provider_call(self, provider, model, messages, **kwargs):  # noqa: ARG001
        call_order.append((provider, model))
        if provider == "openai":
            raise RuntimeError("rate limited")
        return "ok-from-fallback"

    monkeypatch.setattr(ModelRouter, "_call_provider", fake_provider_call)

    router = ModelRouter()
    output = asyncio.run(
        router.call(
            "data_analyst",
            messages=[{"role": "user", "content": "hello"}],
        )
    )

    assert output == "ok-from-fallback"
    assert len(call_order) >= 2
    assert call_order[0][0] == "openai"
    assert call_order[1][0] == "anthropic"
