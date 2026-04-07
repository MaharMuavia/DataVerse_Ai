import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any
from workflow.state import AnalysisState

async def run_eda_pipeline(state: AnalysisState) -> Dict[str, Any]:
    try:
        # Step 1: Cache check
        if state.get("eda_results") and state["eda_results"]:
            return {}

        # Step 2: Load dataset
        if state["dataset_path"].endswith('.xlsx'):
            df = pd.read_excel(state["dataset_path"])
        else:
            df = pd.read_csv(state["dataset_path"])

        # Step 3: Compute EDA results
        eda_results = {}

        # Shape
        eda_results["shape"] = {"rows": len(df), "cols": len(df.columns)}

        # Dtypes
        eda_results["dtypes"] = df.dtypes.astype(str).to_dict()

        # Missing values
        missing_counts = df.isnull().sum()
        missing_percentages = (missing_counts / len(df) * 100).round(2)
        eda_results["missing"] = {
            "counts": missing_counts.to_dict(),
            "percentages": missing_percentages.to_dict()
        }

        # Descriptive stats
        eda_results["descriptive_stats"] = df.describe(include="all").fillna("").to_dict()

        # Correlation matrix (numeric only)
        numeric_df = df.select_dtypes(include=[np.number])
        if not numeric_df.empty:
            eda_results["correlation_matrix"] = numeric_df.corr().round(3).to_dict()
        else:
            eda_results["correlation_matrix"] = {}

        # Outliers (IQR method for numeric columns)
        outliers = {}
        for col in numeric_df.columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outlier_count = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            outliers[col] = {
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "outlier_count": int(outlier_count)
            }
        eda_results["outliers"] = outliers

        # Categorical distributions
        categorical_distributions = {}
        for col in df.select_dtypes(include=['object', 'category']).columns:
            if df[col].nunique() <= 20:
                categorical_distributions[col] = df[col].value_counts().to_dict()
        eda_results["categorical_distributions"] = categorical_distributions

        # Numeric distributions
        numeric_distributions = {}
        for col in numeric_df.columns:
            numeric_distributions[col] = {
                "mean": float(df[col].mean()),
                "std": float(df[col].std()),
                "skewness": float(stats.skew(df[col].dropna())),
                "kurtosis": float(stats.kurtosis(df[col].dropna()))
            }
        eda_results["numeric_distributions"] = numeric_distributions

        return {"eda_results": eda_results}

    except Exception as e:
        return {"error_message": f"EDA pipeline failed: {str(e)}"}