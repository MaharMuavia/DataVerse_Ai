from workflow.state import AnalysisState
from tasks.xai_tasks import compute_xai_task
from typing import Dict, Any

async def run_xai_pipeline(state: AnalysisState) -> Dict[str, Any]:
    if not state.get("ml_model_path"):
        return {"error_message": "No trained model found. Please train a model first by asking me to make a prediction."}

    try:
        task = compute_xai_task.delay(
            model_path=state["ml_model_path"],
            dataset_path=state["dataset_path"],
            session_id=state["session_id"]
        )

        return {"ml_task_id": task.id}

    except Exception as e:
        return {"error_message": f"XAI pipeline failed: {str(e)}"}