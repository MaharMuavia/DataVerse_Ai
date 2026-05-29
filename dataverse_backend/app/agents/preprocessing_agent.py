"""PreprocessingAgent: makes decision-based data cleaning choices.

Design principles:
- Decisions are recorded with explicit reasoning to facilitate reproducibility and audit.
- Default strategies are conservative and explained; they can be extended to include ML-driven imputers.
"""
from __future__ import annotations

import pandas as pd
from typing import Dict, Any

from .base_agent import BaseAgent
from ..data.data_manager import DataManager
from ..state.session_state import SessionState


class PreprocessingAgent(BaseAgent):
    def __init__(self, session_id: str, missing_threshold: float = 0.3):
        super().__init__(name="preprocessing_agent", description="Decision-based preprocessing", session_id=session_id)
        self.missing_threshold = missing_threshold

    def _impute_mode_value(self, series: pd.Series) -> Any:
        non_null = series.dropna()
        if non_null.empty:
            return ""

        try:
            mode = non_null.mode(dropna=True)
            if not mode.empty:
                return mode.iloc[0]
        except Exception:
            pass

        return non_null.iloc[0]

    def _decide_missing(self, series: pd.Series) -> Dict[str, Any]:
        n = len(series)
        missing = int(series.isnull().sum())
        missing_ratio = missing / max(1, n)

        decision = {}
        if missing == 0:
            decision["action"] = "none"
            decision["reason"] = "No missing values"
        elif missing_ratio > self.missing_threshold:
            decision["action"] = "drop_column"
            decision["reason"] = f"Missing ratio {missing_ratio:.2f} above threshold {self.missing_threshold}"
        else:
            if pd.api.types.is_numeric_dtype(series):
                decision["action"] = "impute_median"
                decision["reason"] = "Numeric column with moderate missingness; median imputation preserves distribution"
            else:
                decision["action"] = "impute_mode"
                decision["reason"] = "Categorical/text column with moderate missingness; mode imputation preserves common category"
        return {"missing": missing, "missing_ratio": float(missing_ratio), **decision}

    def run(self) -> Dict[str, Any]:
        dm = DataManager(session_id=self.session_id)
        df = dm.get_raw()
        decisions: Dict[str, Any] = {}

        # Make a copy for cleaning
        cleaned = df.copy()

        # Column-wise decisions
        for col in df.columns:
            col_decision = self._decide_missing(df[col])
            decisions[col] = col_decision

            if col_decision["action"] == "drop_column":
                cleaned.drop(columns=[col], inplace=True)
            elif col_decision["action"] == "impute_median":
                cleaned[col] = cleaned[col].fillna(df[col].median())
            elif col_decision["action"] == "impute_mode":
                cleaned[col] = cleaned[col].fillna(self._impute_mode_value(df[col]))
            # 'none' requires no action

        # Basic type conversions for datetime-like columns
        for col in cleaned.columns:
            if cleaned[col].dtype == object:
                try:
                    converted = pd.to_datetime(cleaned[col], errors="coerce", format="mixed")
                    # If many values convert to timestamps, adopt dtype
                    if converted.notnull().sum() / max(1, len(converted)) > 0.6:
                        cleaned[col] = converted
                        decisions.setdefault(col, {})["converted_to_datetime"] = True
                except Exception:
                    # Leave as is if conversion fails
                    decisions.setdefault(col, {})["converted_to_datetime"] = False

        # Save cleaned dataset
        dm.save_cleaned(cleaned)

        # Store decisions and reasoning
        state = SessionState.get(self.session_id)
        state.set("preprocessing_decisions", decisions)
        state.set("preprocessing_completed", True)

        self.log_action("preprocessed_dataset", {"decisions": decisions})
        return {"status": "success", "decisions": decisions}
