import pandas as pd
import pytest

from app.services.agent import DataAnalysisAgent
from app.services.analytics_tools import AnalyticsTools
from app.services.data_profiler import profile_dataframe
from app.services.llm_provider import LLMProvider


def sample_sales_df():
    return pd.DataFrame(
        {
            "order_date": [
                "2026-01-05",
                "2026-01-12",
                "2026-02-02",
                "2026-02-09",
                "2026-03-03",
                "2026-03-15",
            ],
            "product_name": ["Alpha", "Beta", "Alpha", "Beta", "Alpha", "Beta"],
            "category": ["A", "B", "A", "B", "A", "B"],
            "region": ["North", "South", "North", "South", "North", "South"],
            "customer_id": ["c1", "c2", "c1", "c3", "c4", "c3"],
            "quantity": [10, 20, 20, 15, 70, 10],
            "revenue": [100, 300, 200, 250, 900, 120],
            "profit": [30, 90, 70, 80, 300, 20],
        }
    )


def test_profile_dataframe_detects_business_columns_and_quality():
    profile = profile_dataframe(sample_sales_df())

    assert profile["row_count"] == 6
    assert profile["semantic_columns"]["date"] == "order_date"
    assert profile["semantic_columns"]["product"] == "product_name"
    assert profile["semantic_columns"]["revenue"] == "revenue"
    assert profile["semantic_columns"]["quantity"] == "quantity"
    assert profile["semantic_columns"]["category"] == "category"
    assert profile["semantic_columns"]["region"] == "region"
    assert profile["semantic_columns"]["customer"] == "customer_id"
    assert profile["quality"]["duplicate_rows"] == 0


def test_trending_products_uses_recent_vs_previous_period_not_total_sales():
    result = AnalyticsTools(sample_sales_df()).trending_products(limit=3)

    rows = result["table"]["rows"]
    assert rows[0]["product_name"] == "Alpha"
    assert rows[0]["recent_revenue"] == 900
    assert rows[0]["previous_revenue"] == 200
    assert rows[0]["growth_pct"] == 350.0
    assert result["chart"]["type"] == "bar"


def test_trending_products_falls_back_when_date_column_missing():
    df = sample_sales_df().drop(columns=["order_date"])
    result = AnalyticsTools(df).trending_products(limit=2)

    assert result["warning"]
    assert result["intent"] == "top_products"
    assert result["table"]["rows"][0]["product_name"] == "Alpha"


def test_agent_answers_top_products_with_table_and_chart():
    result = DataAnalysisAgent().answer(sample_sales_df(), "Which products have the highest sales?")

    assert result["intent"] == "top_products"
    assert "Alpha" in result["answer"]
    assert result["tables"][0]["rows"][0]["product_name"] == "Alpha"
    assert result["charts"][0]["type"] == "bar"
    assert "Calculated" in result["method"]


@pytest.mark.asyncio
async def test_llm_provider_prefers_configured_provider_and_falls_back(monkeypatch):
    calls = []

    async def fake_openai(prompt):
        calls.append("openai")
        raise RuntimeError("openai unavailable")

    async def fake_gemini(prompt):
        calls.append("gemini")
        return "gemini narrative"

    provider = LLMProvider(
        provider="openai",
        openai_api_key="x",
        gemini_api_key="y",
        openai_generate=fake_openai,
        gemini_generate=fake_gemini,
    )

    assert await provider.generate("summarize") == "gemini narrative"
    assert calls == ["openai", "gemini"]
