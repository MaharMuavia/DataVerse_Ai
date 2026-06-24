from __future__ import annotations

import pytest

from app.services.report_composer import ReportComposer
from app.services.report_generator import ReportGenerator

# The compact report is a fixed 2-page executive structure.
EXPECTED_SECTION_ORDER = [
    "Executive Summary",
    "KPI Dashboard",
    "Data Quality Summary",
    "AI-Generated Insights",
    "Visual Insights",
    "Explainable AI",
    "Key Actions",
]


def _test_facts():
    return {
        "filename": "sales.csv",
        "dataset_profile": {"row_count": 120, "column_count": 6},
        "semantic_map": {"dataset_type": "sales_dataset"},
        "data_quality": {
            "data_quality_score": 82.0,
            "missing_cells": 24,
            "missing_pct": 8.0,
            "duplicate_rows": 3,
            "numeric_columns": ["revenue", "cost", "quantity"],
            "categorical_columns": ["category", "region"],
            "date_columns": ["date"],
        },
        "business_metrics": {
            "total_revenue": 50000.0,
            "total_quantity": 1200.0,
            "total_profit": 9000.0,
            "gross_margin": 18.0,
            "transaction_count": 120,
        },
        "trends": {
            "series": [
                {
                    "value_column": "revenue",
                    "direction": "up",
                    "percent_change": 37.5,
                    "volatility": 1200.0,
                    "anomaly_points": [],
                }
            ]
        },
        "correlations": {
            "strong_pairs": [{"column_a": "revenue", "column_b": "cost", "correlation": 0.92}],
            "matrix": {},
        },
        "outliers": {"by_column": {"revenue": {"count": 4}, "cost": {"count": 1}}},
        "prediction": {
            "status": "complete",
            "selected_model": "Ridge",
            "target_column": "revenue",
            "task_type": "regression",
            "test_metrics": {"r2": 0.8123, "rmse": 1234.5, "mae": 980.2},
        },
        "xai": {
            "status": "success",
            "plain_english_explanation": "Model is primarily influenced by cost and quantity.",
            "global_feature_importance": [
                {"feature": "cost", "importance": 0.8},
                {"feature": "quantity", "importance": 0.2},
            ],
        },
        "recommendations": [
            "Clean missing values.",
            "Optimize product mix.",
            "Check pricing strategies.",
            "Add more categories.",
        ],
        "charts": [
            {"type": "line", "title": "Revenue trend", "x_key": "period", "y_key": "revenue", "data": [{"period": "2023-01", "revenue": 8000.0}, {"period": "2023-02", "revenue": 11000.0}]},
            {"type": "bar", "title": "Revenue by category", "x_key": "category", "y_key": "revenue", "data": [{"category": "Hardware", "revenue": 35000.0}]},
            {"type": "bar", "title": "Revenue by product", "x_key": "product", "y_key": "revenue", "data": [{"product": "Widget A", "revenue": 30000.0}]},
        ],
    }


def _sections(facts):
    generator = ReportGenerator()
    composed = ReportComposer().compose(facts)
    sections, charts = generator.build_compact_report_sections(facts, composed)
    return sections, charts


@pytest.mark.asyncio
async def test_compact_report_has_exact_executive_structure():
    facts = _test_facts()
    sections, _ = _sections(facts)
    titles = [s["title"] for s in sections]
    assert titles == EXPECTED_SECTION_ORDER
    # The report closes with Key Actions, not XAI.
    assert titles[-1] == "Key Actions"


@pytest.mark.asyncio
async def test_compact_report_limits_charts_and_orders_them_before_xai():
    facts = _test_facts()
    html = str((await ReportGenerator().generate(title="Dataset Analysis Report", facts=facts))["html"])

    # Exactly two charts, no more.
    assert 0 < html.count('<div class="chart">') <= 2

    # Document order: charts → Explainable AI → Key Actions (closing section).
    assert html.index("Visual Insights") < html.index("Explainable AI") < html.index("Key Actions")
    assert "Dataset Analysis Report" in html


@pytest.mark.asyncio
async def test_compact_report_excludes_metadata_and_model_metrics():
    facts = _test_facts()
    generator = ReportGenerator()
    sections, _ = _sections(facts)
    titles = [s["title"] for s in sections]

    # No raw-metadata snapshot or model-evaluation section.
    assert "Section 1: Dataset Snapshot" not in titles
    assert "Model Performance Evaluation" not in titles
    for s in sections:
        assert "Appendix" not in s["title"]
        assert "Column Profile" not in s["title"]

    html = str((await generator.generate(title="Report", facts=facts))["html"])
    # No model accuracy/F1/R²/RMSE figures leak into the business report.
    assert "0.8123" not in html  # the R² value
    assert "RMSE" not in html
    assert "F1 score" not in html
    assert "coefficient of determination" not in html


@pytest.mark.asyncio
async def test_kpi_dashboard_has_business_metrics():
    facts = _test_facts()
    sections, _ = _sections(facts)
    kpi = next(s for s in sections if s["title"] == "KPI Dashboard")
    labels = {item["label"] for item in kpi["body"]["items"]}
    assert {"Revenue", "Profit", "Margin", "Transactions", "Growth"}.issubset(labels)


@pytest.mark.asyncio
async def test_data_quality_summary_reports_outliers_and_score():
    facts = _test_facts()
    sections, _ = _sections(facts)
    dq = next(s for s in sections if s["title"] == "Data Quality Summary")
    fields = dict(dq["body"]["fields"])
    assert fields["Quality score"] == "82.0 / 100"
    assert fields["Outliers (IQR)"] == "5"  # 4 + 1
    assert "(8.0%)" in fields["Missing values"]


@pytest.mark.asyncio
async def test_explainable_ai_lists_top_factors_in_plain_language():
    facts = _test_facts()
    sections, _ = _sections(facts)
    xai = next(s for s in sections if s["title"] == "Explainable AI")
    bullets = xai["body"]["bullets"]
    assert 1 <= len(bullets) <= 5
    joined = " ".join(bullets)
    assert "cost" in joined and "strongest driver" in joined
    assert "% of the predicted outcome" in joined


@pytest.mark.asyncio
async def test_key_actions_has_three_to_five_recommendations():
    facts = _test_facts()
    sections, _ = _sections(facts)
    actions = next(s for s in sections if s["title"] == "Key Actions")
    bullets = actions["body"]["bullets"]
    assert 3 <= len(bullets) <= 5


@pytest.mark.asyncio
async def test_executive_and_ai_insights_do_not_repeat():
    facts = _test_facts()
    sections, _ = _sections(facts)

    def _norm(value):
        import re
        text = re.sub(r"<[^>]+>", " ", str(value))
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    seen = set()
    for section in sections:
        body = section.get("body") or {}
        for key in ("bullets", "lines"):
            for item in body.get(key, []) or []:
                fp = _norm(item)
                if not fp:
                    continue
                assert fp not in seen, f"repeated content across sections: {item!r}"
                seen.add(fp)


@pytest.mark.asyncio
async def test_compact_report_pdf_and_html_render():
    facts = _test_facts()
    result = await ReportGenerator().generate(title="Dataset Analysis Report", facts=facts)
    assert isinstance(result["pdf"], bytes)
    assert len(result["pdf"]) > 100
    assert "Headline Metrics" not in str(result["html"])  # KPI cards render once, in the dashboard
