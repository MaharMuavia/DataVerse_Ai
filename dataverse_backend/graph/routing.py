from __future__ import annotations

from graph.state import DataVerseState


END_TOKEN = "__END__"


def route_after_orchestrator(state: DataVerseState) -> str:
    plan = state.get("agent_plan") or []
    if not plan:
        return "clarifier"

    # Run anomaly detector proactively when dataset is present.
    if state.get("dataset_path") and "anomaly_detector" not in plan:
        return "anomaly_detector"
    return str(plan[0])


def route_after_analyst(state: DataVerseState) -> str:
    plan = state.get("agent_plan") or []
    if not plan:
        return "insight_generator"

    remaining = plan[1:] if len(plan) > 1 else []
    state["agent_plan"] = remaining

    if "visualizer" in plan:
        return "visualizer"
    if "ml_agent" in plan:
        return "ml_agent"
    return "insight_generator"


def should_continue_or_end(state: DataVerseState):
    if int(state.get("iteration_count", 0)) > int(state.get("max_iterations", 6)):
        return END_TOKEN
    if state.get("final_response"):
        return END_TOKEN
    return "orchestrator"
