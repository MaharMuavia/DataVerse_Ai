import pandas as pd

from app.services.certificate import (
    build_certificate,
    dataset_fingerprint,
    results_fingerprint,
    verify_certificate,
)


def _audit():
    return [
        {"category": "kpi", "metric_key": "total_revenue", "value": 600},
        {"category": "eda", "metric_key": "eda.x.mean", "value": 2.5},
        {"category": "model", "metric_key": "model.r2", "value": 0.97},  # excluded from fingerprint
    ]


def test_fingerprints_are_stable_and_value_sensitive():
    df = pd.DataFrame({"x": [1, 2, 3], "revenue": [100, 200, 300]})
    audit = _audit()
    c1 = build_certificate(df, audit)
    c2 = build_certificate(df, audit)
    assert c1["data_fingerprint"] == c2["data_fingerprint"]
    assert c1["results_fingerprint"] == c2["results_fingerprint"]
    assert c1["algorithm"] == "sha256"
    assert c1["verified_numbers"] == 2  # model entry excluded

    # changing a deterministic value changes the results fingerprint
    tampered = [dict(e) for e in audit]
    tampered[0]["value"] = 601
    assert results_fingerprint(tampered) != c1["results_fingerprint"]

    # changing only the (excluded) model value does NOT change it
    model_changed = [dict(e) for e in audit]
    model_changed[2]["value"] = 0.5
    assert results_fingerprint(model_changed) == c1["results_fingerprint"]


def test_dataset_fingerprint_changes_with_data():
    assert dataset_fingerprint(pd.DataFrame({"x": [1, 2, 3]})) != dataset_fingerprint(pd.DataFrame({"x": [1, 2, 4]}))


def test_verify_matches_and_detects_tampering():
    df = pd.DataFrame({"x": [1, 2, 3], "revenue": [100, 200, 300]})
    audit = _audit()
    cert = build_certificate(df, audit)

    ok = verify_certificate(df, audit, cert)
    assert ok["verified"] is True and ok["data_match"] and ok["results_match"]

    # tampered data
    df_tampered = pd.DataFrame({"x": [1, 2, 3], "revenue": [100, 200, 999]})
    bad = verify_certificate(df_tampered, audit, cert)
    assert bad["verified"] is False and bad["data_match"] is False

    # tampered result
    audit_tampered = [dict(e) for e in audit]
    audit_tampered[0]["value"] = 601
    bad2 = verify_certificate(df, audit_tampered, cert)
    assert bad2["verified"] is False and bad2["results_match"] is False


def test_pipeline_certificate_self_verifies():
    from app.services.analysis_pipeline import AnalysisPipeline

    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=12, freq="MS").astype(str),
            "product": list("ABCD") * 3,
            "revenue": [100, 300, 200, 150, 260, 310, 90, 400, 120, 330, 210, 180],
            "cost": [50, 150, 100, 70, 130, 150, 40, 200, 60, 160, 100, 90],
        }
    )
    facts = AnalysisPipeline().run_full_analysis(
        df, query="overview", run_predictions=False, run_xai=False, use_llm=False
    )
    cert = facts.get("certificate")
    assert cert and cert["data_fingerprint"] and cert["results_fingerprint"]
    result = verify_certificate(df, facts["audit_trail"], cert)
    assert result["verified"] is True
