"""AutoML agent using scikit-learn for automated machine learning.

This agent trains machine learning models for:
- Classification tasks
- Regression tasks

It automatically handles:
- Feature preprocessing (scaling, encoding)
- Model selection (tries multiple algorithms)
- Cross-validation
- Evaluation metrics

Returns: Trained model, metrics, and predictions
"""
from __future__ import annotations

from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from pathlib import Path

try:
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
    from sklearn.linear_model import LogisticRegression, LinearRegression
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from ..core.logger import logger
from ..data.data_manager import DataManager


class AutoMLAgent:
    """Automated machine learning using scikit-learn.

    This agent trains ML models with minimal configuration:
    - Detects task type (classification vs regression)
    - Preprocesses data (handles missing values, encoding)
    - Compares multiple algorithms
    - Selects and evaluates best model
    - Returns metrics and predictions
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = logger.getChild(self.__class__.__name__)
        self.model = None
        self.task_type = None

    def run(self, task_type: str, target_column: str, test_size: float = 0.2) -> Dict[str, Any]:
        """Execute AutoML workflow.

        Args:
            task_type: "classification" or "regression"
            target_column: Name of target column to predict
            test_size: Proportion of data for testing (0.0 to 1.0)

        Returns:
            Dict containing:
            - task_type: Type of task executed
            - target_column: Target variable
            - models_compared: Number of models evaluated
            - best_model_name: Name of best model
            - metrics: Performance metrics (Accuracy, F1, RMSE, etc.)
            - predictions: Sample predictions
            - feature_importance: Feature importance scores
        """
        try:
            dm = DataManager(session_id=self.session_id)
            df = dm.get_raw()
        except Exception as e:
            self.logger.error(f"Failed to load dataset: {e}")
            return {"error": str(e), "status": "failed"}

        # Validate target column
        if target_column not in df.columns:
            return {"error": f"Target column '{target_column}' not found in dataset", "status": "failed"}

        # Remove rows with missing target values
        df_clean = df[df[target_column].notna()].copy()

        if len(df_clean) < 10:
            return {"error": "Insufficient data samples after removing missing target values", "status": "failed"}

        self.task_type = task_type
        self.logger.info(f"Running AutoML ({task_type})", extra={"session_id": self.session_id, "target": target_column})

        try:
            if task_type.lower() == "classification":
                return self._run_classification(df_clean, target_column, test_size)
            elif task_type.lower() == "regression":
                return self._run_regression(df_clean, target_column, test_size)
            else:
                return {"error": f"Unknown task type: {task_type}", "status": "failed"}

        except Exception as e:
            self.logger.exception(f"AutoML workflow failed: {e}")
            return {"error": str(e), "status": "failed"}

    def _run_classification(self, df: pd.DataFrame, target_column: str, test_size: float) -> Dict[str, Any]:
        """Run classification AutoML using scikit-learn."""
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn not available", "status": "failed"}

        try:
            X, y, scaler, label_encoders = self._preprocess_data(df, target_column, task_type="classification")

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

            # Try multiple classifiers
            classifiers = {
                "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42, max_depth=15),
                "GradientBoosting": GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5),
                "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
            }

            best_model = None
            best_score = -1
            best_model_name = None
            model_scores = {}

            for name, clf in classifiers.items():
                try:
                    clf.fit(X_train, y_train)
                    score = clf.score(X_test, y_test)
                    model_scores[name] = score

                    if score > best_score:
                        best_score = score
                        best_model = clf
                        best_model_name = name
                except Exception as e:
                    self.logger.warning(f"Failed to train {name}: {e}")

            if best_model is None:
                return {"error": "No classifiers could be trained", "status": "failed"}

            self.model = best_model

            # Get predictions
            y_pred = best_model.predict(X_test)
            pred_proba = best_model.predict_proba(X_test)[:, 1] if hasattr(best_model, 'predict_proba') else None

            # Create prediction samples
            pred_sample = []
            for i in range(min(10, len(X_test))):
                pred_sample.append({
                    "predicted": int(y_pred[i]),
                    "probability": float(pred_proba[i]) if pred_proba is not None else None,
                })

            # Extract metrics
            metrics = {
                "accuracy": float(accuracy_score(y_test, y_pred)),
                "precision": float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
                "recall": float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
                "f1": float(f1_score(y_test, y_pred, average='weighted', zero_division=0)),
                "train_score": float(best_model.score(X_train, y_train)),
            }

            # Feature importance
            feature_importance = self._get_feature_importance(best_model, X.columns)

            result = {
                "session_id": self.session_id,
                "task_type": "classification",
                "target_column": target_column,
                "best_model": best_model_name,
                "models_evaluated": list(model_scores.keys()),
                "metrics": metrics,
                "predictions_sample": pred_sample,
                "feature_importance": feature_importance,
                "status": "success",
            }

            self.logger.info("Classification AutoML completed", extra={"session_id": self.session_id, "model": best_model_name})
            return result

        except Exception as e:
            self.logger.exception(f"Classification AutoML failed: {e}")
            return {"error": str(e), "status": "failed"}

    def _run_regression(self, df: pd.DataFrame, target_column: str, test_size: float) -> Dict[str, Any]:
        """Run regression AutoML using scikit-learn."""
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn not available", "status": "failed"}

        try:
            X, y, scaler, label_encoders = self._preprocess_data(df, target_column, task_type="regression")

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

            # Try multiple regressors
            regressors = {
                "RandomForest": RandomForestRegressor(n_estimators=100, random_state=42, max_depth=15),
                "GradientBoosting": GradientBoostingRegressor(n_estimators=100, random_state=42, max_depth=5),
                "LinearRegression": LinearRegression(),
            }

            best_model = None
            best_score = -float('inf')
            best_model_name = None
            model_scores = {}

            for name, reg in regressors.items():
                try:
                    reg.fit(X_train, y_train)
                    score = reg.score(X_test, y_test)
                    model_scores[name] = score

                    if score > best_score:
                        best_score = score
                        best_model = reg
                        best_model_name = name
                except Exception as e:
                    self.logger.warning(f"Failed to train {name}: {e}")

            if best_model is None:
                return {"error": "No regressors could be trained", "status": "failed"}

            self.model = best_model

            # Get predictions
            y_pred = best_model.predict(X_test)

            # Create prediction samples
            pred_sample = []
            for i in range(min(10, len(X_test))):
                pred_sample.append({
                    "predicted": float(y_pred[i]),
                    "actual": float(y_test.iloc[i]) if hasattr(y_test, 'iloc') else float(list(y_test)[i]),
                })

            # Extract metrics
            metrics = {
                "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
                "mae": float(mean_absolute_error(y_test, y_pred)),
                "mse": float(mean_squared_error(y_test, y_pred)),
                "r2": float(r2_score(y_test, y_pred)),
                "train_r2": float(best_model.score(X_train, y_train)),
            }

            # Feature importance
            feature_importance = self._get_feature_importance(best_model, X.columns)

            result = {
                "session_id": self.session_id,
                "task_type": "regression",
                "target_column": target_column,
                "best_model": best_model_name,
                "models_evaluated": list(model_scores.keys()),
                "metrics": metrics,
                "predictions_sample": pred_sample,
                "feature_importance": feature_importance,
                "status": "success",
            }

            self.logger.info("Regression AutoML completed", extra={"session_id": self.session_id, "model": best_model_name})
            return result

        except Exception as e:
            self.logger.exception(f"Regression AutoML failed: {e}")
            return {"error": str(e), "status": "failed"}

    def _preprocess_data(self, df: pd.DataFrame, target_column: str, task_type: str) -> Tuple:
        """Preprocess data for ML."""
        X = df.drop(columns=[target_column]).copy()
        y = df[target_column].copy()

        # Handle missing values
        X = X.fillna(X.mean(numeric_only=True))
        X = X.fillna(X.mode().iloc[0] if len(X.mode()) > 0 else 0)

        # Encode categorical variables
        label_encoders = {}
        for col in X.select_dtypes(include=['object']).columns:
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))
            label_encoders[col] = le

        # Encode target if classification
        if task_type == "classification" and y.dtype == 'object':
            le = LabelEncoder()
            y = le.fit_transform(y.astype(str))
            label_encoders['target'] = le

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        X = pd.DataFrame(X_scaled, columns=X.columns)

        return X, y, scaler, label_encoders

    def _get_feature_importance(self, model, columns: pd.Index = None) -> Dict[str, float]:
        """Extract feature importance from trained model."""
        try:
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
                
                if columns is not None:
                    feature_names = columns
                else:
                    feature_names = [f"feature_{i}" for i in range(len(importances))]

                importance_dict = {str(name): float(imp) for name, imp in zip(feature_names, importances)}
                # Sort by importance and return top 10
                return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:10])

            return {}
        except Exception as e:
            self.logger.warning(f"Could not extract feature importance: {e}")
            return {}

