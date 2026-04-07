from langchain_openai import ChatOpenAI
from workflow.state import AnalysisState
from typing import Dict, Any

def get_top_correlations(eda_results: Dict[str, Any]) -> str:
    corr_matrix = eda_results.get("correlation_matrix", {})
    if not corr_matrix:
        return "No correlations available."

    # Flatten correlation matrix and get top 5 absolute correlations
    correlations = []
    for col1, row in corr_matrix.items():
        for col2, corr in row.items():
            if col1 != col2 and abs(corr) > 0.1:  # Ignore self and weak correlations
                correlations.append((col1, col2, corr))

    correlations.sort(key=lambda x: abs(x[2]), reverse=True)
    top_5 = correlations[:5]

    if not top_5:
        return "No significant correlations found."

    result = []
    for col1, col2, corr in top_5:
        direction = "positive" if corr > 0 else "negative"
        result.append(f"{col1} and {col2}: {direction} correlation ({corr:.2f})")

    return "\n".join(result)

def summarize_outliers(eda_results: Dict[str, Any]) -> str:
    outliers = eda_results.get("outliers", {})
    if not outliers:
        return "No outlier analysis available."

    total_outliers = sum(info["outlier_count"] for info in outliers.values())
    if total_outliers == 0:
        return "No outliers detected in numeric columns."

    top_outlier_cols = sorted(outliers.items(), key=lambda x: x[1]["outlier_count"], reverse=True)[:3]

    result = f"Total outliers detected: {total_outliers}\n"
    for col, info in top_outlier_cols:
        if info["outlier_count"] > 0:
            result += f"{col}: {info['outlier_count']} outliers\n"

    return result.strip()

async def generate_response(state: AnalysisState) -> Dict[str, Any]:
    try:
        context_parts = []

        if state.get("eda_results"):
            eda = state["eda_results"]
            context_parts.append(f"""
Dataset shape: {eda['shape']}
Missing values summary: {sum(eda['missing']['counts'].values())} total missing values
Top correlations: {get_top_correlations(eda)}
Outlier summary: {summarize_outliers(eda)}
""".strip())

        if state.get("ml_task_id"):
            context_parts.append(f"ML model training submitted. Task ID: {state['ml_task_id']}")

        if state.get("xai_narrative"):
            context_parts.append(f"XAI result: {state['xai_narrative']}")

        context = "\n\n".join(context_parts) if context_parts else "No analysis results available yet."

        system_prompt = """You are DataVerse AI, a friendly business intelligence assistant. You help non-technical users understand their data. Given the following computed results from the analytics engine, write a clear, helpful, concise response in plain English. Do NOT make up numbers or statistics. Only describe what is in the provided context. If the context is empty, say you are waiting for the computation to complete.
Keep responses under 150 words unless doing EDA summary.
Use bullet points for lists of insights."""

        user_prompt = f"User asked: {state['user_query']}\n\nComputed results:\n{context}"

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])

        return {"final_response": response.content}

    except Exception as e:
        return {"error_message": f"Response generation failed: {str(e)}"}