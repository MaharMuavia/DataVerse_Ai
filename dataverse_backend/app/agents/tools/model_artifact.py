from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd


def get_model_storage_dir() -> Path:
    """Return the directory used to persist trained model artifacts."""
    configured = os.getenv("DATAVERSE_MODEL_DIR")
    if configured:
        path = Path(configured)
    else:
        path = Path(__file__).resolve().parents[3] / "model_storage"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_model_artifact_path(model_id: str) -> Path:
    """Return the pickle path for a model artifact."""
    return get_model_storage_dir() / f"{model_id}.pkl"


def save_model_artifact(model_id: str, artifact: Dict[str, Any]) -> Path:
    """Persist a model artifact and return the written path."""
    path = get_model_artifact_path(model_id)
    with path.open("wb") as handle:
        pickle.dump(artifact, handle)
    return path


def load_model_artifact(model_id: str) -> Dict[str, Any]:
    """Load a saved model artifact, supporting older plain-model pickle files."""
    path = get_model_artifact_path(model_id)
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found for '{model_id}' at {path}")

    with path.open("rb") as handle:
        loaded = pickle.load(handle)

    if isinstance(loaded, dict) and "model" in loaded:
        loaded.setdefault("model_id", model_id)
        return loaded

    # Backward compatibility for older model-only pickles.
    return {
        "version": 1,
        "model_id": model_id,
        "model": loaded,
        "feature_cols": None,
        "fill_values": {},
        "task_type": "unknown",
        "target_col": None,
        "label_encoder": None,
        "class_names": None,
        "feature_stats": {},
        "background_sample": None,
    }


def compute_fill_values(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute stable fill values for each feature column."""
    fill_values: Dict[str, Any] = {}
    for column in df.columns:
        series = df[column]
        if pd.api.types.is_numeric_dtype(series):
            value = series.median()
            fill_values[column] = 0.0 if pd.isna(value) else float(value)
        else:
            mode = series.mode(dropna=True)
            fill_values[column] = mode.iloc[0] if not mode.empty else ""
    return fill_values


def prepare_feature_frame(df: pd.DataFrame, artifact: Dict[str, Any]) -> pd.DataFrame:
    """Prepare model feature inputs using artifact metadata."""
    feature_cols = artifact.get("feature_cols")
    if not feature_cols:
        raise ValueError("Model artifact does not include feature columns.")

    missing = [column for column in feature_cols if column not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required feature columns: {missing}")

    X = df[feature_cols].copy()
    fill_values = artifact.get("fill_values", {})
    if fill_values:
        for column in X.columns:
            if column in fill_values:
                X[column] = X[column].fillna(fill_values[column])

    # Keep booleans numeric-friendly for sklearn explainers and distance metrics.
    for column in X.columns:
        if pd.api.types.is_bool_dtype(X[column]):
            X[column] = X[column].astype(int)

    return X


def compute_feature_stats(X: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Collect numeric feature stats used for explanations and counterfactual search."""
    stats: Dict[str, Dict[str, float]] = {}
    for column in X.columns:
        if pd.api.types.is_numeric_dtype(X[column]):
            series = X[column].astype(float)
            stats[column] = {
                "mean": float(series.mean()),
                "std": float(series.std(ddof=0)) if len(series) > 1 else 0.0,
                "min": float(series.min()),
                "max": float(series.max()),
                "median": float(series.median()),
            }
    return stats


def get_background_sample(X: pd.DataFrame, artifact: Dict[str, Any], max_rows: int = 100) -> pd.DataFrame:
    """Return a compact background sample for SHAP/LIME explainers."""
    background = artifact.get("background_sample")
    if isinstance(background, pd.DataFrame) and not background.empty:
        usable = background.copy()
        common_columns = [column for column in X.columns if column in usable.columns]
        if common_columns:
            return usable[common_columns]

    if len(X) <= max_rows:
        return X.copy()
    return X.sample(n=max_rows, random_state=42)


def decode_prediction(prediction: Any, artifact: Dict[str, Any]) -> Any:
    """Decode a model prediction back to its original label if possible."""
    label_encoder = artifact.get("label_encoder")
    if label_encoder is None:
        return prediction.item() if hasattr(prediction, "item") else prediction

    try:
        decoded = label_encoder.inverse_transform([prediction])[0]
        return decoded.item() if hasattr(decoded, "item") else decoded
    except Exception:
        return prediction.item() if hasattr(prediction, "item") else prediction


def encode_target_value(value: Any, artifact: Dict[str, Any]) -> Any:
    """Encode a target label using the saved label encoder when available."""
    label_encoder = artifact.get("label_encoder")
    if label_encoder is None:
        return value
    return label_encoder.transform([value])[0]


def prediction_label_and_score(model: Any, row: pd.DataFrame, artifact: Dict[str, Any]) -> Tuple[Any, Optional[float], Optional[int]]:
    """Return decoded prediction, confidence/score when available, and raw class index."""
    raw_prediction = model.predict(row)[0]
    decoded = decode_prediction(raw_prediction, artifact)

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(row)[0]
        raw_index = int(np.argmax(probabilities))
        return decode_prediction(raw_index, artifact), float(np.max(probabilities)), raw_index

    return decoded, None, int(raw_prediction) if isinstance(raw_prediction, (int, np.integer)) else None


def model_importance_hint(model: Any, feature_names: list[str]) -> Dict[str, float]:
    """Extract a model-native importance hint when available."""
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
        return {
            str(name): float(score)
            for name, score in sorted(zip(feature_names, values), key=lambda item: item[1], reverse=True)
        }

    if hasattr(model, "coef_"):
        values = np.asarray(model.coef_)
        if values.ndim > 1:
            values = np.mean(np.abs(values), axis=0)
        else:
            values = np.abs(values)
        return {
            str(name): float(score)
            for name, score in sorted(zip(feature_names, values), key=lambda item: item[1], reverse=True)
        }

    return {}
