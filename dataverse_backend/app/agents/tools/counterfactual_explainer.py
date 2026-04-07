from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .base_tool import BaseTool
from .model_artifact import (
    decode_prediction,
    encode_target_value,
    load_model_artifact,
    prediction_label_and_score,
    prepare_feature_frame,
)

try:
    import dice_ml  # noqa: F401

    HAS_DICE = True
except ImportError:  # pragma: no cover - depends on local environment
    HAS_DICE = False


class CounterfactualExplainerTool(BaseTool):
    """Tool for generating counterfactual explanations using model-backed nearest contrasts."""

    def __init__(self):
        super().__init__()
        self.name = "explain_counterfactual"
        self.aliases = ["counterfactual_explainer"]
        self.description = """Generate counterfactual explanations for model predictions.
USE WHEN: User asks 'what would need to change?' or 'why this prediction?'"""
        self.input_schema = {
            "model_id": {
                "type": "string",
                "description": "ID of the trained model",
            },
            "row_index": {
                "type": "integer",
                "description": "Index of the row to explain",
            },
            "n_counterfactuals": {
                "type": "integer",
                "description": "Number of counterfactuals to generate",
                "default": 3,
            },
            "desired_class": {
                "type": "string",
                "description": "Optional target class for classification models",
                "default": None,
            },
            "desired_direction": {
                "type": "string",
                "enum": ["increase", "decrease"],
                "description": "Optional direction for regression counterfactuals",
                "default": None,
            },
            "desired_prediction": {
                "type": "number",
                "description": "Optional target prediction value for regression counterfactuals",
                "default": None,
            },
        }
        self.output_schema = {
            "description": "TableSpec showing original vs counterfactual values",
        }

    async def execute(self, params: Dict[str, Any], session) -> Any:
        try:
            from ..core.tool_registry import ToolResult

            model_id = params.get("model_id")
            row_index = int(params.get("row_index", 0))
            n_counterfactuals = max(1, int(params.get("n_counterfactuals", 3)))

            if not model_id:
                return ToolResult(
                    success=False,
                    data={},
                    error_message="No model_id was provided.",
                    confidence=0.0,
                )

            artifact = load_model_artifact(model_id)
            model = artifact["model"]

            df = self.load_dataset(session)
            X = prepare_feature_frame(df, artifact)

            if row_index < 0 or row_index >= len(X):
                return ToolResult(
                    success=False,
                    data={},
                    error_message=f"Row index {row_index} out of bounds",
                    confidence=0.0,
                )

            source_row = X.iloc[[row_index]]
            source_prediction, source_score, _ = prediction_label_and_score(model, source_row, artifact)

            task_type = artifact.get("task_type")
            if task_type == "classification":
                counterfactuals = self._classification_counterfactuals(
                    model=model,
                    X=X,
                    artifact=artifact,
                    row_index=row_index,
                    desired_class=params.get("desired_class"),
                    limit=n_counterfactuals,
                )
            else:
                counterfactuals = self._regression_counterfactuals(
                    model=model,
                    X=X,
                    artifact=artifact,
                    row_index=row_index,
                    desired_direction=params.get("desired_direction"),
                    desired_prediction=params.get("desired_prediction"),
                    limit=n_counterfactuals,
                )

            if not counterfactuals:
                return ToolResult(
                    success=False,
                    data={},
                    error_message="Could not find a plausible counterfactual from the observed dataset.",
                    confidence=0.0,
                )

            table_data = []
            source_values = source_row.iloc[0]
            for index, candidate in enumerate(counterfactuals, start=1):
                candidate_row = candidate["row"]
                changed_features = []
                for feature in X.columns:
                    source_value = source_values[feature]
                    candidate_value = candidate_row[feature]
                    if not self._same_value(source_value, candidate_value):
                        changed_features.append(f"{feature}: {self._format_value(source_value)} -> {self._format_value(candidate_value)}")

                table_data.append(
                    {
                        "scenario": f"Counterfactual {index}",
                        "predicted_outcome": str(candidate["prediction"]),
                        "score": self._format_value(candidate.get("score")),
                        "distance": f"{candidate['distance']:.3f}",
                        "changes": "; ".join(changed_features[:5]) if changed_features else "No feature change captured",
                    }
                )

            original_data = {
                "scenario": "Original",
                "predicted_outcome": str(source_prediction),
                "score": self._format_value(source_score),
                "distance": "0.000",
                "changes": "Current observation",
            }
            table_data.insert(0, original_data)

            table_spec = self.create_table_spec(
                columns=["scenario", "predicted_outcome", "score", "distance", "changes"],
                data=table_data,
                title="Counterfactual Scenarios",
            )

            summary_changes = self._summarize_change_patterns(counterfactuals, source_values)
            narrative = (
                f"Generated {len(counterfactuals)} model-backed counterfactual scenarios for row {row_index}. "
                f"Current predicted outcome: {source_prediction}. "
                f"Most common change pattern: {summary_changes}."
            )
            if task_type == "classification" and params.get("desired_class"):
                narrative += f" Target class requested: {params['desired_class']}."
            narrative_spec = self.create_narrative_spec(narrative, "professional")

            return ToolResult(
                success=True,
                data={
                    "model_id": model_id,
                    "method": "nearest_observed_counterfactual",
                    "task_type": task_type,
                    "original_prediction": source_prediction,
                    "original_score": source_score,
                    "counterfactuals": [
                        {
                            "prediction": item["prediction"],
                            "score": item.get("score"),
                            "distance": item["distance"],
                            "row_index": item["row_index"],
                        }
                        for item in counterfactuals
                    ],
                },
                display=[table_spec, narrative_spec],
            )

        except Exception as e:
            from ..core.tool_registry import ToolResult

            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0,
            )

    def _classification_counterfactuals(
        self,
        model: Any,
        X: pd.DataFrame,
        artifact: Dict[str, Any],
        row_index: int,
        desired_class: Any,
        limit: int,
    ) -> List[Dict[str, Any]]:
        source_row = X.iloc[[row_index]]
        source_label, _, _ = prediction_label_and_score(model, source_row, artifact)
        raw_predictions = model.predict(X)
        decoded_predictions = [decode_prediction(value, artifact) for value in raw_predictions]

        if desired_class is not None:
            try:
                target_label = desired_class
                target_encoded = encode_target_value(desired_class, artifact)
                candidate_mask = raw_predictions == target_encoded
            except Exception:
                candidate_mask = np.array([str(label) == str(desired_class) for label in decoded_predictions])
        else:
            target_label = None
            candidate_mask = np.array([str(label) != str(source_label) for label in decoded_predictions])

        candidate_mask[row_index] = False
        candidate_indices = np.where(candidate_mask)[0]
        return self._rank_candidates(model, X, artifact, row_index, candidate_indices, limit, target_label=target_label)

    def _regression_counterfactuals(
        self,
        model: Any,
        X: pd.DataFrame,
        artifact: Dict[str, Any],
        row_index: int,
        desired_direction: Any,
        desired_prediction: Any,
        limit: int,
    ) -> List[Dict[str, Any]]:
        source_row = X.iloc[[row_index]]
        source_prediction = float(model.predict(source_row)[0])
        all_predictions = np.asarray(model.predict(X), dtype=float)

        if desired_prediction is not None:
            target_value = float(desired_prediction)
            candidate_mask = all_predictions >= target_value if target_value >= source_prediction else all_predictions <= target_value
        else:
            std = float(np.std(all_predictions)) if len(all_predictions) > 1 else 0.0
            delta = std * 0.5 if std > 0 else max(abs(source_prediction) * 0.1, 1.0)
            direction = desired_direction or "increase"
            if direction == "decrease":
                candidate_mask = all_predictions <= source_prediction - delta
            else:
                candidate_mask = all_predictions >= source_prediction + delta

        candidate_mask[row_index] = False
        candidate_indices = np.where(candidate_mask)[0]
        return self._rank_candidates(model, X, artifact, row_index, candidate_indices, limit)

    def _rank_candidates(
        self,
        model: Any,
        X: pd.DataFrame,
        artifact: Dict[str, Any],
        row_index: int,
        candidate_indices: np.ndarray,
        limit: int,
        target_label: Any = None,
    ) -> List[Dict[str, Any]]:
        if len(candidate_indices) == 0:
            return []

        source_row = X.iloc[row_index]
        stats = artifact.get("feature_stats", {})
        ranked: List[Dict[str, Any]] = []

        for index in candidate_indices.tolist():
            candidate_row = X.iloc[index]
            distance = 0.0
            for feature in X.columns:
                source_value = source_row[feature]
                candidate_value = candidate_row[feature]
                if pd.api.types.is_numeric_dtype(X[feature]):
                    std = stats.get(feature, {}).get("std", 0.0) or 1.0
                    distance += abs(float(candidate_value) - float(source_value)) / std
                else:
                    distance += 0.0 if self._same_value(source_value, candidate_value) else 1.0

            candidate_frame = X.iloc[[index]]
            prediction, score, _ = prediction_label_and_score(model, candidate_frame, artifact)
            if target_label is not None and str(prediction) != str(target_label):
                continue

            ranked.append(
                {
                    "row_index": index,
                    "row": candidate_row,
                    "prediction": prediction,
                    "score": score,
                    "distance": float(distance),
                }
            )

        ranked.sort(key=lambda item: item["distance"])
        return ranked[:limit]

    def _summarize_change_patterns(self, counterfactuals: List[Dict[str, Any]], source_values: pd.Series) -> str:
        """Summarize the repeated feature changes seen across counterfactuals."""
        direction_counts: Dict[str, int] = defaultdict(int)
        for candidate in counterfactuals:
            row = candidate["row"]
            for feature in row.index:
                if self._same_value(source_values[feature], row[feature]):
                    continue
                if isinstance(source_values[feature], (int, float, np.number)) and isinstance(row[feature], (int, float, np.number)):
                    direction = "higher" if float(row[feature]) > float(source_values[feature]) else "lower"
                    direction_counts[f"{feature} {direction}"] += 1
                else:
                    direction_counts[f"{feature} changed"] += 1

        if not direction_counts:
            return "no dominant feature change"
        top_patterns = sorted(direction_counts.items(), key=lambda item: item[1], reverse=True)[:3]
        return ", ".join(pattern for pattern, _ in top_patterns)

    def _same_value(self, left: Any, right: Any) -> bool:
        """Compare values while handling NaNs gracefully."""
        if pd.isna(left) and pd.isna(right):
            return True
        return left == right

    def _format_value(self, value: Any) -> str:
        """Format values for display."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "n/a"
        if isinstance(value, (int, float, np.number)):
            return f"{float(value):.4f}"
        return str(value)
