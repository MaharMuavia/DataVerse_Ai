"""Dataset profiling utilities.

Profiles provide structured metadata about the dataset and are intended to be consumed by agents.
"""
from __future__ import annotations

import pandas as pd
from typing import Dict, Any, List


class DatasetProfile:
    """Compute dataset metadata and summary statistics.

    This class purposefully avoids heavy computations and external dependencies. It focuses
    on metadata useful for automated decision-making by agents.

    Attributes stored in `profile` are serializable and suitable for logging and storage.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.profile: Dict[str, Any] = {}

    def compute_profile(self) -> None:
        """Populate the profile with key metadata."""
        df = self.df
        self.profile["rows"] = int(df.shape[0])
        self.profile["columns"] = int(df.shape[1])

        # Data types
        dtypes = df.dtypes.apply(lambda x: str(x)).to_dict()
        self.profile["dtypes"] = dtypes

        # Missing values
        missing = df.isnull().sum().to_dict()
        self.profile["missing_values"] = {k: int(v) for k, v in missing.items()}

        # Column roles heuristic
        roles = {}
        for col in df.columns:
            series = df[col]
            if pd.api.types.is_numeric_dtype(series):
                role = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(series):
                role = "datetime"
            elif pd.api.types.is_bool_dtype(series):
                role = "boolean"
            else:
                # As a heuristic: low cardinality -> categorical
                unique_ratio = series.nunique(dropna=True) / max(1, len(series))
                if unique_ratio < 0.05:
                    role = "categorical"
                else:
                    role = "text"
            roles[col] = role
        self.profile["column_roles"] = roles

    def to_dict(self) -> Dict[str, Any]:
        return self.profile.copy()
