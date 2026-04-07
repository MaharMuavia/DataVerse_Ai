from .base_tool import BaseTool
from ..core.tool_registry import SessionContext, ToolResult
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, List


class OutlierDetectionTool(BaseTool):
    """Tool for detecting outliers using IQR and Z-score methods."""

    def __init__(self):
        super().__init__()
        self.name = "outlier_detection"
        self.description = """IQR and Z-score outlier detection, flag rows.
USE WHEN: User asks about outliers, anomalies, or data quality issues."""
        self.input_schema = {
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of numeric column names to analyze"
            },
            "method": {
                "type": "string",
                "enum": ["iqr", "zscore"],
                "description": "Detection method",
                "default": "iqr"
            },
            "threshold": {
                "type": "number",
                "description": "z-score threshold (default 3) or IQR multiplier (default 1.5)",
                "default": 1.5
            }
        }
        self.output_schema = {
            "description": "TableSpec with outlier summary and ChartSpec with visualization"
        }

    async def execute(self, params: Dict[str, Any], session) -> Any:
        try:
            from ..core.tool_registry import ToolResult

            df = self.load_dataset(session)
            columns = params.get("columns", [])
            method = params.get("method", "iqr")
            threshold = params.get("threshold", 1.5)

            if not columns:
                columns = df.select_dtypes(include=[np.number]).columns.tolist()

            if not columns:
                return ToolResult(
                    success=False,
                    data={},
                    error_message="No numeric columns found",
                    confidence=0.0
                )

            self.validate_columns_exist(df, columns)

            outlier_summary = []
            all_outlier_indices = set()

            for col in columns:
                series = df[col].dropna()

                if method == "iqr":
                    Q1 = series.quantile(0.25)
                    Q3 = series.quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - threshold * IQR
                    upper_bound = Q3 + threshold * IQR
                    outliers = (series < lower_bound) | (series > upper_bound)
                else:  # zscore
                    z_scores = np.abs((series - series.mean()) / series.std())
                    outliers = z_scores > threshold
                    lower_bound = series.mean() - threshold * series.std()
                    upper_bound = series.mean() + threshold * series.std()

                outlier_count = outliers.sum()
                outlier_indices = outliers[outliers].index.tolist()
                all_outlier_indices.update(outlier_indices)

                outlier_summary.append({
                    "column": col,
                    "outlier_count": int(outlier_count),
                    "outlier_percentage": round(100 * outlier_count / len(series), 2),
                    "lower_bound": round(lower_bound, 3),
                    "upper_bound": round(upper_bound, 3)
                })

            # Create summary table
            table_spec = self.create_table_spec(
                columns=["column", "outlier_count", "outlier_percentage", "lower_bound", "upper_bound"],
                data=outlier_summary,
                title=f"Outlier Detection ({method.upper()})"
            )

            # Create visualization for first numeric column if outliers exist
            if len(columns) > 0 and outlier_summary[0]["outlier_count"] > 0:
                col = columns[0]
                series = df[col].dropna()
                bounds = outlier_summary[0]

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=range(len(series)),
                    y=series.values,
                    mode='markers',
                    name='Data points',
                    marker=dict(size=5)
                ))

                # Add bounds as horizontal lines
                fig.add_hline(y=bounds["lower_bound"], line_dash="dash", line_color="red", name="Lower bound")
                fig.add_hline(y=bounds["upper_bound"], line_dash="dash", line_color="red", name="Upper bound")

                fig.update_layout(
                    title=f"Outliers in {col}",
                    xaxis_title="Row Index",
                    yaxis_title=col
                )

                chart_spec = self.create_chart_spec(
                    chart_type="scatter",
                    data=fig.to_dict(),
                    title="Outlier Visualization"
                )

                result_data = {
                    "outlier_summary": outlier_summary,
                    "total_outlier_rows": len(all_outlier_indices),
                    "outlier_indices": list(all_outlier_indices),
                    "method": method,
                    "threshold": threshold
                }

                return ToolResult(
                    success=True,
                    data=result_data,
                    display=[table_spec, chart_spec]
                )
            else:
                result_data = {
                    "outlier_summary": outlier_summary,
                    "total_outlier_rows": len(all_outlier_indices),
                    "outlier_indices": list(all_outlier_indices),
                    "method": method,
                    "threshold": threshold
                }

                return ToolResult(
                    success=True,
                    data=result_data,
                    display=table_spec
                )

        except Exception as e:
            from ..core.tool_registry import ToolResult
            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0
            )