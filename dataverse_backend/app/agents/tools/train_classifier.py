from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
from pandas.api.types import CategoricalDtype
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from .base_tool import BaseTool
from .model_artifact import (
    compute_feature_stats,
    compute_fill_values,
    save_model_artifact,
)


class TrainClassifierTool(BaseTool):
    """Tool for training a classification model using AutoML."""

    def __init__(self):
        super().__init__()
        self.name = "train_classifier"
        self.description = """Train best-fit classification model via AutoML.
USE WHEN: User wants to predict categories or binary outcomes."""
        self.input_schema = {
            "target_col": {
                "type": "string",
                "description": "Target column to predict",
            },
            "feature_cols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Feature columns to use",
            },
            "metric": {
                "type": "string",
                "enum": ["accuracy", "f1", "precision", "recall"],
                "description": "Optimization metric",
                "default": "f1",
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
            metric = params.get("metric", "f1")

            if not target_col or target_col not in df.columns:
                return ToolResult(
                    success=False,
                    data={},
                    error_message=f"Target column '{target_col}' not found",
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
                    error_message="No usable feature columns were provided for classifier training.",
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
                    error_message=f"Only numeric or boolean features are currently supported for classification: {unsupported}",
                    confidence=0.0,
                )

            X = df[feature_cols].copy()
            for column in X.columns:
                if pd.api.types.is_bool_dtype(X[column]):
                    X[column] = X[column].astype(int)

            fill_values = compute_fill_values(X)
            for column, fill_value in fill_values.items():
                X[column] = X[column].fillna(fill_value)

            y = df[target_col].copy()
            label_encoder = None
            class_names = None
            if (
                pd.api.types.is_object_dtype(y)
                or isinstance(y.dtype, CategoricalDtype)
                or pd.api.types.is_bool_dtype(y)
            ):
                label_encoder = LabelEncoder()
                y = label_encoder.fit_transform(y)
                class_names = [str(item) for item in label_encoder.classes_]

            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
                stratify=y if len(pd.Series(y).unique()) > 1 else None,
            )

            models = {
                "random_forest": RandomForestClassifier(n_estimators=100, random_state=42),
                "gradient_boosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
                "logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
            }

            best_model = None
            best_score = -1.0
            best_name = None
            results: Dict[str, Dict[str, float]] = {}

            for name, model in models.items():
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)

                if metric == "accuracy":
                    score = accuracy_score(y_test, y_pred)
                elif metric == "f1":
                    score = f1_score(y_test, y_pred, average="weighted", zero_division=0)
                elif metric == "precision":
                    score = precision_score(y_test, y_pred, average="weighted", zero_division=0)
                elif metric == "recall":
                    score = recall_score(y_test, y_pred, average="weighted", zero_division=0)
                else:
                    score = accuracy_score(y_test, y_pred)

                results[name] = {
                    "accuracy": float(accuracy_score(y_test, y_pred)),
                    "f1": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
                    "precision": float(precision_score(y_test, y_pred, average="weighted", zero_division=0)),
                    "recall": float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
                }

                if score > best_score:
                    best_score = float(score)
                    best_model = model
                    best_name = name

            model_id = f"classifier_{session.session_id}"
            artifact = {
                "version": 2,
                "model_id": model_id,
                "model": best_model,
                "task_type": "classification",
                "target_col": target_col,
                "feature_cols": feature_cols,
                "fill_values": fill_values,
                "feature_stats": compute_feature_stats(X),
                "background_sample": X_train.sample(min(len(X_train), 100), random_state=42),
                "label_encoder": label_encoder,
                "class_names": class_names,
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
                "class_names": class_names,
            }

            narrative = (
                f"Trained a classification model using {best_name}. "
                f"Best {metric}: {best_score:.3f}. "
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
