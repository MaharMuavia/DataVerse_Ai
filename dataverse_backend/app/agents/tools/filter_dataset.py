from .base_tool import BaseTool
from ..core.tool_registry import SessionContext, ToolResult
import pandas as pd
from typing import Dict, Any, List
import os
from ..core.intent_extractor import FilterCondition


class FilterDatasetTool(BaseTool):
    """Tool for applying filters to create a working dataset."""

    def __init__(self):
        super().__init__()
        self.name = "filter_dataset"
        self.description = """Apply row filters for downstream analysis.
USE WHEN: User wants to focus analysis on specific data subsets."""
        self.input_schema = {
            "conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "operator": {"type": "string", "enum": ["eq", "neq", "gt", "lt", "gte", "lte", "in", "contains"]},
                        "value": {"type": "string"}
                    }
                },
                "description": "List of filter conditions to apply"
            }
        }
        self.output_schema = {
            "description": "DatasetRef to filtered dataset"
        }

    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        try:
            df = self.load_dataset(session)
            conditions = params.get("conditions", [])

            if not conditions:
                return ToolResult(
                    success=False,
                    data={},
                    error_message="No filter conditions provided",
                    confidence=0.0
                )

            # Apply filters
            filtered_df = df.copy()
            for condition in conditions:
                col = condition["column"]
                op = condition["operator"]
                val = condition["value"]

                self.validate_columns_exist(filtered_df, [col])

                if op == "eq":
                    filtered_df = filtered_df[filtered_df[col] == val]
                elif op == "neq":
                    filtered_df = filtered_df[filtered_df[col] != val]
                elif op == "gt":
                    filtered_df = filtered_df[pd.to_numeric(filtered_df[col], errors='coerce') > float(val)]
                elif op == "lt":
                    filtered_df = filtered_df[pd.to_numeric(filtered_df[col], errors='coerce') < float(val)]
                elif op == "gte":
                    filtered_df = filtered_df[pd.to_numeric(filtered_df[col], errors='coerce') >= float(val)]
                elif op == "lte":
                    filtered_df = filtered_df[pd.to_numeric(filtered_df[col], errors='coerce') <= float(val)]
                elif op == "in":
                    values = [v.strip() for v in val.split(",")]
                    filtered_df = filtered_df[filtered_df[col].isin(values)]
                elif op == "contains":
                    filtered_df = filtered_df[filtered_df[col].str.contains(val, case=False, na=False)]

            # Save filtered dataset
            base_path = os.path.splitext(session.dataset_path)[0]
            filtered_path = f"{base_path}_filtered_{session.session_id}.parquet"
            filtered_df.to_parquet(filtered_path)

            result_data = {
                "original_rows": len(df),
                "filtered_rows": len(filtered_df),
                "dataset_ref": filtered_path,
                "applied_filters": conditions
            }

            return ToolResult(
                success=True,
                data=result_data,
                display=self.create_narrative_spec(
                    f"Applied {len(conditions)} filter(s). Dataset reduced from {len(df)} to {len(filtered_df)} rows.",
                    "professional"
                )
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0
            )