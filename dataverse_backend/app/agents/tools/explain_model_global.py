from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .base_tool import BaseTool
from .model_artifact import (
    get_background_sample,
    load_model_artifact,
    model_importance_hint,
    prepare_feature_frame,
)
from .xai_utils import compute_shap_explanation


class ExplainModelGlobalTool(BaseTool):
    """Tool for explaining model predictions using SHAP feature importance."""

    def __init__(self):
        super().__init__()
        self.name = "explain_model_global"
        self.description = """SHAP global feature importance plot.
USE WHEN: User wants to understand which features drive model decisions overall."""
        self.input_schema = {
            "model_id": {
                "type": "string",
                "description": "ID of the trained model",
            },
            "n_features": {
                "type": "integer",
                "description": "Number of top features to show",
                "default": 10,
            },
        }
        self.output_schema = {
            "description": "ChartSpec with feature importance and NarrativeSpec with explanation",
        }

    async def execute(self, params: Dict[str, Any], session) -> Any:
        try:
            from ..core.tool_registry import ToolResult

            model_id = params.get("model_id")
            n_features = max(1, int(params.get("n_features", 10)))
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
            background = get_background_sample(X, artifact)
            sample = X if len(X) <= 200 else X.sample(n=200, random_state=42)

            method = "model_importance"
            importance_scores: Dict[str, float]
            try:
                shap_matrix, _, method, _ = compute_shap_explanation(model, background, sample)
                mean_abs_shap = np.abs(shap_matrix).mean(axis=0)
                importance_scores = {
                    str(column): float(score)
                    for column, score in sorted(
                        zip(sample.columns.tolist(), mean_abs_shap),
                        key=lambda item: item[1],
                        reverse=True,
                    )
                }
            except Exception:
                importance_scores = model_importance_hint(model, X.columns.tolist())

            if not importance_scores:
                return ToolResult(
                    success=False,
                    data={},
                    error_message="Could not compute global feature importance for this model.",
                    confidence=0.0,
                )

            sorted_features = list(importance_scores.items())[:n_features]
            features = [item[0] for item in sorted_features]
            scores = [item[1] for item in sorted_features]

            fig = go.Figure(
                data=[
                    go.Bar(
                        x=scores[::-1],
                        y=features[::-1],
                        orientation="h",
                        marker=dict(color="#0f766e"),
                    )
                ]
            )
            fig.update_layout(
                title="Global Feature Importance",
                xaxis_title="Importance score",
                yaxis_title="Feature",
                template="plotly_white",
                margin=dict(l=80, r=40, t=60, b=40),
            )

            chart_spec = self.create_chart_spec(
                chart_type="bar",
                data=fig.to_dict(),
                title="Global Feature Importance",
            )

            top_3 = features[:3]
            narrative = (
                f"Computed a real {method} explanation for model `{model_id}`. "
                f"The strongest global drivers are {', '.join(top_3)}."
            )
            if artifact.get("task_type") == "classification" and artifact.get("class_names"):
                narrative += f" The classifier predicts among: {', '.join(artifact['class_names'])}."

            narrative_spec = self.create_narrative_spec(narrative, "professional")

            result_data = {
                "model_id": model_id,
                "method": method,
                "feature_importance": dict(sorted_features),
                "top_features": top_3,
                "feature_count": len(X.columns),
                "samples_used": int(len(sample)),
            }

            return ToolResult(
                success=True,
                data=result_data,
                display=[chart_spec, narrative_spec],
            )

        except Exception as e:
            from ..core.tool_registry import ToolResult

            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0,
            )
