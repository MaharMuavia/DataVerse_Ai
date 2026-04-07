from workflow.pipelines.viz_pipeline import run_viz_pipeline
from workflow.state import AnalysisState
from typing import Dict, Any

async def run_viz_node(state: AnalysisState) -> Dict[str, Any]:
    return await run_viz_pipeline(state)