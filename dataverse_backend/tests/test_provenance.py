import pandas as pd

from app.services.provenance import (
    build_series_provenance,
    build_derived_provenance,
    provenance_to_dict,
)


def test_series_provenance_records_sum_and_samples():
    df = pd.DataFrame({"product": ["A", "B", "C"], "revenue": [100, 300, 200]})
    series = df["revenue"]
    prov = build_series_provenance(
        metric_key="total_revenue",
        label="Total revenue",
        operation="SUM",
        series=series,
        df=df,
        source_columns=["revenue"],
        value=600,
    )
    data = provenance_to_dict(prov)
    assert data["value"] == 600
    assert data["operation"] == "SUM"
    assert data["row_count"] == 3
    assert data["source_columns"] == ["revenue"]
    # sample rows are the largest contributors, json-safe
    assert len(data["sample_rows"]) == 3
    assert data["sample_rows"][0]["revenue"] == 300


def test_derived_provenance_lists_components():
    prov = build_derived_provenance(
        metric_key="gross_margin",
        label="Gross margin",
        operation="DIVIDE",
        formula_plain="Total profit / total revenue * 100 = 25.0%",
        value=25.0,
        source_columns=["revenue", "cost"],
        components=[("total_profit", 150), ("total_revenue", 600)],
    )
    data = provenance_to_dict(prov)
    assert data["value"] == 25.0
    assert data["row_count"] == 2
    assert data["sample_rows"] == [
        {"component": "total_profit", "value": 150},
        {"component": "total_revenue", "value": 600},
    ]


def test_calculate_business_metrics_emits_matching_provenance():
    from app.services.business_metrics import calculate_business_metrics
    from app.services.semantic_mapper import SemanticMapper

    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "product": ["A", "B", "C"],
            "revenue": [100, 300, 200],
            "cost": [50, 150, 100],
        }
    )
    sm = SemanticMapper().map_dataframe(df, filename="sales.csv")
    bm = calculate_business_metrics(df, sm)

    prov = bm.get("provenance")
    assert isinstance(prov, dict)
    assert "total_revenue" in prov
    # the receipt value equals the reported metric value (the trust guarantee)
    assert prov["total_revenue"]["value"] == bm["total_revenue"]
    assert prov["total_revenue"]["operation"] == "SUM"
    assert prov["total_revenue"]["row_count"] == 3
    assert prov["transaction_count"]["value"] == bm["transaction_count"]


def test_kpi_cards_carry_provenance():
    from app.services.business_metrics import build_kpi_cards, calculate_business_metrics
    from app.services.semantic_mapper import SemanticMapper

    df = pd.DataFrame(
        {"product": ["A", "B"], "revenue": [100, 300], "cost": [40, 110]}
    )
    sm = SemanticMapper().map_dataframe(df, filename="sales.csv")
    bm = calculate_business_metrics(df, sm)
    cards = build_kpi_cards(bm)

    sales = next(c for c in cards if c["label"] == "Total Sales")
    assert "provenance" in sales
    assert sales["provenance"]["value"] == bm["total_revenue"]
    # cards without a receipt simply omit the field (graceful)
    assert all("label" in c and "value" in c for c in cards)


def test_pipeline_facts_kpis_include_provenance():
    from app.services.analysis_pipeline import AnalysisPipeline

    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "product": ["A", "B", "C"],
            "revenue": [100, 300, 200],
            "cost": [50, 150, 100],
        }
    )
    facts = AnalysisPipeline().run_full_analysis(
        df, query="dataset overview", run_predictions=False, run_xai=False, use_llm=False
    )
    kpis = facts.get("kpis") or []
    assert kpis, "expected KPI cards"
    sales = next((c for c in kpis if c.get("label") == "Total Sales"), None)
    assert sales is not None
    assert sales.get("provenance") is not None
    assert sales["provenance"]["value"] == facts["business_metrics"]["total_revenue"]
    # provenance survived the json_safe pass (sample rows are plain dicts)
    assert isinstance(sales["provenance"]["sample_rows"], list)
