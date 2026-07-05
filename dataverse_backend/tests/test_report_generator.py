from __future__ import annotations

import asyncio
import re

from app.services.report_composer import ReportComposer, ReportMemory, SECTION_ORDER
from app.services.report_generator import ReportGenerator


def _sales_facts():
    """Minimal but realistic computed-facts payload for a sales dataset."""
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
            "text_columns": [],
            "high_cardinality_columns": ["order_id"],
            "missing_values_by_column": {
                "region": {"count": 18, "pct": 15.0},
                "category": {"count": 6, "pct": 5.0},
            },
        },
        "business_metrics": {
            "total_revenue": 50000.0,
            "total_quantity": 1200.0,
            "total_profit": 9000.0,
            "gross_margin": 18.0,
            "transaction_count": 120,
            "average_order_value": 416.0,
            "top_products": [
                {"product": "Widget A", "revenue": 30000.0},
                {"product": "Widget B", "revenue": 12000.0},
                {"product": "Gadget C", "revenue": 8000.0},
            ],
            "top_categories": [
                {"category": "Hardware", "revenue": 35000.0},
                {"category": "Accessories", "revenue": 15000.0},
            ],
            "top_regions": [{"region": "North", "revenue": 26000.0}, {"region": "South", "revenue": 24000.0}],
            "revenue_by_month": [
                {"period": "2023-01", "revenue": 8000.0},
                {"period": "2023-02", "revenue": 9500.0},
                {"period": "2023-03", "revenue": 11000.0},
            ],
        },
        "product_analysis": {"fastest_growing_products": [{"product": "Widget B", "absolute_growth": 3000.0}], "tables": []},
        "trends": {"series": [{"value_column": "revenue", "direction": "up", "percent_change": 37.5, "slope": 1500.0, "last_value": 11000.0, "volatility": 1200.0, "anomaly_points": [], "chart_data": [{"date": "2023-01-01", "value": 8000.0}, {"date": "2023-02-01", "value": 9500.0}, {"date": "2023-03-01", "value": 11000.0}]}]},
        "correlations": {
            "strong_pairs": [{"column_a": "revenue", "column_b": "cost", "correlation": 0.99}],
            "matrix": {
                "revenue": {"revenue": 1.0, "cost": 0.99, "quantity": 0.85},
                "cost": {"revenue": 0.99, "cost": 1.0, "quantity": 0.82},
                "quantity": {"revenue": 0.85, "cost": 0.82, "quantity": 1.0},
            }
        },
        "prediction": {"status": "not_run"},
        "xai": {},
        "recommendations": ["Clean missing region values.", "Clean missing region values.", "Diversify product mix."],
        "key_insights": [],
        "charts": [
            {"type": "line", "title": "Revenue by month", "x_key": "period", "y_key": "revenue", "data": [{"period": "2023-01", "revenue": 8000.0}, {"period": "2023-03", "revenue": 11000.0}]},
            {"type": "bar", "title": "Revenue by category", "x_key": "category", "y_key": "revenue", "data": [{"category": "Hardware", "revenue": 35000.0}, {"category": "Accessories", "revenue": 15000.0}]},
            # Exact duplicate of the first chart -> must be deduped.
            {"type": "line", "title": "Revenue by month", "x_key": "period", "y_key": "revenue", "data": [{"period": "2023-01", "revenue": 8000.0}, {"period": "2023-03", "revenue": 11000.0}]},
        ],
    }


def test_required_sections_present_and_ordered():
    composed = ReportComposer().compose(_sales_facts())
    titles = [s["title"] for s in composed["sections"]]
    for required in ["Executive Summary", "Data Quality Assessment", "Dataset Overview", "Business Overview", "KPI Metrics", "Performance Evaluation", "Trend Analysis", "Category Analysis", "Correlation Analysis", "Data Leakage Analysis", "Recommendations", "Action Plan"]:
        assert required in titles, f"missing section: {required}"
    positions = [SECTION_ORDER.index(t) for t in titles if t in SECTION_ORDER]
    assert positions == sorted(positions), "sections are out of order"


def test_business_overview_contains_interpretation_not_raw_values():
    composed = ReportComposer().compose(_sales_facts())
    overview = next(s for s in composed["sections"] if s["title"] == "Business Overview")
    labels = {block["label"] for block in overview["body"]["blocks"]}
    assert {"Business Context", "Revenue Drivers"}.issubset(labels)
    text = " ".join(b["text"] for b in overview["body"]["blocks"]).lower()
    assert "concentration" in text or "risk" in text or "driver" in text


def test_performance_evaluation_has_health_scores():
    composed = ReportComposer().compose(_sales_facts())
    perf = next(s for s in composed["sections"] if s["title"] == "Performance Evaluation")
    names = {score["name"] for score in perf["body"]["scores"]}
    assert "Business Health" in names and "Revenue Health" in names
    for score in perf["body"]["scores"]:
        assert score["grade"] in {"Excellent", "Good", "Average", "Poor"}


def test_data_quality_section_reports_missing_values_and_severity():
    composed = ReportComposer().compose(_sales_facts())
    dq = next(s for s in composed["sections"] if s["title"] == "Data Quality Assessment")
    body = dq["body"]
    assert any("Medium" in line or "8.0%" in line for line in body["lines"])
    assert body["table"]["rows"], "missing-values table should list affected columns"


def test_data_leakage_section_flags_derived_correlation():
    composed = ReportComposer().compose(_sales_facts())
    leak = next(s for s in composed["sections"] if s["title"] == "Data Leakage Analysis")
    assert leak["body"]["risk"] in {"Low", "Medium", "High"}
    findings = " ".join(leak["body"]["findings"]).lower()
    assert "correlat" in findings  # revenue<->cost r=0.99 should be flagged


def test_charts_are_deduped_and_carry_explanation_and_takeaway():
    composed = ReportComposer().compose(_sales_facts())
    titles = [c["title"] for c in composed["charts"]]
    assert titles.count("Revenue by month") == 1, "duplicate chart was not deduped"
    for chart in composed["charts"]:
        assert chart["explanation"], "chart missing business explanation"
        assert chart["takeaway"], "chart missing key takeaway"


def test_insights_are_deduplicated_globally():
    memory = ReportMemory()
    assert memory.add_insight("Revenue increased 18% YoY.", score=5, category="trend") is True
    assert memory.add_insight("revenue increased 18% yoy", score=5, category="trend") is False
    assert len(memory.ranked_insights()) == 1


def test_full_html_report_is_premium_themed_and_has_no_duplicate_bullets():
    facts = _sales_facts()
    generated = asyncio.run(ReportGenerator().generate(title="Sales Report", facts=facts))
    html = str(generated["html"])
    # Premium light theme (project convention: light theme only).
    assert "color-scheme: light" in html
    assert "#0B1120" not in html  # dark-mode background must be gone
    assert "@media print" in html  # print fallback
    bullets = re.findall(r"<li>(.*?)</li>", html)
    normalized = [re.sub(r"\s+", " ", b).strip().lower() for b in bullets]
    assert len(normalized) == len(set(normalized)), "duplicate bullet content rendered"


def _financial_facts():
    """Realistic computed-facts payload for the Microsoft/Apple/Tesla financial dataset."""
    return {
        "filename": "financial_data.csv",
        "dataset_profile": {"row_count": 9, "column_count": 7},
        "semantic_map": {"dataset_type": "generic_tabular"},
        "data_quality": {
            "data_quality_score": 98.0,
            "missing_cells": 0,
            "missing_pct": 0.0,
            "duplicate_rows": 0,
            "numeric_columns": ["Total Revenue", "Net Income", "Total Assets", "Total Liabilities", "Cash Flow from Operating Activities"],
            "categorical_columns": ["Company"],
            "date_columns": [],
            "text_columns": [],
            "high_cardinality_columns": [],
            "missing_values_by_column": {},
        },
        "business_metrics": {},
        "product_analysis": {},
        "trends": {"series": []},
        "correlations": {
            "strong_pairs": [
                {"column_a": "Total Revenue", "column_b": "Total Assets", "correlation": 0.96},
                {"column_a": "Total Revenue", "column_b": "Net Income", "correlation": 0.91},
            ],
            "matrix": {
                "Total Revenue": {"Total Revenue": 1.0, "Total Assets": 0.96, "Net Income": 0.91},
                "Total Assets": {"Total Revenue": 0.96, "Total Assets": 1.0, "Net Income": 0.85},
                "Net Income": {"Total Revenue": 0.91, "Total Assets": 0.85, "Net Income": 1.0},
            },
        },
        "prediction": {"status": "not_run"},
        "xai": {},
        "recommendations": [],
        "key_insights": [],
        "charts": [],
        "financial_analysis": {
            "is_financial": True,
            "year_column": "Year",
            "entity_column": "Company",
            "revenue_column": "Total Revenue",
            "income_column": "Net Income",
            "assets_column": "Total Assets",
            "liabilities_column": "Total Liabilities",
            "cashflow_column": "Cash Flow from Operating Activities",
            "entities": ["Apple", "Microsoft", "Tesla"],
            "years": ["2023", "2024", "2025"],
            "company_metrics": [
                {"entity": "Apple", "total_revenue": 1190481, "total_net_income": 302741, "profit_margin": 25.43, "total_assets": 1076804, "total_liabilities": 883975, "liability_ratio": 82.08, "total_cashflow": 340279, "revenue_growth_pct": 8.57},
                {"entity": "Microsoft", "total_revenue": 738761, "total_net_income": 262329, "profit_margin": 35.51, "total_assets": 1543142, "total_liabilities": 724963, "liability_ratio": 46.98, "total_cashflow": 342292, "revenue_growth_pct": 33.0},
                {"entity": "Tesla", "total_revenue": 289290, "total_net_income": 25982, "profit_margin": 8.98, "total_assets": 366494, "total_liabilities": 146340, "liability_ratio": 39.93, "total_cashflow": 42926, "revenue_growth_pct": -2.01},
            ],
            "revenue_by_year": [
                {"year": "2023", "total_revenue": 691973, "total_net_income": 184330, "total_cashflow": 211381},
                {"year": "2024", "total_revenue": 733847, "total_net_income": 189025, "total_cashflow": 251725},
                {"year": "2025", "total_revenue": 792712, "total_net_income": 217697, "total_cashflow": 262391},
            ],
            "grouped_revenue_data": [
                {"company": "Microsoft", "year": "2023", "revenue": 211915},
                {"company": "Microsoft", "year": "2024", "revenue": 245122},
                {"company": "Microsoft", "year": "2025", "revenue": 281724},
                {"company": "Apple", "year": "2023", "revenue": 383285},
                {"company": "Apple", "year": "2024", "revenue": 391035},
                {"company": "Apple", "year": "2025", "revenue": 416161},
                {"company": "Tesla", "year": "2023", "revenue": 96773},
                {"company": "Tesla", "year": "2024", "revenue": 97690},
                {"company": "Tesla", "year": "2025", "revenue": 94827},
            ],
            "total_revenue_all": 2218532,
            "total_net_income_all": 591052,
            "total_cashflow_all": 725497,
            "revenue_growth_pct": 14.55,
        },
    }


def test_financial_dataset_detection():
    """Financial datasets must produce a Business Overview with financial blocks."""
    composed = ReportComposer().compose(_financial_facts())
    titles = [s["title"] for s in composed["sections"]]
    assert "Business Overview" in titles
    overview = next(s for s in composed["sections"] if s["title"] == "Business Overview")
    labels = {block["label"] for block in overview["body"]["blocks"]}
    assert "Business Context" in labels
    assert "Revenue Leadership" in labels


def test_financial_business_overview_uses_correct_terminology():
    """Business Overview must use financial language and not use retail/transaction terms."""
    composed = ReportComposer().compose(_financial_facts())
    overview = next(s for s in composed["sections"] if s["title"] == "Business Overview")
    text = " ".join(b["text"] for b in overview["body"]["blocks"]).lower()
    # Banned retail/transaction terms
    for banned in ("transaction", "order value", "basket", "upsell", "average order"):
        assert banned not in text, f"Found banned retail term '{banned}' in financial overview"
    # Financial entities should appear
    for company in ("apple", "microsoft", "tesla"):
        assert company in text, f"Expected company '{company}' in financial overview"


def test_financial_kpi_cards_are_financial():
    """KPI section must contain revenue, income, margin, and leader — not retail terms."""
    composed = ReportComposer().compose(_financial_facts())
    kpi = next((s for s in composed["sections"] if s["title"] == "KPI Metrics"), None)
    assert kpi is not None, "KPI Metrics section missing for financial dataset"
    labels = {item["label"] for item in kpi["body"]["items"]}
    assert any("Revenue" in label for label in labels), "No Revenue KPI card found"
    assert any("Income" in label or "Margin" in label or "Leader" in label for label in labels)
    for banned in ("Transaction", "Order Value", "Basket"):
        for label in labels:
            assert banned.lower() not in label.lower(), f"Found banned KPI label '{label}'"


def test_financial_trend_works_with_year_column():
    """Trend section must reference actual years and must not say 'could not be measured'."""
    composed = ReportComposer().compose(_financial_facts())
    trend = next((s for s in composed["sections"] if s["title"] == "Trend Analysis"), None)
    assert trend is not None, "Trend Analysis section missing for financial dataset"
    text = " ".join(trend["body"]["lines"]).lower()
    assert "could not be measured" not in text
    assert "2023" in text or "2024" in text or "2025" in text, "No year labels found in trend section"


def test_financial_charts_are_relevant():
    """Financial charts must not contain generic histogram-of-year or count-by-company charts."""
    composed = ReportComposer().compose(_financial_facts())
    chart_titles = [c["title"] for c in composed["charts"]]
    # Should not have generic histograms or row-count charts
    for bad_title in ("Distribution of Year", "Top Company", "Count by"):
        for title in chart_titles:
            assert bad_title.lower() not in title.lower(), f"Found generic chart '{title}' in financial report"
    # Should have at least a revenue chart and an explanation+takeaway on each
    assert any("Revenue" in t for t in chart_titles), "No revenue chart generated for financial dataset"
    for chart in composed["charts"]:
        assert chart.get("explanation"), f"Chart '{chart.get('title')}' missing explanation"
        assert chart.get("takeaway"), f"Chart '{chart.get('title')}' missing takeaway"


def test_financial_leakage_is_not_alarmist():
    """Scale correlations in financial data (r=0.96, r=0.91) must not be rated High risk."""
    composed = ReportComposer().compose(_financial_facts())
    leak = next(s for s in composed["sections"] if s["title"] == "Data Leakage Analysis")
    assert leak["body"]["risk"] in {"Low", "Medium", "Low / Manual Review", "Low to Medium / Manual Review"}, (
        f"Leakage risk should be Low or Medium for scale correlations, got {leak['body']['risk']}"
    )
    findings_text = " ".join(leak["body"]["findings"]).lower()
    assert "scale" in findings_text or "normal" in findings_text or "expected" in findings_text, (
        "Leakage section should note that financial scale correlations are expected"
    )


def test_report_generation_skips_zero_value_bar_charts():
    facts = {
        "filename": "zero_values.csv",
        "dataset_profile": {"row_count": 2, "column_count": 2},
        "business_metrics": {"transaction_count": 2},
        "data_quality": {"data_quality_score": 1.0},
        "key_insights": ["All chart values are currently zero."],
        "charts": [
            {
                "type": "bar",
                "title": "Zero values",
                "x_key": "label",
                "y_key": "value",
                "data": [
                    {"label": "A", "value": 0},
                    {"label": "B", "value": 0},
                ],
            }
        ],
    }

    generated = asyncio.run(ReportGenerator().generate(title="Zero Value Report", facts=facts))

    assert "Zero values" not in str(generated["html"])
    assert isinstance(generated["pdf"], bytes)
    assert len(generated["pdf"]) > 100


def test_financial_dataset_temporal_year_detection():
    """Verify that Year column is detected as temporal if no date column is present."""
    facts = _financial_facts()
    # Ensure Year is listed in facts columns but no date columns
    facts["dataset_profile"]["column_roles"] = {"Year": "numeric", "Company": "categorical", "Total Revenue": "numeric"}
    composed = ReportComposer().compose(facts)
    overview = next(s for s in composed["sections"] if s["title"] == "Dataset Overview")
    lines = " ".join(overview["body"]["lines"]).lower()
    assert "temporal period column detected: year" in lines or "temporal columns: 1 (year)" in lines


def test_kpi_card_deduplication():
    """Verify that Total Revenue/Income/Growth cards are in headline metrics and not in KPI Metrics section."""
    composed = ReportComposer().compose(_financial_facts())
    headline_labels = {c["label"] for c in composed["metrics"]}
    assert "Total Revenue" in headline_labels
    assert "Total Net Income" in headline_labels
    assert "Revenue Growth" in headline_labels
    
    kpi_section = next(s for s in composed["sections"] if s["title"] == "KPI Metrics")
    kpi_items = {item["label"] for item in kpi_section["body"]["items"]}
    
    # Standard headline cards should not be duplicated in KPI Metrics section
    for card in ["Total Revenue", "Total Net Income", "Revenue Growth", "Revenue Leader", "Best Margin"]:
        assert card not in kpi_items


def test_assets_vs_liabilities_chart_spec():
    """Verify that the assets vs liabilities grouped bar and cash flow bar charts exist."""
    composed = ReportComposer().compose(_financial_facts())
    chart_titles = [c["title"] for c in composed["charts"]]
    assert "Total Assets vs Total Liabilities by Company" in chart_titles
    assert "Operating Cash Flow by Company" in chart_titles
    
    assets_chart = next(c for c in composed["charts"] if c["title"] == "Total Assets vs Total Liabilities by Company")
    assert assets_chart["type"] == "grouped_bar"
    assert assets_chart["series_key"] == "metric"


def test_correlation_matrix_table_present():
    """Verify that Correlation Analysis contains a Pearson r table."""
    composed = ReportComposer().compose(_financial_facts())
    corr_section = next(s for s in composed["sections"] if s["title"] == "Correlation Analysis")
    assert "table" in corr_section["body"]
    assert "Pearson r" in corr_section["body"]["table"]["title"]
    assert corr_section["body"]["table"]["columns"][0] == "Column"


def test_system_health_and_project_readiness_sections():
    """Verify that health and project readiness sections are composed with badges."""
    composed = ReportComposer().compose(_financial_facts())
    titles = [s["title"] for s in composed["sections"]]
    assert "System & Integration Health" in titles
    assert "Project Readiness Score" in titles
    
    health = next(s for s in composed["sections"] if s["title"] == "System & Integration Health")
    assert any("FastAPI Backend:" in line for line in health["body"]["lines"])
    
    readiness = next(s for s in composed["sections"] if s["title"] == "Project Readiness Score")
    scores = readiness["body"]["scores"]
    assert scores[0]["name"] == "Production Demo Ready"
    assert scores[0]["grade"] in {"Yes", "No", "Partial"}

