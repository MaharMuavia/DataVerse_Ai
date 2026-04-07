"""
Scatter Relationship Analysis Tool

Visualizes relationships between two numeric variables with optional
color encoding for categorical/numeric grouping.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import plotly.graph_objects as go

from .base_tool import BaseTool
from ..core.tool_registry import ToolResult, ChartSpec, SessionContext


class ScatterRelationshipTool(BaseTool):
    """
    Analyze relationships between two variables.
    
    Creates scatter plots with optional color encoding for:
    1. Correlation visualization
    2. Outlier detection
    3. Group separation
    4. Trend identification
    """
    
    @property
    def name(self) -> str:
        return "scatter_relationship"
    
    @property
    def description(self) -> str:
        return """
        Visualize relationship between two variables as scatter plot.
        Supports color encoding by a third variable for multi-dimensional analysis.
        
        Params:
        - x_column: str - X-axis variable (numeric or categorical)
        - y_column: str - Y-axis variable (numeric)
        - color_column: str (optional) - Column for color encoding
        - max_points: int (optional, default=5000) - Subsample if > this many points
        """
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "x_column": "str (required)",
            "y_column": "str (required)",
            "color_column": "str (optional)",
            "max_points": "int (optional, default=5000)"
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "correlation": "float (-1 to 1) if both numeric",
            "outlier_count": "int - number of outliers detected",
            "group_count": "int - number of groups if color_column used",
            "chart": "Plotly scatter plot"
        }
    
    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        """Execute scatter relationship analysis."""
        try:
            # Load dataset
            df = self.load_dataset(session)
            
            x_column = params.get("x_column")
            y_column = params.get("y_column")
            color_column = params.get("color_column")
            max_points = params.get("max_points", 5000)
            
            # Validate inputs
            if not x_column or not y_column:
                return ToolResult(
                    success=False,
                    error_message="x_column and y_column are required"
                )
            
            self.validate_columns_exist(df, [x_column, y_column])
            
            if color_column:
                self.validate_columns_exist(df, [color_column])
            
            # Prepare data
            plot_data = df[[x_column, y_column]].copy()
            if color_column:
                plot_data[color_column] = df[color_column]
            
            # Remove rows with missing values
            plot_data = plot_data.dropna()
            
            # Subsample if too many points
            if len(plot_data) > max_points:
                plot_data = plot_data.sample(n=max_points, random_state=42)
                subsampled = True
            else:
                subsampled = False
            
            # Calculate correlation if both numeric
            is_x_numeric = pd.api.types.is_numeric_dtype(plot_data[x_column])
            is_y_numeric = pd.api.types.is_numeric_dtype(plot_data[y_column])
            
            correlation = None
            if is_x_numeric and is_y_numeric:
                correlation = float(plot_data[x_column].corr(plot_data[y_column]))
            
            # Detect outliers (IQR method on y)
            if is_y_numeric:
                Q1 = plot_data[y_column].quantile(0.25)
                Q3 = plot_data[y_column].quantile(0.75)
                IQR = Q3 - Q1
                outlier_mask = (plot_data[y_column] < (Q1 - 1.5 * IQR)) | \
                               (plot_data[y_column] > (Q3 + 1.5 * IQR))
                outlier_count = int(outlier_mask.sum())
            else:
                outlier_count = 0
            
            # Create visualization
            fig = go.Figure()
            
            if color_column:
                # Group by color column
                is_color_numeric = pd.api.types.is_numeric_dtype(plot_data[color_column])
                
                if is_color_numeric:
                    # Continuous color scale
                    fig.add_trace(go.Scatter(
                        x=plot_data[x_column],
                        y=plot_data[y_column],
                        mode='markers',
                        marker=dict(
                            size=6,
                            color=plot_data[color_column],
                            colorscale='Viridis',
                            showscale=True,
                            colorbar=dict(title=color_column)
                        ),
                        text=plot_data[color_column],
                        hovertemplate=f'<b>{x_column}</b>: %{{x}}<br>' +
                                     f'<b>{y_column}</b>: %{{y}}<br>' +
                                     f'<b>{color_column}</b>: %{{text}}<br>' +
                                     '<extra></extra>',
                        name=color_column
                    ))
                else:
                    # Categorical colors
                    unique_groups = plot_data[color_column].unique()
                    colors = [f'hsl({i * 360 / len(unique_groups)}, 70%, 50%)' 
                             for i in range(len(unique_groups))]
                    
                    for group, color in zip(unique_groups, colors):
                        group_data = plot_data[plot_data[color_column] == group]
                        fig.add_trace(go.Scatter(
                            x=group_data[x_column],
                            y=group_data[y_column],
                            mode='markers',
                            marker=dict(size=6, color=color),
                            name=str(group),
                            hovertemplate=f'<b>{x_column}</b>: %{{x}}<br>' +
                                         f'<b>{y_column}</b>: %{{y}}<br>' +
                                         f'<b>{color_column}</b>: {group}<br>' +
                                         '<extra></extra>'
                        ))
            else:
                # Simple scatter without color
                fig.add_trace(go.Scatter(
                    x=plot_data[x_column],
                    y=plot_data[y_column],
                    mode='markers',
                    marker=dict(size=6, color='#1f77b4'),
                    hovertemplate=f'<b>{x_column}</b>: %{{x}}<br>' +
                                 f'<b>{y_column}</b>: %{{y}}<br>' +
                                 '<extra></extra>',
                    name='Data'
                ))
            
            # Add correlation line if both numeric
            if is_x_numeric and is_y_numeric and correlation is not None:
                x_range = np.array([plot_data[x_column].min(), plot_data[x_column].max()])
                z = np.polyfit(plot_data[x_column], plot_data[y_column], 1)
                p = np.poly1d(z)
                y_line = p(x_range)
                
                fig.add_trace(go.Scatter(
                    x=x_range,
                    y=y_line,
                    mode='lines',
                    name='Trend',
                    line=dict(color='red', dash='dash', width=2)
                ))
            
            fig.update_layout(
                title=f"{x_column} vs {y_column}" + 
                      (f" (colored by {color_column})" if color_column else ""),
                xaxis_title=x_column,
                yaxis_title=y_column,
                hovermode='closest',
                height=500,
                template='plotly_white'
            )
            
            # Build result
            graph_count = len(plot_data[color_column].unique()) if color_column else 1
            
            return ToolResult(
                success=True,
                data={
                    "correlation": correlation,
                    "outlier_count": outlier_count,
                    "point_count": len(plot_data),
                    "subsampled": subsampled,
                    "group_count": graph_count if color_column else 1
                },
                display=self.create_chart_spec(
                    chart_type="scatter",
                    data={
                        "x": plot_data[x_column].tolist(),
                        "y": plot_data[y_column].tolist()
                    },
                    title=f"{x_column} vs {y_column}",
                    x_label=x_column,
                    y_label=y_column
                ),
                confidence=0.80
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Scatter relationship analysis failed: {str(e)}"
            )
