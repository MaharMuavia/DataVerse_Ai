"""Pro-level report quality: full KPI row, data-driven actions, business insights,
and readable labels — enforced on the rendered 2-page PDF."""
import asyncio
import io

import pandas as pd
from pypdf import PdfReader

from app.services.analysis_pipeline import AnalysisPipeline
from app.services.business_metrics import compute_product_trends, calculate_business_metrics
from app.services.report_generator import ReportGenerator
from app.services.semantic_mapper import SemanticMapper


def _coded_df(rows: int = 60) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=rows, freq="D").astype(str),
            "region": [(i % 4) for i in range(rows)],
            "subcategory": [(i % 5) for i in range(rows)],
            "quantity": [1 + (i % 3) for i in range(rows)],
            "total_sales": [100 + (i % 9) * 25 for i in range(rows)],
            "profit": [15 + (i % 9) * 4 for i in range(rows)],
            "discount": [(i % 4) * 2.5 for i in range(rows)],
        }
    )


def test_product_trend_chart_labels_are_not_bare_codes():
    df = _coded_df()
    sm = SemanticMapper().map_dataframe(df, filename="retail.csv")
    bm = calculate_business_metrics(df, sm)
    product = compute_product_trends(df, sm, bm)
    top = product.get("top_revenue_products") or []
    charts = product.get("charts") or []
    rows = top or next((c.get("data") for c in charts if c.get("data")), [])
    assert rows, "expected ranked product rows"
    label = str(rows[0].get("product"))
    assert not label.strip().isdigit(), f"bare coded chart label leaked: {label!r}"


def _rich_facts():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=120, freq="D").astype(str),
            "product": [f"Item {chr(65 + i % 6)}" for i in range(120)],
            "category": [["Electronics", "Grocery", "Fashion"][i % 3] for i in range(120)],
            "region": [["North", "South", "East", "West"][i % 4] for i in range(120)],
            "quantity": [1 + (i % 5) for i in range(120)],
            "revenue": [100 + (i % 7) * 35 for i in range(120)],
            "cost": [40 + (i % 7) * 15 for i in range(120)],
            "discount": [(i % 5) * 1.5 for i in range(120)],
        }
    )
    return AnalysisPipeline().run_full_analysis(
        df, query="full report", run_predictions=True, run_xai=True, use_llm=False
    )


def test_pdf_keeps_full_kpi_dashboard_and_actions():
    facts = _rich_facts()
    generated = asyncio.run(
        ReportGenerator().generate(title="Quality Audit", facts=facts, xai_output=facts.get("xai") or {})
    )
    reader = PdfReader(io.BytesIO(generated["pdf"]))
    assert len(reader.pages) <= 2
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    # the KPI dashboard must survive compaction with more than Revenue+Profit
    for kpi in ("Revenue", "Profit", "Margin", "Transactions"):
        assert kpi in text, f"KPI '{kpi}' missing from rendered PDF"
    # a clean dataset must not get missing-values boilerplate as its key action
    lowered = text.lower()
    assert "review missing values, duplicate rows" not in lowered, "boilerplate action on a clean dataset"


def test_key_actions_are_data_driven_for_clean_data():
    facts = _rich_facts()
    quality = facts.get("data_quality") or {}
    assert (quality.get("missing_cells") or 0) == 0, "fixture should be clean"
    gen = ReportGenerator()
    composed = gen.composer.compose(facts) if hasattr(gen, "composer") else None
    from app.services.report_composer import ReportComposer

    composed = ReportComposer().compose(facts)
    sections, _charts = gen.build_compact_report_sections(facts, composed, facts.get("xai") or {})
    actions = next(s for s in sections if s["title"] == "Key Actions")
    bullets = [str(b).lower() for b in actions["body"]["bullets"]]
    assert bullets, "expected key actions"
    assert not any("review missing values" in b for b in bullets), bullets
