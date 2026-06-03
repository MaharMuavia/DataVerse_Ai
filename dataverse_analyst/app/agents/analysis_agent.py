from __future__ import annotations

import json
from typing import Any

import numpy as np
import openai
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from app.core.config import settings


HINT_NAMES = ["target", "label", "outcome", "sales", "price", "revenue", "score", "result", "y"]


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


class AnalysisAgent:
    def run(self, df: pd.DataFrame, target_column: str | None = None) -> dict[str, Any]:
        eda = self.run_eda(df)
        trends = self.detect_trends(df)
        model_result = self.train_automl(df, target_column)
        public_model = self.public_model_result(model_result)

        lime = (
            self.explain_lime(model_result["model"], model_result["X_train"], model_result["X_test"])
            if model_result.get("status") == "success"
            else {"status": "skipped", "error": "Model training did not complete", "explanations": []}
        )

        return {
            "eda": eda,
            "trends": trends,
            "model_result": model_result,
            "public_model": public_model,
            "lime": lime,
        }

    def public_model_result(self, model_result: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in model_result.items()
            if key not in {"model", "X_train", "X_test", "y_test", "label_encoder"}
        }

    def run_eda(self, df: pd.DataFrame) -> dict[str, Any]:
        try:
            roles = self.classify_columns(df)
            numeric = df.select_dtypes(include=["number"])
            missing = {
                str(column): {
                    "count": int(count),
                    "pct": round(float(count) / max(1, len(df)) * 100, 2),
                }
                for column, count in df.isna().sum().items()
            }
            outliers: dict[str, dict[str, float | int]] = {}
            skewness: dict[str, float | None] = {}
            for column in numeric.columns:
                series = pd.to_numeric(df[column], errors="coerce").dropna()
                if series.empty:
                    continue
                q1 = series.quantile(0.25)
                q3 = series.quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                outliers[str(column)] = {
                    "count": int(((series < lower) | (series > upper)).sum()),
                    "lower_bound": float(lower),
                    "upper_bound": float(upper),
                }
                skewness[str(column)] = float(series.skew()) if len(series) > 2 else None

            correlations = numeric.corr(numeric_only=True).round(4).to_dict() if numeric.shape[1] >= 2 else {}
            dtypes = [{"column": str(column), "dtype": str(dtype)} for column, dtype in df.dtypes.items()]
            return json_safe(
                {
                    "status": "success",
                    "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
                    "column_types": roles,
                    "dtypes": dtypes,
                    "missing": missing,
                    "duplicates": {"rows": int(df.duplicated().sum())},
                    "outliers": outliers,
                    "skewness": skewness,
                    "correlations": correlations,
                    "describe": numeric.describe().round(4).to_dict() if not numeric.empty else {},
                }
            )
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def detect_target(self, df: pd.DataFrame) -> str:
        for column in df.columns:
            if str(column).lower() in HINT_NAMES:
                return str(column)
        numeric_columns = df.select_dtypes(include="number").columns.tolist()
        if not numeric_columns:
            raise ValueError("No numeric columns found for prediction")
        return str(df[numeric_columns].var(numeric_only=True).idxmax())

    def train_automl(self, df: pd.DataFrame, target: str | None = None) -> dict[str, Any]:
        try:
            target_column = target or self.detect_target(df)
            task_type = self._task_type(df[target_column])
            X, y, encoder = self._prepare_xy(df, target_column, task_type)
            if len(X) < 8 or X.shape[1] == 0:
                return {
                    "status": "error",
                    "error": "Not enough usable rows or features for model training",
                    "target_column": target_column,
                    "task_type": task_type,
                }

            stratify = y if task_type == "classification" and y.nunique() > 1 else None
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.25, random_state=42, stratify=stratify
                )
            except ValueError:
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

            use_flaml = len(X_train) >= 30
            engine = "FLAML" if use_flaml else "sklearn_fallback"
            try:
                if not use_flaml:
                    raise ValueError("Training set is small; using sklearn fallback for a stable quick model")
                from flaml import AutoML

                model = AutoML()
                model.fit(
                    X_train=X_train,
                    y_train=y_train,
                    task=task_type,
                    time_budget=settings.automl_time_budget,
                    verbose=0,
                )
                predictions = model.predict(X_test)
                if predictions is None:
                    raise ValueError("FLAML did not produce predictions")
                model_name = str(model.best_estimator)
            except Exception as exc:
                engine = "sklearn_fallback"
                if task_type == "classification":
                    model = RandomForestClassifier(n_estimators=80, random_state=42, max_depth=8)
                else:
                    model = RandomForestRegressor(n_estimators=80, random_state=42, max_depth=8)
                model.fit(X_train, y_train)
                predictions = model.predict(X_test)
                model_name = type(model).__name__
                fallback_error = str(exc)
            else:
                fallback_error = None

            if task_type == "classification":
                metrics = {
                    "accuracy": float(accuracy_score(y_test, predictions)),
                    "f1": float(f1_score(y_test, predictions, average="weighted", zero_division=0)),
                }
            else:
                metrics = {
                    "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
                    "mae": float(mean_absolute_error(y_test, predictions)),
                    "r2": float(r2_score(y_test, predictions)) if len(y_test) > 1 else 0.0,
                }

            feature_importance = self._feature_importance(model, X_train.columns.tolist())
            return json_safe(
                {
                    "status": "success",
                    "target_column": target_column,
                    "task_type": task_type,
                    "engine": engine,
                    "model_type": model_name,
                    "metrics": metrics,
                    "feature_importance": feature_importance,
                    "predictions": {
                        "sample": predictions[:10].tolist() if hasattr(predictions, "tolist") else list(predictions[:10]),
                        "min": float(np.min(predictions)) if task_type == "regression" else None,
                        "median": float(np.median(predictions)) if task_type == "regression" else None,
                        "max": float(np.max(predictions)) if task_type == "regression" else None,
                    },
                    "model": model,
                    "X_train": X_train,
                    "X_test": X_test,
                    "y_test": y_test,
                    "label_encoder": encoder,
                    "warning": (
                        f"FLAML unavailable or failed, used sklearn fallback: {fallback_error}"
                        if fallback_error
                        else None
                    ),
                }
            )
        except Exception as exc:
            return {"status": "error", "error": str(exc), "target_column": target}

    def detect_trends(self, df: pd.DataFrame) -> dict[str, Any]:
        try:
            date_columns = self.detect_datetime_columns(df)
            numeric_columns = [str(col) for col in df.select_dtypes(include=["number"]).columns]
            time_series: list[dict[str, Any]] = []
            if date_columns and numeric_columns:
                date_column = date_columns[0]
                working = df.copy()
                working[date_column] = pd.to_datetime(working[date_column], errors="coerce")
                working = working.dropna(subset=[date_column]).sort_values(date_column)
                for value_column in numeric_columns[:5]:
                    grouped = working.groupby(working[date_column].dt.date)[value_column].mean(numeric_only=True).dropna()
                    values = [float(value) for value in grouped.values]
                    trend_result = self._mann_kendall(values)
                    time_series.append(
                        {
                            "date_column": date_column,
                            "value_column": value_column,
                            "trend": trend_result["trend"],
                            "p_value": trend_result["p_value"],
                            "slope": trend_result["slope"],
                            "seasonality_flag": len(values) >= 14 and np.std(values) > 0,
                            "points": [
                                {"date": str(idx), "value": round(float(value), 4)}
                                for idx, value in grouped.tail(100).items()
                            ],
                        }
                    )

            categorical_tests: list[dict[str, Any]] = []
            categorical_columns = [
                str(col)
                for col in df.columns
                if not pd.api.types.is_numeric_dtype(df[col]) and df[col].nunique(dropna=True) <= 20
            ]
            for left, right in zip(categorical_columns, categorical_columns[1:]):
                table = pd.crosstab(df[left], df[right])
                if table.shape[0] >= 2 and table.shape[1] >= 2:
                    chi2, p_value, _, _ = chi2_contingency(table)
                    categorical_tests.append(
                        {"columns": [left, right], "chi_square": float(chi2), "p_value": float(p_value)}
                    )

            return json_safe(
                {
                    "status": "success",
                    "datetime_columns": date_columns,
                    "time_series": time_series,
                    "categorical_tests": categorical_tests,
                }
            )
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def explain_lime(self, model: Any, X_train: pd.DataFrame, X_sample: pd.DataFrame) -> dict[str, Any]:
        if model is None:
            return {"status": "error", "error": "No trained model available for LIME", "explanations": []}
        try:
            from lime.lime_tabular import LimeTabularExplainer

            mode = "classification" if hasattr(model, "predict_proba") else "regression"
            explainer = LimeTabularExplainer(
                training_data=np.asarray(X_train),
                feature_names=X_train.columns.tolist(),
                mode=mode,
                discretize_continuous=True,
            )

            def as_frame(values: np.ndarray) -> pd.DataFrame:
                return pd.DataFrame(values, columns=X_train.columns)

            predict_fn = (
                (lambda values: model.predict_proba(as_frame(values)))
                if mode == "classification"
                else (lambda values: model.predict(as_frame(values)))
            )
            explanations = []
            for idx, (_, row) in enumerate(X_sample.head(3).iterrows(), start=1):
                exp = explainer.explain_instance(np.asarray(row), predict_fn, num_features=min(8, X_train.shape[1]))
                explanations.append(
                    {"sample": idx, "features": [{"rule": rule, "weight": weight} for rule, weight in exp.as_list()]}
                )
            return json_safe({"status": "success", "explanations": explanations})
        except Exception as exc:
            return {"status": "error", "error": str(exc), "explanations": []}

    def generate_narrative(
        self,
        eda_summary: dict[str, Any],
        shap_importances: dict[str, Any],
        predictions: dict[str, Any],
    ) -> str:
        if not settings.openai_api_key:
            return self._fallback_narrative(eda_summary, shap_importances, predictions)

        try:
            client = openai.OpenAI(api_key=settings.openai_api_key, timeout=20.0)
            prompt = f"""
You are an expert data analyst. Given this dataset analysis:

EDA: {json.dumps(eda_summary, indent=2)}
Feature importances: {json.dumps(shap_importances, indent=2)}
Model predictions summary: {json.dumps(predictions, indent=2)}

Write a professional data analysis report with:
1. Executive Summary (2-3 sentences)
2. Key Findings (5 bullet points with specific numbers)
3. Anomalies & Risks detected
4. 3 Predictions with confidence percentages
5. Actionable Recommendations

Be specific, use the actual numbers from the data. Do not be generic.
"""
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            fallback = self._fallback_narrative(eda_summary, shap_importances, predictions)
            return f"{fallback}\n\n> GPT narrative unavailable: {exc}"

    def detect_datetime_columns(self, df: pd.DataFrame) -> list[str]:
        columns: list[str] = []
        for column in df.columns:
            series = df[column]
            if pd.api.types.is_datetime64_any_dtype(series):
                columns.append(str(column))
                continue
            if pd.api.types.is_numeric_dtype(series):
                continue
            parsed = pd.to_datetime(series, errors="coerce")
            if parsed.notna().sum() >= max(3, int(len(series) * 0.5)):
                columns.append(str(column))
        return columns

    def classify_columns(self, df: pd.DataFrame) -> dict[str, list[str]]:
        datetime_columns = set(self.detect_datetime_columns(df))
        numeric = [str(col) for col in df.select_dtypes(include=["number"]).columns]
        categorical: list[str] = []
        text: list[str] = []
        for column in df.columns:
            name = str(column)
            if name in datetime_columns or name in numeric:
                continue
            unique_ratio = df[column].nunique(dropna=True) / max(1, df[column].notna().sum())
            if unique_ratio <= 0.35 or df[column].nunique(dropna=True) <= 20:
                categorical.append(name)
            else:
                text.append(name)
        return {
            "numeric": numeric,
            "categorical": categorical,
            "datetime": sorted(datetime_columns),
            "text": text,
        }

    def _fallback_narrative(
        self,
        eda_summary: dict[str, Any],
        shap_importances: dict[str, Any],
        predictions: dict[str, Any],
    ) -> str:
        shape = eda_summary.get("shape", {})
        top_features = list((shap_importances or {}).keys())[:5]
        metric_bits = ", ".join(f"{key}: {value}" for key, value in (predictions.get("metrics") or {}).items())
        return (
            "## Executive Summary\n"
            f"The dataset contains {shape.get('rows', 'unknown')} rows and {shape.get('columns', 'unknown')} columns. "
            "The automated pipeline completed deterministic profiling and model analysis, but GPT narration was not available.\n\n"
            "## Key Findings\n"
            f"- Top model drivers: {', '.join(top_features) if top_features else 'not available'}.\n"
            f"- Model metrics: {metric_bits or 'not available'}.\n"
            f"- Missing cells detected: {eda_summary.get('missing', {})}.\n\n"
            "## Recommendations\n"
            "- Review high-missing columns before operational decisions.\n"
            "- Validate the auto-selected target with domain knowledge.\n"
            "- Re-run with a larger time budget if model accuracy is business-critical."
        )

    def _task_type(self, series: pd.Series) -> str:
        clean = series.dropna()
        if pd.api.types.is_numeric_dtype(clean) and clean.nunique(dropna=True) > max(10, int(len(clean) * 0.08)):
            return "regression"
        return "classification"

    def _prepare_xy(
        self,
        df: pd.DataFrame,
        target: str,
        task_type: str,
    ) -> tuple[pd.DataFrame, pd.Series, LabelEncoder | None]:
        working = df.dropna(subset=[target]).copy()
        y = working[target]
        X = working.drop(columns=[target]).copy()
        for column in X.columns:
            if pd.api.types.is_datetime64_any_dtype(X[column]):
                X[column] = pd.to_datetime(X[column], errors="coerce").astype("int64")
            elif not pd.api.types.is_numeric_dtype(X[column]):
                parsed = pd.to_datetime(X[column], errors="coerce")
                if parsed.notna().sum() >= max(3, int(len(X) * 0.5)):
                    X[column] = parsed.astype("int64")
        X = pd.get_dummies(X, dummy_na=True)
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(X.median(numeric_only=True)).fillna(0)
        encoder: LabelEncoder | None = None
        if task_type == "classification":
            encoder = LabelEncoder()
            y = pd.Series(encoder.fit_transform(y.astype(str)), index=y.index, name=target)
        else:
            y = pd.to_numeric(y, errors="coerce")
            valid = y.dropna().index
            X = X.loc[valid]
            y = y.loc[valid]
        return X, y, encoder

    def _feature_importance(self, model: Any, columns: list[str]) -> dict[str, float]:
        estimator = getattr(model, "model", None) or getattr(model, "estimator", None) or model
        values = getattr(estimator, "feature_importances_", None)
        if values is None and hasattr(model, "feature_importances_"):
            values = model.feature_importances_
        if values is None:
            return {}
        pairs = {str(column): float(value) for column, value in zip(columns, values)}
        return dict(sorted(pairs.items(), key=lambda item: item[1], reverse=True)[:20])

    def _mann_kendall(self, values: list[float]) -> dict[str, Any]:
        if len(values) < 4:
            return {"trend": "insufficient_data", "p_value": None, "slope": 0.0}
        try:
            import pymannkendall as mk

            result = mk.original_test(values)
            return {
                "trend": str(result.trend),
                "p_value": float(result.p),
                "slope": float(result.slope),
            }
        except Exception:
            slope = float(np.polyfit(range(len(values)), values, 1)[0])
            return {
                "trend": "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat",
                "p_value": None,
                "slope": slope,
            }
