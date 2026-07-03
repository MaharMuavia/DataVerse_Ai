"""Counterfactual XAI: the smallest deterministic change that flips a prediction.

For each explained test row, scan the model's numeric features (most important
first) over a fixed multiplier grid and report the smallest single-feature change
that flips the predicted class (classification) or moves the prediction across
the observed target median (regression). The search is exhaustive over a fixed
grid — no randomness — so the same model and rows always produce the same
counterfactuals, keeping the "verifiable analyst" guarantee intact.

Categorical features are not perturbed in v1 (stated in limitations).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .modeling import TrainedModelBundle

MULTIPLIER_GRID = (0.05, 0.10, 0.15, 0.20, 0.30, 0.50)
MAX_ROWS = 3
MAX_COUNTERFACTUALS_PER_ROW = 2


def _predict_one(bundle: TrainedModelBundle, row: pd.DataFrame) -> Any:
    transformed = bundle.preprocessor.transform(row)
    return bundle.model.predict(transformed)[0]


def _numeric_features_by_importance(
    X: pd.DataFrame, feature_importance: list[dict[str, Any]] | None
) -> list[str]:
    numeric = [
        col for col in X.columns
        if pd.api.types.is_numeric_dtype(X[col]) and not pd.api.types.is_bool_dtype(X[col])
    ]
    rank = {str(item.get("feature")): index for index, item in enumerate(feature_importance or [])}
    return sorted(numeric, key=lambda col: (rank.get(col, len(rank)), col))


def _scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    return value


def _sentence(
    feature: str, original: float, new: float, pct: float, target: str,
    before: Any, after: Any, task_type: str, threshold: float | None,
) -> str:
    direction = "raising" if new > original else "lowering"
    if task_type == "classification":
        return (
            f"{direction.title()} `{feature}` from {original:g} to {new:g} ({pct:+.0f}%) "
            f"would flip the predicted {target} from '{before}' to '{after}'."
        )
    side = "above" if threshold is not None and float(after) >= threshold else "below"
    return (
        f"{direction.title()} `{feature}` from {original:g} to {new:g} ({pct:+.0f}%) "
        f"would move the predicted {target} from {float(before):g} to {float(after):g}, "
        f"crossing {side} the typical value ({threshold:g})."
    )


def generate_counterfactuals(
    bundle: TrainedModelBundle | None,
    feature_importance: list[dict[str, Any]] | None = None,
    max_rows: int = MAX_ROWS,
) -> dict[str, Any]:
    if bundle is None or bundle.X_test is None or len(bundle.X_test) == 0:
        return {"status": "skipped", "reason": "No trained model bundle available.", "rows": [], "limitations": []}

    limitations: list[str] = []
    task_type = bundle.task_type
    threshold: float | None = None
    if task_type == "regression":
        y_numeric = pd.to_numeric(pd.Series(bundle.y_test), errors="coerce").dropna()
        if y_numeric.empty:
            return {"status": "skipped", "reason": "Regression target values are not numeric.", "rows": [], "limitations": []}
        threshold = float(y_numeric.median())

    X = bundle.X_test
    candidates = _numeric_features_by_importance(X, feature_importance)
    if not candidates:
        return {
            "status": "skipped",
            "reason": "The model has no numeric features to perturb.",
            "rows": [],
            "limitations": ["Only numeric features are searched for counterfactuals."],
        }
    categorical = [col for col in X.columns if col not in candidates]
    if categorical:
        limitations.append(f"Categorical features are not perturbed: {', '.join(map(str, categorical[:5]))}.")

    rows_out: list[dict[str, Any]] = []
    for position in range(min(max_rows, len(X))):
        row = X.iloc[[position]]
        before = _scalar(_predict_one(bundle, row))
        found: list[dict[str, Any]] = []
        for feature in candidates:
            if len(found) >= MAX_COUNTERFACTUALS_PER_ROW:
                break
            original = float(row.iloc[0][feature])
            if original == 0 or not np.isfinite(original):
                continue
            hit: dict[str, Any] | None = None
            for multiplier in MULTIPLIER_GRID:
                for sign in (1.0, -1.0):
                    new_value = original * (1.0 + sign * multiplier)
                    candidate = row.copy()
                    candidate[feature] = candidate[feature].astype(float)
                    candidate.iloc[0, candidate.columns.get_loc(feature)] = new_value
                    after = _scalar(_predict_one(bundle, candidate))
                    if task_type == "classification":
                        success = str(after) != str(before)
                    else:
                        success = (float(before) >= threshold) != (float(after) >= threshold)
                    if success:
                        pct = sign * multiplier * 100.0
                        hit = {
                            "feature": str(feature),
                            "original": round(original, 6),
                            "new": round(new_value, 6),
                            "pct_change": round(pct, 2),
                            "prediction_before": before,
                            "prediction_after": after,
                            "sentence": _sentence(
                                str(feature), original, new_value, pct,
                                bundle.target_column, before, after, task_type, threshold,
                            ),
                        }
                        break
                if hit:
                    break
            if hit:
                found.append(hit)
        rows_out.append(
            {
                "sample_index": position,
                "row_index": _scalar(X.index[position]),
                "prediction_before": before,
                "counterfactuals": found,
            }
        )

    if not any(row["counterfactuals"] for row in rows_out):
        limitations.append(
            "No single-feature change within ±50% flipped the outcome for the sampled rows; "
            "the predictions are locally stable."
        )

    return {
        "status": "complete",
        "method": "deterministic_single_feature_search",
        "task_type": task_type,
        "target_column": bundle.target_column,
        "threshold": threshold,
        "multiplier_grid_pct": [m * 100 for m in MULTIPLIER_GRID],
        "rows": rows_out,
        "limitations": limitations,
    }
