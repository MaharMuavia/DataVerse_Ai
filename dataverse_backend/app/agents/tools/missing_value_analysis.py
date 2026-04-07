from .base_tool import BaseTool
from ..core.tool_registry import SessionContext, ToolResult
import pandas as pd
import numpy as np
import plotly.express as px
from typing import Dict, Any, List


class MissingValueAnalysisTool(BaseTool):
    """Tool for analyzing missing values in the dataset."""

    def __init__(self):
        super().__init__()
        self.name = "missing_value_analysis"
        self.description = """Count and % missing per column, pattern detection.
USE WHEN: User asks about missing data, nulls, or data quality."""
        self.input_schema = {
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of column names to analyze (optional, analyzes all if empty)"
            }
        }
        self.output_schema = {
            "description": "TableSpec with missing value statistics and ChartSpec with visualization"
        }

    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        try:
            df = self.load_dataset(session)
            columns = params.get("columns", df.columns.tolist())

            self.validate_columns_exist(df, columns)

            missing_data = []
            for col in columns:
                total_count = len(df)
                missing_count = df[col].isnull().sum()
                missing_pct = (missing_count / total_count) * 100 if total_count > 0 else 0

                missing_data.append({
                    "column": col,
                    "total_rows": total_count,
                    "missing_count": int(missing_count),
                    "missing_percentage": round(missing_pct, 2),
                    "data_type": str(df[col].dtype)
                })

            # Sort by missing percentage descending
            missing_data.sort(key=lambda x: x["missing_percentage"], reverse=True)

            # Create table
            table_spec = self.create_table_spec(
                columns=["column", "data_type", "total_rows", "missing_count", "missing_percentage"],
                data=missing_data,
                title="Missing Value Analysis"
            )

            # Create visualization for columns with missing data
            columns_with_missing = [row for row in missing_data if row["missing_count"] > 0]

            if columns_with_missing:
                chart_data = {
                    "columns": [row["column"] for row in columns_with_missing],
                    "missing_percentage": [row["missing_percentage"] for row in columns_with_missing]
                }

                fig = px.bar(
                    x=chart_data["columns"],
                    y=chart_data["missing_percentage"],
                    title="Missing Value Percentage by Column",
                    labels={"x": "Column", "y": "Missing %"}
                )

                chart_spec = self.create_chart_spec(
                    chart_type="bar",
                    data=fig.to_dict(),
                    title="Missing Values Visualization"
                )
            else:
                chart_spec = None

            return ToolResult(
                success=True,
                data={"missing_analysis": missing_data},
                display=table_spec if not chart_spec else [table_spec, chart_spec]
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0
            )