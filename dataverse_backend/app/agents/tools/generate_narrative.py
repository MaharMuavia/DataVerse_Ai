from .base_tool import BaseTool
from ..core.tool_registry import SessionContext, ToolResult
from typing import Dict, Any
import json


class GenerateNarrativeTool(BaseTool):
    """Tool for generating business insights from analysis results."""

    def __init__(self):
        super().__init__()
        self.name = "generate_narrative"
        self.description = """LLM-generated business insight from computed stats.
USE WHEN: Need to explain analysis results in natural language."""
        self.input_schema = {
            "stats_context": {
                "type": "object",
                "description": "Dictionary of statistical results to narrate"
            },
            "tone": {
                "type": "string",
                "enum": ["professional", "casual", "technical"],
                "description": "Tone of the narrative",
                "default": "professional"
            }
        }
        self.output_schema = {
            "description": "NarrativeSpec with business insights"
        }

    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        # This would normally call an LLM, but for now we'll create a simple narrative
        stats_context = params.get("stats_context", {})
        tone = params.get("tone", "professional")

        try:
            # Generate a simple narrative based on stats
            narrative = self._generate_simple_narrative(stats_context, tone)

            narrative_spec = self.create_narrative_spec(narrative, tone)

            return ToolResult(
                success=True,
                data={"narrative": narrative},
                display=narrative_spec
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error_message=str(e),
                confidence=0.0
            )

    def _generate_simple_narrative(self, stats_context: Dict[str, Any], tone: str) -> str:
        """Generate a simple narrative from stats context."""
        if not stats_context:
            return "No statistical context provided for narrative generation."

        # This is a placeholder - in real implementation, this would call an LLM
        narrative_parts = []

        if "correlation_matrix" in stats_context:
            corr_data = stats_context["correlation_matrix"]
            narrative_parts.append("The correlation analysis reveals relationships between variables in the dataset.")

        if "statistics" in stats_context:
            stats = stats_context["statistics"]
            if stats:
                col = stats[0]["column"]
                mean_val = stats[0]["mean"]
                narrative_parts.append(f"The average value for {col} is {mean_val:.2f}.")

        if "missing_analysis" in stats_context:
            missing = stats_context["missing_analysis"]
            high_missing = [row for row in missing if row["missing_percentage"] > 10]
            if high_missing:
                cols = [row["column"] for row in high_missing]
                narrative_parts.append(f"Columns with significant missing data: {', '.join(cols)}.")

        if not narrative_parts:
            narrative_parts.append("The analysis has been completed. Key insights will be summarized here.")

        return " ".join(narrative_parts)