from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import shap
except ImportError:  # pragma: no cover - depends on local environment
    shap = None

try:
    from lime import lime_tabular
except ImportError:  # pragma: no cover - depends on local environment
    lime_tabular = None


def _normalize_shap_outputs(
    values: Any,
    base_values: Any,
    n_rows: int,
    n_features: int,
    output_index: Optional[int] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[int]]:
    """Normalize SHAP outputs to a 2D matrix of shape [rows, features]."""
    chosen_index = output_index

    if isinstance(values, list):
        if not values:
            raise ValueError("Empty SHAP value list returned.")
        if chosen_index is None:
            chosen_index = 1 if len(values) > 1 else 0
        values = values[chosen_index]
        if isinstance(base_values, (list, tuple, np.ndarray)) and len(np.atleast_1d(base_values)) > chosen_index:
            base_values = np.atleast_1d(base_values)[chosen_index]

    matrix = np.asarray(values)

    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    elif matrix.ndim == 3:
        if matrix.shape[0] == n_rows and matrix.shape[1] == n_features:
            if chosen_index is None:
                chosen_index = 1 if matrix.shape[2] > 1 else 0
            matrix = matrix[:, :, chosen_index]
        elif matrix.shape[1] == n_rows and matrix.shape[2] == n_features:
            if chosen_index is None:
                chosen_index = 1 if matrix.shape[0] > 1 else 0
            matrix = matrix[chosen_index, :, :]
        else:
            raise ValueError(f"Unsupported SHAP output shape: {matrix.shape}")

    if matrix.ndim != 2:
        raise ValueError(f"Unsupported SHAP output dimensionality: {matrix.ndim}")

    if base_values is None:
        normalized_base = None
    else:
        normalized_base = np.asarray(base_values)
        if normalized_base.ndim > 1:
            normalized_base = normalized_base.reshape(-1)
        if normalized_base.size == 1:
            normalized_base = normalized_base.astype(float)
        elif normalized_base.size >= n_rows:
            normalized_base = normalized_base[:n_rows].astype(float)
        else:
            normalized_base = normalized_base.astype(float)

    return matrix.astype(float), normalized_base, chosen_index


def _preferred_output_index(model: Any, rows: pd.DataFrame, fallback: Optional[int] = None) -> Optional[int]:
    """Pick a meaningful output index for multi-output SHAP explanations."""
    if fallback is not None:
        return fallback

    if hasattr(model, "predict_proba"):
        try:
            probabilities = model.predict_proba(rows)
            if isinstance(probabilities, list):
                probabilities = probabilities[0]
            probabilities = np.asarray(probabilities)
            if probabilities.ndim == 2 and probabilities.shape[1] > 1:
                return int(np.argmax(probabilities[0]))
        except Exception:
            return fallback

    return fallback


def compute_shap_explanation(
    model: Any,
    background: pd.DataFrame,
    rows: pd.DataFrame,
    output_index: Optional[int] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray], str, Optional[int]]:
    """Compute SHAP values using the best available explainer strategy."""
    if shap is None:
        raise ImportError("SHAP is not installed.")

    preferred_index = _preferred_output_index(model, rows, output_index)
    attempts = [
        ("Explainer", lambda: shap.Explainer(model, background)),
        ("TreeExplainer", lambda: shap.TreeExplainer(model)),
        ("LinearExplainer", lambda: shap.LinearExplainer(model, background)),
        (
            "KernelExplainer",
            lambda: shap.KernelExplainer(
                model.predict_proba if hasattr(model, "predict_proba") else model.predict,
                background.iloc[: min(len(background), 50)],
            ),
        ),
    ]

    last_error: Optional[Exception] = None
    for name, factory in attempts:
        try:
            explainer = factory()
            try:
                explanation = explainer(rows)
                values = explanation.values
                base_values = getattr(explanation, "base_values", None)
            except Exception:
                values = explainer.shap_values(rows)
                base_values = getattr(explainer, "expected_value", None)

            matrix, normalized_base, chosen_index = _normalize_shap_outputs(
                values=values,
                base_values=base_values,
                n_rows=len(rows),
                n_features=rows.shape[1],
                output_index=preferred_index,
            )
            return matrix, normalized_base, name, chosen_index
        except Exception as exc:  # pragma: no cover - best-effort fallbacks
            last_error = exc
            continue

    raise RuntimeError(f"Unable to compute SHAP explanation: {last_error}")


def compute_lime_explanation(
    model: Any,
    background: pd.DataFrame,
    row: pd.DataFrame,
    task_type: str,
    num_features: int = 10,
) -> Dict[str, float]:
    """Compute a LIME explanation for a single row."""
    if lime_tabular is None:
        raise ImportError("LIME is not installed.")

    explainer = lime_tabular.LimeTabularExplainer(
        background.values,
        feature_names=background.columns.tolist(),
        mode="classification" if task_type == "classification" else "regression",
        verbose=False,
    )

    if task_type == "classification" and hasattr(model, "predict_proba"):
        predict_fn = model.predict_proba
    else:
        predict_fn = model.predict

    explanation = explainer.explain_instance(
        row.iloc[0].values,
        predict_fn,
        num_features=min(num_features, row.shape[1]),
    )

    feature_weights: Dict[str, float] = {}
    for feature, weight in explanation.as_list():
        feature_weights[str(feature)] = float(weight)
    return feature_weights
