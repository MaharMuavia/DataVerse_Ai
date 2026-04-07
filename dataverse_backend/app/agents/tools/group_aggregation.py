"""
Group Aggregation Tool

Performs GROUP BY equivalent operations with multiple aggregation methods,
useful for segment analysis and comparative statistics.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
import plotly.graph_objects as go

from .base_tool import BaseTool
from ..core.tool_registry import ToolResult, TableSpec, ChartSpec, SessionContext


class GroupAggregationTool(BaseTool):
    """
    Perform GROUP BY aggregations on dataset.
    
    Supports:
    1. Single or multiple grouping columns
    2. Multiple aggregation functions per column
    3. Sorting and limiting results
    4. Visualization of aggregated data
    """
    
    @property
    def name(self) -> str:
        return "group_aggregation"
    
    @property
    def description(self) -> str:
        return """
        Group data and compute aggregate statistics.
        Equivalent to SQL GROUP BY with multiple aggregations.
        
        Params:
        - group_columns: list[str] - Column(s) to group by
        - agg_column: str - Numeric column to aggregate
        - agg_functions: list[str] - Functions to apply ('sum', 'mean', 'count', 'min', 'max', default=['mean'])
        - sort_by: str (optional) - Column to sort by (default is first group column)
        - limit: int (optional) - Max rows to return (default=None, all rows)
        """
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "group_columns": "list[str]",
            "agg_column": "str",
            "agg_functions": "list[str] (default=['mean'])",
            "sort_by": "str (optional)",
            "limit": "int (optional)"
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "group_count": "int - number of groups",
            "aggregations": "dict - results by group",
            "table": "Pandas-like table display",
            "chart": "Bar chart of aggregations"
        }
    
    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        """Execute group aggregation."""
        try:
            # Load dataset
            df = self.load_dataset(session)
            
            group_columns = params.get("group_columns", [])
            agg_column = params.get("agg_column")
            agg_functions = params.get("agg_functions", ["mean"])
            sort_by = params.get("sort_by")
            limit = params.get("limit")
            
            # Validate inputs
            if not group_columns:
                return ToolResult(
                    success=False,
                    error_message="group_columns is required (list of column names)"
                )
            
            if not agg_column:
                return ToolResult(
                    success=False,
                    error_message="agg_column is required (numeric column to aggregate)"
                )
            
            # Convert single string to list
            if isinstance(group_columns, str):
                group_columns = [group_columns]
            
            if isinstance(agg_functions, str):
                agg_functions = [agg_functions]
            
            # Validate columns exist
            self.validate_columns_exist(df, group_columns + [agg_column])
            
            # Validate agg_column is numeric
            if not pd.api.types.is_numeric_dtype(df[agg_column]):
                return ToolResult(
                    success=False,
                    error_message=f"{agg_column} must be numeric for aggregation"
                )
            
            # Perform aggregation
            agg_dict = {agg_column: agg_functions}
            grouped = df.groupby(group_columns, as_index=False).agg(agg_dict)
            
            # Flatten column names from MultiIndex
            if isinstance(grouped.columns, pd.MultiIndex):
                grouped.columns = ['_'.join(col).strip('_') for col in grouped.columns.values]
            
            # Sort
            if sort_by and sort_by in grouped.columns:
                grouped = grouped.sort_values(by=sort_by, ascending=False)
            elif len(agg_functions) == 1:
                # Sort by aggregated column
                agg_col_name = f"{agg_column}_{agg_functions[0]}"
                if agg_col_name in grouped.columns:
                    grouped = grouped.sort_values(by=agg_col_name, ascending=False)
            
            # Limit results
            if limit and limit > 0:
                grouped = grouped.head(limit)
            
            group_count = len(grouped)
            
            # Create table display
            table_data = grouped.values.tolist()
            table_cols = grouped.columns.tolist()
            
            # Create visualization (bar chart for first agg function)
            if len(agg_functions) > 0 and group_count > 0:
                display_column = f"{agg_column}_{agg_functions[0]}"
                if display_column not in grouped.columns:
                    display_column = grouped.columns[-1]  # Use last column
                
                group_label = '_'.join(group_columns) if len(group_columns) == 1 else '_'.join(group_columns)
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=grouped[group_label].astype(str) if len(group_columns) == 1 else grouped[group_label].astype(str),
                        y=grouped[display_column],
                        name=display_column
                    )
                ])
                
                fig.update_layout(
                    title=f"Aggregated {agg_column} by {group_label}",
                    xaxis_title=group_label,
                    yaxis_title=display_column,
                    height=400,
                    template='plotly_white',
                    hovermode='closest'
                )
            else:
                fig = None
            
            # Create summary narrative
            total_groups = group_count
            agg_funcs_str = ', '.join(agg_functions)
            narrative = f"Grouped {len(df)} records by {', '.join(group_columns)} into {total_groups} groups. "
            narrative += f"Applied {agg_funcs_str} aggregation to {agg_column}."
            
            if group_count > 0 and len(agg_functions) > 0:
                display_column = f"{agg_column}_{agg_functions[0]}"
                if display_column not in grouped.columns:
                    display_column = grouped.columns[-1]
                
                max_val = grouped[display_column].max()
                min_val = grouped[display_column].min()
                narrative += f" Values range from {min_val:.2f} to {max_val:.2f}."
            
            return ToolResult(
                success=True,
                data={
                    "group_count": total_groups,
                    "groups": grouped.to_dict(orient='records'),
                    "agg_functions": agg_functions,
                    "group_columns": group_columns
                },
                display=self.create_table_spec(
                    columns=table_cols,
                    data=table_data,
                    title=f"Grouped Aggregation: {agg_column} by {', '.join(group_columns)}"
                ),
                confidence=0.90
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Group aggregation failed: {str(e)}"
            )
