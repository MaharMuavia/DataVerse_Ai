"""LLM plan→act→observe loop over deterministic analysis tools.

This makes the "agentic" claim literal: for each chat question, the LLM decides
which deterministic tool to call next (KPIs, segments, trends, what-if,
root-cause, prediction/XAI, quality), observes the computed result, and repeats
until it can answer — max `max_steps` tool calls. Every number the agent sees
comes from pandas/scikit-learn tools; the LLM only plans and phrases.

The loop degrades safely: if no provider is configured, the JSON protocol
breaks twice, or no final answer arrives within budget, `run` returns None and
the caller falls back to the deterministic answer path (offline mode intact).
"""
from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

from .data_quality import json_safe
from .llm_provider import LLMProvider
from .progress_bus import progress_bus
from .root_cause import investigate
from .whatif import simulate

MAX_STEPS_DEFAULT = 5
OBSERVATION_CHAR_BUDGET = 1600


class AgentTools:
    """Deterministic tools the agent can call. All numbers come from pandas."""

    def __init__(self, df: pd.DataFrame, semantic_map: dict[str, Any], facts: dict[str, Any]):
        self.df = df
        self.semantic_map = semantic_map or {}
        self.facts = facts or {}

    def catalog(self) -> list[dict[str, Any]]:
        return [
            {"name": "get_schema", "args": {}, "description": "Columns, dtypes, row count, and detected dataset type."},
            {"name": "get_kpis", "args": {}, "description": "Business KPIs: total revenue, profit, quantity, transactions, top products/categories."},
            {"name": "get_top_segments", "args": {"dimension": "product|category|region|customer", "limit": "int"}, "description": "Ranked revenue by a dimension."},
            {"name": "get_trend", "args": {"period": "M|D"}, "description": "Revenue over time (monthly or daily)."},
            {"name": "run_whatif", "args": {"column": "str", "pct_change": "float"}, "description": "Simulate changing a numeric column by a percentage and recompute KPIs."},
            {"name": "investigate_root_cause", "args": {"question": "str"}, "description": "Explain WHY a metric changed: period delta, ranked drivers per dimension, price-vs-volume split."},
            {"name": "get_prediction_and_xai", "args": {}, "description": "Trained model status, metrics, top features, and counterfactual explanations."},
            {"name": "scan_quality", "args": {}, "description": "Data quality score and warnings."},
        ]

    def call(self, tool: str, args: dict[str, Any] | None) -> dict[str, Any]:
        args = args or {}
        handler = getattr(self, f"_tool_{tool}", None)
        if handler is None:
            return {"error": f"Unknown tool '{tool}'. Valid tools: {', '.join(t['name'] for t in self.catalog())}"}
        try:
            return json_safe(handler(**args))
        except TypeError as exc:
            return {"error": f"Bad arguments for '{tool}': {exc}"}
        except Exception as exc:
            return {"error": f"{tool} failed: {type(exc).__name__}: {exc}"}

    def _tool_get_schema(self) -> dict[str, Any]:
        return {
            "rows": int(len(self.df)),
            "columns": [{"name": str(col), "dtype": str(self.df[col].dtype)} for col in self.df.columns],
            "dataset_type": self.semantic_map.get("dataset_type"),
        }

    def _tool_get_kpis(self) -> dict[str, Any]:
        bm = self.facts.get("business_metrics") or {}
        return {
            key: bm.get(key)
            for key in (
                "total_revenue", "total_profit", "total_quantity", "total_expenses",
                "gross_margin", "average_order_value", "transaction_count",
            )
        } | {
            "top_products": (bm.get("top_products") or [])[:5],
            "top_categories": (bm.get("top_categories") or [])[:5],
        }

    def _tool_get_top_segments(self, dimension: str = "product", limit: int = 5) -> dict[str, Any]:
        bm = self.facts.get("business_metrics") or {}
        key = {
            "product": "top_products", "category": "top_categories",
            "region": "top_regions", "customer": "top_customers",
        }.get(str(dimension).lower())
        if not key:
            return {"error": f"Unknown dimension '{dimension}'. Use product, category, region, or customer."}
        rows = (bm.get(key) or [])[: max(1, min(int(limit), 20))]
        if not rows:
            return {"error": f"No {dimension} ranking is available for this dataset."}
        return {"dimension": dimension, "ranking": rows}

    def _tool_get_trend(self, period: str = "M") -> dict[str, Any]:
        bm = self.facts.get("business_metrics") or {}
        rows = bm.get("revenue_by_month") if str(period).upper() != "D" else bm.get("revenue_by_date")
        if not rows:
            return {"error": "No time trend is available (missing date or revenue column)."}
        return {"period": str(period).upper(), "revenue_over_time": rows[-24:]}

    def _tool_run_whatif(self, column: str, pct_change: float) -> dict[str, Any]:
        result = simulate(self.df, str(column), float(pct_change), semantic_map=self.semantic_map)
        # Keep the observation small: scenario deltas, not the full KPI cards.
        return {
            "column": column,
            "pct_change": pct_change,
            "kpi_changes": result.get("deltas") or [],
        }

    def _tool_investigate_root_cause(self, question: str = "") -> dict[str, Any]:
        result = investigate(self.df, self.semantic_map, question=question)
        if result.get("status") != "complete":
            return {"error": result.get("reason") or "Root-cause investigation was not possible."}
        return {
            "metric": result["metric"],
            "period_a": result["period_a"],
            "period_b": result["period_b"],
            "delta": result["delta"],
            "pct_change": result["pct_change"],
            "drivers": result["drivers"][:5],
            "price_volume": result["price_volume"],
            "narrative": result["narrative"],
        }

    def _tool_get_prediction_and_xai(self) -> dict[str, Any]:
        prediction = self.facts.get("prediction") or {}
        xai = self.facts.get("xai") or {}
        counterfactuals = [
            cf.get("sentence")
            for row in (xai.get("counterfactuals") or [])
            for cf in (row.get("counterfactuals") or [])
        ]
        return {
            "status": prediction.get("status"),
            "reason": prediction.get("reason"),
            "model": prediction.get("selected_model"),
            "target": prediction.get("target_column"),
            "metrics": prediction.get("test_metrics"),
            "top_features": (xai.get("top_features") or [])[:5],
            "counterfactuals": counterfactuals[:4],
        }

    def _tool_scan_quality(self) -> dict[str, Any]:
        quality = self.facts.get("data_quality") or {}
        return {
            "score": quality.get("data_quality_score"),
            "missing_cells": quality.get("missing_cells"),
            "warnings": (quality.get("warnings") or [])[:6],
        }


def _extract_json(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    for candidate in (cleaned, *re.findall(r"\{.*\}", cleaned, flags=re.DOTALL)):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def _truncate(observation: dict[str, Any]) -> str:
    text = json.dumps(observation, default=str)
    if len(text) > OBSERVATION_CHAR_BUDGET:
        text = text[:OBSERVATION_CHAR_BUDGET] + "…(truncated)"
    return text


SYSTEM_PROMPT = (
    "You are the planning brain of DataVerse AI, a verifiable data analyst. You cannot compute "
    "numbers yourself; you investigate by calling deterministic tools and reading their results. "
    "Respond with ONLY a single JSON object, no prose. Either:\n"
    '  {"thought": "...", "tool": "<tool name>", "args": {...}}\n'
    "to call a tool, or:\n"
    '  {"thought": "...", "final_answer": "..."}\n'
    "when the observations already contain everything needed. The final answer must be 2-5 "
    "sentences, cite ONLY numbers that appear in the observations, and directly answer the "
    "user's question. Never invent or estimate a number. Prefer the fewest tool calls that "
    "fully answer the question."
)


class AgentLoop:
    def __init__(self, provider: LLMProvider | None = None, max_steps: int = MAX_STEPS_DEFAULT):
        self.provider = provider if provider is not None else LLMProvider()
        self.max_steps = max_steps

    async def run(
        self,
        df: pd.DataFrame,
        semantic_map: dict[str, Any],
        question: str,
        facts: dict[str, Any],
        progress_session_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Run the loop. Returns {answer, trace, provider} or None to signal fallback."""
        if not self.provider.is_configured():
            return None
        tools = AgentTools(df, semantic_map, facts)
        catalog_text = "\n".join(
            f"- {tool['name']}({json.dumps(tool['args'])}): {tool['description']}" for tool in tools.catalog()
        )
        schema = tools.call("get_schema", {})
        trace: list[dict[str, Any]] = []
        parse_failures = 0

        for step_index in range(self.max_steps + 1):
            transcript = "\n".join(
                f"Step {i + 1}: called {step['tool']}({json.dumps(step.get('args') or {})}) -> {_truncate(step['observation'])}"
                for i, step in enumerate(trace)
            ) or "(no tools called yet)"
            prompt = (
                f"User question: {question}\n\n"
                f"Dataset schema: {json.dumps(schema, default=str)[:900]}\n\n"
                f"Available tools:\n{catalog_text}\n\n"
                f"Investigation so far:\n{transcript}\n\n"
                + (
                    "You have used all tool calls. You MUST reply with final_answer now."
                    if step_index >= self.max_steps
                    else "Reply with the next single JSON action."
                )
            )
            try:
                raw = await self.provider.generate(prompt, system_prompt=SYSTEM_PROMPT, json_mode=True)
            except Exception:
                raw = None
            action = _extract_json(raw)
            if action is None:
                parse_failures += 1
                if parse_failures >= 2:
                    return None
                continue

            if action.get("final_answer"):
                answer = str(action["final_answer"]).strip()
                if not answer:
                    return None
                if progress_session_id:
                    progress_bus.complete_stage(progress_session_id, "agent_loop", f"{len(trace)} tool calls")
                return {
                    "answer": answer,
                    "trace": [
                        {
                            "thought": step.get("thought"),
                            "tool": step.get("tool"),
                            "args": step.get("args"),
                            "observation": step.get("observation"),
                        }
                        for step in trace
                    ],
                    "provider": getattr(self.provider, "active_provider", None) or "llm",
                }

            tool = str(action.get("tool") or "")
            if not tool or step_index >= self.max_steps:
                return None
            args = action.get("args") if isinstance(action.get("args"), dict) else {}
            if progress_session_id:
                progress_bus.start_stage(
                    progress_session_id, "agent_loop",
                    f"Agent step {len(trace) + 1}: {tool}",
                    str(action.get("thought") or "")[:140] or None,
                )
            observation = tools.call(tool, args)
            trace.append({"thought": action.get("thought"), "tool": tool, "args": args, "observation": observation})
        return None
