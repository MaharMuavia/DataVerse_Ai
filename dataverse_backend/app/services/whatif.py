"""Verified What-If Simulator: deterministic, receipt-backed scenario analysis.

The user nudges a numeric lever (e.g. "+10% price") and the business KPIs are
recomputed on the modified data through the exact same deterministic pipeline.
Because the scenario KPIs flow through `calculate_business_metrics`, each one
carries its own "show the math" provenance receipt — so a hypothetical is just
as verifiable as the real analysis. An LLM-orchestrated analyst cannot offer
reproducible, provenance-backed what-if.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from .business_metrics import build_kpi_cards, calculate_business_metrics
from .semantic_mapper import SemanticMapper


def apply_scenario(df: pd.DataFrame, column: str, pct_change: float) -> pd.DataFrame:
    """Return a copy of df with `column` scaled by (1 + pct_change/100)."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in dataset")
    series = pd.to_numeric(df[column], errors="coerce")
    if int(series.notna().sum()) == 0:
        raise ValueError(f"Column '{column}' is not numeric and cannot be simulated")
    work = df.copy()
    work[column] = series * (1.0 + float(pct_change) / 100.0)
    return work


def simulate(
    df: pd.DataFrame,
    column: str,
    pct_change: float,
    semantic_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    semantic_map = semantic_map or SemanticMapper().map_dataframe(df)
    baseline_metrics = calculate_business_metrics(df, semantic_map)
    scenario_df = apply_scenario(df, column, pct_change)
    scenario_metrics = calculate_business_metrics(scenario_df, semantic_map)

    baseline_kpis = build_kpi_cards(baseline_metrics)
    scenario_kpis = build_kpi_cards(scenario_metrics)

    baseline_by_label = {card["label"]: card.get("value") for card in baseline_kpis}
    deltas: list[dict[str, Any]] = []
    for card in scenario_kpis:
        before = baseline_by_label.get(card["label"])
        after = card.get("value")
        entry: dict[str, Any] = {"label": card["label"], "baseline": before, "scenario": after}
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            entry["delta"] = round(after - before, 2)
            entry["pct"] = round((after - before) / before * 100, 2) if before else None
        deltas.append(entry)

    return {
        "column": column,
        "pct_change": pct_change,
        "baseline_kpis": baseline_kpis,
        "scenario_kpis": scenario_kpis,
        "deltas": deltas,
    }
