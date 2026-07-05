"""Report wording/visual coherence: no contradictory trends, no dark theme,
no duplicate-flavour charts, no boilerplate actions that contradict the data."""
import asyncio
import re

from app.services.report_composer import ReportComposer
from app.services.report_generator import ReportGenerator


def _facts_with_contradictory_trend():
    return {
        "filename": "retail.csv",
        "dataset_profile": {"row_count": 35000, "column_count": 20},
        "semantic_map": {"dataset_type": "retail_sales"},
        "data_quality": {
            "data_quality_score": 97.0,
            "missing_cells": 0,
            "missing_pct": 0.0,
            "duplicate_rows": 0,
            "numeric_columns": ["quantity", "total_sales"],
            "categorical_columns": ["region"],
            "date_columns": [],
            "text_columns": [],
            "high_cardinality_columns": ["product_id"],
            "missing_values_by_column": {},
        },
        "business_metrics": {
            "total_revenue": 2248662.62,
            "total_profit": 336938.93,
            "gross_margin": 15.0,
            "transaction_count": 35000,
            "top_products": [{"product": "PROD_1", "revenue": 148000.0}],
            "top_regions": [{"region": "Punjab", "revenue": 1279763.6}],
            "revenue_by_month": [],
        },
        "product_analysis": {},
        # slope says "up" but the period change is negative — wording must not contradict
        "trends": {"series": [{
            "value_column": "quantity", "direction": "up", "percent_change": -3.4,
            "slope": 0.001, "volatility": 0.03, "anomaly_points": [], "first_value": 100, "last_value": 96.6,
        }]},
        "correlations": {"strong_pairs": [], "matrix": {}},
        "outliers": {"total_outlier_cells": 11421, "by_column": {"unit_price": {"count": 11421}}},
        "prediction": {"status": "skipped"},
        "xai": {"status": "skipped"},
        "recommendations": [
            "Review missing values, duplicate rows, high-cardinality columns, and outliers before operational decisions.",
        ],
        "warnings": [],
        "charts": [],
        "executive_summary": "",
        "key_insights": [],
    }


def _all_text(sections) -> str:
    chunks = []
    for s in sections:
        body = s.get("body")
        chunks.append(str(s.get("title", "")))
        chunks.append(str(body))
    return " ".join(chunks)


def test_trend_wording_never_contradicts_the_change_sign():
    facts = _facts_with_contradictory_trend()
    composed = ReportComposer().compose(facts)
    text = _all_text(composed["sections"]) + " " + " ".join(composed.get("key_insights") or [])
    assert not re.search(r"moved up \(change -", text), "verb contradicts negative change"
    assert not re.search(r"declined [\d.]+% .*direction: up", text), "decline text contradicts direction"
    assert "trend direction:" not in text, "raw slope parenthetical should not leak into prose"


def test_key_actions_never_mention_clean_dimensions():
    facts = _facts_with_contradictory_trend()  # missing=0, dupes=0, quality 97
    gen = ReportGenerator()
    composed = ReportComposer().compose(facts)
    sections, _ = gen.build_compact_report_sections(facts, composed, {})
    actions = next(s for s in sections if s["title"] == "Key Actions")
    joined = " ".join(str(b).lower() for b in actions["body"]["bullets"])
    assert "missing values" not in joined, joined
    assert "duplicate rows" not in joined, joined


def test_chart_selection_prefers_diverse_dimensions():
    gen = ReportGenerator()
    charts = [
        {"type": "bar", "title": "Top 10 Products by Revenue", "x_key": "product", "y_key": "revenue",
         "data": [{"product": "A", "revenue": 10}]},
        {"type": "bar", "title": "Top 10 Products by Quantity", "x_key": "product", "y_key": "quantity",
         "data": [{"product": "A", "quantity": 5}]},
        {"type": "bar", "title": "Region/Store Performance", "x_key": "region", "y_key": "revenue",
         "data": [{"region": "Punjab", "revenue": 9}]},
    ]
    selected = gen._select_useful_charts(charts, "retail_sales")[:2]
    keys = [c.get("x_key") for c in selected]
    assert len(set(keys)) == 2, f"two charts over the same dimension: {[c['title'] for c in selected]}"


def test_html_report_is_light_theme():
    facts = _facts_with_contradictory_trend()
    generated = asyncio.run(ReportGenerator().generate(title="Theme Check", facts=facts, xai_output={}))
    html = str(generated["html"])
    assert "color-scheme: light" in html, "report must be light theme"
    assert "#0B1120" not in html, "dark background palette must be gone"
