from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from .base_tool import BaseTool
from .model_artifact import (
    compute_feature_stats,
    compute_fill_values,
    save_model_artifact,
)


class TrainRegressorTool(BaseTool):
    """Tool for training a regression model using AutoML."""

    def __init__(self):
        super().__init__()
        self.name = "train_regressor"
        self.description = """Train best-fit regression model via AutoML.
USE WHEN: User wants to predict numeric values."""
        self.input_schema = {
            "target_col": {
                "type": "string",
                "description": "Target column to predict (numeric)",
            },
            "feature_cols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Feature columns to use",
            },
            "metric": {
                "type": "string",
                "enum": ["r2", "rmse", "mae"],
                "description": "Optimization metric",
                "default": "r2",
            },
        }
        self.output_schema = {
            "description": "ModelResult with trained model ID and metrics",
        }

    async def execute(self, params: Dict[str, Any], session) -> Any:
        try:
            from ..core.tool_registry import ToolResult

            df = self.load_dataset(session)
            target_col = params.get("target_col")
            feature_cols = list(params.get("feature_cols", []))
            metric = params.get("metric", "r2")

            if not target_col or target_col not in df.columns:
                return ToolResult(
                    success=False,
                    data={},
                    error_message=f"Target column '{target_col}' not found",
                    confidence=0.0,
                )

            if not pd.api.types.is_numeric_dtype(df[target_col]):
                return ToolResult(
                    success=False,
                    data={},
                    error_message=f"Target column '{target_col}' must be numeric for regression.",
                    confidence=0.0,
                )

            if not feature_cols:
                feature_cols = [
                    column
                    for column in df.columns
                    if column != target_col and (pd.api.types.is_numeric_dtype(df[column]) or pd.api.types.is_bool_dtype(df[column]))
                ]

            feature_cols = [column for column in feature_cols if column != target_col]
            self.validate_columns_exist(df, feature_cols)

            if not feature_cols:
                return ToolResult(
                    success=False,
                    data={},
                    error_message="No usable feature columns were provided for regression training.",
                    confidence=0.0,
                )

            unsupported = [
                column
                for column in feature_cols
                if not pd.api.types.is_numeric_dtype(df[column]) and not pd.api.types.is_bool_dtype(df[column])
            ]
            if unsupported:
                return ToolResult(
                    success=False,
                    data={},
                    error_message=f"Only numeric or boolean features are currently supported for regression: {unsupported}",
                    confidence=0.0,
                )

            X = df[feature_cols].copy()
            for column in X.columns:
                if pd.api.types.is_bool_dtype(X[column]):
                    X[column] = X[column].astype(int)

            fill_values = compute_fill_values(X)
            for column, fill_value in fill_values.items():
                X[column] = X[column].fillna(fill_value)

            y = df[target_col].fillna(df[target_col].median())

            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
            )

            models = {
                "random_forest": RandomForestRegressor(n_estimators=100, random_state=42),
                "gradient_boosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
                "linear_regression": LinearRegression(),
                "ridge_regression": Ridge(alpha=1.0),
            }

            best_model = None
            best_score = float("-inf") if metric == "r2" else float("inf")
            best_name = None
            results: Dict[str, Dict[str, float]] = {}

            for name, model in models.items():
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)

                r2 = r2_score(y_test, y_pred)
                rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
                mae = float(mean_absolute_error(y_test, y_pred))

                results[name] = {
                    "r2": float(r2),
                    "rmse": rmse,
                    "mae": mae,
                }

                if metric == "r2":
                    current_score = float(r2)
                    is_better = current_score > best_score
                elif metric == "rmse":
                    current_score = rmse
                    is_better = current_score < best_score
                else:
                    current_score = mae
                    is_better = current_score < best_score

                if is_better:
                    best_score = current_score
                    best_model = model
                    best_name = name

            model_id = f"regressor_{session.session_id}"
            artifact = {
                "version": 2,
                "model_id": model_id,
                "model": best_model,
                "task_type": "regression",
                "target_col": target_col,
                "feature_cols": feature_cols,
                "fill_values": fill_values,
                "feature_stats": compute_feature_stats(X),
                "background_sample": X_train.sample(min(len(X_train), 100), random_state=42),
                "label_encoder": None,
                "class_names": None,
                "best_model": best_name,
                "metric": metric,
                "metrics": results,
            }
            model_path = save_model_artifact(model_id, artifact)

            result_data = {
                "model_id": model_id,
                "model_path": str(model_path),
                "best_model": best_name,
                f"best_{metric}": float(best_score),
                "all_results": results,
                "features": feature_cols,
                "target": target_col,
            }

            narrative = (
                f"Trained a regression model using {best_name}. "
                f"Best {metric}: {best_score:.4f}. "
                f"Model artifact saved with {len(feature_cols)} feature columns for downstream XAI tools."
            )

            narrative_spec = self.create_narrative_spec(narrative, "professional")

            return ToolResult(
                success=True,
                data=result_data,
                display=narrative_spec,
            )

        except Exception as e:
            from ..core.tool_registry import ToolResult

            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0,
            )
