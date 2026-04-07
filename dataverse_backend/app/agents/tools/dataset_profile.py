from .base_tool import BaseTool
from ..core.tool_registry import SessionContext, ToolResult
import pandas as pd
from typing import Dict, Any


class DatasetProfileTool(BaseTool):
    """Tool for getting dataset profile information."""

    def __init__(self):
        super().__init__()
        self.name = "dataset_profile"
        self.description = """Returns schema, dtypes, row count, memory usage, sample rows.
USE WHEN: User asks for overview, summary, or profile of the dataset."""
        self.input_schema = {
            "n_sample_rows": {
                "type": "integer",
                "description": "Number of sample rows to return (default: 5)",
                "default": 5
            }
        }
        self.output_schema = {
            "description": "TableSpec with dataset profile information"
        }

    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        try:
            df = self.load_dataset(session)
            n_samples = params.get("n_sample_rows", 5)

            # Get basic info
            profile_data = {
                "rows": len(df),
                "columns": len(df.columns),
                "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
                "columns_info": []
            }

            # Column information
            for col in df.columns:
                col_info = {
                    "name": col,
                    "dtype": str(df[col].dtype),
                    "non_null_count": df[col].count(),
                    "null_count": df[col].isnull().sum(),
                    "unique_count": df[col].nunique()
                }

                # Add type-specific info
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_info.update({
                        "min": float(df[col].min()) if not df[col].empty else None,
                        "max": float(df[col].max()) if not df[col].empty else None,
                        "mean": float(df[col].mean()) if not df[col].empty else None
                    })
                elif pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                    col_info["most_common"] = df[col].mode().iloc[0] if not df[col].mode().empty else None

                profile_data["columns_info"].append(col_info)

            # Sample rows
            sample_rows = df.head(n_samples).to_dict('records')

            # Create table data
            table_data = [
                {"metric": "Total Rows", "value": profile_data["rows"]},
                {"metric": "Total Columns", "value": profile_data["columns"]},
                {"metric": "Memory Usage (MB)", "value": f"{profile_data['memory_usage_mb']:.2f}"}
            ]

            # Add column details
            for col_info in profile_data["columns_info"]:
                table_data.append({
                    "metric": f"Column '{col_info['name']}'",
                    "value": f"Type: {col_info['dtype']}, Non-null: {col_info['non_null_count']}, Unique: {col_info['unique_count']}"
                })

            table_spec = self.create_table_spec(
                columns=["metric", "value"],
                data=table_data,
                title="Dataset Profile"
            )

            return ToolResult(
                success=True,
                data={
                    "profile": profile_data,
                    "sample_rows": sample_rows
                },
                display=table_spec
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0
            )