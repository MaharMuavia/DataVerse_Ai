"""Root-Cause Investigator: deterministic driver decomposition with receipts."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.root_cause import investigate
from app.services.semantic_mapper import SemanticMapper


def _sales_df_with_planted_drop() -> pd.DataFrame:
    """Two months of sales; in May, Widget revenue collapses (the planted driver).

    April: Widget 1000, Gadget 500, Gizmo 500  -> total 2000
    May:   Widget  200, Gadget 550, Gizmo 450  -> total 1200
    Delta = -800; Widget contributes -800 * 100%? Widget -800, Gadget +50, Gizmo -50.
    """
    rows = []
    april = [("Widget", "North", 1000.0), ("Gadget", "South", 500.0), ("Gizmo", "North", 500.0)]
    may = [("Widget", "North", 200.0), ("Gadget", "South", 550.0), ("Gizmo", "North", 450.0)]
    for product, region, amount in april:
        rows.append({"order_date": "2024-04-15", "product": product, "region": region, "sales_amount": amount, "quantity": 10})
    for product, region, amount in may:
        rows.append({"order_date": "2024-05-15", "product": product, "region": region, "sales_amount": amount, "quantity": 8})
    return pd.DataFrame(rows)


@pytest.fixture()
def sales_df() -> pd.DataFrame:
    return _sales_df_with_planted_drop()


@pytest.fixture()
def semantic_map(sales_df: pd.DataFrame) -> dict:
    return SemanticMapper().map_dataframe(sales_df, filename="sales.csv")


def test_investigator_finds_planted_driver(sales_df, semantic_map):
    result = investigate(sales_df, semantic_map, question="Why did revenue drop in May?")
    assert result["status"] == "complete"
    assert result["metric"] == "revenue"
    assert result["period_b"] == "2024-05"
    assert result["period_a"] == "2024-04"
    assert result["delta"] == pytest.approx(-800.0)

    # The top driver overall must be Widget, explaining 100% of the -800 drop.
    top = result["drivers"][0]
    assert top["value"] == "Widget"
    assert top["contribution"] == pytest.approx(-800.0)
    assert top["share_of_delta"] == pytest.approx(1.0, abs=0.01)


def test_investigator_emits_trace_with_receipts(sales_df, semantic_map):
    result = investigate(sales_df, semantic_map, question="why did sales fall in may")
    steps = result["steps"]
    assert len(steps) >= 3
    for step in steps:
        assert step["action"]
        assert step["finding"]
    # At least one step carries a provenance receipt with a plain formula.
    receipts = [s["receipt"] for s in steps if s.get("receipt")]
    assert receipts
    assert all(r.get("formula_plain") for r in receipts)


def test_investigator_defaults_to_biggest_drop_without_named_period(sales_df, semantic_map):
    result = investigate(sales_df, semantic_map, question="why did revenue decrease?")
    assert result["status"] == "complete"
    assert result["period_b"] == "2024-05"


def test_investigator_chart_is_signed_contributions(sales_df, semantic_map):
    result = investigate(sales_df, semantic_map, question="Why did revenue drop in May?")
    chart = result["chart"]
    assert chart["type"] == "bar"
    assert chart["data"]
    values = {row[chart["x_key"]]: row[chart["y_key"]] for row in chart["data"]}
    assert values["Widget"] == pytest.approx(-800.0)


def test_investigator_unsupported_without_date_column(semantic_map):
    df = pd.DataFrame({"product": ["A", "B"], "sales_amount": [10.0, 20.0]})
    smap = SemanticMapper().map_dataframe(df)
    result = investigate(df, smap, question="why did revenue drop?")
    assert result["status"] == "unsupported"
    assert result["reason"]


def test_investigator_unsupported_with_single_period():
    df = pd.DataFrame(
        {
            "order_date": ["2024-05-01", "2024-05-20"],
            "product": ["A", "B"],
            "sales_amount": [10.0, 20.0],
        }
    )
    smap = SemanticMapper().map_dataframe(df)
    result = investigate(df, smap, question="why did revenue drop?")
    assert result["status"] == "unsupported"
    assert "period" in result["reason"].lower()


def test_investigator_price_volume_split(sales_df, semantic_map):
    result = investigate(sales_df, semantic_map, question="Why did revenue drop in May?")
    pv = result.get("price_volume")
    if pv is not None:
        # The three effects must reconstruct the delta exactly (identity split).
        total = pv["price_effect"] + pv["volume_effect"] + pv["mix_effect"]
        assert total == pytest.approx(result["delta"], rel=1e-6)


def test_investigator_is_deterministic(sales_df, semantic_map):
    a = investigate(sales_df, semantic_map, question="Why did revenue drop in May?")
    b = investigate(sales_df, semantic_map, question="Why did revenue drop in May?")
    assert a == b


def test_investigator_rise_question_targets_increase():
    rows = []
    for amount, month in ((100.0, "2024-04-10"), (400.0, "2024-05-10")):
        rows.append({"order_date": month, "product": "A", "sales_amount": amount})
        rows.append({"order_date": month, "product": "B", "sales_amount": amount / 2})
    df = pd.DataFrame(rows * 3)
    smap = SemanticMapper().map_dataframe(df)
    result = investigate(df, smap, question="why did revenue increase?")
    assert result["status"] == "complete"
    assert result["delta"] > 0
