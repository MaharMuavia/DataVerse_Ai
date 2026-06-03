"""Deterministic full-dataset analysis pipeline for local/demo endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import uuid

import numpy as np
import pandas as pd

from ..core.logger import logger
from ..state.session_state import SessionState
from ..state.persistent_session_state import session_manager
from .data_profiler import profile_dataframe
from .report_narrator import ReportNarrator
from .target_inference import infer_target_column, suggest_targets

try:
    import shap

    SHAP_AVAILABLE = True
except Exception:  # pragma: no cover - environment-dependent
    shap = None
    SHAP_AVAILABLE = False

try:
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import train_test_split

    SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover - environment-dependent
    SKLEARN_AVAILABLE = False


@dataclass
class TrainedModel:
    model: Any
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_test: pd.Series
    feature_names: list[str]
    task_type: str
    target_column: str


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def persist_dataframe_for_session(session_id: str, df: pd.DataFrame, filename: str | None = None) -> Path:
    """Persist dataset locally and mirror it into in-memory session state."""
    persistent = session_manager.get_session(session_id)
    persistent.session_dir.mkdir(exist_ok=True, parents=True)
    dataset_path = persistent.dataset_path
    persistent._write_dataframe(df, dataset_path)
    persistent.set("raw_dataframe", df.copy())
    persistent.set("dataset_filename", filename or "uploaded_dataset")
    persistent.set("dataset_path", str(dataset_path))

    simple = SessionState.get(session_id)
    simple.set("raw_dataframe", df.copy())
    simple.set("dataset_filename", filename or "uploaded_dataset")
    simple.set("dataset_path", str(dataset_path))
    return dataset_path


class AnalysisPipeline:
    """Run profile, EDA, charts, target inference, AutoML, XAI, and narration."""

    def __init__(self, narrator: ReportNarrator | None = None):
        self.narrator = narrator or ReportNarrator()
        self.logger = logger.getChild(self.__class__.__name__)

    def run_full_analysis(
        self,
        df: pd.DataFrame,
        query: str | None = None,
        target_column: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        report = self._compute_report(df, query=query, target_column=target_column, session_id=session_id)
        narration = self.narrator.narrate(report)
        report.update(
            {
                "executive_summary": narration["executive_summary"],
                "recommendations": narration["recommendations"],
                "warnings": narration["warnings"],
                "narration": narration,
            }
        )
        return _json_safe(report)

    async def run_full_analysis_async(
        self,
        df: pd.DataFrame,
        query: str | None = None,
        target_column: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        report = self._compute_report(df, query=query, target_column=target_column, session_id=session_id)
        narration = await self.narrator.narrate_async(report)
        report.update(
            {
                "executive_summary": narration["executive_summary"],
                "recommendations": narration["recommendations"],
                "warnings": narration["warnings"],
                "narration": narration,
            }
        )
        return _json_safe(report)

    def _compute_report(
        self,
        df: pd.DataFrame,
        query: str | None,
        target_column: str | None,
        session_id: str | None,
    ) -> dict[str, Any]:
        warnings: list[str] = []
        df = df.copy()
        dataset_profile = profile_dataframe(df)
        eda = self._eda(df)
        trends = self._trends(df)
        correlations = self._correlations(df)
        outliers = self._outliers(df)
        charts = self._chart_specs(df, dataset_profile, trends, correlations)
        target_suggestions = suggest_targets(df)

        selected_target = infer_target_column(df, query=query, selected_target=target_column)
        automl: dict[str, Any] | None = None
        xai: dict[str, Any] | None = None
        trained: TrainedModel | None = None
        should_train = bool(selected_target and (target_column or self._query_requests_prediction(query) or selected_target["score"] >= 0.78))
        if should_train and selected_target:
            automl, trained = self._train_model(df, selected_target["column"], selected_target["task_type"])
        elif selected_target:
            automl = {
                "status": "skipped",
                "message": "Prediction target suggestions are available; select a target to train AutoML.",
                "target_column": selected_target["column"],
                "task_type": selected_target["task_type"],
            }
        else:
            automl = {
                "status": "skipped",
                "message": "No safe prediction target was found. Review target_suggestions or choose a target manually.",
            }

        if automl and automl.get("status") == "success" and trained is not None:
            xai = self._explain_model(trained, automl)
        else:
            xai = {"status": "skipped", "message": "XAI runs only after successful model training."}

        report = {
            "dataset_profile": dataset_profile,
            "column_roles": dataset_profile.get("column_roles", {}),
            "eda": eda,
            "trends": trends,
            "correlations": correlations,
            "outliers": outliers,
            "charts": charts,
            "target_suggestions": target_suggestions,
            "automl": automl,
            "xai": xai,
            "warnings": warnings,
            "session_id": session_id,
        }
        return report

    def _query_requests_prediction(self, query: str | None) -> bool:
        query_lower = (query or "").lower()
        return any(word in query_lower for word in ("predict", "forecast", "model", "classify", "regression"))

    def _eda(self, df: pd.DataFrame) -> dict[str, Any]:
        missing_columns = {
            str(column): {"count": int(count), "pct": round(float(count) / max(1, len(df)) * 100, 2)}
            for column, count in df.isna().sum().items()
        }
        numeric = df.select_dtypes(include=["number"])
        descriptive = numeric.describe().round(4).to_dict() if not numeric.empty else {}
        top_categories = {}
        for column in df.select_dtypes(include=["object", "category", "bool"]).columns:
            counts = df[column].astype(str).value_counts(dropna=True).head(10)
            top_categories[str(column)] = [{"value": str(idx), "count": int(value)} for idx, value in counts.items()]
        return {
            "missing_values": {
                "total_missing": int(df.isna().sum().sum()),
                "columns": missing_columns,
            },
            "duplicates": {
                "duplicate_rows": int(df.duplicated().sum()),
                "duplicate_pct": round(float(df.duplicated().sum()) / max(1, len(df)) * 100, 2),
            },
            "descriptive_statistics": descriptive,
            "top_categories": top_categories,
        }

    def _date_columns(self, df: pd.DataFrame) -> list[str]:
        date_columns = []
        for column in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[column]):
                date_columns.append(str(column))
                continue
            if pd.api.types.is_numeric_dtype(df[column]):
                continue
            sample = df[column].dropna().astype(str).head(20)
            if sample.empty or not sample.str.contains(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", regex=True).any():
                continue
            parsed = pd.to_datetime(df[column], errors="coerce")
            if parsed.notna().sum() >= max(3, int(len(df) * 0.5)):
                date_columns.append(str(column))
        return date_columns

    def _trends(self, df: pd.DataFrame) -> dict[str, Any]:
        date_columns = self._date_columns(df)
        numeric_columns = [str(col) for col in df.select_dtypes(include=["number"]).columns]
        series = []
        if not date_columns or not numeric_columns:
            return {"date_columns": date_columns, "series": series}
        date_column = date_columns[0]
        working = df.copy()
        working[date_column] = pd.to_datetime(working[date_column], errors="coerce")
        working = working.dropna(subset=[date_column]).sort_values(date_column)
        for value_column in numeric_columns[:3]:
            points = (
                working.groupby(working[date_column].dt.date)[value_column]
                .mean(numeric_only=True)
                .dropna()
                .tail(30)
            )
            values = [float(value) for value in points.values]
            slope = float(np.polyfit(range(len(values)), values, 1)[0]) if len(values) >= 2 else 0.0
            series.append(
                {
                    "date_column": date_column,
                    "value_column": value_column,
                    "direction": "up" if slope > 0 else "down" if slope < 0 else "flat",
                    "slope": round(slope, 6),
                    "points": [
                        {"date": str(idx), "value": round(float(value), 4)}
                        for idx, value in points.items()
                    ],
                }
            )
        return {"date_columns": date_columns, "series": series}

    def _correlations(self, df: pd.DataFrame) -> dict[str, Any]:
        numeric = df.select_dtypes(include=["number"])
        if numeric.shape[1] < 2:
            return {"matrix": {}, "strong_pairs": []}
        matrix = numeric.corr(numeric_only=True).round(4)
        pairs = []
        columns = list(matrix.columns)
        for idx, left in enumerate(columns):
            for right in columns[idx + 1 :]:
                value = matrix.loc[left, right]
                if pd.notna(value) and abs(float(value)) >= 0.65:
                    pairs.append({"columns": [str(left), str(right)], "correlation": round(float(value), 4)})
        pairs.sort(key=lambda item: abs(item["correlation"]), reverse=True)
        return {"matrix": matrix.to_dict(), "strong_pairs": pairs}

    def _outliers(self, df: pd.DataFrame) -> dict[str, Any]:
        columns = {}
        for column in df.select_dtypes(include=["number"]).columns:
            series = pd.to_numeric(df[column], errors="coerce").dropna()
            if series.empty:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            count = int(((series < lower) | (series > upper)).sum())
            columns[str(column)] = {"count": count, "lower_bound": float(lower), "upper_bound": float(upper)}
        return {"columns": columns, "total_outlier_cells": int(sum(item["count"] for item in columns.values()))}

    def _chart_specs(self, df: pd.DataFrame, profile: dict[str, Any], trends: dict[str, Any], correlations: dict[str, Any]) -> list[dict[str, Any]]:
        specs: list[dict[str, Any]] = []
        numeric_columns = profile.get("numeric_columns") or []
        text_columns = profile.get("text_columns") or []
        if numeric_columns:
            specs.append({"type": "histogram", "title": f"Distribution of {numeric_columns[0]}", "x": numeric_columns[0]})
        if text_columns:
            specs.append({"type": "bar", "title": f"Top {text_columns[0]}", "x": text_columns[0], "aggregation": "count"})
        if trends.get("series"):
            first = trends["series"][0]
            specs.append(
                {
                    "type": "line",
                    "title": f"{first['value_column']} over time",
                    "x": first["date_column"],
                    "y": first["value_column"],
                }
            )
        if correlations.get("matrix"):
            specs.append({"type": "heatmap", "title": "Numeric correlations", "matrix": "correlations.matrix"})
        return specs

    def _prepare_features(self, df: pd.DataFrame, target_column: str) -> tuple[pd.DataFrame, pd.Series]:
        working = df.dropna(subset=[target_column]).copy()
        y = working[target_column]
        X = working.drop(columns=[target_column]).copy()
        for column in X.columns:
            if pd.api.types.is_datetime64_any_dtype(X[column]):
                X[column] = pd.to_datetime(X[column], errors="coerce").astype("int64")
            elif not pd.api.types.is_numeric_dtype(X[column]):
                sample = X[column].dropna().astype(str).head(20)
                if sample.empty or not sample.str.contains(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", regex=True).any():
                    continue
                parsed = pd.to_datetime(X[column], errors="coerce")
                if parsed.notna().sum() >= max(3, int(len(X) * 0.5)):
                    X[column] = parsed.astype("int64")
        X = pd.get_dummies(X, dummy_na=True)
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(X.median(numeric_only=True)).fillna(0)
        return X, y

    def _train_model(self, df: pd.DataFrame, target_column: str, task_type: str) -> tuple[dict[str, Any], TrainedModel | None]:
        if not SKLEARN_AVAILABLE:
            return {"status": "failed", "message": "scikit-learn is not installed"}, None
        if target_column not in df.columns:
            return {"status": "failed", "message": f"Target column '{target_column}' was not found"}, None
        try:
            X, y = self._prepare_features(df, target_column)
            if len(X) < 10 or X.shape[1] == 0:
                return {"status": "failed", "message": "Not enough usable rows or features for AutoML"}, None
            stratify = y if task_type == "classification" and y.nunique(dropna=True) > 1 else None
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.25, random_state=42, stratify=stratify
                )
            except ValueError:
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
            if task_type == "classification":
                model = RandomForestClassifier(n_estimators=40, max_depth=8, random_state=42)
                model.fit(X_train, y_train.astype(str))
                predictions = model.predict(X_test)
                metrics = {
                    "accuracy": float(accuracy_score(y_test.astype(str), predictions)),
                    "f1_weighted": float(f1_score(y_test.astype(str), predictions, average="weighted", zero_division=0)),
                }
            else:
                y_numeric = pd.to_numeric(y, errors="coerce")
                valid_index = y_numeric.dropna().index
                X_valid = X.loc[valid_index]
                y_valid = y_numeric.loc[valid_index]
                X_train, X_test, y_train, y_test = train_test_split(X_valid, y_valid, test_size=0.25, random_state=42)
                model = RandomForestRegressor(n_estimators=40, max_depth=8, random_state=42)
                model.fit(X_train, y_train)
                predictions = model.predict(X_test)
                metrics = {
                    "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
                    "mae": float(mean_absolute_error(y_test, predictions)),
                    "r2": float(r2_score(y_test, predictions)) if len(y_test) > 1 else 0.0,
                }
            feature_importance = self._feature_importance(model, list(X_train.columns))
            result = {
                "status": "success",
                "target_column": target_column,
                "task_type": task_type,
                "best_model": type(model).__name__,
                "metrics": metrics,
                "feature_importance": feature_importance,
                "predictions_sample": [
                    {"predicted": _json_safe(value)}
                    for value in list(predictions[: min(8, len(predictions))])
                ],
            }
            trained = TrainedModel(model, X_train, X_test, y_test, list(X_train.columns), task_type, target_column)
            return result, trained
        except Exception as exc:
            self.logger.exception("AutoML training failed")
            return {"status": "failed", "message": str(exc), "target_column": target_column, "task_type": task_type}, None

    def _feature_importance(self, model: Any, feature_names: list[str]) -> dict[str, float]:
        if not hasattr(model, "feature_importances_"):
            return {}
        values = getattr(model, "feature_importances_")
        importance = {str(name): float(value) for name, value in zip(feature_names, values)}
        return dict(sorted(importance.items(), key=lambda item: item[1], reverse=True)[:10])

    def _explain_model(self, trained: TrainedModel, automl: dict[str, Any]) -> dict[str, Any]:
        fallback = {
            "status": "fallback",
            "method": "feature_importance",
            "feature_importance": automl.get("feature_importance", {}),
            "top_features": list((automl.get("feature_importance") or {}).keys())[:10],
        }
        if not SHAP_AVAILABLE or shap is None:
            return fallback
        try:
            sample = trained.X_test.head(50)
            explainer = shap.TreeExplainer(trained.model)
            shap_values = explainer.shap_values(sample)
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            values = np.asarray(shap_values)
            if values.ndim == 3:
                values = values[:, :, 0]
            mean_abs = np.abs(values).mean(axis=0)
            importance = {
                str(name): float(value)
                for name, value in zip(sample.columns, mean_abs)
            }
            importance = dict(sorted(importance.items(), key=lambda item: item[1], reverse=True)[:10])
            return {
                "status": "success",
                "method": "shap",
                "samples_used": int(len(sample)),
                "global_feature_importance": importance,
                "top_features": list(importance.keys())[:10],
            }
        except Exception as exc:
            fallback["message"] = f"SHAP failed, used model feature importance instead: {exc}"
            return fallback


def create_session_id() -> str:
    return str(uuid.uuid4())
