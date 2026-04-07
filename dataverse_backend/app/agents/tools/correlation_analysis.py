from .base_tool import BaseTool
from ..core.tool_registry import SessionContext, ToolResult
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, List


class CorrelationAnalysisTool(BaseTool):
    """Tool for computing and visualizing correlations."""

    def __init__(self):
        super().__init__()
        self.name = "correlation_analysis"
        self.description = """Pearson/Spearman correlation matrix for numeric columns.
USE WHEN: User asks about relationships, correlations, or how variables relate."""
        self.input_schema = {
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of numeric column names to analyze (optional, uses all numeric if empty)"
            },
            "method": {
                "type": "string",
                "enum": ["pearson", "spearman"],
                "description": "Correlation method",
                "default": "pearson"
            }
        }
        self.output_schema = {
            "description": "ChartSpec with correlation heatmap"
        }

    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        try:
            df = self.load_dataset(session)
            columns = params.get("columns", [])
            method = params.get("method", "pearson")

            # Get numeric columns
            if not columns:
                columns = df.select_dtypes(include=[np.number]).columns.tolist()

            numeric_df = df[columns].select_dtypes(include=[np.number])

            if len(numeric_df.columns) < 2:
                return ToolResult(
                    success=False,
                    data={},
                    error_message="Need at least 2 numeric columns for correlation analysis",
                    confidence=0.0
                )

            # Compute correlation matrix
            corr_matrix = numeric_df.corr(method=method)

            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                colorscale='RdBu',
                zmin=-1,
                zmax=1,
                text=np.round(corr_matrix.values, 2),
                texttemplate='%{text}',
                textfont={"size": 10},
                hoverongaps=False
            ))

            fig.update_layout(
                title=f"{method.title()} Correlation Matrix",
                xaxis_title="Variables",
                yaxis_title="Variables"
            )

            chart_data = fig.to_dict()
            chart_spec = self.create_chart_spec(
                chart_type="heatmap",
                data=chart_data,
                title=f"Correlation Analysis ({method})"
            )

            return ToolResult(
                success=True,
                data={
                    "correlation_matrix": corr_matrix.to_dict(),
                    "method": method
                },
                display=chart_spec
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0
            )