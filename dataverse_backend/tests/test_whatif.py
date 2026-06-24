import pandas as pd
import pytest

from app.services.whatif import apply_scenario, simulate


def test_apply_scenario_scales_numeric_column():
    df = pd.DataFrame({"revenue": [100, 200, 300], "product": ["A", "B", "C"]})
    out = apply_scenario(df, "revenue", 10)
    assert out["revenue"].tolist() == pytest.approx([110.0, 220.0, 330.0])
    # original is untouched
    assert list(df["revenue"]) == [100, 200, 300]


def test_apply_scenario_rejects_non_numeric():
    df = pd.DataFrame({"product": ["A", "B"]})
    with pytest.raises(ValueError):
        apply_scenario(df, "product", 10)


def test_apply_scenario_rejects_missing_column():
    df = pd.DataFrame({"revenue": [1, 2]})
    with pytest.raises(ValueError):
        apply_scenario(df, "nope", 10)


def test_simulate_changes_revenue_kpis_and_keeps_receipts():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=6, freq="D").astype(str),
            "product": list("ABCABC"),
            "revenue": [100, 200, 300, 150, 250, 350],
            "cost": [40, 80, 120, 60, 100, 140],
        }
    )
    res = simulate(df, "revenue", 10)
    base = {k["label"]: k["value"] for k in res["baseline_kpis"]}
    scen = {k["label"]: k["value"] for k in res["scenario_kpis"]}

    assert scen["Total Sales"] > base["Total Sales"]
    assert round(scen["Total Sales"], 2) == round(base["Total Sales"] * 1.1, 2)

    # the hypothetical KPIs are themselves verifiable (provenance computed on modified data)
    sales = next(k for k in res["scenario_kpis"] if k["label"] == "Total Sales")
    assert sales.get("provenance") is not None
    assert sales["provenance"]["value"] == scen["Total Sales"]
