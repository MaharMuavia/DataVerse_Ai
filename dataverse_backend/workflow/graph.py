from langgraph.graph import StateGraph, END
from workflow.state import AnalysisState
from workflow.nodes.eda_node import run_eda_node
from workflow.nodes.narrate_node import generate_response
from workflow.intent.classifier import classify_intent
from workflow.router import route_by_intent

def build_graph() -> StateGraph:
    graph = StateGraph(AnalysisState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("run_eda", run_eda_node)
    graph.add_node("generate_response", generate_response)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "run_eda": "run_eda",
            "generate_response": "generate_response",
        }
    )

    graph.add_edge("run_eda", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()

ANALYSIS_GRAPH = build_graph()