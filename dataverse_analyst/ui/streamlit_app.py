from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from app.core.csv_parser import read_csv_bytes


API_BASE = "http://localhost:8001"


def _download_pdf_bytes(markdown_text: str) -> bytes:
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        for line in markdown_text.splitlines():
            pdf.multi_cell(0, 7, line.encode("latin-1", "replace").decode("latin-1"))
        return bytes(pdf.output(dest="S"))
    except Exception:
        return markdown_text.encode("utf-8")


def _post_upload(uploaded_file) -> dict[str, Any]:
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
    response = requests.post(f"{API_BASE}/upload", files=files, timeout=30)
    response.raise_for_status()
    return response.json()


def _post_analyze(session_id: str, target_column: str | None) -> dict[str, Any]:
    data = {"session_id": session_id}
    if target_column:
        data["target_column"] = target_column
    response = requests.post(f"{API_BASE}/analyze", data=data, timeout=120)
    response.raise_for_status()
    return response.json()


def _missing_heatmap(df: pd.DataFrame):
    missing = df.isna().astype(int)
    if missing.to_numpy().sum() == 0:
        st.caption("No missing values detected.")
    else:
        st.plotly_chart(px.imshow(missing, aspect="auto", title="Missing Value Heatmap"), use_container_width=True)


def render_eda(df: pd.DataFrame, report: dict[str, Any] | None) -> None:
    left, right = st.columns(2)
    left.metric("Rows", f"{df.shape[0]:,}")
    right.metric("Columns", f"{df.shape[1]:,}")
    st.dataframe(pd.DataFrame({"column": df.columns, "dtype": [str(dtype) for dtype in df.dtypes]}), use_container_width=True)
    _missing_heatmap(df)
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] >= 2:
        st.plotly_chart(px.imshow(numeric.corr(numeric_only=True), text_auto=True, title="Correlation Heatmap"), use_container_width=True)
    for column in numeric.columns[:5]:
        st.plotly_chart(px.histogram(df, x=column, title=f"Distribution of {column}"), use_container_width=True)
    if report:
        st.json(report.get("eda", {}).get("outliers", {}), expanded=False)


def render_trends(df: pd.DataFrame, report: dict[str, Any] | None) -> None:
    trends = (report or {}).get("trends", {})
    series = trends.get("time_series") or []
    if series:
        first = series[0]
        points = pd.DataFrame(first.get("points", []))
        if not points.empty:
            st.plotly_chart(px.line(points, x="date", y="value", title=f"{first['value_column']} over time"), use_container_width=True)
        st.metric("Trend Direction", first.get("trend", "unknown"))
        st.metric("Seasonality Flag", str(first.get("seasonality_flag", False)))
    else:
        st.caption("No datetime trend was detected.")
    if trends.get("categorical_tests"):
        st.dataframe(pd.DataFrame(trends["categorical_tests"]), use_container_width=True)


def render_model(report: dict[str, Any] | None) -> None:
    model = (report or {}).get("model", {})
    if not model:
        st.caption("Run analysis to train a model.")
        return
    st.write(f"Model: `{model.get('model_type', 'unknown')}` via `{model.get('engine', 'unknown')}`")
    st.write(f"Target: `{model.get('target_column', 'unknown')}` ({model.get('task_type', 'unknown')})")
    metrics = model.get("metrics") or {}
    if metrics:
        st.dataframe(pd.DataFrame([metrics]), use_container_width=True)
    importances = model.get("feature_importance") or {}
    if importances:
        frame = pd.DataFrame({"feature": list(importances.keys()), "importance": list(importances.values())})
        st.plotly_chart(px.bar(frame, x="importance", y="feature", orientation="h", title="Feature Importance"), use_container_width=True)
    if model.get("warning"):
        st.warning(model["warning"])


def render_xai(report: dict[str, Any] | None) -> None:
    xai = (report or {}).get("xai", {})
    lime = (report or {}).get("lime", {})
    importances = xai.get("importances") or {}
    if importances:
        frame = pd.DataFrame({"feature": list(importances.keys()), "mean_abs_shap": list(importances.values())})
        st.plotly_chart(px.bar(frame, x="mean_abs_shap", y="feature", orientation="h", title="SHAP Summary"), use_container_width=True)
    else:
        st.caption(xai.get("error", "SHAP results are not available."))
    waterfall = xai.get("waterfall") or {}
    if waterfall:
        frame = pd.DataFrame({"feature": list(waterfall.keys()), "contribution": list(waterfall.values())})
        st.plotly_chart(px.bar(frame.head(20), x="contribution", y="feature", orientation="h", title="SHAP Waterfall: Top Prediction"), use_container_width=True)
    explanations = lime.get("explanations") or []
    if explanations:
        rows = [
            {"sample": item["sample"], "rule": feature["rule"], "weight": feature["weight"]}
            for item in explanations
            for feature in item["features"]
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.caption(lime.get("error", "LIME explanations are not available."))


def render_report(report: dict[str, Any] | None) -> None:
    narrative = (report or {}).get("narrative", "Run analysis to generate the AI report.")
    st.markdown(narrative)
    st.download_button(
        "Download PDF",
        data=_download_pdf_bytes(narrative),
        file_name="dataverse_ai_report.pdf",
        mime="application/pdf",
    )


st.set_page_config(page_title="DataVerse Analyst", page_icon="DV", layout="wide")
st.title("DataVerse Analyst")

uploaded = st.file_uploader("Upload CSV", type=["csv"])
if uploaded:
    try:
        df = read_csv_bytes(uploaded.getvalue())
    except Exception as exc:
        st.error(f"Could not read CSV: {exc}")
        st.stop()
    st.session_state["latest_df"] = df
    with st.sidebar:
        st.subheader("Analysis")
        target = st.selectbox("Target column", ["Auto-detect"] + [str(col) for col in df.columns])
        if st.button("Run full analysis", type="primary"):
            with st.status("Uploading and analyzing CSV...", expanded=True):
                upload_payload = _post_upload(uploaded)
                st.write(f"Session: {upload_payload['session_id']}")
                selected_target = None if target == "Auto-detect" else target
                st.session_state["report"] = _post_analyze(upload_payload["session_id"], selected_target)
                st.write("Analysis complete.")

    report = st.session_state.get("report")
    tabs = st.tabs(["EDA", "Trends", "Model", "XAI", "AI Report"])
    with tabs[0]:
        render_eda(df, report)
    with tabs[1]:
        render_trends(df, report)
    with tabs[2]:
        render_model(report)
    with tabs[3]:
        render_xai(report)
    with tabs[4]:
        render_report(report)
else:
    st.info("Upload a CSV to begin.")
