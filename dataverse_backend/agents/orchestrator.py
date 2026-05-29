from __future__ import annotations

import json
from typing import Any, Dict, List

from config.llm_providers import ModelRouter
from graph.state import DataVerseState

ORCHESTRATOR_PROMPT = (
    "You are the master orchestrator of a BI platform. Given a user request "
    "and dataset metadata, output a JSON plan: "
    "{agent_plan: [list of agents], reasoning: string}. "
    "Available agents: data_analyst, visualizer, ml_agent, "
    "insight_generator, anomaly_detector, clarifier"
)


def _safe_json(text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        return fallback


async def orchestrator_node(state: DataVerseState) -> DataVerseState:
    router = ModelRouter()
    retries = 0

    while retries <= 2:
        try:
            if not state.get("dataset_metadata"):
                state["agent_plan"] = ["clarifier"]
                state["current_agent"] = "orchestrator"
                return state

            messages: List[dict] = [
                {"role": "system", "content": ORCHESTRATOR_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_message": state.get("user_message"),
                            "dataset_metadata": state.get("dataset_metadata"),
                            "conversation_history": state.get("conversation_history", [])[-10:],
                        }
                    ),
                },
            ]

            llm_output = await router.call("orchestrator", messages)
            parsed = _safe_json(llm_output, {"agent_plan": ["data_analyst", "insight_generator"]})
            plan = parsed.get("agent_plan") or ["clarifier"]

            state["agent_plan"] = [str(x) for x in plan]
            state["current_agent"] = "orchestrator"
            state["iteration_count"] = int(state.get("iteration_count", 0)) + 1
            state["error"] = None
            return state
        except Exception as exc:
            retries += 1
            state["error"] = f"orchestrator failed: {exc}"
            if retries > 2:
                state["agent_plan"] = ["clarifier"]
                return state

    return state
