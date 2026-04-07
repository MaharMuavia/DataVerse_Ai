import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any
from workflow.state import AnalysisState

VIZ_RULES = {
    ("numeric", "distribution"): "histogram",
    ("numeric", "numeric", "relation"): "scatter",
    ("categorical", "frequency"): "bar",
    ("time", "numeric", "trend"): "line",
    ("numeric", "comparison"): "box",
    ("numeric_multi", "correlation"): "heatmap",
    ("categorical", "numeric", "compare"): "grouped_bar",
}

def select_chart_type(sub_intent: str, target_columns: list, dtypes: dict) -> str:
    # Simple rule-based selection based on sub_intent keywords
    sub_lower = sub_intent.lower()

    if "histogram" in sub_lower or "distribution" in sub_lower:
        return "histogram"
    elif "scatter" in sub_lower or "relation" in sub_lower:
        return "scatter"
    elif "bar" in sub_lower or "frequency" in sub_lower:
        return "bar"
    elif "line" in sub_lower or "trend" in sub_lower:
        return "line"
    elif "box" in sub_lower or "comparison" in sub_lower:
        return "box"
    elif "heatmap" in sub_lower or "correlation" in sub_lower:
        return "heatmap"
    else:
        # Default based on column types
        if len(target_columns) == 1 and dtypes.get(target_columns[0]) in ['int64', 'float64']:
            return "histogram"
        elif len(target_columns) == 2 and all(dtypes.get(col) in ['int64', 'float64'] for col in target_columns):
            return "scatter"
        else:
            return "bar"

async def run_viz_pipeline(state: AnalysisState) -> Dict[str, Any]:
    try:
        # Load dataframe
        if state["dataset_path"].endswith('.xlsx'):
            df = pd.read_excel(state["dataset_path"])
        else:
            df = pd.read_csv(state["dataset_path"])

        chart_type = state.get("chart_type") or select_chart_type(
            state.get("sub_intent", ""),
            state["target_columns"],
            state["column_dtypes"]
        )

        target_cols = state["target_columns"]
        fig = None

        if chart_type == "histogram" and target_cols:
            fig = px.histogram(df, x=target_cols[0], title=f"Distribution of {target_cols[0]}")
        elif chart_type == "scatter" and len(target_cols) >= 2:
            fig = px.scatter(df, x=target_cols[0], y=target_cols[1], title=f"{target_cols[0]} vs {target_cols[1]}")
        elif chart_type == "bar" and target_cols:
            value_counts = df[target_cols[0]].value_counts().reset_index()
            value_counts.columns = [target_cols[0], 'count']
            fig = px.bar(value_counts, x=target_cols[0], y='count', title=f"Frequency of {target_cols[0]}")
        elif chart_type == "line" and len(target_cols) >= 2:
            fig = px.line(df, x=target_cols[0], y=target_cols[1], title=f"{target_cols[1]} over {target_cols[0]}")
        elif chart_type == "box" and target_cols:
            fig = px.box(df, y=target_cols[0], title=f"Box plot of {target_cols[0]}")
        elif chart_type == "heatmap":
            numeric_cols = [col for col, dtype in state["column_dtypes"].items() if dtype in ['int64', 'float64']]
            if len(numeric_cols) > 1:
                corr = df[numeric_cols].corr()
                fig = px.imshow(corr, text_auto=True, title="Correlation Heatmap")
            else:
                return {"error_message": "Not enough numeric columns for heatmap"}
        else:
            return {"error_message": f"Unsupported chart type: {chart_type}"}

        if fig:
            # Apply consistent styling
            fig.update_layout(
                template="plotly_white",
                font_family="Inter, sans-serif",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin={"t": 30, "b": 40, "l": 40, "r": 20}
            )

            fig_json = fig.to_json()
            return {"viz_figure_json": fig_json, "chart_type": chart_type}
        else:
            return {"error_message": "Could not generate chart"}

    except Exception as e:
        return {"error_message": f"Viz pipeline failed: {str(e)}"}