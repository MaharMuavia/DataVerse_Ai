from __future__ import annotations

import json
from typing import List

from config.llm_providers import ModelRouter
from graph.state import DataVerseState
from tools.ml_tools import detect_ml_task_tool, run_pycaret_tool, run_shap_tool

ML_PROMPT = (
    "You are an AutoML engineer. Given dataset metadata and user intent, "
    "write PyCaret code to train the best model. Return JSON: "
    "{task_type, pycaret_code, target_column, expected_metrics}"
)


async def ml_agent_node(state: DataVerseState) -> DataVerseState:
    router = ModelRouter()
    retries = 0

    while retries <= 2:
        try:
            dataset_path = state.get("dataset_path")
            if not dataset_path:
                state["error"] = "ml_agent failed: dataset_path missing"
                return state

            messages: List[dict] = [
                {"role": "system", "content": ML_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_message": state.get("user_message"),
                            "dataset_metadata": state.get("dataset_metadata"),
                        }
                    ),
                },
            ]
            llm_output = await router.call("ml_agent", messages)

            try:
                parsed = json.loads(llm_output)
            except Exception:
                parsed = {}

            inferred_task = detect_ml_task_tool.invoke(
                {
                    "user_message": state.get("user_message", ""),
                    "target_hint": parsed.get("target_column"),
                }
            )
            task_type = parsed.get("task_type") or inferred_task.get("task_type", "regression")

            metadata = state.get("dataset_metadata") or {}
            columns = metadata.get("columns", []) if isinstance(metadata, dict) else []
            target_col = parsed.get("target_column")
            if target_col not in columns:
                target_col = columns[-1] if columns else "target"

            pycaret_output = run_pycaret_tool.invoke(
                {
                    "task": task_type,
                    "target": target_col,
                    "df_path": dataset_path,
                }
            )

            shap_result = run_shap_tool.invoke(
                {
                    "model": None,
                    "df_path": dataset_path,
                    "target": target_col,
                }
            )

            state["ml_results"] = {
                "task_type": task_type,
                "target_column": target_col,
                "expected_metrics": parsed.get("expected_metrics", {}),
                "pycaret": pycaret_output,
                "shap": shap_result,
            }
            state["current_agent"] = "ml_agent"
            state["error"] = None
            return state
        except Exception as exc:
            retries += 1
            state["error"] = f"ml_agent failed: {exc}"
            if retries > 2:
                state["agent_plan"] = ["clarifier"]
                return state

    return state
