# Placeholder implementations for remaining tools
# These would be fully implemented in a complete system

from .base_tool import BaseTool
from typing import Dict, Any


class PlaceholderTool(BaseTool):
    """Placeholder for tools not yet implemented."""

    def __init__(self, name: str, description: str):
        super().__init__()
        self.name = name
        self.description = description
        self.input_schema = {}
        self.output_schema = {"description": "Placeholder result"}

    async def execute(self, params: Dict[str, Any], session) -> Any:
        return self.create_narrative_spec(
            f"Tool '{self.name}' is not yet implemented. This is a placeholder.",
            "professional"
        )


# Create placeholder tools for remaining ones
time_series_trend = PlaceholderTool(
    "time_series_trend",
    "Resample and plot a time column vs numeric target. USE WHEN: User asks about trends over time."
)

scatter_relationship = PlaceholderTool(
    "scatter_relationship",
    "Scatter plot with optional color encoding. USE WHEN: User asks about relationships between two variables."
)

group_aggregation = PlaceholderTool(
    "group_aggregation",
    "GROUP BY equivalent — aggregate a numeric col by category. USE WHEN: User asks for grouped summaries."
)

compare_segments = PlaceholderTool(
    "compare_segments",
    "Side-by-side stats comparison for two dataset segments. USE WHEN: User wants to compare groups."
)

explain_counterfactual = PlaceholderTool(
    "explain_counterfactual",
    "DiCE counterfactual explanations. USE WHEN: User asks 'what would need to change?'"
)