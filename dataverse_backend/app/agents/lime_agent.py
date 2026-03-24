"""LIME Agent for Local Interpretable Model-agnostic Explanations.

Provides local explanations of individual model predictions.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, List
import pandas as pd
import numpy as np

try:
    import lime
    import lime.lime_tabular
    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False

from .base_agent import BaseAgent
from ..state.session_state import SessionState
from ..data.data_manager import DataManager
from ..core.logger import logger


class LIMEAgent(BaseAgent):
    """Local explanations using LIME.
    
    Explains individual predictions by approximating model behavior locally.
    """
    
    def __init__(self, session_id: str) -> None:
        """Initialize LIMEAgent."""
        super().__init__(
            name="lime_agent",
            description="Provides local explanations via LIME",
            session_id=session_id
        )
        self.lime_available = LIME_AVAILABLE

    def run(self, model: Any = None, X_data: pd.DataFrame = None, 
            instance_idx: int = 0, feature_names: Optional[List[str]] = None,
            num_features: int = 10) -> Dict[str, Any]:
        """Generate LIME explanation for a single prediction.
        
        Args:
            model: Trained ML model
            X_data: Feature data
            instance_idx: Index of instance to explain
            feature_names: Optional feature names
            num_features: Top features to return
            
        Returns:
            Dict with explanation results
        """
        self.log_action("starting_lime_explanation", {"instance_idx": instance_idx})
        
        try:
            if not self.lime_available:
                self.logger.warning("LIME not available")
                return {
                    "status": "unavailable",
                    "explanation": None,
                    "top_features": [],
                    "feature_weights": {},
                    "error": "LIME library not installed"
                }
            
            if model is None or X_data is None:
                return {
                    "status": "error",
                    "explanation": None,
                    "top_features": [],
                    "feature_weights": {},
                    "error": "Model or data not provided"
                }
            
            # Validate instance index
            if instance_idx >= len(X_data):
                instance_idx = len(X_data) - 1
            
            feat_names = feature_names if feature_names else X_data.columns.tolist()
            
            explainer = lime.lime_tabular.LimeTabularExplainer(
                X_data.values,
                feature_names=feat_names,
                mode='classification' if hasattr(model, 'predict_proba') else 'regression',
                verbose=False
            )
            
            predict_fn = model.predict_proba if hasattr(model, 'predict_proba') else model.predict
            instance = X_data.iloc[instance_idx].values
            exp = explainer.explain_instance(instance, predict_fn, num_features=min(num_features, len(feat_names)))
            
            top_features_list = exp.as_list()
            feature_weights = {f[0]: float(f[1]) for f in top_features_list}
            
            if hasattr(model, 'predict'):
                prediction = model.predict(instance.reshape(1, -1))[0]
            else:
                prediction = None
            
            result = {
                "status": "success",
                "explanation": {
                    "instance_index": int(instance_idx),
                    "prediction": float(prediction) if prediction is not None else None,
                    "feature_contributions": feature_weights
                },
                "top_features": [f[0] for f in top_features_list[:5]],
                "feature_weights": feature_weights,
                "error": None
            }
            
            self.log_action("lime_explanation_completed", {"instance_idx": instance_idx})
            return result
            
        except Exception as e:
            self.logger.exception(f"LIME failed: {e}")
            return {
                "status": "error",
                "explanation": None,
                "top_features": [],
                "feature_weights": {},
                "error": str(e)
            }