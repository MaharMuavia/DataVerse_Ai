"""Deterministic provenance ("receipts") for business metrics.

Self-contained: pandas + stdlib only, so it can be imported by
business_metrics without circular-import risk. Every receipt records HOW a
number was computed; the value itself is always the same value the metric
reports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class Provenance:
    metric_key: str
    label: str
    operation: str
    formula_plain: str
    source_columns: list[str]
    value: Any
    row_count: int
    sample_rows: list[dict[str, Any]] = field(default_factory=list)


def _coerce(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        return value
    try:
        import numpy as np

        if isinstance(value, np.generic):
            return value.item()
    except Exception:
        pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def _sample_rows(
    df: pd.DataFrame | None,
    series: pd.Series | None,
    source_columns: list[str],
    sample_n: int = 5,
) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    cols = [c for c in source_columns if c in df.columns]
    try:
        if series is not None:
            order = series.abs().sort_values(ascending=False)
            idx = list(order.index[:sample_n])
        else:
            idx = list(df.index[:sample_n])
        subset = df.loc[idx, cols] if cols else df.loc[idx]
    except Exception:
        subset = df.head(sample_n)[cols] if cols else df.head(sample_n)
    rows: list[dict[str, Any]] = []
    for record in subset.to_dict(orient="records"):
        rows.append({key: _coerce(val) for key, val in record.items()})
    return rows


def build_series_provenance(
    *,
    metric_key: str,
    label: str,
    operation: str,
    series: pd.Series | None,
    df: pd.DataFrame | None,
    source_columns: list[str],
    value: Any,
    sample_n: int = 5,
) -> Provenance:
    row_count = int(series.notna().sum()) if series is not None else 0
    cols = list(source_columns or [])
    col_text = ", ".join(f"`{c}`" for c in cols) if cols else "values"
    formula = f"{operation} of {col_text} across {row_count} rows = {value}"
    return Provenance(
        metric_key=metric_key,
        label=label,
        operation=operation,
        formula_plain=formula,
        source_columns=cols,
        value=_coerce(value),
        row_count=row_count,
        sample_rows=_sample_rows(df, series, cols, sample_n),
    )


def build_derived_provenance(
    *,
    metric_key: str,
    label: str,
    operation: str,
    formula_plain: str,
    value: Any,
    source_columns: list[str],
    components: list[tuple[str, Any]],
) -> Provenance:
    sample = [{"component": name, "value": _coerce(val)} for name, val in components]
    return Provenance(
        metric_key=metric_key,
        label=label,
        operation=operation,
        formula_plain=formula_plain,
        source_columns=list(source_columns or []),
        value=_coerce(value),
        row_count=len(components),
        sample_rows=sample,
    )


def provenance_to_dict(provenance: Provenance) -> dict[str, Any]:
    return {
        "metric_key": provenance.metric_key,
        "label": provenance.label,
        "operation": provenance.operation,
        "formula_plain": provenance.formula_plain,
        "source_columns": provenance.source_columns,
        "value": provenance.value,
        "row_count": provenance.row_count,
        "sample_rows": provenance.sample_rows,
    }
