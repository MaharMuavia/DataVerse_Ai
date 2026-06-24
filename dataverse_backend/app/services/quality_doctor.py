"""Data Quality Doctor: deterministically detect issues and propose/apply fixes.

Detection is read-only; every proposed fix is a plain pandas transform with a
stated before/after impact, so cleaning is reproducible and explainable.
"""
from __future__ import annotations

from typing import Any

import pandas as pd


def _stats(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "missing_cells": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
    }


def _mostly_numeric_text(series: pd.Series) -> bool:
    """True for an object column whose non-null values are >=90% numeric."""
    if series.dtype != object:
        return False
    non_null = series.dropna()
    if non_null.empty:
        return False
    coerced = pd.to_numeric(non_null, errors="coerce")
    return float(coerced.notna().mean()) >= 0.9


def diagnose(df: pd.DataFrame | None) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if df is None or df.empty or df.shape[1] == 0:
        return {"issues": issues, "summary": _stats(df if df is not None else pd.DataFrame())}

    total_rows = len(df)

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows > 0:
        issues.append({
            "id": "duplicates",
            "category": "duplicates",
            "column": None,
            "severity": "high",
            "issue": f"{duplicate_rows} duplicate row(s) found.",
            "fix": f"Drop {duplicate_rows} duplicate row(s).",
            "fix_type": "drop_duplicates",
            "impact": {"before": f"{total_rows} rows", "after": f"{total_rows - duplicate_rows} rows"},
        })

    for column in df.columns:
        series = df[column]

        # Constant column — no analytical signal.
        if series.nunique(dropna=True) <= 1:
            issues.append({
                "id": f"constant:{column}",
                "category": "constant_column",
                "column": column,
                "severity": "low",
                "issue": f"Column `{column}` has a single value; it carries no signal.",
                "fix": f"Drop the constant column `{column}`.",
                "fix_type": "drop_column",
                "impact": {"before": f"{df.shape[1]} columns", "after": f"{df.shape[1] - 1} columns"},
            })
            continue

        # Numeric stored as text.
        if _mostly_numeric_text(series):
            issues.append({
                "id": f"cast:{column}",
                "category": "type_mismatch",
                "column": column,
                "severity": "medium",
                "issue": f"Column `{column}` holds numbers stored as text.",
                "fix": f"Cast `{column}` to a numeric type.",
                "fix_type": "cast_numeric",
                "impact": {"before": "text", "after": "numeric"},
            })

        # Missing values.
        missing = int(series.isna().sum())
        if missing > 0:
            pct = round(missing / total_rows * 100, 1)
            if pd.api.types.is_numeric_dtype(series):
                fill = pd.to_numeric(series, errors="coerce").median()
                issues.append({
                    "id": f"missing:{column}",
                    "category": "missing_values",
                    "column": column,
                    "severity": "high" if pct >= 20 else "medium",
                    "issue": f"Column `{column}` has {missing} missing value(s) ({pct}%).",
                    "fix": f"Impute {missing} missing value(s) with the median ({_round(fill)}).",
                    "fix_type": "impute_median",
                    "impact": {"before": f"{missing} missing", "after": "0 missing"},
                })
            else:
                modes = series.mode()
                fill = modes.iloc[0] if not modes.empty else None
                issues.append({
                    "id": f"missing:{column}",
                    "category": "missing_values",
                    "column": column,
                    "severity": "high" if pct >= 20 else "medium",
                    "issue": f"Column `{column}` has {missing} missing value(s) ({pct}%).",
                    "fix": f"Impute {missing} missing value(s) with the most frequent value ({fill}).",
                    "fix_type": "impute_mode",
                    "impact": {"before": f"{missing} missing", "after": "0 missing"},
                })

    return {"issues": issues, "summary": {**_stats(df), "total_issues": len(issues)}}


def apply_fixes(df: pd.DataFrame, fix_ids: list[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    requested = set(fix_ids or [])
    issues = {i["id"]: i for i in diagnose(df)["issues"]}
    work = df.copy()
    applied: list[str] = []
    before = _stats(df)

    def selected(fix_type: str) -> list[dict[str, Any]]:
        return [issues[i] for i in requested if i in issues and issues[i]["fix_type"] == fix_type]

    # 1. Cast numeric-as-text.
    for issue in selected("cast_numeric"):
        col = issue["column"]
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")
            applied.append(issue["fix"])

    # 2. Drop constant columns.
    for issue in selected("drop_column"):
        col = issue["column"]
        if col in work.columns:
            work = work.drop(columns=[col])
            applied.append(issue["fix"])

    # 3. Impute missing (recompute from current frame for correctness).
    for issue in selected("impute_median"):
        col = issue["column"]
        if col in work.columns and work[col].isna().any():
            work[col] = work[col].fillna(pd.to_numeric(work[col], errors="coerce").median())
            applied.append(issue["fix"])
    for issue in selected("impute_mode"):
        col = issue["column"]
        if col in work.columns and work[col].isna().any():
            modes = work[col].mode()
            if not modes.empty:
                work[col] = work[col].fillna(modes.iloc[0])
                applied.append(issue["fix"])

    # 4. Drop duplicates last, so imputation can't reintroduce them.
    if any(issues.get(i, {}).get("fix_type") == "drop_duplicates" for i in requested):
        work = work.drop_duplicates(ignore_index=True)
        applied.append("Drop duplicate rows.")

    return work, {"applied": applied, "before": before, "after": _stats(work)}


def _round(value: Any) -> Any:
    try:
        value = float(value)
        return int(value) if value.is_integer() else round(value, 2)
    except (TypeError, ValueError):
        return value
