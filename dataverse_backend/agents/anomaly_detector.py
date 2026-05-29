from __future__ import annotations

from typing import List

import pandas as pd

from config.llm_providers import ModelRouter
from graph.state import DataVerseState
from tools.stats_tools import detect_drift_tool, detect_outliers_tool, run_zscore_tool


async def anomaly_detector_node(state: DataVerseState) -> DataVerseState:
    """Run proactive anomaly detection after upload when dataset is present."""
    retries = 0
    _ = ModelRouter()  # Keep provider availability aligned with architecture.

    while retries <= 2:
        try:
            dataset_path = state.get("dataset_path")
            if not dataset_path:
                return state

            df = pd.read_csv(dataset_path)
            numeric_cols: List[str] = df.select_dtypes(include=["number"]).columns.tolist()
            if not numeric_cols:
                return state

            findings = []
            for col in numeric_cols[:5]:
                iqr = detect_outliers_tool.invoke(
                    {"column": col, "method": "iqr", "df_path": dataset_path}
                )
                zscore = run_zscore_tool.invoke({"column": col, "df_path": dataset_path, "threshold": 3.0})
                drift = detect_drift_tool.invoke(
                    {
                        "column": col,
                        "baseline_df_path": dataset_path,
                        "current_df_path": dataset_path,
                    }
                )

                findings.append(
                    {
                        "column": col,
                        "iqr_outliers": iqr.get("count", 0),
                        "zscore_outliers": zscore.get("count", 0),
                        "drift_detected": drift.get("drift_detected", False),
                    }
                )

            insights = list(state.get("insights", []))
            insights.append(f"Proactive anomaly scan: {findings}")
            state["insights"] = insights
            state["current_agent"] = "anomaly_detector"
            state["error"] = None
            return state
        except Exception as exc:
            retries += 1
            state["error"] = f"anomaly_detector failed: {exc}"
            if retries > 2:
                state["agent_plan"] = ["clarifier"]
                return state

    return state
