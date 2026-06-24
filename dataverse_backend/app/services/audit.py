"""Audit trail: a flat list of deterministic receipts for every number.

Extends the per-KPI "show the math" guarantee to EDA stats, correlations,
trends, and model metrics. Purely additive — it reads already-computed facts
and the dataframe; it does not change how any number is computed.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from .provenance import (
    build_derived_provenance,
    build_stat_provenance,
    provenance_to_dict,
    sample_columns,
)


def build_audit_trail(
    *,
    business_metrics: dict[str, Any] | None,
    eda: dict[str, Any] | None,
    correlations: dict[str, Any] | None,
    trends: dict[str, Any] | None,
    prediction: dict[str, Any] | None,
    df: pd.DataFrame | None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    # 1. KPIs — receipts already computed in business_metrics.
    for prov in (business_metrics or {}).get("provenance", {}).values():
        entries.append({"category": "kpi", **prov})

    # 2. EDA stats — mean / min / max per numeric column.
    numeric_describe = (eda or {}).get("numeric_describe") or {}
    for column, stats in numeric_describe.items():
        count = int(stats.get("count") or 0)
        for operation, stat_key in (("MEAN", "mean"), ("MIN", "min"), ("MAX", "max")):
            raw = stats.get(stat_key)
            if raw is None:
                continue
            value = round(float(raw), 4)
            receipt = build_stat_provenance(
                metric_key=f"eda.{column}.{stat_key}",
                label=f"{column} {stat_key}",
                operation=operation,
                column=column,
                df=df,
                value=value,
                formula_plain=f"{operation} of `{column}` over {count} rows = {value}",
            )
            entries.append({"category": "eda", **provenance_to_dict(receipt)})

    # 3. Correlations — Pearson coefficient per strong pair.
    for pair in (correlations or {}).get("strong_pairs", []) or []:
        a, b, r = pair.get("column_a"), pair.get("column_b"), pair.get("correlation")
        if not a or not b or r is None:
            continue
        coefficient = round(float(r), 4)
        receipt = build_derived_provenance(
            metric_key=f"corr.{a}.{b}",
            label=f"corr({a}, {b})",
            operation="PEARSON_CORR",
            formula_plain=f"Pearson correlation between `{a}` and `{b}` = {coefficient}",
            value=coefficient,
            source_columns=[a, b],
            components=[("column_a", a), ("column_b", b)],
        )
        entry = provenance_to_dict(receipt)
        entry["sample_rows"] = sample_columns(df, [a, b])
        entries.append({"category": "correlation", **entry})

    # 4. Trends — OLS slope per detected series.
    seen_trends: set[str] = set()
    for series in (trends or {}).get("series", []) or []:
        value_column = series.get("value_column")
        slope = series.get("slope")
        if not value_column or slope is None or value_column in seen_trends:
            continue
        seen_trends.add(value_column)
        slope_value = round(float(slope), 4)
        direction = series.get("direction")
        receipt = build_derived_provenance(
            metric_key=f"trend.{value_column}",
            label=f"{value_column} trend",
            operation="OLS_SLOPE",
            formula_plain=f"Linear-trend slope of `{value_column}` = {slope_value} ({direction})",
            value=slope_value,
            source_columns=[value_column],
            components=[
                ("direction", direction),
                ("first_value", series.get("first_value")),
                ("last_value", series.get("last_value")),
                ("percent_change", series.get("percent_change")),
            ],
        )
        entries.append({"category": "trend", **provenance_to_dict(receipt)})

    # 5. Model metrics — one receipt per held-out evaluation metric.
    if (prediction or {}).get("status") == "complete":
        model = prediction.get("selected_model")
        target = prediction.get("target_column")
        test_rows = prediction.get("test_rows")
        for metric_name, metric_value in (prediction.get("test_metrics") or {}).items():
            if metric_value is None:
                continue
            value = round(float(metric_value), 4)
            receipt = build_derived_provenance(
                metric_key=f"model.{metric_name}",
                label=f"{model} {metric_name}",
                operation="MODEL_EVAL",
                formula_plain=(
                    f"{model} {metric_name} on {test_rows} held-out rows predicting "
                    f"`{target}` = {value}"
                ),
                value=value,
                source_columns=[target] if target else [],
                components=[
                    ("model", model),
                    ("target", target),
                    ("test_rows", test_rows),
                    (metric_name, value),
                ],
            )
            entries.append({"category": "model", **provenance_to_dict(receipt)})

    return entries
