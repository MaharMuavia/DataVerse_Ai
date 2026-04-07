"""Explainable AI agent using SHAP for model interpretability.

This agent computes feature importance and SHAP explanations to understand:
- Which features drive model predictions
- How individual features impact the outcome
- Global vs local explanations

Uses SHAP TreeExplainer for tree-based models and KernelExplainer for others.
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

try:
    import shap
except ImportError:
    shap = None

from ..core.logger import logger
from ..data.data_manager import DataManager


class XAIAgent:
    """Explainable AI using SHAP values.

    This agent computes SHAP (SHapley Additive exPlanations) values to provide
    interpretability for ML models. SHAP values quantify the contribution of
    each feature to model predictions.

    Supports:
    - Global explanations (feature importance across all predictions)
    - Local explanations (individual prediction explanations)
    - Different explainers (TreeExplainer, KernelExplainer, LinearExplainer)
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = logger.getChild(self.__class__.__name__)

    def run(self, model, X_data: pd.DataFrame, y_true: Optional[pd.Series] = None, sample_size: int = 100) -> Dict[str, Any]:
        """Compute SHAP explanations for a trained model.

        Args:
            model: Trained ML model
            X_data: Feature data
            y_true: True labels (optional, for accuracy context)
            sample_size: Number of samples to use for explanation (computational efficiency)

        Returns:
            Dict containing:
            - global_importance: Feature importance scores
            - feature_impacts: How features affect predictions
            - sample_explanations: Per-sample explanation
            - summary_plots_data: Data for visualization
        """
        if shap is None:
            return {"error": "SHAP module not available", "status": "failed"}

        # Apply sampling cap for performance
        MAX_SHAP_SAMPLES = 200
        X_sample = self._get_shap_sample(X_data, MAX_SHAP_SAMPLES)

        self.logger.info("Computing SHAP explanations", extra={"session_id": self.session_id, "samples": len(X_sample)})

        try:
            # Create SHAP explainer
            explainer = self._create_explainer(model, X_sample)
            if explainer is None:
                return {"error": "Could not create SHAP explainer", "status": "failed"}

            # Compute SHAP values
            shap_values = explainer.shap_values(X_sample)

            # Handle different SHAP value formats
            if isinstance(shap_values, list):
                # Multi-class case: use first class
                shap_values = shap_values[0]

            # Compute global feature importance
            global_importance = self._compute_global_importance(shap_values, X_sample.columns)

            # Compute feature impacts
            feature_impacts = self._compute_feature_impacts(shap_values, X_sample)

            # Sample explanations
            sample_explanations = self._generate_sample_explanations(shap_values, X_sample, global_importance)

            result = {
                "session_id": self.session_id,
                "explainer_type": type(explainer).__name__,
                "samples_used": len(X_sample),
                "global_feature_importance": global_importance,
                "feature_impacts": feature_impacts,
                "top_features": list(global_importance.keys())[:10],
                "sample_explanations": sample_explanations[:5],  # Top 5 samples
                "status": "success",
            }

            self.logger.info("SHAP explanations computed", extra={"session_id": self.session_id, "features": len(global_importance)})
            return result

        except Exception as e:
            self.logger.exception(f"SHAP explanation failed: {e}")
            return {"error": str(e), "status": "failed"}

    def _get_shap_sample(self, X_data: pd.DataFrame, max_samples: int = 200) -> pd.DataFrame:
        """Get sample of data for SHAP computation to avoid timeouts on large datasets."""
        if len(X_data) > max_samples:
            return X_data.sample(n=max_samples, random_state=42)
        return X_data

    def _create_explainer(self, model, X_data: pd.DataFrame):
        """Create appropriate SHAP explainer for the model.

        Tries:
        1. TreeExplainer (for tree-based models)
        2. KernelExplainer (for any model)
        """
        try:
            # Try TreeExplainer (fast, for tree-based models)
            explainer = shap.TreeExplainer(model)
            self.logger.info("Using TreeExplainer")
            return explainer
        except Exception:
            try:
                # Fallback to KernelExplainer
                explainer = shap.KernelExplainer(model.predict, X_data.iloc[:min(50, len(X_data))])
                self.logger.info("Using KernelExplainer")
                return explainer
            except Exception as e:
                self.logger.warning(f"Could not create any SHAP explainer: {e}")
                return None

    def _compute_global_importance(self, shap_values: np.ndarray, feature_names: pd.Index) -> Dict[str, float]:
        """Compute global feature importance from SHAP values.

        Feature importance = mean(|SHAP value|) for each feature
        """
        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        mean_abs_shap = np.abs(shap_values).mean(axis=0)

        # Create importance dict
        importance_dict = {str(name): float(val) for name, val in zip(feature_names, mean_abs_shap)}

        # Sort by importance
        sorted_importance = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

        return sorted_importance

    def _compute_feature_impacts(self, shap_values: np.ndarray, X_data: pd.DataFrame) -> Dict[str, Any]:
        """Compute how each feature impacts predictions.

        For each feature: mean value, direction of impact, range of impacts.
        """
        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        impacts = {}

        for i, col in enumerate(X_data.columns):
            feature_shap = shap_values[:, i]
            impacts[str(col)] = {
                "mean_impact": float(np.mean(feature_shap)),
                "std_impact": float(np.std(feature_shap)),
                "min_impact": float(np.min(feature_shap)),
                "max_impact": float(np.max(feature_shap)),
                "direction": "positive" if np.mean(feature_shap) > 0 else "negative",
            }

        return impacts

    def _generate_sample_explanations(self, shap_values: np.ndarray, X_data: pd.DataFrame, importance: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate per-sample explanations."""
        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        explanations = []

        # Explain first few samples
        for idx in range(min(5, len(X_data))):
            sample_shaps = shap_values[idx, :]
            sample_features = X_data.iloc[idx]

            # Get top contributing features for this sample
            feature_contributions = []
            for i, col in enumerate(X_data.columns):
                feature_contributions.append({
                    "feature": str(col),
                    "value": float(sample_features.iloc[i]) if isinstance(sample_features.iloc[i], (int, float)) else str(sample_features.iloc[i]),
                    "shap_value": float(sample_shaps[i]),
                })

            # Sort by absolute SHAP value
            feature_contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

            explanations.append({
                "sample_index": int(idx),
                "top_features": feature_contributions[:5],
                "total_shap_impact": float(np.sum(np.abs(sample_shaps))),
            })

        return explanations


class LIMEAgent:
    """LIME (Local Interpretable Model-agnostic Explanations) agent.

    Optional alternative/complement to SHAP for local explanations.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = logger.getChild(self.__class__.__name__)

    def run(self, model, X_data: pd.DataFrame, num_features: int = 10) -> Dict[str, Any]:
        """Compute LIME explanations for model predictions.

        Args:
            model: Trained ML model with predict or predict_proba method
            X_data: Feature data
            num_features: Number of features to explain per instance

        Returns:
            Dict with LIME explanations
        """
        try:
            from lime import lime_tabular
        except ImportError:
            return {"error": "LIME module not available", "status": "failed"}

        try:
            explainer = lime_tabular.LimeTabularExplainer(
                X_data.values,
                feature_names=X_data.columns.tolist(),
                verbose=False,
                mode='classification' if hasattr(model, 'predict_proba') else 'regression'
            )

            # Explain first few samples
            explanations = []
            for idx in range(min(5, len(X_data))):
                exp = explainer.explain_instance(
                    X_data.iloc[idx].values,
                    model.predict_proba if hasattr(model, 'predict_proba') else model.predict,
                    num_features=num_features
                )

                # Extract feature weights
                feature_weights = {feat: weight for feat, weight in exp.as_list()}

                explanations.append({
                    "sample_index": int(idx),
                    "feature_weights": feature_weights,
                })

            result = {
                "session_id": self.session_id,
                "method": "lime",
                "explanations": explanations,
                "status": "success",
            }

            self.logger.info("LIME explanations computed", extra={"session_id": self.session_id})
            return result

        except Exception as e:
            self.logger.exception(f"LIME explanation failed: {e}")
            return {"error": str(e), "status": "failed"}
