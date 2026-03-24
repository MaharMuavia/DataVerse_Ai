"""EDA Agent: performs autonomous exploratory data analysis using pandas.

This agent performs descriptive statistics, cardinality analysis, outlier detection using IQR,
and simple distribution summaries. Results and human-readable explanations are stored in
session state to be used by downstream agents.
"""
from __future__ import annotations

import pandas as pd
from typing import Dict, Any

from .base_agent import BaseAgent
from ..data.data_manager import DataManager
from ..state.session_state import SessionState


class EDAAgent(BaseAgent):
    def __init__(self, session_id: str):
        super().__init__(name="eda_agent", description="Performs autonomous EDA", session_id=session_id)

    def _describe_numeric(self, df: pd.DataFrame) -> Dict[str, Any]:
        desc = df.describe(include=["number"]).to_dict()
        return desc

    def _cardinality(self, df: pd.DataFrame) -> Dict[str, int]:
        return {col: int(df[col].nunique(dropna=True)) for col in df.columns}

    def _outliers_iqr(self, series: pd.Series) -> Dict[str, Any]:
        # Basic IQR rule to detect outliers and counts
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = series[(series < lower) | (series > upper)].dropna()
        return {"count": int(outliers.shape[0]), "lower_threshold": float(lower), "upper_threshold": float(upper)}

    def run(self) -> Dict[str, Any]:
        dm = DataManager(session_id=self.session_id)
        df = dm.get_raw()

        results: Dict[str, Any] = {}

        # Descriptive statistics
        results["numeric_description"] = self._describe_numeric(df)

        # Cardinality
        results["cardinality"] = self._cardinality(df)

        # Outliers per numeric column
        outliers = {}
        for col in df.select_dtypes(include=["number"]).columns:
            outliers[col] = self._outliers_iqr(df[col])
        results["outliers"] = outliers

        # Distribution summaries (for a few high-value columns, sample)
        distributions = {}
        for col in df.columns[:5]:
            distributions[col] = {
                "n_missing": int(df[col].isnull().sum()),
                "top_values": df[col].value_counts(dropna=True).head(5).to_dict()
            }
        results["distributions"] = distributions

        # Human-readable summary
        summary_lines = []
        summary_lines.append(f"Dataset contains {df.shape[0]} rows and {df.shape[1]} columns.")
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            summary_lines.append(f"Numeric columns: {', '.join(numeric_cols)}.")
            summary_lines.append("Outlier counts available for numeric columns.")
        low_cardinality = [c for c, v in results["cardinality"].items() if v < max(5, 0.01 * df.shape[0])]
        if low_cardinality:
            summary_lines.append(f"Detected low-cardinality columns (likely categorical): {', '.join(low_cardinality)}.")

        results["human_readable"] = " ".join(summary_lines)

        # Save to session state
        state = SessionState.get(self.session_id)
        state.set("eda", results)
        state.set("eda_completed", True)

        self.log_action("performed_eda", {"eda_summary": results["human_readable"]})
        return {"status": "success", "eda": results}
