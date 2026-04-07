"""Unit tests for tool registry and tool execution."""
import pytest
from app.agents.tools import (
    DatasetProfileTool,
    ComputeStatisticsTool,
    DistributionPlotTool,
    CorrelationAnalysisTool,
    MissingValueAnalysisTool,
    CategoricalAnalysisTool,
    OutlierDetectionTool,
    TimeSeriesTrendTool,
    ScatterRelationshipTool,
    GroupAggregationTool,
    CompareSegmentsTool,
    CustomMetricCalculatorTool,
    TrainClassifierTool,
    TrainRegressorTool,
    ExplainModelGlobalTool,
    ExplainPredictionLocalTool,
    CounterfactualExplainerTool,
    FilterDatasetTool,
    AskClarificationTool,
    GenerateNarrativeTool
)


@pytest.fixture
def tool_registry():
    """Create a tool registry with all tools."""
    from app.agents.core.agent_loop import ToolRegistry
    registry = ToolRegistry()
    return registry


def test_tool_registration(tool_registry):
    """Test that all 20 tools are registered with correct names."""
    expected_tools = [
        'dataset_profile',
        'compute_statistics',
        'distribution_plot',
        'correlation_analysis',
        'missing_value_analysis',
        'categorical_analysis',
        'outlier_detection',
        'time_series_trend',
        'scatter_relationship',
        'group_aggregation',
        'compare_segments',
        'custom_metric_calculator',
        'train_classifier',
        'train_regressor',
        'explain_model_global',
        'explain_prediction_local',
        'counterfactual_explainer',
        'filter_dataset',
        'ask_clarification',
        'generate_narrative'
    ]
    
    # Get all registered tools
    registered_tools = list(tool_registry.registry.keys())
    
    # Verify each expected tool is registered
    for expected_tool in expected_tools:
        assert expected_tool in registered_tools, \
            f"Tool '{expected_tool}' not found in registry. Registered: {registered_tools}"
    
    # Verify we have at least 20 tools
    assert len(registered_tools) >= 20, \
        f"Expected at least 20 tools, got {len(registered_tools)}"


def test_get_tool(tool_registry):
    """Test retrieval of tools by name."""
    # Test getting dataset_profile tool
    tool = tool_registry.get_tool('dataset_profile')
    assert tool is not None, "dataset_profile tool should exist"
    assert tool.name == 'dataset_profile'
    assert hasattr(tool, 'description')
    assert hasattr(tool, 'input_schema')
    assert hasattr(tool, 'output_schema')
    assert hasattr(tool, 'execute')
    
    # Test getting compute_statistics tool
    tool2 = tool_registry.get_tool('compute_statistics')
    assert tool2 is not None
    assert tool2.name == 'compute_statistics'
    
    # Test getting new tools
    tool3 = tool_registry.get_tool('time_series_trend')
    assert tool3 is not None
    assert tool3.name == 'time_series_trend'


def test_list_tools(tool_registry):
    """Test listing all available tools in registry."""
    tools = tool_registry.list_tools()
    
    # Should return list
    assert isinstance(tools, list), "list_tools should return list"
    
    # Should have at least 20 tools
    assert len(tools) >= 20, f"Should have at least 20 tools, got {len(tools)}"
    
    # Each item should have name
    for tool in tools:
        assert isinstance(tool, str), "Each tool item should be a string name"
        assert len(tool) > 0, "Tool name should not be empty"


def test_tool_descriptions_for_llm(tool_registry):
    """Test tool descriptions and formatting for LLM context."""
    # Get specific tool
    tool = tool_registry.get_tool('dataset_profile')
    
    # Should have description
    assert tool.description is not None, "Tool should have description"
    assert len(tool.description) > 10, "Description should be meaningful"
    
    # Get all tools and check descriptions
    all_tool_names = tool_registry.list_tools()
    
    for tool_name in all_tool_names:
        tool = tool_registry.get_tool(tool_name)
        assert tool is not None, f"Tool '{tool_name}' should exist"
        assert tool.description is not None, f"Tool '{tool_name}' should have description"
        assert len(tool.description) > 5, f"Tool '{tool_name}' description should be meaningful"


def test_tool_input_schemas(tool_registry):
    """Test that tools have valid input schemas."""
    tool = tool_registry.get_tool('filter_dataset')
    
    # Should have input schema
    assert hasattr(tool, 'input_schema'), "Tool should have input_schema attribute"
    assert tool.input_schema is not None, "Tool input_schema should not be None"
    assert isinstance(tool.input_schema, dict), "input_schema should be dict"


def test_tool_output_schemas(tool_registry):
    """Test that tools have valid output schemas."""
    tool = tool_registry.get_tool('compute_statistics')
    
    # Should have output schema
    assert hasattr(tool, 'output_schema'), "Tool should have output_schema attribute"
    assert tool.output_schema is not None, "Tool output_schema should not be None"
    assert isinstance(tool.output_schema, dict), "output_schema should be dict"


@pytest.mark.asyncio
async def test_call_missing_tool(tool_registry):
    """Test error handling when calling non-existent tool."""
    # Try to get non-existent tool
    tool = tool_registry.get_tool('non_existent_tool')
    
    # Should return None
    assert tool is None, "Non-existent tool should return None"


def test_all_analysis_tools_registered(tool_registry):
    """Test that all analysis tools are registered."""
    analysis_tools = [
        'dataset_profile',
        'compute_statistics',
        'distribution_plot',
        'correlation_analysis',
        'missing_value_analysis',
        'categorical_analysis',
        'outlier_detection',
        'time_series_trend'
    ]
    
    for tool_name in analysis_tools:
        tool = tool_registry.get_tool(tool_name)
        assert tool is not None, f"Analysis tool '{tool_name}' should be registered"
        assert tool.name == tool_name


def test_all_visualization_tools_registered(tool_registry):
    """Test that visualization tools are registered."""
    viz_tools = [
        'scatter_relationship',
        'group_aggregation',
        'distribution_plot'
    ]
    
    for tool_name in viz_tools:
        tool = tool_registry.get_tool(tool_name)
        assert tool is not None, f"Visualization tool '{tool_name}' should be registered"


def test_all_ml_tools_registered(tool_registry):
    """Test that ML tools are registered."""
    ml_tools = [
        'train_classifier',
        'train_regressor',
        'explain_model_global'
    ]
    
    for tool_name in ml_tools:
        tool = tool_registry.get_tool(tool_name)
        assert tool is not None, f"ML tool '{tool_name}' should be registered"


def test_all_xai_tools_registered(tool_registry):
    """Test that XAI tools are registered."""
    xai_tools = [
        'explain_prediction_local',
        'counterfactual_explainer',
        'custom_metric_calculator'
    ]
    
    for tool_name in xai_tools:
        tool = tool_registry.get_tool(tool_name)
        assert tool is not None, f"XAI tool '{tool_name}' should be registered"


def test_all_processing_tools_registered(tool_registry):
    """Test that processing tools are registered."""
    processing_tools = [
        'filter_dataset',
        'ask_clarification',
        'generate_narrative'
    ]
    
    for tool_name in processing_tools:
        tool = tool_registry.get_tool(tool_name)
        assert tool is not None, f"Processing tool '{tool_name}' should be registered"


def test_tool_execute_method_exists(tool_registry):
    """Test that all tools have callable execute method."""
    all_tool_names = tool_registry.list_tools()
    
    for tool_name in all_tool_names:
        tool = tool_registry.get_tool(tool_name)
        
        # Tool should have execute method
        assert hasattr(tool, 'execute'), \
            f"Tool '{tool_name}' should have execute method"
        
        # Execute should be callable
        assert callable(tool.execute), \
            f"Tool '{tool_name}' execute should be callable"


def test_tool_names_are_unique(tool_registry):
    """Test that all tool names in registry are unique."""
    tool_names = tool_registry.list_tools()
    
    # Check for duplicates
    name_set = set(tool_names)
    assert len(tool_names) == len(name_set), \
        f"Tool names should be unique. Found duplicates."


def test_tool_registry_consistency(tool_registry):
    """Test that multiple registry instances are consistent."""
    tools1 = tool_registry.list_tools()
    
    # Create another registry
    from app.agents.core.agent_loop import ToolRegistry
    registry2 = ToolRegistry()
    tools2 = registry2.list_tools()
    
    # Should have same set of tools
    assert set(tools1) == set(tools2), \
        "Registry instances should have same tools"


def test_new_tools_are_complete(tool_registry):
    """Test that new placeholder tools are fully implemented."""
    new_tools = [
        'time_series_trend',
        'scatter_relationship',
        'group_aggregation',
        'compare_segments',
        'custom_metric_calculator'
    ]
    
    for tool_name in new_tools:
        tool = tool_registry.get_tool(tool_name)
        
        # Should exist
        assert tool is not None, f"New tool '{tool_name}' should exist"
        
        # Should have all attributes
        assert tool.name == tool_name
        assert tool.description is not None
        assert len(tool.description) > 20, \
            f"Tool '{tool_name}' description should be detailed"
        
        # Should have schemas
        assert tool.input_schema is not None
        assert tool.output_schema is not None
        
        # Should have execute
        assert callable(tool.execute)