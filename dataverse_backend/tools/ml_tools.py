from __future__ import annotations

from typing import Any, Dict, Optional
from pathlib import Path

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
def detect_ml_task_tool(user_message: str, target_hint: Optional[str] = None) -> Dict[str, str]:
    """Infer ML task type from user intent and optional target hint."""
    text = (user_message or "").lower()
    if "cluster" in text or "segment" in text:
        return {"task_type": "clustering"}
    if "forecast" in text or "time series" in text:
        return {"task_type": "forecast"}
    if any(k in text for k in ["predict", "probability", "class", "churn"]) and target_hint:
        return {"task_type": "classification"}
    if any(k in text for k in ["predict", "estimate", "revenue", "sales"]):
        return {"task_type": "regression"}
    return {"task_type": "regression"}


@tool
def run_pycaret_tool(task: str, target: str, df_path: str) -> Dict[str, Any]:
    """Run a PyCaret setup + compare_models flow and return best model metadata."""
    df = _load_dataframe(df_path)
    if target not in df.columns and task != "clustering":
        return {"error": f"Target column '{target}' not found"}

    try:
        if task == "classification":
            from pycaret.classification import compare_models, pull, setup

            setup(data=df, target=target, session_id=42, verbose=False, html=False)
            best = compare_models()
            metrics = pull().to_dict(orient="records")
            return {
                "task": task,
                "best_model": str(best),
                "metrics": metrics,
            }

        if task == "regression":
            from pycaret.regression import compare_models, pull, setup

            setup(data=df, target=target, session_id=42, verbose=False, html=False)
            best = compare_models()
            metrics = pull().to_dict(orient="records")
            return {
                "task": task,
                "best_model": str(best),
                "metrics": metrics,
            }

        if task == "clustering":
            from pycaret.clustering import create_model, pull, setup

            setup(data=df, session_id=42, verbose=False, html=False)
            model = create_model("kmeans")
            metrics = pull().to_dict(orient="records")
            return {"task": task, "best_model": str(model), "metrics": metrics}

        return {"error": f"Unsupported task '{task}'"}
    except Exception as exc:
        return {"error": f"PyCaret failed: {exc}"}


@tool
def run_shap_tool(model: Any, df_path: str, target: Optional[str] = None) -> Dict[str, Any]:
    """Return top SHAP feature importance values as JSON-serializable dict."""
    try:
        import shap
    except Exception as exc:
        return {"error": f"shap unavailable: {exc}"}

    df = _load_dataframe(df_path)
    if target and target in df.columns:
        X = df.drop(columns=[target])
    else:
        X = df.select_dtypes(include=["number"]).copy()

    if X.empty:
        return {"error": "No numeric features available for SHAP analysis"}

    if model is None:
        try:
            from sklearn.ensemble import RandomForestRegressor

            y = (
                pd.to_numeric(df[target], errors="coerce").fillna(0.0)
                if target and target in df.columns
                else pd.Series([0.0] * len(X))
            )
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            model.fit(X, y)
        except Exception as exc:
            return {"error": f"Unable to create fallback model for SHAP: {exc}"}

    try:
        explainer = shap.Explainer(model, X)
        shap_values = explainer(X)
        values = getattr(shap_values, "values", None)
        if values is None:
            return {"error": "Unable to compute SHAP values"}

        # Average absolute SHAP values by feature.
        import numpy as np

        importance = np.abs(values).mean(axis=0)
        feature_importance = {col: float(val) for col, val in zip(X.columns, importance)}
        top = dict(sorted(feature_importance.items(), key=lambda kv: kv[1], reverse=True)[:20])
        return {"feature_importance": top}
    except Exception as exc:
        return {"error": f"SHAP computation failed: {exc}"}
