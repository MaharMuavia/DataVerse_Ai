"""Visualization agent using Plotly for interactive charts.

This agent generates visualizations based on:
- User intent (parsed from query)
- Data types in the dataset
- Visualization type selected by planning agent

Supported visualizations:
- Histogram (univariate distributions)
- Boxplot (outliers and ranges)
- Scatter plot (bivariate relationships)
- Bar chart (categorical aggregations)
- Heatmap (correlation matrix)

Returns Plotly JSON specifications for frontend rendering.
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from ..core.logger import logger
from ..data.data_manager import DataManager


class VisualizationAgent:
    """Generates interactive plots using Plotly.

    This agent creates publication-quality visualizations from data,
    returning Plotly JSON specifications for frontend rendering.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = logger.getChild(self.__class__.__name__)

    def run(self, viz_type: str, target_column: Optional[str] = None, numeric_cols: Optional[List[str]] = None, categorical_cols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate visualization.

        Args:
            viz_type: Type of visualization (histogram, boxplot, scatter, bar_chart, heatmap)
            target_column: Primary column to visualize
            numeric_cols: List of numeric columns to consider
            categorical_cols: List of categorical columns to consider

        Returns:
            Dict with visualization metadata and Plotly JSON spec
        """
        if not PLOTLY_AVAILABLE:
            return {"error": "Plotly not available", "status": "failed"}

        try:
            dm = DataManager(session_id=self.session_id)
            df = dm.get_raw()
        except Exception as e:
            self.logger.error(f"Failed to load dataset: {e}")
            return {"error": str(e), "status": "failed"}

        self.logger.info(f"Generating {viz_type} visualization", extra={"session_id": self.session_id})

        try:
            if viz_type == "histogram":
                result = self._create_histogram(df, target_column, numeric_cols)
            elif viz_type == "boxplot":
                result = self._create_boxplot(df, target_column, numeric_cols)
            elif viz_type == "scatter":
                result = self._create_scatter(df, numeric_cols)
            elif viz_type == "bar_chart":
                result = self._create_bar_chart(df, target_column, categorical_cols)
            elif viz_type == "heatmap":
                result = self._create_heatmap(df, numeric_cols)
            else:
                return {"error": f"Unknown visualization type: {viz_type}", "status": "failed"}

            self.logger.info(f"{viz_type} visualization created successfully", extra={"session_id": self.session_id})
            return result

        except Exception as e:
            self.logger.exception(f"Failed to create {viz_type} visualization")
            return {"error": str(e), "status": "failed"}

    def _create_histogram(self, df: pd.DataFrame, target_column: Optional[str], numeric_cols: Optional[List[str]]) -> Dict[str, Any]:
        """Create histogram for numeric distribution."""
        # Select column to plot
        plot_col = target_column if target_column and target_column in df.columns else (numeric_cols[0] if numeric_cols else df.select_dtypes(include=['number']).columns[0])

        col_data = df[plot_col].dropna()

        # Create Plotly histogram
        fig = px.histogram(
            df,
            x=plot_col,
            title=f'Distribution of {plot_col}',
            labels={plot_col: plot_col, 'count': 'Frequency'},
            opacity=0.7
        )

        # Add mean and median lines
        mean_val = col_data.mean()
        median_val = col_data.median()

        fig.add_vline(
            x=mean_val,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Mean: {mean_val:.2f}",
            annotation_position="top right"
        )
        fig.add_vline(
            x=median_val,
            line_dash="dash",
            line_color="green",
            annotation_text=f"Median: {median_val:.2f}",
            annotation_position="top left"
        )

        return {
            "viz_type": "histogram",
            "column": plot_col,
            "chart_spec": fig.to_json(),
            "statistics": {
                "mean": float(mean_val),
                "median": float(median_val),
                "std": float(col_data.std()),
                "count": int(len(col_data)),
            }
        }

    def _create_boxplot(self, df: pd.DataFrame, target_column: Optional[str], numeric_cols: Optional[List[str]]) -> Dict[str, Any]:
        """Create boxplot for outlier visualization."""
        # Select columns to plot
        cols_to_plot = numeric_cols if numeric_cols else df.select_dtypes(include=['number']).columns.tolist()
        cols_to_plot = cols_to_plot[:5]  # Limit to 5 columns

        # Melt dataframe for Plotly boxplot
        melted_df = df[cols_to_plot].melt(var_name='Variable', value_name='Value')

        fig = px.box(
            melted_df,
            x='Variable',
            y='Value',
            title='Distribution and Outliers',
            color='Variable'
        )

        return {
            "viz_type": "boxplot",
            "columns": cols_to_plot,
            "chart_spec": fig.to_json(),
            "message": f"Boxplot created for {len(cols_to_plot)} numeric columns"
        }

    def _create_scatter(self, df: pd.DataFrame, numeric_cols: Optional[List[str]]) -> Dict[str, Any]:
        """Create scatter plot for bivariate relationships."""
        numeric_df = df.select_dtypes(include=['number'])
        cols_to_plot = numeric_cols if numeric_cols else numeric_df.columns.tolist()

        if len(cols_to_plot) < 2:
            cols_to_plot = numeric_df.columns.tolist()[:2]

        x_col, y_col = cols_to_plot[0], cols_to_plot[1]

        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            title=f'Relationship: {x_col} vs {y_col}',
            opacity=0.6
        )

        # Add correlation coefficient as annotation
        correlation = df[x_col].corr(df[y_col])
        fig.add_annotation(
            text=f"Correlation: {correlation:.3f}",
            xref="paper", yref="paper",
            x=0.05, y=0.95,
            showarrow=False,
            bgcolor="wheat",
            opacity=0.8
        )

        return {
            "viz_type": "scatter",
            "x_column": x_col,
            "y_column": y_col,
            "correlation": float(correlation),
            "chart_spec": fig.to_json(),
        }

    def _create_bar_chart(self, df: pd.DataFrame, target_column: Optional[str], categorical_cols: Optional[List[str]]) -> Dict[str, Any]:
        """Create bar chart for categorical analysis."""
        # Select column to plot
        plot_col = target_column if target_column and target_column in df.columns else (categorical_cols[0] if categorical_cols else df.select_dtypes(include=['object', 'category']).columns[0])

        value_counts = df[plot_col].value_counts().head(10).reset_index()
        value_counts.columns = [plot_col, 'count']

        fig = px.bar(
            value_counts,
            x=plot_col,
            y='count',
            title=f'Top Values in {plot_col}',
            text='count'
        )

        fig.update_traces(textposition='outside')
        fig.update_layout(xaxis_tickangle=-45)

        return {
            "viz_type": "bar_chart",
            "column": plot_col,
            "top_values": value_counts.set_index(plot_col)['count'].to_dict(),
            "chart_spec": fig.to_json(),
        }

    def _create_heatmap(self, df: pd.DataFrame, numeric_cols: Optional[List[str]]) -> Dict[str, Any]:
        """Create correlation heatmap."""
        numeric_df = df.select_dtypes(include=['number'])
        if numeric_df.shape[1] < 2:
            return {"error": "Insufficient numeric columns for heatmap", "status": "skipped"}

        corr_matrix = numeric_df.corr()

        fig = px.imshow(
            corr_matrix,
            text_auto=True,
            title='Correlation Matrix',
            color_continuous_scale='RdBu_r',
            zmin=-1,
            zmax=1
        )

        # Extract high correlations
        high_corrs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.7:
                    high_corrs.append({
                        "var1": corr_matrix.columns[i],
                        "var2": corr_matrix.columns[j],
                        "correlation": float(corr_val),
                    })

        return {
            "viz_type": "heatmap",
            "chart_spec": fig.to_json(),
            "high_correlations": sorted(high_corrs, key=lambda x: abs(x["correlation"]), reverse=True),
        }
