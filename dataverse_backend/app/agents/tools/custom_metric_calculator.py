"""
Custom Metric Calculator Tool

Allows creation of derived metrics and custom calculations on the dataset.
Useful for business KPI calculations and domain-specific metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Callable
from datetime import datetime

from .base_tool import BaseTool
from ..core.tool_registry import ToolResult, TableSpec, SessionContext


class CustomMetricCalculatorTool(BaseTool):
    """
    Calculate custom metrics and derived columns.
    
    Supports:
    1. Ratio calculations (e.g., revenue per customer)
    2. Period-based metrics (e.g., YoY growth)
    3. Threshold-based categorization
    4. Domain-specific KPIs
    """
    
    @property
    def name(self) -> str:
        return "custom_metric_calculator"
    
    @property
    def description(self) -> str:
        return """
        Calculate custom metrics and derived values.
        Create business KPIs and performance indicators.
        
        Params:
        - metric_name: str - Name of the metric to calculate
        - metric_type: str - Type ('ratio', 'growth', 'threshold', 'aggregate')
        - params: dict - Type-specific parameters
          For 'ratio': {numerator: col, denominator: col}
          For 'growth': {value_col: col, period_col: col, period_type: 'month'/'year'}
          For 'threshold': {target_col: col, thresholds: {name: value}}
          For 'aggregate': {column: col, operation: 'sum'/'avg'/'count'}
        """
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "metric_name": "str",
            "metric_type": "str ('ratio', 'growth', 'threshold', 'aggregate')",
            "params": "dict with type-specific parameters"
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "metric_name": "str",
            "metric_type": "str",
            "result": "Calculated metric(s)",
            "table": "Results table"
        }
    
    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        """Execute custom metric calculation."""
        try:
            # Load dataset
            df = self.load_dataset(session)
            
            metric_name = params.get("metric_name")
            metric_type = params.get("metric_type")
            metric_params = params.get("params", {})
            
            # Validate inputs
            if not metric_name or not metric_type:
                return ToolResult(
                    success=False,
                    error_message="metric_name and metric_type are required"
                )
            
            # Route to specific calculation type
            if metric_type == "ratio":
                return await self._calculate_ratio(df, metric_name, metric_params)
            
            elif metric_type == "growth":
                return await self._calculate_growth(df, metric_name, metric_params)
            
            elif metric_type == "threshold":
                return await self._calculate_threshold(df, metric_name, metric_params)
            
            elif metric_type == "aggregate":
                return await self._calculate_aggregate(df, metric_name, metric_params)
            
            else:
                return ToolResult(
                    success=False,
                    error_message=f"Unknown metric_type: {metric_type}"
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Custom metric calculation failed: {str(e)}"
            )
    
    async def _calculate_ratio(self, df: pd.DataFrame, metric_name: str, 
                               params: Dict[str, Any]) -> ToolResult:
        """Calculate ratio metric (numerator / denominator)."""
        numerator_col = params.get("numerator")
        denominator_col = params.get("denominator")
        
        if not numerator_col or not denominator_col:
            return ToolResult(
                success=False,
                error_message="'numerator' and 'denominator' columns required for ratio"
            )
        
        self.validate_columns_exist(df, [numerator_col, denominator_col])
        
        # Calculate ratio
        ratio = (df[numerator_col] / df[denominator_col].replace(0, np.nan)).fillna(0)
        
        result_df = pd.DataFrame({
            metric_name: ratio,
            f"{metric_name}_percentile": ratio.rank(pct=True) * 100
        })
        
        # Summary statistics
        summary = {
            "mean": float(ratio.mean()),
            "median": float(ratio.median()),
            "std": float(ratio.std()),
            "min": float(ratio.min()),
            "max": float(ratio.max())
        }
        
        # Create table display
        top_rows = result_df.head(10)
        table_data = top_rows.values.tolist()
        table_cols = top_rows.columns.tolist()
        
        return ToolResult(
            success=True,
            data={
                "metric_name": metric_name,
                "metric_type": "ratio",
                "numerator": numerator_col,
                "denominator": denominator_col,
                "statistics": summary,
                "record_count": len(result_df)
            },
            display=self.create_table_spec(
                columns=table_cols,
                data=table_data,
                title=f"Metric: {metric_name} ({numerator_col}/{denominator_col})"
            ),
            confidence=0.90
        )
    
    async def _calculate_growth(self, df: pd.DataFrame, metric_name: str,
                                params: Dict[str, Any]) -> ToolResult:
        """Calculate growth metric (period-over-period)."""
        value_col = params.get("value_column")
        period_col = params.get("period_column")
        
        if not value_col or not period_col:
            return ToolResult(
                success=False,
                error_message="'value_column' and 'period_column' required for growth"
            )
        
        self.validate_columns_exist(df, [value_col, period_col])
        
        # Group by period and sum
        period_totals = df.groupby(period_col)[value_col].sum().sort_index()
        
        # Calculate growth rate
        growth_rate = period_totals.pct_change() * 100
        
        result_df = pd.DataFrame({
            "period": period_totals.index,
            "value": period_totals.values,
            "growth_rate": growth_rate.values
        })
        
        # Summary
        avg_growth = float(growth_rate.mean())
        
        # Create display
        table_data = result_df.values.tolist()
        table_cols = result_df.columns.tolist()
        
        return ToolResult(
            success=True,
            data={
                "metric_name": metric_name,
                "metric_type": "growth",
                "value_column": value_col,
                "period_column": period_col,
                "avg_growth_rate": avg_growth,
                "periods_analyzed": len(result_df)
            },
            display=self.create_table_spec(
                columns=table_cols,
                data=table_data,
                title=f"Growth Metric: {metric_name}"
            ),
            confidence=0.85
        )
    
    async def _calculate_threshold(self, df: pd.DataFrame, metric_name: str,
                                   params: Dict[str, Any]) -> ToolResult:
        """Calculate threshold-based categorization."""
        target_col = params.get("target_column")
        thresholds = params.get("thresholds", {})
        
        if not target_col or not thresholds:
            return ToolResult(
                success=False,
                error_message="'target_column' and 'thresholds' dict required for threshold metric"
            )
        
        self.validate_columns_exist(df, [target_col])
        
        # Create categories based on thresholds
        categories = []
        for value in df[target_col]:
            category = "Other"
            for threshold_name in sorted(thresholds.keys(), 
                                        key=lambda x: thresholds[x], 
                                        reverse=True):
                if value >= thresholds[threshold_name]:
                    category = threshold_name
                    break
            categories.append(category)
        
        # Count by category
        category_counts = pd.Series(categories).value_counts()
        
        result_df = pd.DataFrame({
            "category": category_counts.index,
            "count": category_counts.values,
            "percentage": (category_counts.values / len(df) * 100).round(1)
        })
        
        # Create display
        table_data = result_df.values.tolist()
        table_cols = result_df.columns.tolist()
        
        return ToolResult(
            success=True,
            data={
                "metric_name": metric_name,
                "metric_type": "threshold",
                "target_column": target_col,
                "thresholds": thresholds,
                "category_distribution": category_counts.to_dict()
            },
            display=self.create_table_spec(
                columns=table_cols,
                data=table_data,
                title=f"Threshold Metric: {metric_name}"
            ),
            confidence=0.85
        )
    
    async def _calculate_aggregate(self, df: pd.DataFrame, metric_name: str,
                                   params: Dict[str, Any]) -> ToolResult:
        """Calculate aggregate metric."""
        column = params.get("column")
        operation = params.get("operation", "sum")
        
        if not column:
            return ToolResult(
                success=False,
                error_message="'column' required for aggregate metric"
            )
        
        self.validate_columns_exist(df, [column])
        
        # Calculate aggregate
        if operation == "sum":
            result = float(df[column].sum())
        elif operation == "avg":
            result = float(df[column].mean())
        elif operation == "count":
            result = int(df[column].count())
        elif operation == "median":
            result = float(df[column].median())
        else:
            return ToolResult(
                success=False,
                error_message=f"Unknown operation: {operation}"
            )
        
        result_df = pd.DataFrame({
            "metric": [metric_name],
            "value": [result],
            "operation": [operation],
            "records_processed": [len(df)]
        })
        
        table_data = result_df.values.tolist()
        table_cols = result_df.columns.tolist()
        
        return ToolResult(
            success=True,
            data={
                "metric_name": metric_name,
                "metric_type": "aggregate",
                "column": column,
                "operation": operation,
                "result": result
            },
            display=self.create_table_spec(
                columns=table_cols,
                data=table_data,
                title=f"{operation.upper()}({column})"
            ),
            confidence=0.95
        )
