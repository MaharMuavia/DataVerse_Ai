from .base_tool import BaseTool
from ..core.tool_registry import SessionContext, ToolResult
import pandas as pd
import numpy as np
import plotly.express as px
from typing import Dict, Any, List


class CategoricalAnalysisTool(BaseTool):
    """Tool for analyzing categorical columns."""

    def __init__(self):
        super().__init__()
        self.name = "categorical_analysis"
        self.description = """Value counts, mode, entropy for categorical columns.
USE WHEN: User asks about categories, distributions, or categorical data."""
        self.input_schema = {
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of categorical column names to analyze"
            },
            "top_n": {
                "type": "integer",
                "description": "Number of top categories to show",
                "default": 10
            }
        }
        self.output_schema = {
            "description": "ChartSpec with category breakdown and TableSpec with statistics"
        }

    async def execute(self, params: Dict[str, Any], session) -> Any:
        try:
            from ..core.tool_registry import ToolResult

            df = self.load_dataset(session)
            columns = params.get("columns", [])
            top_n = params.get("top_n", 10)

            if not columns:
                # Get all categorical columns
                columns = df.select_dtypes(include=['object', 'category']).columns.tolist()

            if not columns:
                return ToolResult(
                    success=False,
                    data={},
                    error_message="No categorical columns found",
                    confidence=0.0
                )

            self.validate_columns_exist(df, columns)

            results = {}
            table_data = []

            for col in columns:
                value_counts = df[col].value_counts(dropna=False).head(top_n)
                total = len(df)
                unique = df[col].nunique()

                results[col] = {
                    "value_counts": value_counts.to_dict(),
                    "total_count": total,
                    "unique_count": unique,
                    "mode": df[col].mode().iloc[0] if not df[col].mode().empty else None
                }

                # Add to table
                table_data.append({
                    "column": col,
                    "unique_values": unique,
                    "mode": results[col]["mode"],
                    "top_category": value_counts.index[0],
                    "top_count": int(value_counts.iloc[0])
                })

            # Create visualization
            if len(columns) == 1:
                col = columns[0]
                value_counts = df[col].value_counts(dropna=False).head(top_n)
                fig = px.bar(
                    x=value_counts.index.astype(str),
                    y=value_counts.values,
                    title=f"Category Distribution: {col}",
                    labels={"x": col, "y": "Count"}
                )

                chart_spec = self.create_chart_spec(
                    chart_type="bar",
                    data=fig.to_dict(),
                    title=f"Distribution of {col}"
                )
            else:
                # Multiple columns - create multiple charts
                chart_spec = None

            table_spec = self.create_table_spec(
                columns=["column", "unique_values", "mode", "top_category", "top_count"],
                data=table_data,
                title="Categorical Analysis Summary"
            )

            result_data = {
                "analysis": results,
                "summary": table_data
            }

            return ToolResult(
                success=True,
                data=result_data,
                display=[table_spec] if not chart_spec else [chart_spec, table_spec]
            )

        except Exception as e:
            from ..core.tool_registry import ToolResult
            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0
            )