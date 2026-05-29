"""Dataset profiling and semantic column detection for business analytics."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

import pandas as pd


SEMANTIC_HINTS: dict[str, list[str]] = {
    "date": ["date", "order_date", "created_at", "timestamp", "time", "day", "month"],
    "product": ["product", "product_name", "item", "sku", "title", "name"],
    "revenue": ["sales", "revenue", "amount", "total", "total_sales", "sales_amount"],
    "quantity": ["quantity", "qty", "units", "units_sold", "volume"],
    "price": ["price", "unit_price", "cost", "rate"],
    "category": ["category", "department", "segment", "type", "class"],
    "region": ["region", "country", "city", "state", "location", "territory", "area"],
    "customer": ["customer", "customer_id", "buyer", "client", "user"],
    "order_id": ["order_id", "order", "invoice", "transaction", "receipt"],
    "profit": ["profit", "margin", "net_profit", "gross_profit"],
}


def _normalize(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")


def _name_score(column: str, hints: list[str]) -> float:
    normalized = _normalize(column)
    tokens = set(normalized.split("_"))
    best = 0.0
    for hint in hints:
        hint_norm = _normalize(hint)
        hint_tokens = set(hint_norm.split("_"))
        if normalized == hint_norm:
            return 1.0
        if hint_norm in normalized:
            best = max(best, 0.88)
        if tokens & hint_tokens:
            best = max(best, 0.72)
        best = max(best, SequenceMatcher(None, normalized, hint_norm).ratio() * 0.68)
    return best


def _looks_like_date(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if pd.api.types.is_numeric_dtype(series):
        return False
    sample = series.dropna().astype(str).head(20)
    if sample.empty:
        return False
    dateish = sample.str.contains(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", regex=True)
    if int(dateish.sum()) < max(1, int(len(sample) * 0.5)):
        return False
    parsed = pd.to_datetime(series, errors="coerce")
    return bool(parsed.notna().sum() >= max(2, int(len(series.dropna()) * 0.55)))


def _safe_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def dataframe_preview(df: pd.DataFrame, rows: int = 10) -> list[dict[str, Any]]:
    return [
        {str(column): _safe_value(value) for column, value in row.items()}
        for row in df.head(rows).to_dict(orient="records")
    ]


def detect_semantic_columns(df: pd.DataFrame) -> dict[str, str | None]:
    """Detect common business roles using column names plus basic dtype checks."""
    detected: dict[str, str | None] = {role: None for role in SEMANTIC_HINTS}

    for role, hints in SEMANTIC_HINTS.items():
        best_column: str | None = None
        best_score = 0.0
        for column in df.columns:
            series = df[column]
            score = _name_score(str(column), hints)

            if role == "date":
                if _looks_like_date(series):
                    score = max(score, 0.93)
                elif pd.api.types.is_numeric_dtype(series):
                    score *= 0.35
            elif role in {"revenue", "quantity", "price", "profit"}:
                if pd.api.types.is_numeric_dtype(series):
                    score += 0.12
                else:
                    numeric = pd.to_numeric(series, errors="coerce")
                    if numeric.notna().sum() >= max(2, int(len(series.dropna()) * 0.7)):
                        score += 0.08
                    else:
                        score *= 0.45
            elif role in {"product", "category", "region", "customer", "order_id"}:
                if pd.api.types.is_numeric_dtype(series) and role not in {"customer", "order_id"}:
                    score *= 0.45

            if score > best_score:
                best_score = score
                best_column = str(column)

        detected[role] = best_column if best_score >= 0.58 else None

    return detected


def coerce_analysis_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with likely date/numeric business columns converted safely."""
    result = df.copy()
    semantics = detect_semantic_columns(result)

    for role in ("revenue", "quantity", "price", "profit"):
        column = semantics.get(role)
        if column and column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")

    date_column = semantics.get("date")
    if date_column and date_column in result.columns:
        result[date_column] = pd.to_datetime(result[date_column], errors="coerce")

    return result


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    df = coerce_analysis_dataframe(df)
    semantic_columns = detect_semantic_columns(df)
    missing = df.isna().sum()
    missing_pct = (missing / max(1, len(df)) * 100).round(2)
    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
    date_columns = [
        column for column in df.columns
        if pd.api.types.is_datetime64_any_dtype(df[column]) or _looks_like_date(df[column])
    ]
    text_columns = [
        column for column in df.columns
        if column not in numeric_columns and column not in date_columns
    ]

    numeric_summary: dict[str, dict[str, float | None]] = {}
    for column in numeric_columns:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            numeric_summary[column] = {"min": None, "max": None, "mean": None, "median": None}
            continue
        numeric_summary[column] = {
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
            "mean": round(float(series.mean()), 4),
            "median": round(float(series.median()), 4),
        }

    column_profiles = []
    for column in df.columns:
        column_profiles.append(
            {
                "name": str(column),
                "dtype": str(df[column].dtype),
                "missing": int(missing[column]),
                "missing_pct": float(missing_pct[column]),
                "unique": int(df[column].nunique(dropna=True)),
                "role": next(
                    (role for role, role_column in semantic_columns.items() if role_column == column),
                    None,
                ),
            }
        )

    duplicate_rows = int(df.duplicated().sum())
    total_missing = int(missing.sum())
    total_cells = int(df.size)
    completeness = 1 - (total_missing / total_cells if total_cells else 0)
    duplicate_penalty = duplicate_rows / max(1, len(df))
    quality_score = max(0.0, min(100.0, (completeness - duplicate_penalty) * 100))

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": [str(column) for column in df.columns],
        "dtypes": {str(column): str(dtype) for column, dtype in df.dtypes.items()},
        "semantic_columns": semantic_columns,
        "numeric_columns": [str(column) for column in numeric_columns],
        "date_columns": [str(column) for column in date_columns],
        "text_columns": [str(column) for column in text_columns],
        "missing_values": {
            str(column): {"count": int(missing[column]), "pct": float(missing_pct[column])}
            for column in df.columns
        },
        "numeric_summary": numeric_summary,
        "quality": {
            "score": round(float(quality_score), 1),
            "duplicate_rows": duplicate_rows,
            "total_missing": total_missing,
            "total_cells": total_cells,
        },
        "column_profiles": column_profiles,
        "preview": dataframe_preview(df),
    }
