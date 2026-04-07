from workflow.state import AnalysisState

def route_by_intent(state: AnalysisState) -> str:
    intent = state.get("intent", "")

    if intent == "EDA":
        return "run_eda"
    elif intent == "VIZ":
        return "run_viz"
    elif intent == "ML":
        return "run_ml"
    elif intent == "XAI":
        # Check if model exists
        if state.get("ml_model_path") is None:
            state["sub_intent"] = "xai_after_ml"
            return "run_ml"
        return "run_xai"
    elif intent == "SQL":
        return "run_sql"
    elif intent == "CHITCHAT":
        return "generate_response"
    else:
        return "generate_response"