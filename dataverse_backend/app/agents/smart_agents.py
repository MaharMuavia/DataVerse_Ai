"""Smart Agent System for DataVerse AI.

A complete multi-agent system that works locally without external APIs.
Each agent has a specific responsibility and they coordinate through the orchestrator.

Agents:
- ProfilingAgent: Auto-analyzes datasets on upload (schema, stats, quality)
- PreprocessingAgent: Cleans and prepares data (missing values, encoding, outliers)
- AnalystAgent: Handles analytical queries (aggregations, filtering, comparisons)
- MLAgent: Trains models, evaluates, predicts
- XAIAgent: Explains model predictions and feature importance
- VisualizationAgent: Generates chart specifications
- Orchestrator: Routes queries to the right agent(s)
"""
from __future__ import annotations

import re
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    mean_squared_error, mean_absolute_error, r2_score,
    classification_report, confusion_matrix,
)
from sklearn.tree import DecisionTreeClassifier

from ..core.logger import logger
from ..state.session_state import SessionState


# =============================================================================
# Data Classes for Agent Communication
# =============================================================================

@dataclass
class AgentResult:
    """Standard result from any agent."""
    agent_name: str
    status: str  # "success", "error", "partial"
    narrative: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    chart: Optional[Dict[str, Any]] = None
    table: Optional[List[Dict[str, Any]]] = None
    suggestions: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class DataProfile:
    """Complete dataset profile."""
    rows: int = 0
    cols: int = 0
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    datetime_columns: List[str] = field(default_factory=list)
    boolean_columns: List[str] = field(default_factory=list)
    missing_summary: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    column_profiles: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    memory_usage: str = ""


# =============================================================================
# PROFILING AGENT
# =============================================================================

class ProfilingAgent:
    """Automatically profiles a dataset on upload.

    Responsibilities:
    - Detect column types (numeric, categorical, datetime, boolean)
    - Compute descriptive statistics
    - Identify data quality issues
    - Generate a quality score
    - Provide initial insights about the data
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.name = "profiling"

    def run(self, df: pd.DataFrame) -> AgentResult:
        """Profile the dataset and return structured results."""
        try:
            profile = self._build_profile(df)
            narrative = self._generate_narrative(df, profile)
            insights = self._generate_insights(df, profile)

            state = SessionState.get(self.session_id)
            state.set("data_profile", profile.__dict__)
            state.set("profiling_completed", True)

            return AgentResult(
                agent_name="ProfilingAgent",
                status="success",
                narrative=narrative,
                data={
                    "profile": profile.__dict__,
                    "insights": insights,
                },
                suggestions=[
                    "Ask about data quality issues",
                    "Show distributions of numeric columns",
                    "Find correlations between features",
                ],
            )
        except Exception as e:
            logger.exception("ProfilingAgent failed")
            return AgentResult(agent_name="ProfilingAgent", status="error", error=str(e))

    def _build_profile(self, df: pd.DataFrame) -> DataProfile:
        profile = DataProfile()
        profile.rows = len(df)
        profile.cols = len(df.columns)

        # Classify columns
        for col in df.columns:
            dtype = df[col].dtype
            if pd.api.types.is_bool_dtype(dtype):
                profile.boolean_columns.append(col)
            elif pd.api.types.is_numeric_dtype(dtype):
                profile.numeric_columns.append(col)
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                profile.datetime_columns.append(col)
            else:
                # Check if string column is actually a date
                if df[col].dtype == object:
                    try:
                        parsed = pd.to_datetime(df[col], errors='coerce')
                        if parsed.notna().sum() > len(df) * 0.6:
                            profile.datetime_columns.append(col)
                            continue
                    except Exception:
                        pass
                # Check if low-cardinality => categorical
                profile.categorical_columns.append(col)

        # Missing values
        missing = df.isnull().sum()
        missing_pct = (missing / len(df) * 100).round(2)
        profile.missing_summary = {
            "total_missing": int(missing.sum()),
            "total_cells": int(df.size),
            "overall_pct": round(float(missing.sum() / df.size * 100), 2),
            "by_column": {col: {"count": int(missing[col]), "pct": float(missing_pct[col])} for col in df.columns if missing[col] > 0},
        }

        # Statistics for numeric columns
        if profile.numeric_columns:
            stats = df[profile.numeric_columns].describe().T
            profile.statistics = {
                col: {
                    "mean": round(float(stats.loc[col, "mean"]), 4),
                    "std": round(float(stats.loc[col, "std"]), 4),
                    "min": round(float(stats.loc[col, "min"]), 4),
                    "25%": round(float(stats.loc[col, "25%"]), 4),
                    "50%": round(float(stats.loc[col, "50%"]), 4),
                    "75%": round(float(stats.loc[col, "75%"]), 4),
                    "max": round(float(stats.loc[col, "max"]), 4),
                    "skew": round(float(df[col].skew()), 4),
                    "kurtosis": round(float(df[col].kurtosis()), 4),
                }
                for col in profile.numeric_columns
            }

        # Column profiles
        for col in df.columns:
            col_info = {
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "null_pct": round(float(df[col].isnull().sum() / len(df) * 100), 2),
                "unique_count": int(df[col].nunique()),
            }
            if col in profile.numeric_columns:
                col_info["mean"] = round(float(df[col].mean()), 2)
                col_info["std"] = round(float(df[col].std()), 2)
            elif col in profile.categorical_columns:
                top_values = df[col].value_counts().head(5)
                col_info["top_values"] = {str(k): int(v) for k, v in top_values.items()}
            profile.column_profiles[col] = col_info

        # Quality score (0-100)
        completeness = 1 - (missing.sum() / df.size)
        uniqueness_penalty = sum(1 for col in df.columns if df[col].nunique() == 1) / len(df.columns)
        profile.quality_score = round(float(completeness * 100 - uniqueness_penalty * 20), 1)
        profile.memory_usage = f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"

        return profile

    def _generate_narrative(self, df: pd.DataFrame, profile: DataProfile) -> str:
        parts = []
        parts.append(f"**Dataset Profile:** {profile.rows:,} rows × {profile.cols} columns")
        parts.append(f"**Memory:** {profile.memory_usage} | **Quality Score:** {profile.quality_score}/100")
        parts.append("")

        parts.append("**Column Types:**")
        if profile.numeric_columns:
            parts.append(f"- Numeric ({len(profile.numeric_columns)}): {', '.join(profile.numeric_columns[:8])}")
        if profile.categorical_columns:
            parts.append(f"- Categorical ({len(profile.categorical_columns)}): {', '.join(profile.categorical_columns[:8])}")
        if profile.datetime_columns:
            parts.append(f"- Datetime ({len(profile.datetime_columns)}): {', '.join(profile.datetime_columns)}")

        if profile.missing_summary["total_missing"] > 0:
            parts.append("")
            parts.append(f"**Missing Values:** {profile.missing_summary['total_missing']:,} cells ({profile.missing_summary['overall_pct']}%)")
            for col, info in list(profile.missing_summary["by_column"].items())[:5]:
                parts.append(f"  - {col}: {info['count']} ({info['pct']}%)")

        return "\n".join(parts)

    def _generate_insights(self, df: pd.DataFrame, profile: DataProfile) -> List[str]:
        insights = []

        if profile.quality_score >= 90:
            insights.append("Data quality is excellent — minimal cleaning needed.")
        elif profile.quality_score >= 70:
            insights.append("Data quality is good — some missing values should be handled.")
        else:
            insights.append("Data quality needs attention — significant missing values detected.")

        # High cardinality detection
        for col in profile.categorical_columns:
            if df[col].nunique() > len(df) * 0.5:
                insights.append(f"Column '{col}' has very high cardinality ({df[col].nunique()} unique values) — may be an ID column.")

        # Skewness detection
        for col in profile.numeric_columns[:5]:
            skew = abs(df[col].skew())
            if skew > 2:
                insights.append(f"Column '{col}' is highly skewed (skew={df[col].skew():.2f}) — consider log transformation.")

        return insights


# =============================================================================
# PREPROCESSING AGENT
# =============================================================================

class PreprocessingAgent:
    """Cleans and preprocesses data automatically.

    Responsibilities:
    - Handle missing values (imputation strategies)
    - Detect and handle outliers
    - Encode categorical variables
    - Normalize/standardize numeric features
    - Create a clean, ML-ready dataset
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.name = "preprocessing"

    def run(self, df: pd.DataFrame) -> AgentResult:
        """Preprocess the dataset and store the cleaned version."""
        try:
            state = SessionState.get(self.session_id)
            steps_taken = []
            original_shape = df.shape

            # Step 1: Handle missing values
            df_clean, missing_steps = self._handle_missing(df)
            steps_taken.extend(missing_steps)

            # Step 2: Detect outliers
            outlier_info = self._detect_outliers(df_clean)
            if outlier_info["total_outliers"] > 0:
                steps_taken.append(f"Detected {outlier_info['total_outliers']} outliers across {len(outlier_info['columns'])} columns")

            # Step 3: Encode categoricals (for ML-ready version)
            df_encoded, encoding_steps = self._encode_categoricals(df_clean)
            steps_taken.extend(encoding_steps)

            # Store both versions
            state.set("cleaned_dataframe", df_clean)
            state.set("ml_ready_dataframe", df_encoded)
            state.set("preprocessing_completed", True)
            state.set("preprocessing_steps", steps_taken)
            state.set("outlier_info", outlier_info)

            narrative = self._generate_narrative(original_shape, df_clean.shape, steps_taken, outlier_info)

            return AgentResult(
                agent_name="PreprocessingAgent",
                status="success",
                narrative=narrative,
                data={
                    "steps": steps_taken,
                    "original_shape": list(original_shape),
                    "cleaned_shape": list(df_clean.shape),
                    "outliers": outlier_info,
                },
                suggestions=[
                    "Show me the cleaned data statistics",
                    "Train a predictive model",
                    "Show distributions after cleaning",
                ],
            )
        except Exception as e:
            logger.exception("PreprocessingAgent failed")
            return AgentResult(agent_name="PreprocessingAgent", status="error", error=str(e))

    def _handle_missing(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Handle missing values with smart strategies."""
        df = df.copy()
        steps = []

        for col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count == 0:
                continue

            null_pct = null_count / len(df) * 100

            # Drop column if >60% missing
            if null_pct > 60:
                df.drop(columns=[col], inplace=True)
                steps.append(f"Dropped column '{col}' ({null_pct:.1f}% missing)")
                continue

            # Impute based on type
            if pd.api.types.is_numeric_dtype(df[col]):
                if abs(df[col].skew()) > 1:
                    fill_val = df[col].median()
                    df[col].fillna(fill_val, inplace=True)
                    steps.append(f"Filled '{col}' nulls with median ({fill_val:.2f})")
                else:
                    fill_val = df[col].mean()
                    df[col].fillna(fill_val, inplace=True)
                    steps.append(f"Filled '{col}' nulls with mean ({fill_val:.2f})")
            else:
                fill_val = df[col].mode().iloc[0] if not df[col].mode().empty else "Unknown"
                df[col].fillna(fill_val, inplace=True)
                steps.append(f"Filled '{col}' nulls with mode ('{fill_val}')")

        if not steps:
            steps.append("No missing values found — dataset is complete")

        return df, steps

    def _detect_outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect outliers using IQR method."""
        numeric_cols = df.select_dtypes(include=['number']).columns
        outlier_info = {"total_outliers": 0, "columns": {}}

        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outliers = ((df[col] < lower) | (df[col] > upper)).sum()
            if outliers > 0:
                outlier_info["columns"][col] = {
                    "count": int(outliers),
                    "pct": round(float(outliers / len(df) * 100), 2),
                    "lower_bound": round(float(lower), 2),
                    "upper_bound": round(float(upper), 2),
                }
                outlier_info["total_outliers"] += int(outliers)

        return outlier_info

    def _encode_categoricals(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Encode categorical columns for ML."""
        df_encoded = df.copy()
        steps = []

        cat_cols = df_encoded.select_dtypes(include=['object', 'category']).columns

        for col in cat_cols:
            n_unique = df_encoded[col].nunique()
            if n_unique == 2:
                # Binary encode
                le = LabelEncoder()
                df_encoded[col] = le.fit_transform(df_encoded[col].astype(str))
                steps.append(f"Binary encoded '{col}' (2 categories)")
            elif n_unique <= 10:
                # One-hot encode
                dummies = pd.get_dummies(df_encoded[col], prefix=col, drop_first=True)
                df_encoded = pd.concat([df_encoded.drop(columns=[col]), dummies], axis=1)
                steps.append(f"One-hot encoded '{col}' ({n_unique} categories)")
            else:
                # Label encode high cardinality
                le = LabelEncoder()
                df_encoded[col] = le.fit_transform(df_encoded[col].astype(str))
                steps.append(f"Label encoded '{col}' ({n_unique} categories - high cardinality)")

        # Convert datetime columns to numeric features
        dt_cols = df_encoded.select_dtypes(include=['datetime64']).columns
        for col in dt_cols:
            df_encoded[f"{col}_year"] = df_encoded[col].dt.year
            df_encoded[f"{col}_month"] = df_encoded[col].dt.month
            df_encoded[f"{col}_dayofweek"] = df_encoded[col].dt.dayofweek
            df_encoded.drop(columns=[col], inplace=True)
            steps.append(f"Extracted year/month/dayofweek from '{col}'")

        if not steps:
            steps.append("No encoding needed — all columns are already numeric")

        return df_encoded, steps

    def _generate_narrative(self, original_shape, cleaned_shape, steps, outliers) -> str:
        parts = []
        parts.append("**Preprocessing Complete**\n")
        parts.append(f"- Original: {original_shape[0]} rows × {original_shape[1]} columns")
        parts.append(f"- After cleaning: {cleaned_shape[0]} rows × {cleaned_shape[1]} columns")
        parts.append("")
        parts.append("**Steps Taken:**")
        for i, step in enumerate(steps, 1):
            parts.append(f"{i}. {step}")

        if outliers["total_outliers"] > 0:
            parts.append("")
            parts.append(f"**Outliers Detected:** {outliers['total_outliers']} total")
            for col, info in list(outliers["columns"].items())[:5]:
                parts.append(f"  - {col}: {info['count']} outliers ({info['pct']}%)")

        return "\n".join(parts)


# =============================================================================
# ANALYST AGENT (EDA)
# =============================================================================

class AnalystAgent:
    """Handles analytical queries about the data.

    Capabilities:
    - Aggregations (sum, mean, count, etc.)
    - Filtering and grouping
    - Top-N analysis
    - Trend detection
    - Comparison between groups
    - Correlation analysis
    - Distribution analysis
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.name = "analyst"

    def run(self, query: str, df: pd.DataFrame) -> AgentResult:
        """Process an analytical query."""
        try:
            query_lower = query.lower().strip()

            if self._is_top_query(query_lower):
                return self._handle_top(query_lower, df)
            elif self._is_trend_query(query_lower):
                return self._handle_trend(query_lower, df)
            elif self._is_comparison_query(query_lower):
                return self._handle_comparison(query_lower, df)
            elif self._is_correlation_query(query_lower):
                return self._handle_correlation(query_lower, df)
            elif self._is_distribution_query(query_lower):
                return self._handle_distribution(query_lower, df)
            elif self._is_filter_query(query_lower):
                return self._handle_filter(query_lower, df)
            elif self._is_stats_query(query_lower):
                return self._handle_statistics(query_lower, df)
            else:
                return self._handle_general(query_lower, df)

        except Exception as e:
            logger.exception("AnalystAgent failed")
            return AgentResult(agent_name="AnalystAgent", status="error", error=str(e), narrative=f"Analysis failed: {e}")

    # --- Column Detection Helpers ---

    def _find_metric_col(self, query: str, df: pd.DataFrame) -> Optional[str]:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        query_lower = query.lower()

        metric_hints = {
            'sale': ['sales', 'sale', 'total_sales', 'revenue', 'amount'],
            'revenue': ['revenue', 'total_revenue', 'amount', 'sales'],
            'profit': ['profit', 'net_profit', 'gross_profit', 'margin'],
            'quantity': ['quantity', 'qty', 'units_sold', 'units', 'count'],
            'price': ['price', 'unit_price', 'cost'],
            'rating': ['rating', 'score', 'review_score'],
        }

        for hint, patterns in metric_hints.items():
            if hint in query_lower:
                for pattern in patterns:
                    for col in numeric_cols:
                        if pattern in col.lower():
                            return col

        for col in numeric_cols:
            if col.lower() in query_lower or col.lower().replace('_', ' ') in query_lower:
                return col

        return numeric_cols[0] if numeric_cols else None

    def _find_group_col(self, query: str, df: pd.DataFrame) -> Optional[str]:
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        query_lower = query.lower()

        group_hints = {
            'product': ['product', 'product_name', 'item', 'sku', 'name'],
            'category': ['category', 'type', 'group', 'class', 'segment'],
            'region': ['region', 'area', 'location', 'city', 'state', 'country'],
            'customer': ['customer', 'client', 'user'],
            'brand': ['brand', 'manufacturer'],
        }

        for hint, patterns in group_hints.items():
            if hint in query_lower:
                for pattern in patterns:
                    for col in cat_cols:
                        if pattern in col.lower():
                            return col

        for col in cat_cols:
            if col.lower() in query_lower or col.lower().replace('_', ' ') in query_lower:
                return col

        return cat_cols[0] if cat_cols else None

    def _find_date_col(self, df: pd.DataFrame) -> Optional[str]:
        dt_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        if dt_cols:
            return dt_cols[0]
        for col in df.select_dtypes(include=['object']).columns:
            try:
                parsed = pd.to_datetime(df[col], errors='coerce')
                if parsed.notna().sum() > len(df) * 0.5:
                    return col
            except Exception:
                pass
        return None

    # --- Intent Detection ---

    def _is_top_query(self, q: str) -> bool:
        return bool(re.search(r'\b(top|best|most|highest|largest|maximum|leading|popular|lowest|worst|minimum|least)\b', q))

    def _is_trend_query(self, q: str) -> bool:
        return bool(re.search(r'\b(trend|over time|monthly|weekly|daily|growth|timeline|time series|seasonal)\b', q))

    def _is_comparison_query(self, q: str) -> bool:
        return bool(re.search(r'\b(compare|vs|versus|difference|between|breakdown|by)\b', q))

    def _is_correlation_query(self, q: str) -> bool:
        return bool(re.search(r'\b(correlation|correlat|relationship|related|affect|impact|influence)\b', q))

    def _is_distribution_query(self, q: str) -> bool:
        return bool(re.search(r'\b(distribution|histogram|spread|range|outlier|skew)\b', q))

    def _is_filter_query(self, q: str) -> bool:
        return bool(re.search(r'\b(filter|where|only|greater|less|equal|between|above|below)\b', q))

    def _is_stats_query(self, q: str) -> bool:
        return bool(re.search(r'\b(average|mean|median|std|statistic|summary|describe|overview|profile|total)\b', q))

    # --- Query Handlers ---

    def _handle_top(self, query: str, df: pd.DataFrame) -> AgentResult:
        n_match = re.search(r'\b(\d+)\b', query)
        n = int(n_match.group(1)) if n_match else 10
        ascending = bool(re.search(r'\b(lowest|worst|minimum|least|bottom)\b', query))

        metric_col = self._find_metric_col(query, df)
        group_col = self._find_group_col(query, df)

        if not metric_col:
            return AgentResult(agent_name="AnalystAgent", status="error", narrative="Could not identify a metric column for ranking.")

        if group_col and group_col != metric_col:
            result = df.groupby(group_col)[metric_col].sum().sort_values(ascending=ascending).head(n)
            total = df[metric_col].sum()

            narrative = f"**{'Bottom' if ascending else 'Top'} {n} {group_col} by {metric_col}:**\n\n"
            for i, (name, value) in enumerate(result.items(), 1):
                share = (value / total * 100) if total > 0 else 0
                narrative += f"{i}. **{name}** — {value:,.2f} ({share:.1f}% of total)\n"
            narrative += f"\n**Total {metric_col}:** {total:,.2f}"

            chart = {
                "type": "bar",
                "x": [str(name) for name in result.index],
                "y": [round(float(v), 2) for v in result.values],
                "x_label": group_col,
                "y_label": metric_col,
                "title": f"{'Bottom' if ascending else 'Top'} {n} {group_col} by {metric_col}",
            }

            return AgentResult(
                agent_name="AnalystAgent", status="success", narrative=narrative,
                chart=chart,
                suggestions=["Show trend over time", "Compare regions", "Train a prediction model"],
            )
        else:
            top_rows = df.nlargest(n, metric_col) if not ascending else df.nsmallest(n, metric_col)
            display_cols = [metric_col] + [c for c in df.columns if c != metric_col][:4]
            narrative = f"**{'Bottom' if ascending else 'Top'} {n} rows by {metric_col}:**\n\n"
            narrative += top_rows[display_cols].to_markdown(index=False)
            return AgentResult(agent_name="AnalystAgent", status="success", narrative=narrative)

    def _handle_trend(self, query: str, df: pd.DataFrame) -> AgentResult:
        metric_col = self._find_metric_col(query, df)
        date_col = self._find_date_col(df)

        if not metric_col:
            return AgentResult(agent_name="AnalystAgent", status="error", narrative="No numeric column found for trend analysis.")

        if not date_col:
            return AgentResult(agent_name="AnalystAgent", status="error", narrative="No date column found for trend analysis.")

        df_tmp = df.copy()
        df_tmp[date_col] = pd.to_datetime(df_tmp[date_col], errors='coerce')
        df_tmp = df_tmp.dropna(subset=[date_col]).sort_values(date_col)
        df_tmp['_period'] = df_tmp[date_col].dt.to_period('M')
        trend = df_tmp.groupby('_period')[metric_col].sum()

        narrative = f"**{metric_col} Trend Over Time:**\n\n"
        for period, value in trend.items():
            narrative += f"- {period}: {value:,.2f}\n"

        if len(trend) >= 2:
            first_val, last_val = trend.iloc[0], trend.iloc[-1]
            change_pct = ((last_val - first_val) / first_val * 100) if first_val != 0 else 0
            direction = "📈 increased" if change_pct > 0 else "📉 decreased"
            narrative += f"\n**Overall:** {metric_col} {direction} by {abs(change_pct):.1f}%"

        chart = {
            "type": "line",
            "x": [str(p) for p in trend.index],
            "y": [round(float(v), 2) for v in trend.values],
            "x_label": "Period",
            "y_label": metric_col,
            "title": f"{metric_col} Over Time",
        }

        return AgentResult(
            agent_name="AnalystAgent", status="success", narrative=narrative,
            chart=chart,
            suggestions=["Predict next period", "Find anomalies", "Compare segments"],
        )

    def _handle_comparison(self, query: str, df: pd.DataFrame) -> AgentResult:
        metric_col = self._find_metric_col(query, df)
        group_col = self._find_group_col(query, df)

        if not metric_col or not group_col:
            return self._handle_general(query, df)

        comparison = df.groupby(group_col)[metric_col].agg(['sum', 'mean', 'count', 'std'])
        comparison = comparison.sort_values('sum', ascending=False).head(10)

        narrative = f"**{metric_col} Breakdown by {group_col}:**\n\n"
        narrative += f"| {group_col} | Total | Average | Count | Std Dev |\n|---|---|---|---|---|\n"
        for name, row in comparison.iterrows():
            narrative += f"| {name} | {row['sum']:,.2f} | {row['mean']:,.2f} | {int(row['count'])} | {row['std']:,.2f} |\n"

        chart = {
            "type": "bar",
            "x": [str(name) for name in comparison.index],
            "y": [round(float(v), 2) for v in comparison['sum']],
            "x_label": group_col,
            "y_label": f"Total {metric_col}",
            "title": f"{metric_col} by {group_col}",
        }

        return AgentResult(agent_name="AnalystAgent", status="success", narrative=narrative, chart=chart)

    def _handle_correlation(self, query: str, df: pd.DataFrame) -> AgentResult:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if len(numeric_cols) < 2:
            return AgentResult(agent_name="AnalystAgent", status="error", narrative="Need at least 2 numeric columns for correlation.")

        corr = df[numeric_cols].corr()
        pairs = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                pairs.append((corr.columns[i], corr.columns[j], corr.iloc[i, j]))
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        narrative = "**Correlation Analysis:**\n\n"
        for col1, col2, val in pairs[:10]:
            strength = "🔴 strong" if abs(val) > 0.7 else "🟡 moderate" if abs(val) > 0.4 else "⚪ weak"
            direction = "positive" if val > 0 else "negative"
            narrative += f"- **{col1}** ↔ **{col2}**: {val:.3f} ({strength} {direction})\n"

        return AgentResult(
            agent_name="AnalystAgent", status="success", narrative=narrative,
            suggestions=["Train model using correlated features", "Show scatter plot"],
        )

    def _handle_distribution(self, query: str, df: pd.DataFrame) -> AgentResult:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        col = None
        for c in numeric_cols:
            if c.lower() in query or c.lower().replace('_', ' ') in query:
                col = c
                break
        if not col:
            col = numeric_cols[0] if numeric_cols else None

        if not col:
            return AgentResult(agent_name="AnalystAgent", status="error", narrative="No numeric column found.")

        series = df[col].dropna()
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        n_outliers = int(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum())

        narrative = f"**Distribution of {col}:**\n\n"
        narrative += f"- Count: {len(series):,}\n"
        narrative += f"- Mean: {series.mean():,.2f} | Median: {series.median():,.2f}\n"
        narrative += f"- Std Dev: {series.std():,.2f}\n"
        narrative += f"- Range: [{series.min():,.2f}, {series.max():,.2f}]\n"
        narrative += f"- IQR: [{q1:,.2f}, {q3:,.2f}]\n"
        narrative += f"- Skewness: {series.skew():.3f}\n"
        narrative += f"- Outliers: {n_outliers} ({n_outliers/len(series)*100:.1f}%)\n"

        hist, bin_edges = np.histogram(series, bins=10)
        chart = {
            "type": "bar",
            "x": [f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}" for i in range(len(hist))],
            "y": [int(h) for h in hist],
            "x_label": col,
            "y_label": "Count",
            "title": f"Distribution of {col}",
        }

        return AgentResult(agent_name="AnalystAgent", status="success", narrative=narrative, chart=chart)

    def _handle_filter(self, query: str, df: pd.DataFrame) -> AgentResult:
        return self._handle_general(query, df)

    def _handle_statistics(self, query: str, df: pd.DataFrame) -> AgentResult:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

        narrative = f"**Dataset Statistics:**\n\n"
        narrative += f"- Rows: {len(df):,} | Columns: {len(df.columns)}\n\n"

        if numeric_cols:
            narrative += "| Column | Mean | Median | Std | Min | Max |\n|---|---|---|---|---|---|\n"
            for col in numeric_cols[:10]:
                s = df[col]
                narrative += f"| {col} | {s.mean():,.2f} | {s.median():,.2f} | {s.std():,.2f} | {s.min():,.2f} | {s.max():,.2f} |\n"

        return AgentResult(agent_name="AnalystAgent", status="success", narrative=narrative)

    def _handle_general(self, query: str, df: pd.DataFrame) -> AgentResult:
        metric_col = self._find_metric_col(query, df)
        group_col = self._find_group_col(query, df)

        if metric_col and group_col and group_col != metric_col:
            result = df.groupby(group_col)[metric_col].agg(['sum', 'mean', 'count'])
            result = result.sort_values('sum', ascending=False).head(10)

            narrative = f"**{metric_col} by {group_col}:**\n\n"
            narrative += f"| {group_col} | Total | Average | Count |\n|---|---|---|---|\n"
            for name, row in result.iterrows():
                narrative += f"| {name} | {row['sum']:,.2f} | {row['mean']:,.2f} | {int(row['count'])} |\n"

            chart = {
                "type": "bar",
                "x": [str(name) for name in result.index],
                "y": [round(float(v), 2) for v in result['sum']],
                "x_label": group_col,
                "y_label": metric_col,
                "title": f"{metric_col} by {group_col}",
            }
            return AgentResult(agent_name="AnalystAgent", status="success", narrative=narrative, chart=chart)

        return self._handle_statistics(query, df)


# =============================================================================
# ML AGENT
# =============================================================================

class MLAgent:
    """Trains machine learning models.

    Capabilities:
    - Auto-detect task type (classification vs regression)
    - Feature selection
    - Train multiple models and compare
    - Cross-validation
    - Return predictions and metrics
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.name = "ml"

    def run(self, query: str, df: pd.DataFrame) -> AgentResult:
        """Train models based on the query."""
        try:
            target_col = self._detect_target(query, df)
            if not target_col:
                return AgentResult(
                    agent_name="MLAgent", status="error",
                    narrative="Could not determine target variable. Please specify what to predict, e.g., 'predict sales' or 'classify churn'.",
                )

            task_type = self._detect_task_type(df, target_col)
            X, y, feature_cols = self._prepare_features(df, target_col)

            if len(X) < 10:
                return AgentResult(agent_name="MLAgent", status="error", narrative="Not enough data to train a model (need at least 10 rows).")

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            if task_type == "classification":
                results = self._train_classifiers(X_train, X_test, y_train, y_test)
            else:
                results = self._train_regressors(X_train, X_test, y_train, y_test)

            # Store model info in session
            state = SessionState.get(self.session_id)
            state.set("ml_results", results)
            state.set("ml_target", target_col)
            state.set("ml_task_type", task_type)
            state.set("ml_feature_cols", feature_cols)
            state.set("ml_completed", True)

            narrative = self._generate_narrative(target_col, task_type, results, feature_cols)
            chart = self._build_comparison_chart(results)

            return AgentResult(
                agent_name="MLAgent", status="success", narrative=narrative,
                chart=chart, data={"results": results, "target": target_col, "task_type": task_type},
                suggestions=["Explain the model predictions", "Show feature importance", "Predict on new data"],
            )
        except Exception as e:
            logger.exception("MLAgent failed")
            return AgentResult(agent_name="MLAgent", status="error", error=str(e), narrative=f"Model training failed: {e}")

    def _detect_target(self, query: str, df: pd.DataFrame) -> Optional[str]:
        query_lower = query.lower()

        # Look for "predict X" pattern
        predict_match = re.search(r'predict\s+(\w+)', query_lower)
        if predict_match:
            target_word = predict_match.group(1)
            for col in df.columns:
                if target_word in col.lower():
                    return col

        # Look for "classify X" pattern
        classify_match = re.search(r'classif\w*\s+(\w+)', query_lower)
        if classify_match:
            target_word = classify_match.group(1)
            for col in df.columns:
                if target_word in col.lower():
                    return col

        # Check for column name directly mentioned
        for col in df.columns:
            if col.lower() in query_lower or col.lower().replace('_', ' ') in query_lower:
                if col != df.columns[0]:  # Don't use the first column by default
                    return col

        # Heuristic: look for common target column names
        target_hints = ['target', 'label', 'class', 'churn', 'outcome', 'result', 'y']
        for hint in target_hints:
            for col in df.columns:
                if hint in col.lower():
                    return col

        # Use last numeric column as target
        numeric = df.select_dtypes(include=['number']).columns.tolist()
        if numeric:
            return numeric[-1]

        return None

    def _detect_task_type(self, df: pd.DataFrame, target_col: str) -> str:
        if df[target_col].dtype == 'object' or df[target_col].dtype.name == 'category':
            return "classification"
        if df[target_col].nunique() <= 10:
            return "classification"
        return "regression"

    def _prepare_features(self, df: pd.DataFrame, target_col: str) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        df_work = df.copy()

        # Drop non-numeric, non-target columns for simplicity
        y = df_work[target_col].copy()
        X = df_work.drop(columns=[target_col])

        # Remove datetime and high-cardinality string columns
        drop_cols = []
        for col in X.columns:
            if X[col].dtype == 'object':
                if X[col].nunique() > 20:
                    drop_cols.append(col)
                else:
                    # Label encode
                    le = LabelEncoder()
                    X[col] = le.fit_transform(X[col].astype(str))
            elif pd.api.types.is_datetime64_any_dtype(X[col]):
                drop_cols.append(col)

        X.drop(columns=drop_cols, inplace=True, errors='ignore')

        # Handle remaining nulls
        X = X.fillna(X.median(numeric_only=True))
        for col in X.select_dtypes(include=['object']).columns:
            X[col] = X[col].fillna('Unknown')
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))

        # Encode target if classification
        if y.dtype == 'object':
            le = LabelEncoder()
            y = pd.Series(le.fit_transform(y.astype(str)), name=target_col)

        # Keep only numeric
        X = X.select_dtypes(include=['number'])

        # Drop rows with any remaining NaN
        mask = X.notna().all(axis=1) & y.notna()
        X = X[mask]
        y = y[mask]

        return X, y, X.columns.tolist()

    def _train_classifiers(self, X_train, X_test, y_train, y_test) -> Dict[str, Any]:
        models = {
            "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
            "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
            "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        }

        results = {"task_type": "classification", "models": {}}

        for name, model in models.items():
            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)

                metrics = {
                    "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
                    "f1": round(float(f1_score(y_test, y_pred, average='weighted', zero_division=0)), 4),
                    "precision": round(float(precision_score(y_test, y_pred, average='weighted', zero_division=0)), 4),
                    "recall": round(float(recall_score(y_test, y_pred, average='weighted', zero_division=0)), 4),
                }

                # Feature importance
                if hasattr(model, 'feature_importances_'):
                    importance = dict(zip(X_train.columns, [round(float(v), 4) for v in model.feature_importances_]))
                    metrics["feature_importance"] = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10])
                elif hasattr(model, 'coef_'):
                    coefs = model.coef_[0] if model.coef_.ndim > 1 else model.coef_
                    importance = dict(zip(X_train.columns, [round(float(abs(v)), 4) for v in coefs]))
                    metrics["feature_importance"] = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10])

                results["models"][name] = metrics
            except Exception as e:
                results["models"][name] = {"error": str(e)}

        # Determine best model
        best_name = max(
            (name for name in results["models"] if "accuracy" in results["models"][name]),
            key=lambda n: results["models"][n]["accuracy"],
            default=None,
        )
        results["best_model"] = best_name

        return results

    def _train_regressors(self, X_train, X_test, y_train, y_test) -> Dict[str, Any]:
        models = {
            "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
            "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "Linear Regression": LinearRegression(),
        }

        results = {"task_type": "regression", "models": {}}

        for name, model in models.items():
            try:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)

                metrics = {
                    "r2": round(float(r2_score(y_test, y_pred)), 4),
                    "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
                    "mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
                }

                if hasattr(model, 'feature_importances_'):
                    importance = dict(zip(X_train.columns, [round(float(v), 4) for v in model.feature_importances_]))
                    metrics["feature_importance"] = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10])

                results["models"][name] = metrics
            except Exception as e:
                results["models"][name] = {"error": str(e)}

        best_name = max(
            (name for name in results["models"] if "r2" in results["models"][name]),
            key=lambda n: results["models"][n]["r2"],
            default=None,
        )
        results["best_model"] = best_name

        return results

    def _generate_narrative(self, target, task_type, results, feature_cols) -> str:
        parts = []
        parts.append(f"**Model Training Complete**\n")
        parts.append(f"- Target: **{target}** ({task_type})")
        parts.append(f"- Features used: {len(feature_cols)}")
        parts.append(f"- Best model: **{results.get('best_model', 'N/A')}**\n")

        parts.append("**Model Comparison:**\n")
        if task_type == "classification":
            parts.append("| Model | Accuracy | F1 | Precision | Recall |\n|---|---|---|---|---|")
            for name, metrics in results["models"].items():
                if "error" not in metrics:
                    best_marker = " 🏆" if name == results.get("best_model") else ""
                    parts.append(f"| {name}{best_marker} | {metrics['accuracy']:.4f} | {metrics['f1']:.4f} | {metrics['precision']:.4f} | {metrics['recall']:.4f} |")
        else:
            parts.append("| Model | R² | RMSE | MAE |\n|---|---|---|---|")
            for name, metrics in results["models"].items():
                if "error" not in metrics:
                    best_marker = " 🏆" if name == results.get("best_model") else ""
                    parts.append(f"| {name}{best_marker} | {metrics['r2']:.4f} | {metrics['rmse']:.4f} | {metrics['mae']:.4f} |")

        # Feature importance from best model
        best = results.get("best_model")
        if best and best in results["models"]:
            fi = results["models"][best].get("feature_importance", {})
            if fi:
                parts.append("\n**Top Features (importance):**")
                for feat, imp in list(fi.items())[:5]:
                    bar = "█" * int(imp * 20)
                    parts.append(f"- {feat}: {imp:.4f} {bar}")

        return "\n".join(parts)

    def _build_comparison_chart(self, results: Dict[str, Any]) -> Dict[str, Any]:
        models = []
        scores = []
        metric_name = "accuracy" if results["task_type"] == "classification" else "r2"

        for name, metrics in results["models"].items():
            if metric_name in metrics:
                models.append(name)
                scores.append(round(float(metrics[metric_name]), 4))

        return {
            "type": "bar",
            "x": models,
            "y": scores,
            "x_label": "Model",
            "y_label": metric_name.upper(),
            "title": f"Model Comparison ({metric_name})",
        }


# =============================================================================
# XAI AGENT (Explainability)
# =============================================================================

class XAIAgent:
    """Explains model predictions and feature importance.

    Capabilities:
    - Global feature importance
    - Feature contribution analysis
    - Decision path explanation
    - What-if analysis
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.name = "xai"

    def run(self, query: str, df: pd.DataFrame) -> AgentResult:
        """Generate explanations for the trained model."""
        try:
            state = SessionState.get(self.session_id)
            ml_results = state.get_value("ml_results")

            if not ml_results:
                return AgentResult(
                    agent_name="XAIAgent", status="error",
                    narrative="No trained model found. Please train a model first (e.g., 'predict sales' or 'classify churn').",
                    suggestions=["Train a prediction model", "Predict churn"],
                )

            target_col = state.get_value("ml_target")
            task_type = state.get_value("ml_task_type")
            feature_cols = state.get_value("ml_feature_cols", [])

            # Get feature importance from best model
            best_model_name = ml_results.get("best_model")
            best_metrics = ml_results["models"].get(best_model_name, {})
            feature_importance = best_metrics.get("feature_importance", {})

            # Retrain best model for deeper explanation
            explanation = self._explain_model(df, target_col, task_type, feature_cols)

            narrative = self._generate_narrative(target_col, task_type, best_model_name, feature_importance, explanation)
            chart = self._build_importance_chart(feature_importance)

            return AgentResult(
                agent_name="XAIAgent", status="success", narrative=narrative,
                chart=chart, data={"feature_importance": feature_importance, "explanation": explanation},
                suggestions=["What if we change the top feature?", "Show partial dependence", "Which customers are at risk?"],
            )
        except Exception as e:
            logger.exception("XAIAgent failed")
            return AgentResult(agent_name="XAIAgent", status="error", error=str(e), narrative=f"Explanation failed: {e}")

    def _explain_model(self, df: pd.DataFrame, target_col: str, task_type: str, feature_cols: List[str]) -> Dict[str, Any]:
        """Generate model explanation using a decision tree for interpretability."""
        explanation = {}

        try:
            # Prepare data
            X = df[feature_cols].copy() if all(c in df.columns for c in feature_cols) else df.select_dtypes(include=['number']).drop(columns=[target_col], errors='ignore')

            for col in X.select_dtypes(include=['object']).columns:
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))

            X = X.fillna(X.median(numeric_only=True))
            y = df[target_col].copy()
            if y.dtype == 'object':
                le = LabelEncoder()
                y = pd.Series(le.fit_transform(y.astype(str)))

            mask = X.notna().all(axis=1) & y.notna()
            X, y = X[mask], y[mask]

            # Train interpretable model (decision tree)
            if task_type == "classification":
                tree = DecisionTreeClassifier(max_depth=4, random_state=42)
            else:
                from sklearn.tree import DecisionTreeRegressor
                tree = DecisionTreeRegressor(max_depth=4, random_state=42)

            tree.fit(X, y)

            # Extract rules from tree
            feature_names = X.columns.tolist()
            tree_rules = self._extract_tree_rules(tree, feature_names)
            explanation["decision_rules"] = tree_rules[:5]

            # Feature interactions (correlation between top features)
            if len(feature_names) >= 2:
                fi = dict(zip(feature_names, tree.feature_importances_))
                top_feats = sorted(fi, key=fi.get, reverse=True)[:3]
                if len(top_feats) >= 2:
                    corr = X[top_feats].corr()
                    explanation["top_feature_correlations"] = {
                        f"{top_feats[0]} vs {top_feats[1]}": round(float(corr.iloc[0, 1]), 3)
                    }

        except Exception as e:
            explanation["error"] = str(e)

        return explanation

    def _extract_tree_rules(self, tree, feature_names: List[str]) -> List[str]:
        """Extract human-readable rules from a decision tree."""
        from sklearn.tree import export_text
        try:
            text = export_text(tree, feature_names=feature_names, max_depth=3)
            lines = [l.strip() for l in text.split('\n') if l.strip() and '|' in l]
            rules = []
            for line in lines[:8]:
                clean = line.replace('|', '').replace('---', '').strip()
                if clean:
                    rules.append(clean)
            return rules
        except Exception:
            return ["Could not extract rules"]

    def _generate_narrative(self, target, task_type, best_model, feature_importance, explanation) -> str:
        parts = []
        parts.append(f"**Model Explanation: {best_model}**\n")
        parts.append(f"- Target: **{target}** ({task_type})")

        if feature_importance:
            parts.append("\n**Feature Importance (what drives predictions):**\n")
            for i, (feat, imp) in enumerate(list(feature_importance.items())[:8], 1):
                bar = "█" * int(imp * 30)
                parts.append(f"{i}. **{feat}**: {imp:.4f} {bar}")

        rules = explanation.get("decision_rules", [])
        if rules:
            parts.append("\n**Key Decision Rules:**\n")
            for rule in rules[:5]:
                parts.append(f"- {rule}")

        parts.append("\n**Interpretation:**")
        if feature_importance:
            top_feat = list(feature_importance.keys())[0]
            parts.append(f"The most influential factor is **{top_feat}**. Changes in this feature have the largest impact on {target} predictions.")

        return "\n".join(parts)

    def _build_importance_chart(self, feature_importance: Dict[str, float]) -> Dict[str, Any]:
        if not feature_importance:
            return None

        features = list(feature_importance.keys())[:8]
        values = [feature_importance[f] for f in features]

        return {
            "type": "bar",
            "x": features,
            "y": values,
            "x_label": "Feature",
            "y_label": "Importance",
            "title": "Feature Importance",
        }


# =============================================================================
# VISUALIZATION AGENT
# =============================================================================

class VisualizationAgent:
    """Generates appropriate visualizations based on data and context.

    Capabilities:
    - Auto-detect best chart type
    - Generate chart specifications for Plotly
    - Support: bar, line, scatter, histogram, pie, heatmap
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.name = "visualization"

    def run(self, query: str, df: pd.DataFrame) -> AgentResult:
        """Generate visualization based on query."""
        try:
            chart_type = self._detect_chart_type(query, df)
            chart_spec = self._generate_chart(chart_type, query, df)

            if not chart_spec:
                return AgentResult(agent_name="VisualizationAgent", status="error", narrative="Could not generate chart for this query.")

            narrative = f"Generated a **{chart_type}** chart based on your request."

            return AgentResult(
                agent_name="VisualizationAgent", status="success",
                narrative=narrative, chart=chart_spec,
            )
        except Exception as e:
            logger.exception("VisualizationAgent failed")
            return AgentResult(agent_name="VisualizationAgent", status="error", error=str(e))

    def _detect_chart_type(self, query: str, df: pd.DataFrame) -> str:
        q = query.lower()
        if any(w in q for w in ['pie', 'proportion', 'share', 'percentage']):
            return 'pie'
        if any(w in q for w in ['scatter', 'relationship', 'correlation']):
            return 'scatter'
        if any(w in q for w in ['line', 'trend', 'time', 'over time']):
            return 'line'
        if any(w in q for w in ['histogram', 'distribution', 'frequency']):
            return 'histogram'
        if any(w in q for w in ['heatmap', 'correlation matrix']):
            return 'heatmap'
        return 'bar'

    def _generate_chart(self, chart_type: str, query: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        if chart_type == 'bar' and cat_cols and numeric_cols:
            group_col = cat_cols[0]
            metric_col = numeric_cols[0]
            data = df.groupby(group_col)[metric_col].sum().sort_values(ascending=False).head(10)
            return {
                "type": "bar",
                "x": [str(x) for x in data.index],
                "y": [round(float(v), 2) for v in data.values],
                "x_label": group_col,
                "y_label": metric_col,
                "title": f"{metric_col} by {group_col}",
            }

        elif chart_type == 'scatter' and len(numeric_cols) >= 2:
            return {
                "type": "scatter",
                "x": df[numeric_cols[0]].tolist()[:200],
                "y": df[numeric_cols[1]].tolist()[:200],
                "x_label": numeric_cols[0],
                "y_label": numeric_cols[1],
                "title": f"{numeric_cols[0]} vs {numeric_cols[1]}",
            }

        elif chart_type == 'histogram' and numeric_cols:
            col = numeric_cols[0]
            hist, edges = np.histogram(df[col].dropna(), bins=15)
            return {
                "type": "bar",
                "x": [f"{edges[i]:.1f}" for i in range(len(hist))],
                "y": [int(h) for h in hist],
                "x_label": col,
                "y_label": "Frequency",
                "title": f"Distribution of {col}",
            }

        elif chart_type == 'pie' and cat_cols and numeric_cols:
            group_col = cat_cols[0]
            metric_col = numeric_cols[0]
            data = df.groupby(group_col)[metric_col].sum().head(8)
            return {
                "type": "pie",
                "labels": [str(x) for x in data.index],
                "values": [round(float(v), 2) for v in data.values],
                "title": f"{metric_col} Share by {group_col}",
            }

        return None


# =============================================================================
# ORCHESTRATOR - Routes queries to the right agent
# =============================================================================

class SmartOrchestrator:
    """Routes queries to the appropriate agent(s).

    Decision logic:
    - Upload → ProfilingAgent + PreprocessingAgent (automatic)
    - Analytical queries → AnalystAgent
    - ML/prediction queries → MLAgent
    - Explanation queries → XAIAgent
    - Visualization queries → VisualizationAgent (may combine with others)
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.profiler = ProfilingAgent(session_id)
        self.preprocessor = PreprocessingAgent(session_id)
        self.analyst = AnalystAgent(session_id)
        self.ml_agent = MLAgent(session_id)
        self.xai_agent = XAIAgent(session_id)
        self.viz_agent = VisualizationAgent(session_id)

    def on_upload(self, df: pd.DataFrame) -> List[AgentResult]:
        """Run on dataset upload — profile and preprocess automatically."""
        results = []

        # Profile the data
        profile_result = self.profiler.run(df)
        results.append(profile_result)

        # Preprocess the data
        preprocess_result = self.preprocessor.run(df)
        results.append(preprocess_result)

        return results

    def route_query(self, query: str, df: pd.DataFrame) -> AgentResult:
        """Route a user query to the appropriate agent."""
        intent = self._classify_intent(query)

        logger.info(f"Query routed to: {intent}", extra={"session_id": self.session_id, "query": query[:100]})

        if intent == "ml":
            return self.ml_agent.run(query, df)
        elif intent == "xai":
            return self.xai_agent.run(query, df)
        elif intent == "visualization":
            result = self.analyst.run(query, df)
            if not result.chart:
                viz_result = self.viz_agent.run(query, df)
                result.chart = viz_result.chart
            return result
        else:
            return self.analyst.run(query, df)

    def _classify_intent(self, query: str) -> str:
        """Classify query intent to route to the right agent."""
        q = query.lower()

        # ML intent
        if re.search(r'\b(predict|forecast|train|model|classify|regression|machine learning|ml|automl)\b', q):
            return "ml"

        # XAI intent
        if re.search(r'\b(explain|why|feature importance|shap|lime|interpret|what.?if|understand model|decision)\b', q):
            return "xai"

        # Visualization intent
        if re.search(r'\b(chart|plot|graph|visuali|show me|histogram|scatter|bar chart|heatmap|pie|display)\b', q):
            return "visualization"

        # Default to analyst
        return "analyst"
