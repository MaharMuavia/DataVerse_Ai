"""The PDF report is a hard 2-page executive product — never 3, for any dataset."""
import asyncio
import io

import pandas as pd
from pypdf import PdfReader

from app.services.analysis_pipeline import AnalysisPipeline
from app.services.report_generator import ReportGenerator


def _rich_dataframe(rows: int = 120) -> pd.DataFrame:
    """Synthetic sales data rich enough to fill every report section (incl. ML + XAI)."""
    products = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
    categories = ["Electronics", "Grocery", "Fashion"]
    regions = ["North", "South", "East", "West"]
    data = {
        "date": pd.date_range("2024-01-01", periods=rows, freq="D").astype(str),
        "product": [products[i % len(products)] for i in range(rows)],
        "category": [categories[i % len(categories)] for i in range(rows)],
        "region": [regions[i % len(regions)] for i in range(rows)],
        "quantity": [1 + (i % 5) for i in range(rows)],
        "revenue": [100 + (i % 7) * 35 + (i % 3) * 11 for i in range(rows)],
        "cost": [40 + (i % 7) * 15 for i in range(rows)],
    }
    return pd.DataFrame(data)


def test_pdf_report_is_at_most_two_pages():
    df = _rich_dataframe()
    facts = AnalysisPipeline().run_full_analysis(
        df, query="full report", run_predictions=True, run_xai=True, use_llm=False
    )
    generated = asyncio.run(
        ReportGenerator().generate(title="Two Page Audit", facts=facts, xai_output=facts.get("xai") or {})
    )
    pdf_bytes = generated["pdf"]
    pages = len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    assert pages <= 2, f"PDF report must be at most 2 pages, got {pages}"
    # and it still carries the essential content
    text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf_bytes)).pages)
    for needle in ("Executive Summary", "Explainable"):
        assert needle.lower() in text.lower(), f"missing section: {needle}"


def test_pdf_never_exceeds_two_pages_even_with_bloated_sections():
    """Adversarial: even if the composer emits far too much content, the PDF
    renderer must compact/trim to the 2-page executive budget."""
    long_para = (
        "This is a deliberately verbose analytical paragraph describing revenue drivers, "
        "seasonal effects, discount elasticity, and channel mix in exhaustive detail. "
    ) * 4
    sections = [
        {"title": f"Section {i}: Extended Analysis", "body": long_para}
        for i in range(18)
    ]
    composed = {
        "metrics": [
            {"label": "Total Sales", "value": "187,940.91"},
            {"label": "Total Profit", "value": "28,064.60"},
            {"label": "Gross Margin", "value": "14.93%"},
            {"label": "Transactions", "value": "3,000"},
        ],
        "sections": sections,
    }
    pdf_bytes = ReportGenerator()._reportlab_pdf("Bloat Audit", {}, composed)
    pages = len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    assert pages <= 2, f"renderer must enforce the 2-page budget, got {pages}"
