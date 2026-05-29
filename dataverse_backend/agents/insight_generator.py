from __future__ import annotations

import json
from typing import List

from config.llm_providers import ModelRouter
from graph.state import DataVerseState

INSIGHT_PROMPT = (
    "You are a senior business analyst. Given data stats, visualizations, "
    "and ML results, generate exactly 3 actionable business insights. "
    "Format: {insights: [{finding, implication, recommendation}], "
    "summary: str, confidence: high/medium/low}"
)


async def insight_generator_node(state: DataVerseState) -> DataVerseState:
    router = ModelRouter()
    retries = 0

    while retries <= 2:
        try:
            messages: List[dict] = [
                {"role": "system", "content": INSIGHT_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_message": state.get("user_message"),
                            "dataset_metadata": state.get("dataset_metadata"),
                            "visualizations": state.get("visualizations", []),
                            "ml_results": state.get("ml_results"),
                            "analysis_notes": state.get("insights", []),
                        }
                    ),
                },
            ]

            llm_output = await router.call("insight_generator", messages)
            try:
                parsed = json.loads(llm_output)
            except Exception:
                parsed = {
                    "insights": [
                        {
                            "finding": "Insufficient structured insight JSON from model.",
                            "implication": "Fallback summary used.",
                            "recommendation": "Re-run with clearer target KPI.",
                        }
                    ],
                    "summary": llm_output,
                    "confidence": "low",
                }

            insights = list(state.get("insights", []))
            for item in parsed.get("insights", [])[:5]:
                if isinstance(item, dict):
                    insights.append(
                        "Finding: {finding} | Implication: {implication} | Recommendation: {recommendation}".format(
                            finding=item.get("finding", ""),
                            implication=item.get("implication", ""),
                            recommendation=item.get("recommendation", ""),
                        )
                    )
            state["insights"] = insights
            state["final_response"] = parsed.get("summary", "Analysis completed.")
            state["current_agent"] = "insight_generator"
            state["error"] = None
            return state
        except Exception as exc:
            retries += 1
            state["error"] = f"insight_generator failed: {exc}"
            if retries > 2:
                state["final_response"] = "I could not complete insight generation. Please clarify your request."
                state["agent_plan"] = ["clarifier"]
                return state

    return state
