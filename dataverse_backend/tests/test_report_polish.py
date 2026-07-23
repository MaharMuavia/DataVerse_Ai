"""Report-polish invariants: business-readable prose, no repetition, honest visuals.

These tests pin the fixes from docs/markdown/02_architecture_and_design/REPORT_QUALITY_DESIGN.md:
no internal jargon reaches the reader, the same trend fact is never restated in
different words, XAI groups one-hot dummies by source column, chart titles match
the data, and charts carry axis context.
"""
from __future__ import annotations

import re

from app.services.report_composer import ReportComposer
from app.services.report_generator import ReportGenerator, _line_svg, _section_plaintext


def _facts(**overrides):
    base = {
        "filename": "sales.csv",
        "dataset_profile": {"row_count": 120, "column_count": 6},
        "semantic_map": {"dataset_type": "sales_dataset"},
        "data_quality": {
            "data_quality_score": 100.0,
            "missing_cells": 0,
            "missing_pct": 0.0,
            "duplicate_rows": 0,
            "numeric_columns": ["revenue", "quantity"],
            "categorical_columns": ["product", "region"],
            "date_columns": ["date"],
        },
        "business_metrics": {
            "total_revenue": 50000.0,
            "total_quantity": 1200.0,
            "transaction_count": 120,
            "top_products": [
                {"product": "Widget A", "revenue": 30000.0},
                {"product": "Widget B", "revenue": 12000.0},
            ],
            "top_regions": [{"region": "North", "revenue": 26000.0}],
            "revenue_by_month": [
                {"period": "2023-01", "revenue": 8000.0},
                {"period": "2023-02", "revenue": 9500.0},
                {"period": "2023-03", "revenue": 11000.0},
            ],
        },
        "trends": {
            "series": [
                {
                    "value_column": "revenue",
                    "direction": "up",
                    "percent_change": 37.5,
                    "volatility": 1200.123456,
                    "mean": 9500.0,
                    "anomaly_points": [],
                }
            ]
        },
        "correlations": {"strong_pairs": [], "matrix": {}},
        "outliers": {"by_column": {}},
        "prediction": {
            "status": "complete",
            "selected_model": "Ridge",
            "target_column": "revenue",
            "task_type": "regression",
            "test_metrics": {"r2": 0.8, "rmse": 100.0, "mae": 80.0},
        },
        "xai": {
            "status": "success",
            "plain_english_explanation": (
                "Method used: feature_importance_fallback. The model is primarily "
                "influenced by Date_2024-04-15, Date_2024-12-15."
            ),
            "global_feature_importance": [
                {"feature": "Date_2024-04-15", "importance": 0.18},
                {"feature": "Date_2024-12-15", "importance": 0.11},
                {"feature": "Date_2024-02-15", "importance": 0.09},
                {"feature": "Date_2024-07-15", "importance": 0.08},
                {"feature": "quantity", "importance": 0.25},
            ],
        },
        "warnings": [
            "Category column missing; skipped category ranking.",
            "SHAP unavailable or failed; used feature importance fallback (TypeError).",
            "Categorical features are not perturbed: Product, Region, Date.",
            "No single-feature change within ±50% flipped the outcome for the sampled rows; the predictions are locally stable.",
        ],
        "recommendations": ["Diversify the product mix."],
        "charts": [
            {
                "type": "line",
                "title": "Monthly Revenue Trend",
                "x_key": "period",
                "y_key": "revenue",
                "data": [
                    {"period": "2023-01", "revenue": 9000.0},
                    {"period": "2023-02", "revenue": 9500.0},
                    {"period": "2023-03", "revenue": 8000.0},
                ],
            },
            {
                "type": "bar",
                "title": "Top 10 Products by Revenue",
                "x_key": "product",
                "y_key": "revenue",
                "data": [
                    {"product": "Widget A", "revenue": 30000.0},
                    {"product": "Widget B", "revenue": 12000.0},
                    {"product": "Gadget C", "revenue": 8000.0},
                ],
            },
        ],
    }
    base.update(overrides)
    return base


def _compact_sections(facts):
    generator = ReportGenerator()
    composed = ReportComposer().compose(facts)
    return generator.build_compact_report_sections(facts, composed)


def _all_text(sections) -> str:
    chunks: list[str] = []
    for section in sections:
        body = section.get("body") or {}
        chunks.extend(str(b) for b in body.get("bullets", []))
        chunks.extend(str(l) for l in body.get("lines", []))
        for label, value in body.get("fields", []) or []:
            chunks.append(f"{label}: {value}")
        for item in body.get("items", []) or []:
            chunks.append(f"{item.get('label')}: {item.get('value')}")
        if body.get("recommendation"):
            chunks.append(str(body["recommendation"]))
        for chart in body.get("charts", []) or []:
            chunks.append(str(chart.get("title", "")))
            chunks.append(str(chart.get("explanation", "")))
            chunks.append(str(chart.get("takeaway", "")))
    return "\n".join(chunks)


def test_no_internal_jargon_reaches_the_reader():
    sections, _ = _compact_sections(_facts())
    text = _all_text(sections)
    assert "feature_importance_fallback" not in text
    assert "Method used" not in text
    # Volatility must never be printed as a raw float.
    assert not re.search(r"volatility[\s:]+[\d.]", text, re.IGNORECASE)
    # Pipeline skip-notes are internal, not data-quality findings.
    assert "skipped" not in text.lower()
    # Library/exception chatter never reaches the reader either.
    assert "SHAP" not in text
    assert "TypeError" not in text
    assert "perturbed" not in text
    assert "single-feature change" not in text
    # Model names live in structured fields, not report prose.
    assert "Ridge" not in text


def test_exec_summary_has_no_model_jargon():
    sections, _ = _compact_sections(_facts())
    exec_section = next(s for s in sections if s["title"] == "Executive Summary")
    text = " ".join(str(b) for b in exec_section["body"]["bullets"])
    assert "Ridge" not in text
    assert "(regression)" not in text


def test_trend_fact_is_stated_at_most_once():
    sections, _ = _compact_sections(_facts())
    text = _all_text(sections)
    # "revenue ... 37.5%" must appear exactly once no matter the verb used.
    mentions = [
        line
        for line in text.splitlines()
        if re.search(r"revenue\b.*\b37\.5\s*%", line, re.IGNORECASE)
    ]
    assert len(mentions) <= 1, f"trend fact repeated: {mentions}"


def test_xai_groups_one_hot_dummies_by_source_column():
    sections, _ = _compact_sections(_facts())
    xai = next(s for s in sections if s["title"] == "Explainable AI")
    bullets = [str(b) for b in (xai["body"].get("bullets") or [])]
    text = " ".join(bullets)
    # No per-dummy bullets like "Date_2024-04-15 is ...".
    assert not any(re.match(r"Date_\d{4}", b) for b in bullets), bullets
    # The grouped driver names the source column.
    assert re.search(r"\bdate\b", text, re.IGNORECASE)
    # The real (non-dummy) feature still appears by name.
    assert "quantity" in text.lower()


def test_line_chart_takeaway_scoped_to_charted_series():
    sections, _ = _compact_sections(_facts())
    charts = []
    for s in sections:
        body = s.get("body") or {}
        charts.extend(body.get("charts", []) or [])
    line_charts = [c for c in charts if str(c.get("type")) == "line"]
    assert line_charts, "expected a line chart in the compact report"
    takeaway = str(line_charts[0].get("takeaway", ""))
    # The takeaway describes the charted series, so it can never read as a
    # contradiction of the headline metric trend.
    assert "charted" in takeaway.lower()


def test_chart_titles_adapt_to_actual_item_count():
    _, charts = _compact_sections(_facts())
    for chart in charts:
        title = str(chart.get("title", ""))
        match = re.search(r"top\s+(\d+)", title, re.IGNORECASE)
        if match:
            assert int(match.group(1)) == len(chart.get("data") or []), title


def test_generic_boilerplate_captions_removed():
    sections, _ = _compact_sections(_facts())
    text = _all_text(sections)
    assert "plots how the metric changes over time" not in text
    assert "compares values across categories to surface" not in text


def test_line_svg_carries_axis_context():
    svg = _line_svg(
        {
            "type": "line",
            "title": "Monthly Revenue",
            "x_key": "period",
            "y_key": "revenue",
            "data": [
                {"period": "2023-01", "revenue": 8000.0},
                {"period": "2023-02", "revenue": 9500.0},
                {"period": "2023-03", "revenue": 11000.0},
            ],
        }
    )
    # First and last period labels plus min/max value labels must be drawn.
    assert "2023-01" in svg and "2023-03" in svg
    assert "8,000" in svg and "11,000" in svg


def test_pdf_plaintext_gives_bullets_a_glyph():
    out = _section_plaintext({"bullets": ["First insight."], "lines": ["A plain line."]})
    assert "• First insight." in out
    assert "A plain line." in out
