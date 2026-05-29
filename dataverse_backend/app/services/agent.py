"""Agentic business analytics coordinator.

The "agent" chooses from safe predefined dataframe tools. It can optionally
ask an LLM to phrase computed facts, but every number comes from pandas.
"""
from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

from .analytics_tools import AnalyticsTools
from .llm_provider import LLMProvider


class DataAnalysisAgent:
    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm_provider = llm_provider or LLMProvider()

    def answer(self, df: pd.DataFrame, question: str, previous_result: dict[str, Any] | None = None) -> dict[str, Any]:
        tools = AnalyticsTools(df)
        query = question.lower().strip()
        limit = self._extract_limit(query)

        if self._asks_for_previous_chart(query) and previous_result:
            result = dict(previous_result)
            result["answer"] = "Here is the chart view for the previous analysis."
            return result

        if any(word in query for word in ["trending", "trend product", "growing product", "growth product"]):
            return tools.trending_products(limit=limit)
        if any(word in query for word in ["declining", "falling", "dropping", "decreasing"]):
            return tools.declining_products(limit=limit)
        if any(word in query for word in ["recommend", "stock more", "stock", "business advice", "what should i"]):
            return tools.recommendations()
        if any(word in query for word in ["forecast", "predict next", "future sales"]):
            return tools.forecast()
        if any(phrase in query for phrase in ["missing", "null", "empty values"]):
            return tools.missing_value_report()
        if any(phrase in query for phrase in ["quality", "duplicates", "wrong column", "data type", "clean"]):
            return tools.data_quality_report()
        if any(word in query for word in ["correlation", "relationship", "related"]):
            return tools.correlation_analysis()
        if any(word in query for word in ["outlier", "anomaly", "unusual"]):
            return tools.outlier_detection()
        if any(word in query for word in ["category", "department", "segment"]):
            return tools.dimension_performance("category", limit=limit)
        if any(word in query for word in ["region", "city", "country", "location"]):
            return tools.dimension_performance("region", limit=limit)
        if any(word in query for word in ["customer", "buyer", "client"]):
            return tools.dimension_performance("customer", limit=limit)
        if any(word in query for word in ["monthly", "weekly", "daily", "revenue trend", "sales trend", "over time"]):
            period = "D" if "daily" in query else "W" if "weekly" in query else "M"
            return tools.revenue_trend(period=period)
        if any(word in query for word in ["top", "highest", "best", "most", "sales", "revenue", "products"]):
            ascending = any(word in query for word in ["lowest", "worst", "least", "bottom"])
            return tools.top_products(limit=limit, ascending=ascending)
        return tools.data_quality_report()

    async def answer_with_optional_llm(
        self,
        df: pd.DataFrame,
        question: str,
        previous_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.answer(df, question, previous_result)
        if not self.llm_provider.is_configured():
            result["llm_provider"] = None
            return result

        prompt = self._build_summary_prompt(question, result)
        try:
            narrative = await self.llm_provider.generate(prompt)
            if narrative:
                result["answer"] = narrative.strip()
                result["llm_provider"] = self.llm_provider.configured_order()[0]
        except Exception as exc:
            result["warnings"].append(f"LLM summary unavailable, used deterministic analysis answer instead: {exc}")
            result["llm_provider"] = None
        return result

    def _extract_limit(self, query: str) -> int:
        match = re.search(r"\b(\d{1,2})\b", query)
        if not match:
            return 10
        return max(1, min(25, int(match.group(1))))

    def _asks_for_previous_chart(self, query: str) -> bool:
        return any(phrase in query for phrase in ["show this as a chart", "chart this", "make a chart", "visualize this"])

    def _build_summary_prompt(self, question: str, result: dict[str, Any]) -> str:
        facts = {
            "intent": result.get("intent"),
            "method": result.get("method"),
            "answer": result.get("answer"),
            "tables": result.get("tables", [])[:1],
            "warnings": result.get("warnings", []),
            "recommendations": result.get("recommendations", []),
        }
        return (
            "Rewrite these computed analytics facts in concise business language. "
            "Use only the facts and numbers provided, include a warning if present, "
            "and do not invent extra calculations.\n\n"
            f"User question: {question}\n"
            f"Computed facts JSON:\n{json.dumps(facts, default=str)}"
        )
