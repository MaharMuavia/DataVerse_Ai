"""LangGraph-based orchestrator for coordinating multi-agent analysis workflow.

Implements a state machine that routes user queries to appropriate agents:
- Orchestrator Agent: Routes queries, understands intent
- Data Analyst Agent: Performs analytical computations
- Visualization Agent: Creates visual representations
- Insight Agent: Generates business insights
- ML Agent: Trains predictive models
"""
from typing import Any, Dict, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
import json
import asyncio
from datetime import datetime

from ..core.config import settings
from ..core.logger import logger
from ..core.llm import get_llm
from ..data.data_manager import DataManager
from .memory.session_store import (
    load_session,
    save_session,
    update_session,
    add_message,
)


# ============================================================================
# STATE DEFINITION
# ============================================================================

class AnalysisState(dict):
    """State passed through the workflow graph.
    
    Key fields:
    - session_id: str - Unique session identifier
    - dataset_id: str - Dataset being analyzed
    - user_query: str - User's natural language query
    - intent: Dict - Parsed intent (category, operation, metrics)
    - analysis_results: Dict - Output from analysis agent
    - viz_spec: Dict - Visualization specification
    - ml_results: Dict - ML model results
    - error_message: str - Any error encountered
    - final_response: str - Response to send to user
    - messages: List - Conversation history
    """
    pass


# ============================================================================
# NODE: ORCHESTRATOR - PARSE INTENT & ROUTE
# ============================================================================

async def orchestrator_node(state: AnalysisState) -> AnalysisState:
    """Parse user query and determine which agents to invoke.
    
    Uses Claude to classify the query intent:
    - data_exploration: Show patterns, distributions, trends
    - visualization: Create charts and plots
    - prediction: Train ML models
    - comparison: Compare categories or time periods
    - aggregation: Summarize and compute metrics
    """
    try:
        session = load_session(state.get("session_id"))
        user_query = state.get("user_query") or session.get("user_query")
        dataset_id = state.get("dataset_id") or session.get("dataset_id")
        
        logger.info(f"[Orchestrator] Processing query: {user_query[:100]}")
        
        # Get LLM to parse intent
        llm = get_llm()
        
        prompt = f"""You are an intelligent query router for a data analysis system.
Analyze this user query and respond with a JSON object containing:
- intent: One of [exploration, visualization, prediction, comparison, aggregation]
- operation: What the user wants (e.g., "show top 10 products")
- metrics: Columns to analyze (e.g., ["product_name", "sales"])
- filters: Any temporal or categorical filters
- requires_ml: Boolean - whether prediction/ML is needed
- requires_viz: Boolean - whether visualizations should be created

User Query: "{user_query}"

Respond ONLY with valid JSON, no markdown.
"""
        
        response = await llm.ainvoke(message=prompt)
        
        try:
            # Extract JSON from response
            response_text = response.content if hasattr(response, 'content') else str(response)
            intent_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: simple rule-based classification
            intent_data = classify_intent_fallback(user_query)
        
        state["intent"] = intent_data
        state["analyzed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"[Orchestrator] Intent parsed: {intent_data.get('intent')}")
        update_session(state["session_id"], {"intent": intent_data})
        
        return state
        
    except Exception as e:
        logger.error(f"[Orchestrator] Error: {e}")
        state["error_message"] = f"Intent parsing failed: {str(e)}"
        return state


def classify_intent_fallback(query: str) -> Dict[str, Any]:
    """Fallback intent classifier using keyword matching."""
    query_lower = query.lower()
    
    intent = "exploration"
    operation = "analyze"
    requires_ml = False
    requires_viz = True
    
    if any(word in query_lower for word in ["predict", "forecast", "model", "train", "regression", "classify"]):
        intent = "prediction"
        requires_ml = True
    elif any(word in query_lower for word in ["compare", "vs", "difference"]):
        intent = "comparison"
    elif any(word in query_lower for word in ["total", "sum", "count", "average", "mean", "aggregate"]):
        intent = "aggregation"
    elif any(word in query_lower for word in ["distribution", "histogram", "scatter", "trend", "chart", "graph"]):
        intent = "visualization"
    
    return {
        "intent": intent,
        "operation": operation,
        "metrics": [],
        "filters": {},
        "requires_ml": requires_ml,
        "requires_viz": requires_viz,
    }


# ============================================================================
# NODE: DATA ANALYST - COMPUTE & AGGREGATE
# ============================================================================

async def analyst_node(state: AnalysisState) -> AnalysisState:
    """Perform data analysis based on parsed intent."""
    try:
        intent = state.get("intent", {})
        session = load_session(state["session_id"])
        
        logger.info(f"[Analyst] Running analysis for intent: {intent.get('intent')}")
        
        dm = DataManager(session_id=state["session_id"])
        df = dm.get_cleaned()
        
        if df is None or df.empty:
            state["error_message"] = "Dataset is empty or unavailable"
            return state
        
        results = {}
        
        # Compute basic statistics
        results["shape"] = {"rows": len(df), "cols": len(df.columns)}
        results["columns"] = list(df.columns)
        results["dtypes"] = {col: str(df[col].dtype) for col in df.columns}
        
        # Compute numeric summaries
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            results["statistics"] = {}
            for col in numeric_cols:
                results["statistics"][col] = {
                    "mean": float(df[col].mean()),
                    "median": float(df[col].median()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                }
        
        # Find categorical insights
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        if categorical_cols:
            results["categorical"] = {}
            for col in categorical_cols[:3]:  # Limit to first 3
                results["categorical"][col] = df[col].value_counts().head(5).to_dict()
        
        state["analysis_results"] = results
        logger.info(f"[Analyst] Analysis complete: {len(results)} result groups")
        update_session(state["session_id"], {"analysis_results": results})
        
        return state
        
    except Exception as e:
        logger.error(f"[Analyst] Error: {e}")
        state["error_message"] = f"Analysis failed: {str(e)}"
        return state


# ============================================================================
# NODE: VISUALIZER - CREATE CHART SPECS
# ============================================================================

async def visualizer_node(state: AnalysisState) -> AnalysisState:
    """Create visualization specifications based on analysis results."""
    try:
        intent = state.get("intent", {})
        analysis = state.get("analysis_results", {})
        
        if not intent.get("requires_viz"):
            logger.info("[Visualizer] Visualization not required")
            return state
        
        logger.info("[Visualizer] Creating visualization specs")
        
        # Build Vega-Lite spec (can be rendered in frontend)
        viz_spec = {
            "analysis_intent": intent.get("intent", "exploration"),
            "charts": [],
        }
        
        # Create summary statistics visualization if available
        if "statistics" in analysis:
            viz_spec["charts"].append({
                "type": "statistics_table",
                "title": "Numeric Summary Statistics",
                "data": analysis["statistics"],
            })
        
        # Create categorical breakdown if available
        if "categorical" in analysis:
            for col_name, value_counts in analysis["categorical"].items():
                viz_spec["charts"].append({
                    "type": "bar",
                    "title": f"Top categories in {col_name}",
                    "x_axis": col_name,
                    "y_axis": "count",
                    "data": value_counts,
                })
        
        state["viz_spec"] = viz_spec
        logger.info(f"[Visualizer] Generated {len(viz_spec['charts'])} visualizations")
        update_session(state["session_id"], {"viz_figure_json": viz_spec})
        
        return state
        
    except Exception as e:
        logger.error(f"[Visualizer] Error: {e}")
        state["error_message"] = f"Visualization failed: {str(e)}"
        return state


# ============================================================================
# NODE: INSIGHT AGENT - GENERATE BUSINESS TEXT
# ============================================================================

async def insight_node(state: AnalysisState) -> AnalysisState:
    """Generate business insights from analysis results."""
    try:
        logger.info("[Insight] Generating insights")
        
        intent = state.get("intent", {})
        analysis = state.get("analysis_results", {})
        
        if not analysis:
            state["final_response"] = "No analysis results available to generate insights."
            return state
        
        # Use Claude to generate a human-friendly summary
        llm = get_llm()
        
        prompt = f"""Based on this data analysis result, generate a concise business insight (2-3 sentences):

Intent: {intent.get('intent')}
Operation: {intent.get('operation')}

Analysis Results:
{json.dumps(analysis, indent=2, default=str)[:1000]}  # Limit context

Provide a natural, business-friendly insight without explaining methodology.
"""
        
        response = await llm.ainvoke(message=prompt)
        insight_text = response.content if hasattr(response, 'content') else str(response)
        
        state["final_response"] = insight_text
        logger.info("[Insight] Insight generated")
        update_session(state["session_id"], {"final_response": insight_text})
        
        return state
        
    except Exception as e:
        logger.error(f"[Insight] Error: {e}")
        # Fallback: return summary of analysis
        state["final_response"] = f"Analysis complete. Found {len(state.get('analysis_results', {}))} result groups."
        return state


# ============================================================================
# NODE: ML AGENT - TRAIN MODELS & PREDICTIONS
# ============================================================================

async def ml_node(state: AnalysisState) -> AnalysisState:
    """Trigger ML model training or prediction."""
    try:
        intent = state.get("intent", {})
        
        if not intent.get("requires_ml"):
            logger.info("[ML] ML not required for this query")
            return state
        
        logger.info("[ML] Starting ML job")
        
        # TODO: Integration with Celery async tasks
        # For now, we queue the job and return immediately
        ml_task = {
            "status": "queued",
            "task_type": intent.get("intent", "prediction"),
            "queued_at": datetime.utcnow().isoformat(),
            # "task_id": "celery_task_id_will_go_here"
        }
        
        state["ml_results"] = ml_task
        logger.info("[ML] ML job queued")
        update_session(state["session_id"], {"ml_task_id": ml_task.get("task_id")})
        
        return state
        
    except Exception as e:
        logger.error(f"[ML] Error: {e}")
        state["error_message"] = f"ML job failed: {str(e)}"
        return state


# ============================================================================
# NODE: SYNTHESIZER - COMBINE RESULTS
# ============================================================================

async def synthesizer_node(state: AnalysisState) -> AnalysisState:
    """Combine all agent outputs into final response."""
    try:
        logger.info("[Synthesizer] Combining results")
        
        # Final response already set by insight node
        # Add context from other agents
        final_response = state.get("final_response", "Analysis complete")
        
        # Add metadata
        state["response_metadata"] = {
            "analysis_results": bool(state.get("analysis_results")),
            "visualization_generated": bool(state.get("viz_spec")),
            "ml_queued": bool(state.get("ml_results")),
            "error": state.get("error_message"),
        }
        
        logger.info("[Synthesizer] Response ready")
        return state
        
    except Exception as e:
        logger.error(f"[Synthesizer] Error: {e}")
        return state


# ============================================================================
# CONDITIONAL ROUTING LOGIC
# ============================================================================

def should_analyze(state: AnalysisState) -> str:
    """Route to analyzer if not errored."""
    if state.get("error_message"):
        return "synthesizer"
    return "analyst"


def should_visualize(state: AnalysisState) -> str:
    """Route to visualizer if visualization is required."""
    intent = state.get("intent", {})
    if intent.get("requires_viz"):
        return "visualizer"
    return "insight"


def should_ml(state: AnalysisState) -> str:
    """Route to ML if model training is required."""
    intent = state.get("intent", {})
    if intent.get("requires_ml"):
        return "ml"
    return "synthesizer"


# ============================================================================
# BUILD GRAPH
# ============================================================================

def build_analysis_graph():
    """Construct the LangGraph state machine."""
    
    graph = StateGraph(AnalysisState)
    
    # Add nodes
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("visualizer", visualizer_node)
    graph.add_node("insight", insight_node)
    graph.add_node("ml", ml_node)
    graph.add_node("synthesizer", synthesizer_node)
    
    # Define entry point
    graph.set_entry_point("orchestrator")
    
    # Define edges and routing
    graph.add_conditional_edges(
        "orchestrator",
        should_analyze,
        {"analyst": "analyst", "synthesizer": "synthesizer"}
    )
    
    graph.add_edge("analyst", "visualizer")
    
    graph.add_conditional_edges(
        "visualizer",
        should_visualize,
        {"visualizer": "visualizer", "insight": "insight"}
    )
    
    graph.add_edge("visualizer", "insight")
    
    graph.add_conditional_edges(
        "insight",
        should_ml,
        {"ml": "ml", "synthesizer": "synthesizer"}
    )
    
    graph.add_edge("ml", "synthesizer")
    
    # Exit from synthesizer
    graph.add_edge("synthesizer", END)
    
    return graph.compile()


# Create the graph instance
ANALYSIS_GRAPH = build_analysis_graph()


# ============================================================================
# PUBLIC API
# ============================================================================

async def run_analysis(session_id: str, user_query: str, dataset_id: str) -> Dict[str, Any]:
    """Run the complete analysis workflow.
    
    Args:
        session_id: Unique session identifier
        user_query: User's natural language query
        dataset_id: ID of dataset to analyze
        
    Returns:
        State dictionary with all results
    """
    initial_state = {
        "session_id": session_id,
        "user_query": user_query,
        "dataset_id": dataset_id,
    }
    
    try:
        result = await ANALYSIS_GRAPH.ainvoke(initial_state)
        save_session(session_id, result)
        return result
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        return {
            "session_id": session_id,
            "error_message": str(e),
            "final_response": "An error occurred during analysis",
        }
