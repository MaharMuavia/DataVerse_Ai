from workflow.pipelines.xai_pipeline import run_xai_pipeline
from workflow.state import AnalysisState
from typing import Dict, Any

async def run_xai_node(state: AnalysisState) -> Dict[str, Any]:
    return await run_xai_pipeline(state)