from __future__ import annotations

from typing import Any, Dict
from pathlib import Path

import numpy as np
import pandas as pd
from langchain_core.tools import tool


def _load_dataframe(df_path: str) -> pd.DataFrame:
    path = Path(df_path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".json":
        return pd.read_json(path)
    if suffix == ".pkl":
        return pd.read_pickle(path)
    return pd.read_csv(path)


@tool
def read_csv_tool(df_path: str) -> Dict[str, Any]:
    """Read a CSV file and return lightweight preview metadata."""
    df = _load_dataframe(df_path)
    return {
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "columns": list(df.columns),
        "preview": df.head(5).to_dict(orient="records"),
    }


@tool
def get_column_stats_tool(df_path: str) -> Dict[str, Any]:
    """Return dataset metadata and describe() statistics for a CSV path."""
    df = _load_dataframe(df_path)
    return {
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "null_counts": {col: int(v) for col, v in df.isnull().sum().items()},
        "describe": df.describe(include="all").fillna("").to_dict(),
    }


@tool
def detect_outliers_tool(column: str, method: str, df_path: str) -> Dict[str, Any]:
    """Detect outliers in a numeric column using iqr, zscore, or isolation_forest."""
    df = _load_dataframe(df_path)
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}

    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return {"error": f"Column '{column}' has no numeric values"}

    method = method.lower()
    if method == "iqr":
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (series < low) | (series > high)
        indices = series[mask].index.tolist()
        return {"method": "iqr", "count": len(indices), "indices": indices[:500], "bounds": [float(low), float(high)]}

    if method == "zscore":
        z = np.abs((series - series.mean()) / (series.std(ddof=0) + 1e-12))
        indices = series[z > 3.0].index.tolist()
        return {"method": "zscore", "count": len(indices), "indices": indices[:500], "threshold": 3.0}

    if method == "isolation_forest":
        from sklearn.ensemble import IsolationForest

        clf = IsolationForest(contamination=0.05, random_state=42)
        preds = clf.fit_predict(series.to_frame())
        outlier_indices = series[preds == -1].index.tolist()
        return {"method": "isolation_forest", "count": len(outlier_indices), "indices": outlier_indices[:500]}

    return {"error": "Unsupported method. Use iqr, zscore, or isolation_forest"}


@tool
def detect_drift_tool(column: str, baseline_df_path: str, current_df_path: str) -> Dict[str, Any]:
    """Detect basic distribution drift using mean/std deltas for numeric columns."""
    baseline_df = _load_dataframe(baseline_df_path)
    current_df = _load_dataframe(current_df_path)

    if column not in baseline_df.columns or column not in current_df.columns:
        return {"error": f"Column '{column}' not found in one or both datasets"}

    b = pd.to_numeric(baseline_df[column], errors="coerce").dropna()
    c = pd.to_numeric(current_df[column], errors="coerce").dropna()
    if b.empty or c.empty:
        return {"error": f"Column '{column}' has no numeric values in one dataset"}

    mean_delta = float(c.mean() - b.mean())
    std_delta = float(c.std(ddof=0) - b.std(ddof=0))
    drift_score = float(abs(mean_delta) / (abs(b.mean()) + 1e-9))

    return {
        "column": column,
        "baseline_mean": float(b.mean()),
        "current_mean": float(c.mean()),
        "mean_delta": mean_delta,
        "std_delta": std_delta,
        "drift_score": drift_score,
        "drift_detected": drift_score > 0.2,
    }


@tool
def run_zscore_tool(column: str, df_path: str, threshold: float = 3.0) -> Dict[str, Any]:
    """Return rows where absolute z-score exceeds threshold."""
    df = _load_dataframe(df_path)
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}

    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return {"error": f"Column '{column}' has no numeric values"}

    z = np.abs((series - series.mean()) / (series.std(ddof=0) + 1e-12))
    indices = series[z > float(threshold)].index.tolist()
    return {
        "column": column,
        "threshold": float(threshold),
        "count": len(indices),
        "indices": indices[:500],
    }
