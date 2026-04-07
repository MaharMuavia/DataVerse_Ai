"""
Advanced Anomaly Detection Tool

Detects anomalies using multiple algorithms:
- Isolation Forest
- Local Outlier Factor (LOF)
- Z-score based detection
- IQR-based detection
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import plotly.graph_objects as go
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

from .base_tool import BaseTool
from ..core.tool_registry import ToolResult, ChartSpec, NarrativeSpec, SessionContext


class AnomalyDetectionTool(BaseTool):
    """
    Advanced multi-algorithm anomaly detection.
    
    Combines multiple detection methods:
    1. Isolation Forest (tree-based)
    2. Local Outlier Factor (density-based)
    3. Z-score thresholding (statistical)
    4. IQR method (quartile-based)
    
    Returns anomaly scores and visualizations.
    """
    
    @property
    def name(self) -> str:
        return "advanced_anomaly_detection"
    
    @property
    def description(self) -> str:
        return """
        Multi-algorithm anomaly detection for univariate and multivariate data.
        
        Params:
        - columns: list[str] - Numeric columns to analyze
        - method: str - Detection method ('ensemble', 'isolation_forest', 'lof', 'zscore', 'iqr')
        - contamination: float - Expected proportion of anomalies (0.01-0.5, default=0.05)
        - sensitivity: float - Sensitivity level (0.1-2.0, default=1.0)
        """
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "columns": "list[str]",
            "method": "str (ensemble|isolation_forest|lof|zscore|iqr)",
            "contamination": "float (0.0-1.0)",
            "sensitivity": "float (0.1-2.0)",
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "anomaly_count": "int",
            "anomaly_percentage": "float",
            "anomaly_scores": "dict",
            "flagged_rows": "list[int]",
            "charts": "list[ChartSpec]",
            "narrative": "str",
        }
    
    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        """Execute anomaly detection."""
        try:
            df = session.dataframe
            columns = params.get("columns", df.select_dtypes(include=[np.number]).columns.tolist())
            method = params.get("method", "ensemble")
            contamination = params.get("contamination", 0.05)
            sensitivity = params.get("sensitivity", 1.0)
            
            # Select numeric columns
            numeric_cols = [col for col in columns if df[col].dtype in [np.number]]
            if not numeric_cols:
                return ToolResult(
                    narrative=self.create_narrative_spec(
                        "No numeric columns available for anomaly detection.",
                        "professional"
                    ),
                    data={"anomaly_count": 0},
                )
            
            # Prepare data
            X = df[numeric_cols].fillna(df[numeric_cols].mean())
            
            # Detect anomalies
            if method == "ensemble":
                anomalies = self._ensemble_detection(X, contamination, sensitivity)
            elif method == "isolation_forest":
                anomalies = self._isolation_forest_detection(X, contamination, sensitivity)
            elif method == "lof":
                anomalies = self._lof_detection(X, contamination, sensitivity)
            elif method == "zscore":
                anomalies = self._zscore_detection(X, sensitivity)
            elif method == "iqr":
                anomalies = self._iqr_detection(X, sensitivity)
            else:
                anomalies = self._ensemble_detection(X, contamination, sensitivity)
            
            # Get flagged indices
            flagged_indices = np.where(anomalies)[0].tolist()
            anomaly_count = len(flagged_indices)
            anomaly_pct = (anomaly_count / len(df)) * 100
            
            # Create visualizations
            charts = self._create_visualizations(df, numeric_cols, anomalies)
            
            # Create narrative
            narrative = self._create_narrative(anomaly_count, anomaly_pct, method, numeric_cols)
            
            return ToolResult(
                narrative=narrative,
                charts=charts,
                data={
                    "anomaly_count": anomaly_count,
                    "anomaly_percentage": round(anomaly_pct, 2),
                    "flagged_rows": flagged_indices[:100],  # Return first 100
                    "method": method,
                    "columns_analyzed": numeric_cols,
                }
            )
        
        except Exception as e:
            return ToolResult(
                narrative=self.create_narrative_spec(
                    f"Error during anomaly detection: {str(e)}",
                    "professional"
                ),
                error=str(e),
            )
    
    def _ensemble_detection(self, X: np.ndarray, contamination: float, sensitivity: float) -> np.ndarray:
        """Ensemble of multiple methods."""
        iso_forest = IsolationForest(contamination=contamination, random_state=42)
        iso_pred = iso_forest.fit_predict(X) == -1
        
        lof = LocalOutlierFactor(n_neighbors=20, contamination=contamination)
        lof_pred = lof.fit_predict(X) == -1
        
        z_pred = np.abs(stats.zscore(X)) > (3 / sensitivity)
        z_pred = z_pred.any(axis=1)
        
        # Ensemble: flag if at least 2 methods agree
        ensemble = (iso_pred.astype(int) + lof_pred.astype(int) + z_pred.astype(int)) >= 2
        return ensemble
    
    def _isolation_forest_detection(self, X: np.ndarray, contamination: float, sensitivity: float) -> np.ndarray:
        """Isolation Forest method."""
        iso_forest = IsolationForest(contamination=contamination * sensitivity, random_state=42)
        return iso_forest.fit_predict(X) == -1
    
    def _lof_detection(self, X: np.ndarray, contamination: float, sensitivity: float) -> np.ndarray:
        """Local Outlier Factor method."""
        lof = LocalOutlierFactor(n_neighbors=20, contamination=contamination * sensitivity)
        return lof.fit_predict(X) == -1
    
    def _zscore_detection(self, X: np.ndarray, sensitivity: float) -> np.ndarray:
        """Z-score based detection."""
        z_scores = np.abs(stats.zscore(X))
        threshold = 3 / sensitivity
        return (z_scores > threshold).any(axis=1)
    
    def _iqr_detection(self, X: np.ndarray, sensitivity: float) -> np.ndarray:
        """IQR-based detection."""
        Q1 = np.percentile(X, 25, axis=0)
        Q3 = np.percentile(X, 75, axis=0)
        IQR = Q3 - Q1
        lower_bound = Q1 - (1.5 * IQR * sensitivity)
        upper_bound = Q3 + (1.5 * IQR * sensitivity)
        
        return ((X < lower_bound) | (X > upper_bound)).any(axis=1)
    
    def _create_visualizations(self, df: pd.DataFrame, columns: List[str], anomalies: np.ndarray) -> List[ChartSpec]:
        """Create anomaly visualizations."""
        charts = []
        
        # Anomaly distribution chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=['Normal', 'Anomalies'],
            y=[np.sum(~anomalies), np.sum(anomalies)],
            marker=dict(color=['#2563EB', '#DC2626']),
        ))
        fig.update_layout(
            title="Anomaly Distribution",
            yaxis_title="Count",
            hovermode='x unified',
        )
        charts.append(ChartSpec(fig=fig, title="Anomaly Distribution"))
        
        # Scatter plot for first 2 numeric columns
        if len(columns) >= 2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df[columns[0]][~anomalies],
                y=df[columns[1]][~anomalies],
                mode='markers',
                name='Normal',
                marker=dict(color='#2563EB', size=6),
            ))
            fig.add_trace(go.Scatter(
                x=df[columns[0]][anomalies],
                y=df[columns[1]][anomalies],
                mode='markers',
                name='Anomalies',
                marker=dict(color='#DC2626', size=8, symbol='star'),
            ))
            fig.update_layout(
                title=f"{columns[0]} vs {columns[1]}",
                xaxis_title=columns[0],
                yaxis_title=columns[1],
                hovermode='closest',
            )
            charts.append(ChartSpec(fig=fig, title="Detected Anomalies"))
        
        return charts
    
    def _create_narrative(self, count: int, pct: float, method: str, columns: List[str]) -> NarrativeSpec:
        """Create explanatory narrative."""
        text = f"""
        ## Anomaly Detection Results
        
        **Overview:**
        - Total anomalies detected: **{count}** ({pct:.2f}%)
        - Detection method: **{method}**
        - Columns analyzed: {', '.join(columns)}
        
        **Interpretation:**
        Anomalies are data points that deviate significantly from the normal pattern.
        The {method} method was used to identify these outliers based on statistical
        and machine learning principles.
        
        **Next Steps:**
        - Investigate the flagged rows for data quality issues
        - Consider removing or treating anomalies based on business context
        - Correlate with external events or domain knowledge
        """
        
        return self.create_narrative_spec(text, "professional")
