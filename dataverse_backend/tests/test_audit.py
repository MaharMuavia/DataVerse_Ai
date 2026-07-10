import pandas as pd

from app.services.audit import build_audit_trail
from app.services.business_metrics import calculate_business_metrics
from app.services.data_quality import (
    compute_correlations,
    compute_eda,
    compute_outliers,
    compute_trends,
)
from app.services.semantic_mapper import SemanticMapper


def _facts():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=12, freq="MS").astype(str),
            "product": list("ABCD") * 3,
            "revenue": [100, 300, 200, 150, 260, 310, 90, 400, 120, 330, 210, 180],
            "cost": [50, 150, 100, 70, 130, 150, 40, 200, 60, 160, 100, 90],
        }
    )
    sm = SemanticMapper().map_dataframe(df, filename="sales.csv")
    bm = calculate_business_metrics(df, sm)
    eda = compute_eda(df, outliers=compute_outliers(df))
    corr = compute_correlations(df)
    trends = compute_trends(df)
    return df, bm, eda, corr, trends


def test_audit_trail_covers_categories_and_schema():
    df, bm, eda, corr, trends = _facts()
    trail = build_audit_trail(
        business_metrics=bm, eda=eda, correlations=corr, trends=trends,
        prediction={"status": "skipped"}, df=df,
    )
    assert trail, "expected receipts"
    cats = {e["category"] for e in trail}
    assert {"kpi", "eda"} <= cats
    required = {"category", "metric_key", "operation", "formula_plain", "value", "row_count", "sample_rows"}
    for entry in trail:
        assert required <= set(entry), f"missing keys in {entry.get('metric_key')}"


def test_audit_trail_values_match_source_facts():
    df, bm, eda, corr, trends = _facts()
    trail = build_audit_trail(
        business_metrics=bm, eda=eda, correlations=corr, trends=trends,
        prediction={"status": "skipped"}, df=df,
    )
    by_key = {e["metric_key"]: e for e in trail}

    # KPI receipt equals the metric (trust guarantee, extended)
    assert by_key["total_revenue"]["value"] == bm["total_revenue"]

    # EDA receipt equals numeric_describe
    expected_mean = round(float(eda["numeric_describe"]["revenue"]["mean"]), 4)
    assert by_key["eda.revenue.mean"]["value"] == expected_mean

    # Correlation receipt present and equals the reported coefficient
    corr_entries = [e for e in trail if e["category"] == "correlation"]
    assert corr_entries, "expected a correlation receipt"
    pair = corr["strong_pairs"][0]
    expected_r = round(float(pair["correlation"]), 4)
    assert any(e["value"] == expected_r for e in corr_entries)


def test_audit_trail_includes_model_metrics():
    df, bm, eda, corr, trends = _facts()
    prediction = {
        "status": "complete",
        "selected_model": "Ridge",
        "target_column": "revenue",
        "test_rows": 3,
        "test_metrics": {"rmse": 10.1, "r2": 0.97},
    }
    trail = build_audit_trail(
        business_metrics=bm, eda=eda, correlations=corr, trends=trends,
        prediction=prediction, df=df,
    )
    model_entries = {e["metric_key"]: e for e in trail if e["category"] == "model"}
    assert model_entries["model.rmse"]["value"] == 10.1
    assert model_entries["model.r2"]["value"] == 0.97


def test_pipeline_facts_include_audit_trail():
    from app.services.analysis_pipeline import AnalysisPipeline

    df, _bm, _eda, _corr, _trends = _facts()
    facts = AnalysisPipeline().run_full_analysis(
        df, query="dataset overview", run_predictions=False, run_xai=False, use_llm=False
    )
    trail = facts.get("audit_trail")
    assert isinstance(trail, list) and trail, "expected an audit trail in facts"
    cats = {e["category"] for e in trail}
    assert "kpi" in cats
    kpi = next(e for e in trail if e["category"] == "kpi" and e["metric_key"] == "total_revenue")
    assert kpi["value"] == facts["business_metrics"]["total_revenue"]
    # survived the pipeline json_safe pass
    assert isinstance(kpi["sample_rows"], list)
