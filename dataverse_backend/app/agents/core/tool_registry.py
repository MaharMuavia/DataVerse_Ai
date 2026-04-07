from abc import abstractmethod
from typing import Dict, Any, Optional, Protocol, List
from pydantic import BaseModel
from dataclasses import dataclass


@dataclass
class SessionContext:
    """Context passed to tools during execution."""
    session_id: str
    dataset_path: str  # Path to the dataset file
    working_dataset_path: Optional[str] = None  # Path to filtered dataset if active


class ChartSpec(BaseModel):
    """Specification for chart display."""
    type: str  # 'bar', 'line', 'scatter', 'heatmap', etc.
    data: Dict[str, Any]
    title: str
    x_label: Optional[str] = None
    y_label: Optional[str] = None


class TableSpec(BaseModel):
    """Specification for table display."""
    columns: list
    data: list  # List of dicts
    title: str


class NarrativeSpec(BaseModel):
    """Specification for narrative text display."""
    content: str
    tone: str = "professional"  # 'professional', 'casual', 'technical'


class ToolResult(BaseModel):
    """Result returned by tool execution."""
    success: bool
    data: Dict[str, Any]
    display: Optional[Any] = None  # ChartSpec, TableSpec, or NarrativeSpec
    error_message: Optional[str] = None
    confidence: float = 1.0


class Tool(Protocol):
    """Protocol for all tools in the registry."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

    @abstractmethod
    async def execute(self, params: Dict[str, Any], session: SessionContext) -> ToolResult:
        """Execute the tool with given parameters."""
        pass


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(self, auto_register_defaults: bool = True):
        self.tools: Dict[str, Tool] = {}
        # Backwards-compatible alias used by the new test suite.
        self.registry = self.tools
        if auto_register_defaults:
            self.register_defaults()

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool
        aliases = getattr(tool, "aliases", [])
        for alias in aliases:
            self.tools[alias] = tool

    def register_defaults(self) -> None:
        """Register the default agentic toolset."""
        from ..tools import (
            AskClarificationTool,
            CategoricalAnalysisTool,
            CompareSegmentsTool,
            ComputeStatisticsTool,
            CorrelationAnalysisTool,
            CounterfactualExplainerTool,
            CustomMetricCalculatorTool,
            DatasetProfileTool,
            DistributionPlotTool,
            ExplainModelGlobalTool,
            ExplainPredictionLocalTool,
            FilterDatasetTool,
            GenerateNarrativeTool,
            GroupAggregationTool,
            MissingValueAnalysisTool,
            OutlierDetectionTool,
            ScatterRelationshipTool,
            TimeSeriesTrendTool,
            TrainClassifierTool,
            TrainRegressorTool,
        )

        for tool in [
            DatasetProfileTool(),
            ComputeStatisticsTool(),
            DistributionPlotTool(),
            CorrelationAnalysisTool(),
            MissingValueAnalysisTool(),
            CategoricalAnalysisTool(),
            OutlierDetectionTool(),
            TimeSeriesTrendTool(),
            ScatterRelationshipTool(),
            GroupAggregationTool(),
            CompareSegmentsTool(),
            CustomMetricCalculatorTool(),
            TrainClassifierTool(),
            TrainRegressorTool(),
            ExplainModelGlobalTool(),
            ExplainPredictionLocalTool(),
            CounterfactualExplainerTool(),
            FilterDatasetTool(),
            AskClarificationTool(),
            GenerateNarrativeTool(),
        ]:
            self.register(tool)

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self.tools.keys())

    def get_tool_descriptions_for_llm(self) -> str:
        """Format tool descriptions for LLM context."""
        descriptions = []
        seen = set()
        for name, tool in self.tools.items():
            tool_identity = id(tool)
            if tool_identity in seen:
                continue
            seen.add(tool_identity)
            desc = f"TOOL: {name}\n{tool.description}\n"
            if tool.input_schema:
                desc += "PARAMETERS:\n"
                for param, param_info in tool.input_schema.items():
                    if isinstance(param_info, dict):
                        param_desc = param_info.get("description", "No description")
                    else:
                        param_desc = str(param_info)
                    desc += f"  - {param}: {param_desc}\n"
            output_schema = tool.output_schema if isinstance(tool.output_schema, dict) else {}
            desc += f"OUTPUT: {output_schema.get('description', 'Tool result')}\n"
            descriptions.append(desc)

        return "\n".join(descriptions)

    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        session: SessionContext
    ) -> ToolResult:
        """Call a tool by name."""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                data={},
                error_message=f"Tool '{tool_name}' not found",
                confidence=0.0
            )

        try:
            return await tool.execute(params, session)
        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error_message=f"Tool execution failed: {str(e)}",
                confidence=0.0
            )
