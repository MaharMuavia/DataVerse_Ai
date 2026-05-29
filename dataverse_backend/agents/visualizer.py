from __future__ import annotations

import json
from typing import List

from config.llm_providers import ModelRouter
from graph.state import DataVerseState

VISUALIZER_PROMPT = (
    "Generate Plotly Express code for visualization. "
    "Always return valid JSON: {plotly_json: str, chart_title: str, chart_type: str}. "
    "Use px.* functions only. df is pre-loaded."
)


async def visualizer_node(state: DataVerseState) -> DataVerseState:
    router = ModelRouter()
    retries = 0

    while retries <= 2:
        try:
            messages: List[dict] = [
                {"role": "system", "content": VISUALIZER_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_message": state.get("user_message"),
                            "dataset_metadata": state.get("dataset_metadata"),
                            "analysis_notes": state.get("insights", [])[-5:],
                        }
                    ),
                },
            ]

            llm_output = await router.call("visualizer", messages)
            try:
                parsed = json.loads(llm_output)
            except Exception:
                parsed = {
                    "plotly_json": json.dumps({"data": [], "layout": {"title": "Fallback chart"}}),
                    "chart_title": "Fallback chart",
                    "chart_type": "bar",
                }

            visualizations = list(state.get("visualizations", []))
            visualizations.append(
                {
                    "type": parsed.get("chart_type", "bar"),
                    "title": parsed.get("chart_title", "Generated chart"),
                    "data": parsed.get("plotly_json"),
                }
            )
            state["visualizations"] = visualizations
            state["error"] = None
            state["current_agent"] = "visualizer"
            return state
        except Exception as exc:
            retries += 1
            state["error"] = f"visualizer failed: {exc}"
            if retries > 2:
                state["agent_plan"] = ["clarifier"]
                return state

    return state
