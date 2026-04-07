"""
Compare Segments Tool

Compares statistics across dataset segments for A/B testing and
comparative segment analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
import plotly.graph_objects as go
from scipy import stats

from .base_tool import BaseTool
from ..core.tool_registry import ToolResult, TableSpec, SessionContext


class CompareSegmentsTool(BaseTool):
    """
    Compare statistics across different segments.
    
    Supports:
    1. A/B comparison (two segments)
    2. Multiple segment comparison
    3. Statistical significance testing
    4. Multiple metrics across segments
    """
    
    @property
    def name(self) -> str:
        return "compare_segments"
    
    @property
    def description(self) -> str:
        return """
        Compare statistics across dataset segments.
        Useful for A/B testing, cohort comparison, and segment analysis.
        
        Params:
        - segment_column: str - Column defining segments
        - segment_values: list[str] - Values to compare (e.g., ['A', 'B'])
        - metric_columns: list[str] - Numeric columns to compare stats for
        - test_type: str (optional) - Statistical test ('ttest', 'mannwhitney', default='ttest')
        """
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "segment_column": "str",
            "segment_values": "list[str] (values to compare)",
            "metric_columns": "list[str] (numeric columns)",
            "test_type": "str (optional, 'ttest' or 'mannwhitney')"
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "comparison": {
                "segment1": "dict of statistics",
                "segment2": "dict of statistics",
                "difference": "dict of differences",
                "pvalue": "float - statistical significance",
                "significant": "bool - p < 0.05"
            },
            "table": "Comparison table"
        }
    
    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        """Execute segment comparison."""
        try:
            # Load dataset
            df = self.load_dataset(session)
            
            segment_column = params.get("segment_column")
            segment_values = params.get("segment_values", [])
            metric_columns = params.get("metric_columns", [])
            test_type = params.get("test_type", "ttest")
            
            # Validate inputs
            if not segment_column:
                return ToolResult(
                    success=False,
                    error_message="segment_column is required"
                )
            
            if not metric_columns:
                return ToolResult(
                    success=False,
                    error_message="metric_columns is required (list of numeric columns)"
                )
            
            if len(segment_values) < 2:
                return ToolResult(
                    success=False,
                    error_message="segment_values must have at least 2 values to compare"
                )
            
            # Validate columns exist
            self.validate_columns_exist(df, [segment_column] + metric_columns)
            
            # Validate metric columns are numeric
            for col in metric_columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    return ToolResult(
                        success=False,
                        error_message=f"{col} must be numeric"
                    )
            
            # Filter to specified segment values
            segment_data = df[df[segment_column].isin(segment_values)]
            
            if len(segment_data) == 0:
                return ToolResult(
                    success=False,
                    error_message=f"No data found for segment values: {segment_values}"
                )
            
            # Split segments
            segments = {}
            for value in segment_values[:2]:  # Compare first 2 segments
                segments[value] = segment_data[segment_data[segment_column] == value]
            
            # Build comparison
            comparison_rows = []
            
            for metric in metric_columns:
                # Get statistics for each segment
                stats_dict = {"metric": metric}
                
                for seg_name, seg_data in segments.items():
                    metric_values = seg_data[metric].dropna()
                    stats_dict[f"{seg_name}_count"] = len(metric_values)
                    stats_dict[f"{seg_name}_mean"] = metric_values.mean()
                    stats_dict[f"{seg_name}_std"] = metric_values.std()
                    stats_dict[f"{seg_name}_median"] = metric_values.median()
                    stats_dict[f"{seg_name}_min"] = metric_values.min()
                    stats_dict[f"{seg_name}_max"] = metric_values.max()
                
                # Perform statistical test
                seg1_values = segments[segment_values[0]][metric].dropna()
                seg2_values = segments[segment_values[1]][metric].dropna()
                
                if len(seg1_values) > 1 and len(seg2_values) > 1:
                    if test_type == "mannwhitney":
                        stat, pvalue = stats.mannwhitneyu(seg1_values, seg2_values)
                    else:  # ttest (default)
                        stat, pvalue = stats.ttest_ind(seg1_values, seg2_values)
                    
                    stats_dict["p_value"] = pvalue
                    stats_dict["significant"] = pvalue < 0.05
                    stats_dict["difference"] = seg1_values.mean() - seg2_values.mean()
                else:
                    stats_dict["p_value"] = None
                    stats_dict["significant"] = False
                    stats_dict["difference"] = None
                
                comparison_rows.append(stats_dict)
            
            # Create display table
            table_cols = ["Metric", f"{segment_values[0]} Mean", f"{segment_values[1]} Mean", 
                         "Difference", "P-Value", "Significant"]
            table_data = []
            
            for row in comparison_rows:
                table_data.append([
                    row["metric"],
                    f"{row.get(f'{segment_values[0]}_mean', 0):.2f}",
                    f"{row.get(f'{segment_values[1]}_mean', 0):.2f}",
                    f"{row.get('difference', 0):.2f}" if row.get('difference') else "N/A",
                    f"{row.get('p_value', 0):.4f}" if row.get('p_value') else "N/A",
                    "Yes" if row.get('significant') else "No"
                ])
            
            # Count significant results
            significant_count = sum(1 for row in comparison_rows if row.get('significant', False))
            
            # Create narrative
            seg1_size = len(segments[segment_values[0]])
            seg2_size = len(segments[segment_values[1]])
            
            narrative = f"Compared {segment_values[0]} ({seg1_size} records) vs {segment_values[1]} ({seg2_size} records) "
            narrative += f"on {len(metric_columns)} metrics. Found {significant_count}/{len(metric_columns)} "
            narrative += f"statistically significant differences (p<0.05) using {test_type}."
            
            return ToolResult(
                success=True,
                data={
                    "segment1": segment_values[0],
                    "segment1_count": seg1_size,
                    "segment2": segment_values[1],
                    "segment2_count": seg2_size,
                    "metrics_compared": len(metric_columns),
                    "significant_differences": significant_count,
                    "comparisons": comparison_rows,
                    "test_type": test_type
                },
                display=self.create_table_spec(
                    columns=table_cols,
                    data=table_data,
                    title=f"Segment Comparison: {segment_values[0]} vs {segment_values[1]}"
                ),
                confidence=0.85
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Segment comparison failed: {str(e)}"
            )
