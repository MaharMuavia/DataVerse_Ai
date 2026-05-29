from __future__ import annotations

import json
from typing import Any, Dict, List

from config.llm_providers import ModelRouter
from graph.state import DataVerseState
from tools.code_executor import run_python_code_tool
from tools.stats_tools import get_column_stats_tool

ANALYST_PROMPT = (
    "You are a senior data analyst. Write clean, executable Python code "
    "using pandas and numpy to answer the user's question about their dataset. "
    "Always return a JSON with keys: {code: str, output_description: str}. "
    "Dataset is loaded as variable 'df' in the execution context."
)


async def data_analyst_node(state: DataVerseState) -> DataVerseState:
    router = ModelRouter()
    retries = 0

    while retries <= 2:
        try:
            dataset_path = state.get("dataset_path")
            if not dataset_path:
                state["error"] = "data_analyst failed: dataset_path missing"
                return state

            stats = get_column_stats_tool.invoke({"df_path": dataset_path})
            state["dataset_metadata"] = stats

            messages: List[dict] = [
                {"role": "system", "content": ANALYST_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": state.get("user_message"),
                            "dataset_metadata": state.get("dataset_metadata"),
                        }
                    ),
                },
            ]

            llm_output = await router.call("data_analyst", messages)
            try:
                parsed = json.loads(llm_output)
            except Exception:
                parsed = {
                    "code": "result = {'note': 'fallback analysis used'}",
                    "output_description": llm_output,
                }

            generated_code = parsed.get("code", "result = {'note': 'no code generated'}")
            prelude = (
                "import pandas as pd\n"
                "import numpy as np\n"
                f"_p = {dataset_path!r}\n"
                "if _p.lower().endswith('.csv'):\n"
                "    df = pd.read_csv(_p)\n"
                "elif _p.lower().endswith(('.parquet', '.pq')):\n"
                "    df = pd.read_parquet(_p)\n"
                "elif _p.lower().endswith(('.xlsx', '.xls')):\n"
                "    df = pd.read_excel(_p)\n"
                "elif _p.lower().endswith('.json'):\n"
                "    df = pd.read_json(_p)\n"
                "elif _p.lower().endswith('.pkl'):\n"
                "    df = pd.read_pickle(_p)\n"
                "else:\n"
                "    df = pd.read_csv(_p)\n"
            )
            execution = run_python_code_tool.invoke({"code": prelude + generated_code})

            code_history = list(state.get("code_executed", []))
            code_history.append(generated_code)
            state["code_executed"] = code_history

            insights = list(state.get("insights", []))
            insights.append(str(parsed.get("output_description", "Analysis completed")))
            if execution.get("error"):
                insights.append(f"Execution warning: {execution['error']}")
            else:
                insights.append(f"Execution result: {execution.get('output')}")
            state["insights"] = insights

            state["error"] = None
            state["current_agent"] = "data_analyst"
            return state
        except Exception as exc:
            retries += 1
            state["error"] = f"data_analyst failed: {exc}"
            if retries > 2:
                state["agent_plan"] = ["clarifier"]
                return state

    return state
