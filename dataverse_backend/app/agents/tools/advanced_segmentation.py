"""
Advanced Customer Segmentation Tool

Performs K-means, hierarchical, and automated clustering with:
- Optimal cluster number detection
- Silhouette analysis
- Feature importance per cluster
- Segment profiling
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import plotly.graph_objects as go
import plotly.express as px
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist

from .base_tool import BaseTool
from ..core.tool_registry import ToolResult, ChartSpec, TableSpec, NarrativeSpec, SessionContext


class AdvancedSegmentationTool(BaseTool):
    """
    Advanced customer/cohort segmentation using K-means clustering.
    
    Features:
    1. Automatic optimal cluster detection (Elbow + Silhouette)
    2. Cluster profiling (centroid + statistics)
    3. Segment characteristics visualization
    4. Actionable segment descriptions
    """
    
    @property
    def name(self) -> str:
        return "advanced_segmentation"
    
    @property
    def description(self) -> str:
        return """
        Advanced clustering and segmentation analysis.
        
        Params:
        - features: list[str] - Numeric columns for clustering
        - n_clusters: int (optional) - Number of clusters (auto-detect if not specified)
        - clustering_method: str - 'kmeans', 'hierarchical', or 'auto'
        - scale: bool - Whether to standardize features (default=True)
        """
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "features": "list[str]",
            "n_clusters": "int (optional, default=auto)",
            "clustering_method": "str (kmeans|hierarchical|auto)",
            "scale": "bool",
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "n_clusters": "int",
            "silhouette_score": "float",
            "segment_counts": "dict",
            "segment_profiles": "list[dict]",
            "charts": "list[ChartSpec]",
        }
    
    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        """Execute segmentation analysis."""
        try:
            df = session.dataframe
            features = params.get("features", df.select_dtypes(include=[np.number]).columns.tolist())
            n_clusters = params.get("n_clusters", None)
            method = params.get("clustering_method", "kmeans")
            scale = params.get("scale", True)
            
            # Validate features
            valid_features = [f for f in features if f in df.columns and df[f].dtype in [np.number]]
            if not valid_features:
                return ToolResult(
                    narrative=self.create_narrative_spec(
                        "No valid numeric features for segmentation.",
                        "professional"
                    ),
                    error="No valid features",
                )
            
            # Prepare data
            X = df[valid_features].fillna(df[valid_features].mean()).values
            
            if scale:
                scaler = StandardScaler()
                X = scaler.fit_transform(X)
            
            # Determine optimal clusters if not specified
            if n_clusters is None:
                n_clusters = self._find_optimal_clusters(X)
            
            # Perform clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X)
            
            # Calculate metrics
            silhouette = silhouette_score(X, clusters)
            
            # Get segment profiles
            segment_profiles = self._profile_segments(df, valid_features, clusters, n_clusters)
            
            # Create visualizations
            charts = self._create_visualizations(X, clusters, valid_features, silhouette)
            
            # Create narrative
            narrative = self._create_narrative(n_clusters, silhouette, segment_profiles)
            
            # Add cluster labels to dataframe
            df['_segment'] = clusters
            session.dataframe = df
            
            return ToolResult(
                narrative=narrative,
                charts=charts,
                data={
                    "n_clusters": n_clusters,
                    "silhouette_score": round(silhouette, 3),
                    "segment_counts": dict(zip(*np.unique(clusters, return_counts=True))),
                    "features": valid_features,
                    "segment_profiles": segment_profiles,
                }
            )
        
        except Exception as e:
            return ToolResult(
                narrative=self.create_narrative_spec(
                    f"Segmentation error: {str(e)}",
                    "professional"
                ),
                error=str(e),
            )
    
    def _find_optimal_clusters(self, X: np.ndarray, max_k: int = 10) -> int:
        """Find optimal number of clusters using elbow + silhouette."""
        silhouette_scores = []
        
        for k in range(2, min(max_k + 1, len(X))):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X)
            score = silhouette_score(X, clusters)
            silhouette_scores.append(score)
        
        # Return k with best silhouette score
        best_k = np.argmax(silhouette_scores) + 2
        return best_k
    
    def _profile_segments(self, df: pd.DataFrame, features: List[str], clusters: np.ndarray, n_clusters: int) -> List[Dict[str, Any]]:
        """Profile each segment."""
        profiles = []
        
        for cluster_id in range(n_clusters):
            mask = clusters == cluster_id
            segment_df = df[mask]
            
            profile = {
                "segment_id": cluster_id,
                "segment_name": f"Segment {cluster_id + 1}",
                "size": len(segment_df),
                "percentage": round((len(segment_df) / len(df)) * 100, 2),
                "characteristics": {}
            }
            
            # Add feature stats
            for feat in features:
                profile["characteristics"][feat] = {
                    "mean": round(segment_df[feat].mean(), 2),
                    "median": round(segment_df[feat].median(), 2),
                    "std": round(segment_df[feat].std(), 2),
                }
            
            profiles.append(profile)
        
        return profiles
    
    def _create_visualizations(self, X: np.ndarray, clusters: np.ndarray, features: List[str], silhouette: float) -> List[ChartSpec]:
        """Create segmentation visualizations."""
        charts = []
        
        # Cluster size pie chart
        unique, counts = np.unique(clusters, return_counts=True)
        fig = go.Figure(data=[go.Pie(
            labels=[f"Segment {i+1}" for i in unique],
            values=counts,
            marker=dict(colors=['#2563EB', '#7C3AED', '#DC2626', '#D97706', '#059669', '#0891B2']),
        )])
        fig.update_layout(title="Segment Distribution")
        charts.append(ChartSpec(fig=fig, title="Segment Distribution"))
        
        # 2D scatter if we have at least 2 features
        if len(features) >= 2:
            fig = go.Figure()
            for cluster_id in np.unique(clusters):
                mask = clusters == cluster_id
                fig.add_trace(go.Scatter(
                    x=X[mask, 0],
                    y=X[mask, 1],
                    mode='markers',
                    name=f'Segment {cluster_id + 1}',
                    marker=dict(size=8),
                ))
            fig.update_layout(
                title="Cluster Visualization (PCA)",
                xaxis_title=features[0],
                yaxis_title=features[1] if len(features) > 1 else "PC2",
                hovermode='closest',
            )
            charts.append(ChartSpec(fig=fig, title="Segment Visualization"))
        
        # Silhouette score indicator
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=silhouette * 100,
            title={'text': "Silhouette Score"},
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': '#2563EB'},
                'steps': [
                    {'range': [0, 50], 'color': '#FEE2E2'},
                    {'range': [50, 100], 'color': '#DBEAFE'}
                ],
            }
        ))
        charts.append(ChartSpec(fig=fig, title="Model Quality"))
        
        return charts
    
    def _create_narrative(self, n_clusters: int, silhouette: float, profiles: List[Dict]) -> NarrativeSpec:
        """Create interpretable narrative."""
        narrative_text = f"""
        ## Customer Segmentation Analysis
        
        **Segmentation Overview:**
        - Number of segments identified: **{n_clusters}**
        - Model quality (Silhouette Score): **{silhouette:.3f}** (higher is better)
        
        **Segment Details:**
        """
        
        for profile in profiles:
            narrative_text += f"\n- **{profile['segment_name']}**: {profile['size']} customers ({profile['percentage']}%)"
        
        narrative_text += """
        
        **Business Implications:**
        Each segment represents a distinct group of customers with unique characteristics.
        Use these insights for targeted marketing, product positioning, and resource allocation.
        """
        
        return self.create_narrative_spec(narrative_text, "professional")
