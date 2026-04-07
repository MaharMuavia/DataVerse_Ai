from .base_tool import BaseTool
from ..core.tool_registry import SessionContext, ToolResult
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List


class DistributionPlotTool(BaseTool):
    """Tool for creating distribution plots."""

    def __init__(self):
        super().__init__()
        self.name = "distribution_plot"
        self.description = """Create a histogram or KDE density plot for numeric columns.
USE WHEN: User asks to 'show distribution', 'see spread', 'how is X distributed'"""
        self.input_schema = {
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of numeric column names to plot"
            },
            "plot_type": {
                "type": "string",
                "enum": ["histogram", "kde"],
                "description": "Type of plot to create",
                "default": "histogram"
            },
            "bins": {
                "type": "integer",
                "description": "Number of histogram bins",
                "default": 30
            }
        }
        self.output_schema = {
            "description": "ChartSpec with interactive Plotly chart"
        }

    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        try:
            df = self.load_dataset(session)
            columns = params.get("columns", [])
            plot_type = params.get("plot_type", "histogram")
            bins = params.get("bins", 30)

            if not columns:
                return ToolResult(
                    success=False,
                    data={},
                    error_message="No columns specified for distribution plot",
                    confidence=0.0
                )

            self.validate_columns_exist(df, columns)

            # Filter to numeric columns only
            numeric_columns = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]
            if not numeric_columns:
                return ToolResult(
                    success=False,
                    data={},
                    error_message="No numeric columns found in specified columns",
                    confidence=0.0
                )

            if plot_type == "histogram":
                if len(numeric_columns) == 1:
                    fig = px.histogram(
                        df,
                        x=numeric_columns[0],
                        nbins=bins,
                        title=f"Distribution of {numeric_columns[0]}"
                    )
                else:
                    # Multiple histograms
                    fig = go.Figure()
                    for col in numeric_columns:
                        fig.add_trace(go.Histogram(
                            x=df[col],
                            name=col,
                            nbinsx=bins
                        ))
                    fig.update_layout(
                        title="Distribution Comparison",
                        barmode='overlay'
                    )
                    fig.update_traces(opacity=0.75)

            elif plot_type == "kde":
                if len(numeric_columns) == 1:
                    fig = px.histogram(
                        df,
                        x=numeric_columns[0],
                        nbins=bins,
                        histnorm='density',
                        title=f"Density Plot of {numeric_columns[0]}"
                    )
                    # Add KDE curve
                    fig.add_trace(go.Scatter(
                        x=df[numeric_columns[0]].sort_values(),
                        y=df[numeric_columns[0]].plot.kde().get_values(),
                        mode='lines',
                        name='KDE'
                    ))
                else:
                    # Multiple KDE plots
                    fig = go.Figure()
                    for col in numeric_columns:
                        sorted_data = df[col].dropna().sort_values()
                        kde_values = df[col].plot.kde().get_values()
                        fig.add_trace(go.Scatter(
                            x=sorted_data,
                            y=kde_values,
                            mode='lines',
                            name=col
                        ))
                    fig.update_layout(title="Density Comparison")

            # Convert to chart spec
            chart_data = fig.to_dict()
            chart_spec = self.create_chart_spec(
                chart_type=plot_type,
                data=chart_data,
                title=f"Distribution Plot ({plot_type})"
            )

            return ToolResult(
                success=True,
                data={"plot_data": chart_data},
                display=chart_spec
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0
            )