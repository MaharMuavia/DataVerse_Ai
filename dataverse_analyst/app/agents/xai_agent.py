from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.agents.analysis_agent import json_safe


class XAIAgent:
    def explain(self, model: Any, X_train: pd.DataFrame, X_test_sample: pd.DataFrame) -> dict[str, Any]:
        if model is None:
            return {"status": "error", "error": "No trained model available for SHAP", "importances": {}}
        if X_train is None or X_test_sample is None or X_train.empty or X_test_sample.empty:
            return {"status": "error", "error": "XAI requires non-empty train and sample frames", "importances": {}}
        try:
            import shap

            try:
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(X_test_sample)
                method = "TreeExplainer"
            except Exception:
                background = shap.sample(X_train, min(100, len(X_train)), random_state=42)
                explainer = shap.KernelExplainer(self._predict_callable(model), background)
                shap_values = explainer.shap_values(X_test_sample, nsamples=100)
                method = "KernelExplainer"

            values = np.asarray(shap_values[0] if isinstance(shap_values, list) else shap_values)
            if values.ndim == 3:
                values = values[:, :, 0]
            if values.ndim == 1:
                values = values.reshape(1, -1)
            importances = dict(zip(X_test_sample.columns, np.abs(values).mean(axis=0).tolist()))
            importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True)[:20])
            first_row = dict(zip(X_test_sample.columns, values[0].tolist())) if len(values) else {}
            return json_safe(
                {
                    "status": "success",
                    "method": method,
                    "importances": importances,
                    "waterfall": first_row,
                    "samples_explained": int(len(X_test_sample)),
                }
            )
        except Exception as exc:
            return {"status": "error", "error": str(exc), "importances": {}}

    def _predict_callable(self, model: Any):
        if hasattr(model, "predict"):
            return model.predict
        raise ValueError("Model does not expose predict()")
