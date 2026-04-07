from workflow.pipelines.eda_pipeline import run_eda_pipeline
from workflow.state import AnalysisState
from typing import Dict, Any

async def run_eda_node(state: AnalysisState) -> Dict[str, Any]:
    return await run_eda_pipeline(state)