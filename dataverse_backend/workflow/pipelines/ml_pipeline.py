from workflow.state import AnalysisState
from tasks.ml_tasks import train_model_task
from typing import Dict, Any

async def run_ml_pipeline(state: AnalysisState) -> Dict[str, Any]:
    try:
        target = state["target_columns"][0] if state["target_columns"] else None
        if not target or target not in state["column_names"]:
            return {"error_message": "Please specify which column to predict. Available columns: " + ", ".join(state["column_names"])}

        model_type = state.get("model_type")
        if not model_type:
            # Infer from target column unique values
            # Load df to check
            import pandas as pd
            if state["dataset_path"].endswith('.xlsx'):
                df = pd.read_excel(state["dataset_path"])
            else:
                df = pd.read_csv(state["dataset_path"])

            unique_vals = df[target].nunique()
            model_type = "classification" if unique_vals <= 10 else "regression"

        # Submit Celery task
        task = train_model_task.delay(
            dataset_path=state["dataset_path"],
            target_column=target,
            model_type=model_type,
            session_id=state["session_id"]
        )

        return {"ml_task_id": task.id, "model_type": model_type}

    except Exception as e:
        return {"error_message": f"ML pipeline failed: {str(e)}"}