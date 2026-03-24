"""AnalysisAgent: executes analytical plans produced by the intent parser.

The agent performs computations using pandas and returns computed facts suitable for the
DeepAnalyze agent to interpret. This agent does NOT rely on external models and avoids
business-language generation.
"""
from __future__ import annotations

import pandas as pd
from typing import Dict, Any, Optional

from .base_agent import BaseAgent
from ..llm.intent_parser import IntentParser
from ..data.data_manager import DataManager
from ..state.session_state import SessionState


class AnalysisAgent(BaseAgent):
    def __init__(self, session_id: str):
        super().__init__(name="analysis_agent", description="Executes analytical plans", session_id=session_id)

    def _detect_date_column(self, df: pd.DataFrame) -> Optional[str]:
        # Heuristic: pick first datetime column, or column named like 'date' or 'order_date'
        datetime_cols = df.select_dtypes(include=["datetime"]).columns.tolist()
        if datetime_cols:
            return datetime_cols[0]
        for candidate in ["date", "order_date", "timestamp", "sale_date"]:
            if candidate in df.columns:
                return candidate
        return None

    def run(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the plan described by intent and return computed facts.

        The intent follows the structure produced by IntentParser. The agent must be robust
        to missing optional fields and perform conservative operations.
        """
        dm = DataManager(session_id=self.session_id)
        df = dm.get_cleaned()

        plan = intent
        computed: Dict[str, Any] = {"intent": plan}

        # Example supported task: "hot selling product last month"
        # We support simple time filtering and aggregation operations.
        date_col = self._detect_date_column(df)
        timeframe = plan.get("time_filter")

        if timeframe and date_col:
            # Expect timeframe such as {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
            start = pd.to_datetime(timeframe.get("start")) if timeframe.get("start") else None
            end = pd.to_datetime(timeframe.get("end")) if timeframe.get("end") else None
            mask = pd.Series([True] * len(df))
            if start is not None:
                mask &= df[date_col] >= start
            if end is not None:
                mask &= df[date_col] <= end
            df_filtered = df[mask]
            computed["filtered_rows"] = int(df_filtered.shape[0])
        else:
            df_filtered = df

        # Example: find top product by units sold or revenue
        metric = plan.get("metric", "units_sold")

        # Enhanced heuristic: include various name-like fields and category fields
        product_keywords = ["name", "product", "item", "sku", "description", "title", "category", "subcategory", "product_id", "productname"]
        product_col_candidates = [c for c in df.columns if any(k in c.lower() for k in product_keywords)]

        # If user previously confirmed a column, prefer that override
        state = SessionState.get(self.session_id)
        override = state.get_value("product_override")
        if override and override in df.columns:
            product_col = override
            self.log_action("product_column_overridden", {"chosen": product_col})
        else:
            if len(product_col_candidates) == 0:
                computed["error"] = "No product-like column detected"
                self.log_action("analysis_failed", {"reason": "no_product_column"})
                return computed

            if len(product_col_candidates) > 1:
                # Ambiguous: save candidates to session state and ask for confirmation
                state.set("product_candidates", product_col_candidates)
                self.log_action("product_column_ambiguous", {"candidates": product_col_candidates})
                return {"action_required": "confirm_product_column", "candidates": product_col_candidates}

            # single candidate
            product_col = product_col_candidates[0]
            self.log_action("product_column_inferred", {"chosen": product_col, "candidates": product_col_candidates})

        if metric not in df.columns:
            # Try common aliases
            if metric == "units_sold":
                metric_candidate = next((c for c in df.columns if "units" in c.lower() or "quantity" in c.lower()), None)
                if metric_candidate:
                    metric = metric_candidate

        if metric not in df.columns:
            computed["error"] = f"Metric column '{metric}' not found"
            self.log_action("analysis_failed", {"reason": "metric_not_found", "metric": metric})
            return computed

        # Aggregate
        agg = df_filtered.groupby(product_col)[metric].sum().reset_index()
        agg_sorted = agg.sort_values(by=metric, ascending=False)

        if agg_sorted.empty:
            computed["error"] = "No data after filtering"
            return computed

        top_row = agg_sorted.iloc[0]
        total_metric = float(agg[metric].sum()) if agg[metric].sum() != 0 else 0.0
        top_value = float(top_row[metric])
        revenue_share = (top_value / total_metric * 100.0) if total_metric else 0.0

        computed_update = {
            "time_period": timeframe or "entire_dataset",
            "top_product": str(top_row[product_col]),
            "top_metric_value": top_value,
            "metric": metric,
            "total_metric_value": float(total_metric),
            "revenue_share_percent": round(revenue_share, 2),
        }
        computed.update(computed_update)

        # Save to session state for traceability
        state = SessionState.get(self.session_id)
        state.set("computed_facts", computed)

        self.log_action("analysis_completed", {"computed": computed_update})
        return computed
