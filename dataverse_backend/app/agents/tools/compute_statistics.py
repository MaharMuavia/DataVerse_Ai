from .base_tool import BaseTool
from ..core.tool_registry import SessionContext, ToolResult
import pandas as pd
import numpy as np
from typing import Dict, Any, List


class ComputeStatisticsTool(BaseTool):
    """Tool for computing statistics for columns."""

    def __init__(self):
        super().__init__()
        self.name = "compute_statistics"
        self.description = """Mean, median, std, skewness, kurtosis per column.
USE WHEN: User asks for statistics, summary stats, or descriptive statistics."""
        self.input_schema = {
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of column names to compute statistics for"
            },
            "include_percentiles": {
                "type": "boolean",
                "description": "Whether to include 25th, 75th percentiles",
                "default": True
            }
        }
        self.output_schema = {
            "description": "TableSpec with statistics for each column"
        }

    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        try:
            df = self.load_dataset(session)
            columns = params.get("columns", [])
            include_percentiles = params.get("include_percentiles", True)

            if not columns:
                # If no columns specified, use all numeric columns
                columns = df.select_dtypes(include=[np.number]).columns.tolist()

            self.validate_columns_exist(df, columns)

            stats_data = []
            for col in columns:
                series = df[col].dropna()
                if series.empty:
                    continue

                stat_row = {
                    "column": col,
                    "count": len(series),
                    "mean": float(series.mean()),
                    "median": float(series.median()),
                    "std": float(series.std()),
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "skewness": float(series.skew()),
                    "kurtosis": float(series.kurtosis())
                }

                if include_percentiles:
                    stat_row.update({
                        "25th_percentile": float(series.quantile(0.25)),
                        "75th_percentile": float(series.quantile(0.75))
                    })

                stats_data.append(stat_row)

            columns_list = ["column", "count", "mean", "median", "std", "min", "max", "skewness", "kurtosis"]
            if include_percentiles:
                columns_list.extend(["25th_percentile", "75th_percentile"])

            table_spec = self.create_table_spec(
                columns=columns_list,
                data=stats_data,
                title="Column Statistics"
            )

            return ToolResult(
                success=True,
                data={"statistics": stats_data},
                display=table_spec
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0
            )