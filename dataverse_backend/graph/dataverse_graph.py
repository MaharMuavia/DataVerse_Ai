from __future__ import annotations

from importlib import import_module
from typing import Any, Dict

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from agents.anomaly_detector import anomaly_detector_node
from agents.clarifier import clarifier_node
from agents.data_analyst import data_analyst_node
from agents.insight_generator import insight_generator_node
from agents.ml_agent import ml_agent_node
from agents.orchestrator import orchestrator_node
from agents.visualizer import visualizer_node
from graph.routing import END_TOKEN, route_after_analyst, route_after_orchestrator, should_continue_or_end
from graph.state import DEFAULT_STATE, DataVerseState


def _get_sqlite_saver():
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ModuleNotFoundError:
        sqlite_mod = import_module("langgraph.checkpoint.sqlite")
        SqliteSaver = getattr(sqlite_mod, "SqliteSaver")
    return SqliteSaver
from tools.code_executor import run_python_code_tool
from tools.ml_tools import detect_ml_task_tool, run_pycaret_tool, run_shap_tool
from tools.stats_tools import (
    detect_drift_tool,
    detect_outliers_tool,
    get_column_stats_tool,
    read_csv_tool,
    run_zscore_tool,
)

def build_graph():
    graph = StateGraph(DataVerseState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("data_analyst", data_analyst_node)
    graph.add_node("visualizer", visualizer_node)
    graph.add_node("ml_agent", ml_agent_node)
    graph.add_node("insight_generator", insight_generator_node)
    graph.add_node("anomaly_detector", anomaly_detector_node)
    graph.add_node("clarifier", clarifier_node)

    graph.add_node(
        "analysis_tools",
        ToolNode(
            [
                read_csv_tool,
                run_python_code_tool,
                get_column_stats_tool,
                detect_outliers_tool,
                detect_drift_tool,
                run_zscore_tool,
            ]
        ),
    )
    graph.add_node(
        "ml_tools",
        ToolNode([detect_ml_task_tool, run_pycaret_tool, run_shap_tool]),
    )

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "data_analyst": "data_analyst",
            "visualizer": "visualizer",
            "ml_agent": "ml_agent",
            "insight_generator": "insight_generator",
            "anomaly_detector": "anomaly_detector",
            "clarifier": "clarifier",
        },
    )

    graph.add_edge("anomaly_detector", "data_analyst")
    graph.add_conditional_edges(
        "data_analyst",
        route_after_analyst,
        {
            "visualizer": "visualizer",
            "ml_agent": "ml_agent",
            "insight_generator": "insight_generator",
        },
    )
    graph.add_edge("visualizer", "ml_agent")
    graph.add_edge("ml_agent", "insight_generator")

    graph.add_conditional_edges(
        "insight_generator",
        should_continue_or_end,
        {"orchestrator": "orchestrator", END_TOKEN: END},
    )
    graph.add_edge("clarifier", END)

    return graph


def compile_app(db_path: str = "dataverse_memory.db"):
    SqliteSaver = _get_sqlite_saver()
    checkpointer = SqliteSaver.from_conn_string(db_path)
    app = build_graph().compile(checkpointer=checkpointer)
    return app


async def stream_graph_events(
    app,
    input_state: Dict[str, Any],
    user_session_id: str,
):
    config = {"configurable": {"thread_id": user_session_id}}
    async for event in app.astream_events(input_state, config=config, version="v2"):
        if event.get("event") == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            content = getattr(chunk, "content", None)
            if content:
                yield content


def make_input_state(user_message: str, dataset_path: str | None = None) -> DataVerseState:
    state = dict(DEFAULT_STATE)
    state["user_message"] = user_message
    state["dataset_path"] = dataset_path
    return state  # type: ignore[return-value]
