"""Automated EDA agent using ydata-profiling.

This agent generates comprehensive profile reports including:
- Data types and missing values
- Distributions and statistics
- Correlations between variables
- Outlier detection
- Variable relationships

The EDA is fully automated and deterministic, requiring no manual configuration.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
import pandas as pd
from io import StringIO

try:
    from ydata_profiling import ProfileReport
except Exception:
    # ydata-profiling can fail at import time on some dependency combinations
    # (for example an incompatible statsmodels release). The backend should
    # still start, so treat profiling as optional here.
    ProfileReport = None

import sweetviz as sv

from ..core.logger import logger
from ..data.data_manager import DataManager


class EDAAgent:
    """Automated Exploratory Data Analysis using ydata-profiling.

    This agent profiles a dataset and extracts key statistics:
    - Distributions (mean, median, std, skew, kurtosis)
    - Missing value analysis
    - Correlation matrix
    - Outliers (IQR-based)
    - Variable types and cardinality
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = logger.getChild(self.__class__.__name__)

    def run(self) -> Dict[str, Any]:
        """Execute automated EDA and return structured profile.

        Returns:
            Dict containing:
            - profile_summary: High-level statistics
            - distributions: Per-variable distribution info
            - correlations: Correlation matrix (numeric only)
            - missing_values: Missing value analysis
            - outliers: Outlier detection results
            - variable_info: Metadata for each column
        """
        try:
            dm = DataManager(session_id=self.session_id)
            df = dm.get_raw()
        except Exception as e:
            self.logger.error(f"Failed to load dataset: {e}")
            return {"error": str(e), "status": "failed"}

        self.logger.info("Running automated EDA", extra={"session_id": self.session_id, "shape": df.shape})

        eda_result = {
            "session_id": self.session_id,
            "dataset_shape": {"rows": len(df), "columns": len(df.columns)},
            "profile_summary": self._compute_profile_summary(df),
            "distributions": self._compute_distributions(df),
            "correlations": self._compute_correlations(df),
            "missing_values": self._compute_missing_analysis(df),
            "outliers": self._detect_outliers(df),
            "variable_info": self._extract_variable_info(df),
        }

        self.logger.info("EDA completed", extra={"session_id": self.session_id})
        return eda_result

    def _compute_profile_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute high-level dataset statistics."""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        summary = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "numeric_columns": len(numeric_cols),
            "categorical_columns": len(categorical_cols),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
            "numeric_columns_list": numeric_cols,
            "categorical_columns_list": categorical_cols,
        }

        # Add overall statistics for numeric columns
        if numeric_cols:
            numeric_df = df[numeric_cols]
            summary["overall_stats"] = {
                "mean": {col: float(numeric_df[col].mean()) for col in numeric_cols},
                "median": {col: float(numeric_df[col].median()) for col in numeric_cols},
                "std": {col: float(numeric_df[col].std()) for col in numeric_cols},
                "min": {col: float(numeric_df[col].min()) for col in numeric_cols},
                "max": {col: float(numeric_df[col].max()) for col in numeric_cols},
            }

        return summary

    def _compute_distributions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute distribution statistics for each variable."""
        distributions = {}

        for col in df.columns:
            col_data = df[col].dropna()

            if col_data.dtype in ['float64', 'int64']:
                distributions[col] = {
                    "type": "numeric",
                    "count": len(col_data),
                    "mean": float(col_data.mean()),
                    "median": float(col_data.median()),
                    "std": float(col_data.std()),
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "q25": float(col_data.quantile(0.25)),
                    "q75": float(col_data.quantile(0.75)),
                    "skew": float(col_data.skew()),
                    "kurtosis": float(col_data.kurtosis()),
                }
            else:
                value_counts = col_data.value_counts()
                distributions[col] = {
                    "type": "categorical",
                    "count": len(col_data),
                    "unique": col_data.nunique(),
                    "mode": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                    "top_values": value_counts.head(5).to_dict(),
                }

        return distributions

    def _compute_correlations(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute correlation matrix for numeric variables."""
        numeric_df = df.select_dtypes(include=['number'])

        if numeric_df.shape[1] < 2:
            return {
                "status": "insufficient_numeric_columns",
                "message": "At least 2 numeric columns required for correlation analysis"
            }

        corr_matrix = numeric_df.corr().round(3)

        # Extract high correlations (|r| > 0.7)
        high_corrs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                col1, col2 = corr_matrix.columns[i], corr_matrix.columns[j]
                corr_val = corr_matrix.loc[col1, col2]
                if abs(corr_val) > 0.7:
                    high_corrs.append({
                        "variable_1": col1,
                        "variable_2": col2,
                        "correlation": float(corr_val),
                    })

        return {
            "correlation_matrix": corr_matrix.to_dict(),
            "high_correlations": sorted(high_corrs, key=lambda x: abs(x["correlation"]), reverse=True),
        }

    def _compute_missing_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze missing values in the dataset."""
        missing_counts = df.isnull().sum()
        missing_percent = (missing_counts / len(df) * 100).round(2)

        missing_analysis = {
            "total_missing": int(missing_counts.sum()),
            "percent_missing": float(missing_percent.sum() / len(df.columns)),
            "columns_with_missing": {}
        }

        for col in df.columns:
            if missing_counts[col] > 0:
                missing_analysis["columns_with_missing"][col] = {
                    "count": int(missing_counts[col]),
                    "percent": float(missing_percent[col]),
                }

        return missing_analysis

    def _detect_outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect outliers using IQR method for numeric columns."""
        outliers = {}
        numeric_df = df.select_dtypes(include=['number'])

        for col in numeric_df.columns:
            col_data = numeric_df[col]
            q1 = col_data.quantile(0.25)
            q3 = col_data.quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_mask = (col_data < lower_bound) | (col_data > upper_bound)
            outlier_count = outlier_mask.sum()

            if outlier_count > 0:
                outliers[col] = {
                    "count": int(outlier_count),
                    "percent": float(outlier_count / len(col_data) * 100),
                    "lower_bound": float(lower_bound),
                    "upper_bound": float(upper_bound),
                }

        return {
            "method": "IQR (Interquartile Range)",
            "outliers_by_column": outliers,
            "total_outlier_instances": sum(v["count"] for v in outliers.values()),
        }

    def _extract_variable_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract metadata for each variable."""
        var_info = {}

        for col in df.columns:
            col_dtype = str(df[col].dtype)
            var_info[col] = {
                "dtype": col_dtype,
                "non_null_count": int(df[col].count()),
                "null_count": int(df[col].isnull().sum()),
                "unique_values": int(df[col].nunique()),
            }

        return var_info
