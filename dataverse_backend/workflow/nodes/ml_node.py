from workflow.pipelines.ml_pipeline import run_ml_pipeline
from workflow.state import AnalysisState
from typing import Dict, Any

async def run_ml_node(state: AnalysisState) -> Dict[str, Any]:
    return await run_ml_pipeline(state)