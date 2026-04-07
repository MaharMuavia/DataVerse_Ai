from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from .base_tool import BaseTool
from .model_artifact import (
    decode_prediction,
    get_background_sample,
    load_model_artifact,
    prediction_label_and_score,
    prepare_feature_frame,
)
from .xai_utils import compute_lime_explanation, compute_shap_explanation


class ExplainPredictionLocalTool(BaseTool):
    """Tool for explaining individual predictions using SHAP/LIME."""

    def __init__(self):
        super().__init__()
        self.name = "explain_prediction_local"
        self.description = """SHAP/LIME explanation for a specific row.
USE WHEN: User wants to understand why the model made a specific prediction."""
        self.input_schema = {
            "model_id": {
                "type": "string",
                "description": "ID of the trained model",
            },
            "row_index": {
                "type": "integer",
                "description": "Index of the row to explain",
            },
        }
        self.output_schema = {
            "description": "TableSpec with local explanation and NarrativeSpec",
        }

    async def execute(self, params: Dict[str, Any], session) -> Any:
        try:
            from ..core.tool_registry import ToolResult

            model_id = params.get("model_id")
            row_index = int(params.get("row_index", 0))
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

            row = X.iloc[[row_index]]
            background = get_background_sample(X, artifact)

            predicted_label, predicted_score, preferred_output_index = prediction_label_and_score(
                model, row, artifact
            )

            method = "shap"
            explainer_name = None
            base_value = None
            contributions: Dict[str, float]
            try:
                shap_matrix, base_values, explainer_name, _ = compute_shap_explanation(
                    model,
                    background,
                    row,
                    output_index=preferred_output_index,
                )
                contribution_values = shap_matrix[0]
                contributions = {
                    str(column): float(value)
                    for column, value in sorted(
                        zip(row.columns.tolist(), contribution_values),
                        key=lambda item: abs(item[1]),
                        reverse=True,
                    )
                }
                if base_values is not None:
                    base_scalar = np.asarray(base_values).reshape(-1)[0]
                    base_value = float(base_scalar)
            except Exception:
                method = "lime"
                contributions = compute_lime_explanation(
                    model=model,
                    background=background,
                    row=row,
                    task_type=artifact.get("task_type", "regression"),
                    num_features=min(10, row.shape[1]),
                )
                contributions = dict(
                    sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)
                )

            table_data = []
            for feature, contribution in list(contributions.items())[:10]:
                raw_value = row.iloc[0][feature] if feature in row.columns else None
                table_data.append(
                    {
                        "feature": feature,
                        "value": self._format_value(raw_value),
                        "contribution": round(float(contribution), 6),
                        "direction": "positive" if contribution >= 0 else "negative",
                    }
                )

            table_spec = self.create_table_spec(
                columns=["feature", "value", "contribution", "direction"],
                data=table_data,
                title="Local Prediction Explanation",
            )

            positive = [feature for feature, value in contributions.items() if value > 0][:3]
            negative = [feature for feature, value in contributions.items() if value < 0][:3]
            parts = [
                f"Prediction for row {row_index}: {predicted_label}",
                f"confidence/score {predicted_score:.3f}" if predicted_score is not None else None,
                f"Top positive drivers: {', '.join(positive)}" if positive else None,
                f"Top negative drivers: {', '.join(negative)}" if negative else None,
            ]
            if base_value is not None:
                parts.append(f"base value {base_value:.4f}")
            detail = f" Method: {method}"
            if explainer_name:
                detail += f" via {explainer_name}"
            narrative = ". ".join(part for part in parts if part) + "." + detail + "."
            narrative_spec = self.create_narrative_spec(narrative, "professional")

            result_data = {
                "model_id": model_id,
                "row_index": row_index,
                "method": method,
                "explainer": explainer_name,
                "prediction": predicted_label,
                "prediction_score": predicted_score,
                "base_value": base_value,
                "contributions": dict(list(contributions.items())[:10]),
            }

            return ToolResult(
                success=True,
                data=result_data,
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

    def _format_value(self, value: Any) -> str:
        """Format cell values for report-friendly display."""
        if isinstance(value, (int, float, np.number)):
            return f"{float(value):.4f}"
        return str(value)
