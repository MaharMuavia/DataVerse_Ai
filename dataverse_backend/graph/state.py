from __future__ import annotations

from typing import Any, Annotated, List, Optional, TypedDict
import operator


class DataVerseState(TypedDict):
    # Core
    user_message: str
    conversation_history: Annotated[List[dict], operator.add]
    dataset_path: Optional[str]
    dataset_metadata: Optional[dict]

    # Agent routing
    current_agent: str
    agent_plan: Optional[List[str]]

    # Outputs
    code_executed: Annotated[List[str], operator.add]
    visualizations: Annotated[List[dict], operator.add]
    ml_results: Optional[dict]
    insights: Annotated[List[str], operator.add]
    final_response: Optional[str]

    # Control
    error: Optional[str]
    iteration_count: int
    max_iterations: int


DEFAULT_STATE: DataVerseState = {
    "user_message": "",
    "conversation_history": [],
    "dataset_path": None,
    "dataset_metadata": None,
    "current_agent": "orchestrator",
    "agent_plan": None,
    "code_executed": [],
    "visualizations": [],
    "ml_results": None,
    "insights": [],
    "final_response": None,
    "error": None,
    "iteration_count": 0,
    "max_iterations": 6,
}


def merge_state(base: DataVerseState, updates: dict[str, Any]) -> DataVerseState:
    merged = dict(base)
    merged.update(updates)
    return merged  # type: ignore[return-value]
