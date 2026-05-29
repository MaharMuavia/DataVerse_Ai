"""Dataset profiling tasks using Ydata Profiling.

Generates comprehensive data profiles including distributions, correlations,
missing values analysis, and data quality metrics.
"""
from celery import shared_task
import io
import os
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _load_dataframe(file_path: str, nrows: int | None = None) -> pd.DataFrame:
    """Load a dataset from local path or configured storage provider."""

    def _read(source):
        lower_path = file_path.lower()
        if lower_path.endswith('.csv'):
            return pd.read_csv(source, nrows=nrows)
        if lower_path.endswith(('.xlsx', '.xls')):
            return pd.read_excel(source, nrows=nrows)
        if lower_path.endswith('.json'):
            df = pd.read_json(source)
            return df.head(nrows) if nrows else df
        if lower_path.endswith('.parquet'):
            df = pd.read_parquet(source)
            return df.head(nrows) if nrows else df
        return pd.read_csv(source, nrows=nrows)

    if os.path.exists(file_path):
        return _read(file_path)

    from ..core.storage import get_storage

    raw_bytes = get_storage().download(file_path)
    return _read(io.BytesIO(raw_bytes))


@shared_task(name="tasks.profile_dataset.profile", bind=True, queue="slow")
def profile_dataset_task(self, dataset_id: str, file_path: str) -> Dict[str, Any]:
    """
    Profile a dataset using Ydata Profiling.
    
    Args:
        dataset_id: Dataset ID in database
        file_path: Path to dataset file
        
    Returns:
        Dictionary with profiling results
    """
    try:
        logger.info(f"[ProfileTask] Starting profile for dataset {dataset_id}")
        self.update_state(state='PROGRESS', meta={'status': 'Loading data'})
        
        # Read dataset (local path or object storage key)
        df = _load_dataframe(file_path)
        logger.info(f"[ProfileTask] Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Basic statistics
        profile_data = {
            "dataset_id": dataset_id,
            "timestamp": datetime.utcnow().isoformat(),
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": list(df.columns),
            "dtypes": {col: str(df[col].dtype) for col in df.columns},
        }
        
        self.update_state(state='PROGRESS', meta={'status': 'Computing statistics'})
        
        # Numeric statistics
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            profile_data["numeric_stats"] = {}
            for col in numeric_cols:
                profile_data["numeric_stats"][col] = {
                    "mean": float(df[col].mean()),
                    "median": float(df[col].median()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "25%": float(df[col].quantile(0.25)),
                    "50%": float(df[col].quantile(0.50)),
                    "75%": float(df[col].quantile(0.75)),
                    "missing": int(df[col].isnull().sum()),
                    "missing_pct": float(df[col].isnull().sum() / len(df) * 100),
                }
        
        # Categorical statistics
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        if categorical_cols:
            profile_data["categorical_stats"] = {}
            for col in categorical_cols[:5]:  # Limit to first 5
                value_counts = df[col].value_counts().head(10).to_dict()
                profile_data["categorical_stats"][col] = {
                    "unique_count": len(df[col].unique()),
                    "top_values": value_counts,
                    "missing": int(df[col].isnull().sum()),
                    "missing_pct": float(df[col].isnull().sum() / len(df) * 100),
                }
        
        # Correlations (if numeric columns exist)
        if len(numeric_cols) > 1:
            self.update_state(state='PROGRESS', meta={'status': 'Computing correlations'})
            
            corr_matrix = df[numeric_cols].corr()
            # Convert correlation matrix to dict
            profile_data["correlations"] = {
                f"{col1}_{col2}": float(corr_matrix[col2][col1])
                for col1 in numeric_cols
                for col2 in numeric_cols
                if col1 != col2
            }
        
        # Data quality metrics
        profile_data["data_quality"] = {
            "total_cells": len(df) * len(df.columns),
            "missing_cells": int(df.isnull().sum().sum()),
            "missing_pct": float(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100),
            "duplicate_rows": int(df.duplicated().sum()),
            "duplicate_pct": float(df.duplicated().sum() / len(df) * 100),
        }
        
        self.update_state(state='PROGRESS', meta={'status': 'Complete'})
        
        logger.info(f"[ProfileTask] Profile complete for dataset {dataset_id}")
        
        # Return result
        return {
            "status": "success",
            "dataset_id": dataset_id,
            "profile": profile_data,
        }
        
    except Exception as e:
        logger.error(f"[ProfileTask] Error profiling dataset {dataset_id}: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        return {
            "status": "error",
            "dataset_id": dataset_id,
            "error": str(e),
        }


@shared_task(name="tasks.compute_stats.quick", bind=True, queue="fast")
def compute_quick_stats(self, dataset_id: str, file_path: str) -> Dict[str, Any]:
    """
    Compute quick statistics for a dataset (milliseconds).
    
    Used for immediate feedback after upload.
    """
    try:
        df = _load_dataframe(file_path, nrows=1000)  # Sample first 1000 rows
        
        return {
            "dataset_id": dataset_id,
            "rows": len(df),
            "cols": len(df.columns),
            "memory_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
        }
    except Exception as e:
        logger.error(f"[QuickStats] Error: {e}")
        return {"error": str(e)}
