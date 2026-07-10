"""Agent loop: LLM plans over deterministic tools; falls back safely."""
from __future__ import annotations

import asyncio
import json

import pandas as pd
import pytest

from app.services.agent_loop import AgentLoop, AgentTools
from app.services.semantic_mapper import SemanticMapper


class FakeProvider:
    """Scripted stand-in for LLMProvider: returns queued responses in order."""

    def __init__(self, responses: list[str], configured: bool = True):
        self.responses = list(responses)
        self.configured = configured
        self.calls: list[str] = []

    def is_configured(self) -> bool:
        return self.configured

    async def generate(self, prompt: str, *, system_prompt: str | None = None, json_mode: bool = False) -> str | None:
        self.calls.append(prompt)
        if not self.responses:
            return None
        return self.responses.pop(0)


def _sales_df() -> pd.DataFrame:
    rows = []
    for month, widget, gadget in (("2024-04-15", 1000.0, 500.0), ("2024-05-15", 200.0, 550.0)):
        rows.append({"order_date": month, "product": "Widget", "sales_amount": widget, "quantity": 10})
        rows.append({"order_date": month, "product": "Gadget", "sales_amount": gadget, "quantity": 5})
    return pd.DataFrame(rows)


@pytest.fixture()
def context():
    df = _sales_df()
    semantic_map = SemanticMapper().map_dataframe(df, filename="sales.csv")
    facts = {
        "business_metrics": {
            "total_revenue": 2250.0,
            "total_profit": None,
            "transaction_count": 4,
            "top_products": [{"product": "Widget", "revenue": 1200.0}, {"product": "Gadget", "revenue": 1050.0}],
            "revenue_by_month": [{"period": "2024-04", "revenue": 1500.0}, {"period": "2024-05", "revenue": 750.0}],
        },
        "data_quality": {"data_quality_score": 97.0, "warnings": []},
        "prediction": {"status": "skipped", "reason": "not requested"},
        "xai": {"status": "skipped"},
    }
    return df, semantic_map, facts


def test_agent_loop_executes_tools_and_answers(context):
    df, semantic_map, facts = context
    provider = FakeProvider([
        json.dumps({"thought": "Check the KPIs first.", "tool": "get_kpis", "args": {}}),
        json.dumps({"thought": "Now find why revenue dropped.", "tool": "investigate_root_cause",
                    "args": {"question": "why did revenue drop in May?"}}),
        json.dumps({"thought": "I have enough evidence.",
                    "final_answer": "Revenue fell 750 in May, driven by Widget (-800)."}),
    ])
    result = asyncio.run(AgentLoop(provider=provider).run(df, semantic_map, "why did revenue drop in May?", facts))
    assert result is not None
    assert "Widget" in result["answer"]
    tools_used = [step["tool"] for step in result["trace"] if step.get("tool")]
    assert tools_used == ["get_kpis", "investigate_root_cause"]
    # Observations are real computed numbers, not LLM output.
    investigate_step = result["trace"][1]
    assert investigate_step["observation"]["drivers"][0]["value"] == "Widget"


def test_agent_loop_unconfigured_provider_falls_back(context):
    df, semantic_map, facts = context
    provider = FakeProvider([], configured=False)
    result = asyncio.run(AgentLoop(provider=provider).run(df, semantic_map, "top products?", facts))
    assert result is None


def test_agent_loop_malformed_json_falls_back(context):
    df, semantic_map, facts = context
    provider = FakeProvider(["this is not json", "still not { json"])
    result = asyncio.run(AgentLoop(provider=provider).run(df, semantic_map, "top products?", facts))
    assert result is None


def test_agent_loop_respects_max_steps(context):
    df, semantic_map, facts = context
    tool_call = json.dumps({"thought": "loop", "tool": "get_kpis", "args": {}})
    provider = FakeProvider([tool_call] * 10)
    result = asyncio.run(AgentLoop(provider=provider, max_steps=3).run(df, semantic_map, "kpis?", facts))
    # Loop must stop at max_steps; with no final answer it degrades to None (fallback).
    assert result is None
    assert len(provider.calls) <= 4


def test_agent_loop_unknown_tool_reports_error_and_continues(context):
    df, semantic_map, facts = context
    provider = FakeProvider([
        json.dumps({"thought": "use a bad tool", "tool": "hack_the_db", "args": {}}),
        json.dumps({"thought": "ok", "final_answer": "The dataset has 4 transactions."}),
    ])
    result = asyncio.run(AgentLoop(provider=provider).run(df, semantic_map, "how many rows?", facts))
    assert result is not None
    assert "error" in result["trace"][0]["observation"]


def test_tools_are_deterministic_and_json_safe(context):
    df, semantic_map, facts = context
    tools = AgentTools(df, semantic_map, facts)
    for name in ("get_schema", "get_kpis", "get_trend", "scan_quality"):
        first = tools.call(name, {})
        second = tools.call(name, {})
        assert first == second
        json.dumps(first)  # must serialize


def test_whatif_tool_runs_simulation(context):
    df, semantic_map, facts = context
    tools = AgentTools(df, semantic_map, facts)
    result = tools.call("run_whatif", {"column": "sales_amount", "pct_change": 10})
    assert "error" not in result
    json.dumps(result)


def test_catalog_lists_all_tools(context):
    df, semantic_map, facts = context
    tools = AgentTools(df, semantic_map, facts)
    names = {tool["name"] for tool in tools.catalog()}
    assert {"get_schema", "get_kpis", "get_top_segments", "get_trend", "run_whatif",
            "investigate_root_cause", "get_prediction_and_xai", "scan_quality"} <= names
