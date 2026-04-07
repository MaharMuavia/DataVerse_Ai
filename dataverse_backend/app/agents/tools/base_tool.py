import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import json
import os
from ..core.tool_registry import Tool, ToolResult, SessionContext, ChartSpec, TableSpec, NarrativeSpec


class BaseTool(Tool):
    """Base class for all tools with common functionality."""

    def __init__(self):
        # Subclasses either populate plain attributes in __init__ or expose
        # them via @property. Avoid assigning defaults here so property-based
        # tools do not fail on instantiation.
        pass

    def load_dataset(self, session: SessionContext) -> pd.DataFrame:
        """Load the appropriate dataset (working or main)."""
        dataset_path = session.working_dataset_path or session.dataset_path

        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")

        # Determine file type and load
        if dataset_path.endswith('.csv'):
            return pd.read_csv(dataset_path)
        elif dataset_path.endswith('.parquet'):
            return pd.read_parquet(dataset_path)
        else:
            raise ValueError(f"Unsupported file format: {dataset_path}")

    def validate_columns_exist(self, df: pd.DataFrame, columns: List[str]) -> None:
        """Validate that columns exist in the dataframe."""
        missing = [col for col in columns if col not in df.columns]
        if missing:
            raise ValueError(f"Columns not found in dataset: {missing}")

    def create_chart_spec(
        self,
        chart_type: str,
        data: Dict[str, Any],
        title: str,
        **kwargs
    ) -> ChartSpec:
        """Create a chart specification."""
        return ChartSpec(
            type=chart_type,
            data=data,
            title=title,
            **kwargs
        )

    def create_table_spec(
        self,
        columns: List[str],
        data: List[Dict[str, Any]],
        title: str
    ) -> TableSpec:
        """Create a table specification."""
        return TableSpec(
            columns=columns,
            data=data,
            title=title
        )

    def create_narrative_spec(self, content: str, tone: str = "professional") -> NarrativeSpec:
        """Create a narrative specification."""
        return NarrativeSpec(content=content, tone=tone)
