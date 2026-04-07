"""
Time Series Trend Analysis Tool

Detects temporal trends in data by resampling time-based columns
and correlating with numeric targets.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import plotly.graph_objects as go
from datetime import datetime

from .base_tool import BaseTool
from ..core.tool_registry import ToolResult, ChartSpec, NarrativeSpec, SessionContext


class TimeSeriesTrendTool(BaseTool):
    """
    Analyze time series trends in dataset.
    
    Detects temporal patterns by:
    1. Identifying date/datetime columns
    2. Resampling to monthly/weekly/daily
    3. Correlating with numeric targets
    4. Visualizing trend with confidence bands
    """
    
    @property
    def name(self) -> str:
        return "time_series_trend"
    
    @property
    def description(self) -> str:
        return """
        Analyze temporal trends in data. Resamples time series data and correlates
        with numeric targets to reveal patterns over time.
        
        Params:
        - time_column: str - Column name with timestamps/dates
        - value_column: str - Numeric column to track over time
        - freq: str - Resampling frequency ('D'=daily, 'W'=weekly, 'M'=monthly, default='M')
        - agg_method: str - Aggregation method ('mean', 'sum', 'count', default='mean')
        """
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "time_column": "str",
            "value_column": "str",
            "freq": "str (optional, default='M')",
            "agg_method": "str (optional, default='mean')"
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "trend_stats": {
                "start_value": "float",
                "end_value": "float",
                "trend_direction": "str (up/down/stable)",
                "volatility": "float",
                "correlation": "float (with time)"
            },
            "chart": "Plotly line chart with trend",
            "narrative": "Business interpretation of trend"
        }
    
    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        """Execute time series trend analysis."""
        try:
            # Load dataset
            df = self.load_dataset(session)
            
            time_column = params.get("time_column")
            value_column = params.get("value_column")
            freq = params.get("freq", "M")
            agg_method = params.get("agg_method", "mean")
            
            # Validate inputs
            if not time_column or not value_column:
                return ToolResult(
                    success=False,
                    error_message="time_column and value_column are required"
                )
            
            self.validate_columns_exist(df, [time_column, value_column])
            
            # Convert time column to datetime
            try:
                df[time_column] = pd.to_datetime(df[time_column])
            except Exception as e:
                return ToolResult(
                    success=False,
                    error_message=f"Could not parse {time_column} as datetime: {str(e)}"
                )
            
            # Resample and aggregate
            ts_data = df.set_index(time_column)[[value_column]].sort_index()
            
            if agg_method == "mean":
                resampled = ts_data.resample(freq).mean()
            elif agg_method == "sum":
                resampled = ts_data.resample(freq).sum()
            elif agg_method == "count":
                resampled = ts_data.resample(freq).count()
            else:
                resampled = ts_data.resample(freq).mean()
            
            # Calculate trend statistics
            resampled = resampled.dropna()
            
            if len(resampled) < 2:
                return ToolResult(
                    success=False,
                    error_message=f"Not enough time periods for trend analysis (need 2+, got {len(resampled)})"
                )
            
            start_value = float(resampled.iloc[0, 0])
            end_value = float(resampled.iloc[-1, 0])
            volatility = float(resampled[value_column].std())
            
            # Determine direction
            if end_value > start_value * 1.05:
                trend_direction = "upward"
            elif end_value < start_value * 0.95:
                trend_direction = "downward"
            else:
                trend_direction = "stable"
            
            # Calculate correlation with time (as numeric)
            time_numeric = np.arange(len(resampled))
            correlation = float(np.corrcoef(time_numeric, resampled[value_column].values)[0, 1])
            
            # Create visualization
            fig = go.Figure()
            
            # Add main trend line
            fig.add_trace(go.Scatter(
                x=resampled.index,
                y=resampled[value_column],
                mode='lines+markers',
                name='Trend',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
            ))
            
            # Add trend line (linear fit)
            z = np.polyfit(time_numeric, resampled[value_column].values, 1)
            p = np.poly1d(z)
            trend_line = p(time_numeric)
            fig.add_trace(go.Scatter(
                x=resampled.index,
                y=trend_line,
                mode='lines',
                name='Linear Trend',
                line=dict(color='red', dash='dash', width=2)
            ))
            
            # Add confidence bands (±1 std)
            std_dev = resampled[value_column].std()
            mean_val = resampled[value_column].mean()
            
            fig.add_trace(go.Scatter(
                x=resampled.index,
                y=mean_val + std_dev,
                mode='lines',
                showlegend=False,
                line=dict(width=0),
                hoverinfo='skip'
            ))
            
            fig.add_trace(go.Scatter(
                x=resampled.index,
                y=mean_val - std_dev,
                mode='lines',
                name='Confidence Band',
                fill='tonexty',
                line=dict(width=0),
                fillcolor='rgba(31, 119, 180, 0.2)'
            ))
            
            fig.update_layout(
                title=f"Time Series Trend: {value_column}",
                xaxis_title="Time",
                yaxis_title=value_column,
                hovermode='x unified',
                height=400,
                template='plotly_white'
            )
            
            # Create narrative
            pct_change = ((end_value - start_value) / abs(start_value)) * 100 if start_value != 0 else 0
            narrative = f"{value_column} shows a {trend_direction} trend over the analyzed period. "
            narrative += f"Starting at {start_value:.2f}, it moved to {end_value:.2f} ({pct_change:+.1f}%). "
            narrative += f"Volatility level is {volatility:.2f}, with {abs(correlation):.2f} correlation to time."
            
            return ToolResult(
                success=True,
                data={
                    "start_value": start_value,
                    "end_value": end_value,
                    "trend_direction": trend_direction,
                    "pct_change": pct_change,
                    "volatility": volatility,
                    "correlation": correlation,
                    "periods": len(resampled),
                    "frequency": freq
                },
                display=self.create_chart_spec(
                    chart_type="line",
                    data={"values": resampled[value_column].tolist(), "dates": resampled.index.strftime("%Y-%m-%d").tolist()},
                    title=f"Time Series Trend: {value_column}",
                    x_label="Time",
                    y_label=value_column
                ),
                confidence=0.85
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Time series analysis failed: {str(e)}"
            )
