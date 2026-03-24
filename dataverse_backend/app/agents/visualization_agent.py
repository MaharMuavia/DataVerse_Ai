"""Visualization agent using Matplotlib and Seaborn.

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
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # non-GUI backend for server-side rendering
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from ..core.logger import logger
from ..data.data_manager import DataManager


class VisualizationAgent:
    """Generates plots using Matplotlib + Seaborn.

    This agent creates publication-quality visualizations from data,
    with automatic selection of plot types based on data characteristics
    and user intent.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = logger.getChild(self.__class__.__name__)
        # Set style for better-looking plots
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 6)
        plt.rcParams['font.size'] = 10

    def run(self, viz_type: str, target_column: Optional[str] = None, numeric_cols: Optional[List[str]] = None, categorical_cols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate visualization.

        Args:
            viz_type: Type of visualization (histogram, boxplot, scatter, bar_chart, heatmap)
            target_column: Primary column to visualize
            numeric_cols: List of numeric columns to consider
            categorical_cols: List of categorical columns to consider

        Returns:
            Dict with visualization metadata and file path
        """
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
        plt.figure(figsize=(12, 6))

        # Select column to plot
        plot_col = target_column if target_column and target_column in df.columns else (numeric_cols[0] if numeric_cols else df.select_dtypes(include=['number']).columns[0])

        col_data = df[plot_col].dropna()

        plt.hist(col_data, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
        plt.xlabel(plot_col, fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.title(f'Distribution of {plot_col}', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)

        # Add statistics annotations
        mean_val = col_data.mean()
        median_val = col_data.median()
        plt.axvline(mean_val, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f}')
        plt.axvline(median_val, color='green', linestyle='--', linewidth=2, label=f'Median: {median_val:.2f}')
        plt.legend()

        filepath = self._save_plot(f"histogram_{plot_col}")
        return {
            "viz_type": "histogram",
            "column": plot_col,
            "filepath": filepath,
            "statistics": {
                "mean": float(mean_val),
                "median": float(median_val),
                "std": float(col_data.std()),
                "count": int(len(col_data)),
            }
        }

    def _create_boxplot(self, df: pd.DataFrame, target_column: Optional[str], numeric_cols: Optional[List[str]]) -> Dict[str, Any]:
        """Create boxplot for outlier visualization."""
        plt.figure(figsize=(12, 6))

        # Select columns to plot
        cols_to_plot = numeric_cols if numeric_cols else df.select_dtypes(include=['number']).columns.tolist()
        cols_to_plot = cols_to_plot[:5]  # Limit to 5 columns

        sns.boxplot(data=df[cols_to_plot], palette='Set2')
        plt.ylabel('Value', fontsize=12)
        plt.title('Distribution and Outliers', fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        filepath = self._save_plot("boxplot_multicolumn")
        return {
            "viz_type": "boxplot",
            "columns": cols_to_plot,
            "filepath": filepath,
            "message": f"Boxplot created for {len(cols_to_plot)} numeric columns"
        }

    def _create_scatter(self, df: pd.DataFrame, numeric_cols: Optional[List[str]]) -> Dict[str, Any]:
        """Create scatter plot for bivariate relationships."""
        plt.figure(figsize=(12, 6))

        numeric_df = df.select_dtypes(include=['number'])
        cols_to_plot = numeric_cols if numeric_cols else numeric_df.columns.tolist()

        if len(cols_to_plot) < 2:
            cols_to_plot = numeric_df.columns.tolist()[:2]

        x_col, y_col = cols_to_plot[0], cols_to_plot[1]

        plt.scatter(df[x_col], df[y_col], alpha=0.6, s=50, color='steelblue', edgecolors='black')
        plt.xlabel(x_col, fontsize=12)
        plt.ylabel(y_col, fontsize=12)
        plt.title(f'Relationship: {x_col} vs {y_col}', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)

        # Add correlation coefficient
        correlation = df[x_col].corr(df[y_col])
        plt.text(0.05, 0.95, f'Correlation: {correlation:.3f}', transform=plt.gca().transAxes, fontsize=11, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        filepath = self._save_plot(f"scatter_{x_col}_vs_{y_col}")
        return {
            "viz_type": "scatter",
            "x_column": x_col,
            "y_column": y_col,
            "correlation": float(correlation),
            "filepath": filepath,
        }

    def _create_bar_chart(self, df: pd.DataFrame, target_column: Optional[str], categorical_cols: Optional[List[str]]) -> Dict[str, Any]:
        """Create bar chart for categorical analysis."""
        plt.figure(figsize=(12, 6))

        # Select column to plot
        plot_col = target_column if target_column and target_column in df.columns else (categorical_cols[0] if categorical_cols else df.select_dtypes(include=['object', 'category']).columns[0])

        value_counts = df[plot_col].value_counts().head(10)

        bars = plt.bar(range(len(value_counts)), value_counts.values, color='steelblue', edgecolor='black', alpha=0.7)
        plt.xticks(range(len(value_counts)), value_counts.index, rotation=45, ha='right')
        plt.ylabel('Count', fontsize=12)
        plt.xlabel(plot_col, fontsize=12)
        plt.title(f'Top Values in {plot_col}', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3, axis='y')

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2., height, f'{int(height)}', ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        filepath = self._save_plot(f"bar_chart_{plot_col}")

        return {
            "viz_type": "bar_chart",
            "column": plot_col,
            "top_values": value_counts.to_dict(),
            "filepath": filepath,
        }

    def _create_heatmap(self, df: pd.DataFrame, numeric_cols: Optional[List[str]]) -> Dict[str, Any]:
        """Create correlation heatmap."""
        plt.figure(figsize=(12, 8))

        numeric_df = df.select_dtypes(include=['number'])
        if numeric_df.shape[1] < 2:
            return {"error": "Insufficient numeric columns for heatmap", "status": "skipped"}

        corr_matrix = numeric_df.corr()

        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', center=0, square=True, linewidths=1, cbar_kws={"shrink": 0.8})
        plt.title('Correlation Matrix', fontsize=14, fontweight='bold')
        plt.tight_layout()

        filepath = self._save_plot("heatmap_correlations")

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
            "filepath": filepath,
            "high_correlations": sorted(high_corrs, key=lambda x: abs(x["correlation"]), reverse=True),
        }

    def _save_plot(self, filename: str) -> str:
        """Save plot to file and return filepath."""
        plots_dir = Path(__file__).parent.parent.parent / "plots"
        plots_dir.mkdir(exist_ok=True)

        # Sanitize filename
        filename = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in filename)
        filepath = plots_dir / f"{self.session_id}_{filename}.png"

        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        return str(filepath)
