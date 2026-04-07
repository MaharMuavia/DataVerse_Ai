from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import add_messages

class AnalysisState(TypedDict):
    session_id: str
    user_query: str
    dataset_id: str
    dataset_path: str
    column_names: List[str]
    column_dtypes: Dict[str, str]

    # Intent fields
    intent: str
    sub_intent: str
    target_columns: List[str]
    chart_type: Optional[str]
    model_type: Optional[str]
    confidence: float

    # Result fields
    eda_results: Optional[Dict[str, Any]]
    eda_narrative: Optional[str]
    viz_figure_json: Optional[str]
    viz_caption: Optional[str]
    ml_task_id: Optional[str]
    ml_model_path: Optional[str]
    ml_metrics: Optional[Dict[str, Any]]
    xai_shap_plot_path: Optional[str]
    xai_lime_plot_path: Optional[str]
    xai_narrative: Optional[str]
    sql_result: Optional[List[Dict[str, Any]]]
    sql_query_used: Optional[str]

    # Conversation fields
    conversation_history: add_messages
    final_response: Optional[str]
    error_message: Optional[str]