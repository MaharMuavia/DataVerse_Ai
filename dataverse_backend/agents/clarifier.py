from __future__ import annotations

from typing import List

from config.llm_providers import ModelRouter
from graph.state import DataVerseState

CLARIFIER_PROMPT = (
    "Ask a short clarification question if the request is ambiguous or dataset context is missing. "
    "Be concise and list 2 to 3 options the user can pick from."
)


async def clarifier_node(state: DataVerseState) -> DataVerseState:
    router = ModelRouter()
    retries = 0

    while retries <= 2:
        try:
            messages: List[dict] = [
                {"role": "system", "content": CLARIFIER_PROMPT},
                {
                    "role": "user",
                    "content": state.get("user_message")
                    or "No dataset or ambiguous request. Ask for next step.",
                },
            ]
            text = await router.call("clarifier", messages)
            state["final_response"] = text
            state["current_agent"] = "clarifier"
            state["error"] = None
            return state
        except Exception as exc:
            retries += 1
            state["error"] = f"clarifier failed: {exc}"
            if retries > 2:
                state["final_response"] = "Please clarify your analysis goal and target columns."
                return state

    return state
