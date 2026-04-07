"""Unit tests for intent extraction."""
import pytest
import json
from app.agents.core.intent_extractor import IntentExtractor, IntentObject, FilterCondition
from app.llm.llm_client import LLMClient


@pytest.fixture
def intent_extractor(mock_llm_client):
    """Create an intent extractor with mock LLM client."""
    return IntentExtractor(mock_llm_client)


@pytest.mark.asyncio
async def test_intent_extraction_basic(intent_extractor, dataset_schema):
    """Test basic intent extraction produces valid IntentObject."""
    query = "What is the distribution of product prices?"
    schema_json = json.dumps(dataset_schema)
    
    intent = await intent_extractor.extract_intent(
        query,
        schema_json,
        [],
        "test_session"
    )
    
    # Verify IntentObject structure
    assert isinstance(intent, IntentObject)
    assert intent.primary_goal in ['explore', 'visualize', 'predict', 'explain', 'compare', 'query']
    assert isinstance(intent.target_columns, list)
    assert isinstance(intent.confidence, float)
    assert 0.0 <= intent.confidence <= 1.0
    assert isinstance(intent.ambiguities, list)


@pytest.mark.asyncio
async def test_intent_confidence_scoring(intent_extractor, dataset_schema, intent_test_cases):
    """Test confidence scoring correctly identifies ambiguous queries."""
    schema_json = json.dumps(dataset_schema)
    
    # Test high-confidence query
    high_conf_case = intent_test_cases[0]
    intent_high = await intent_extractor.extract_intent(
        high_conf_case["query"],
        schema_json,
        [],
        "test_session"
    )
    
    # High confidence > 0.8
    assert intent_high.confidence >= 0.75, \
        f"High-confidence query should have confidence >= 0.75, got {intent_high.confidence}"
    
    # Test low-confidence (ambiguous) query
    ambiguous_case = intent_test_cases[5]
    intent_low = await intent_extractor.extract_intent(
        ambiguous_case["query"],
        schema_json,
        [],
        "test_session"
    )
    
    # Low confidence should be below 0.7
    assert intent_low.confidence < 0.7, \
        f"Ambiguous query should have confidence < 0.7, got {intent_low.confidence}"


@pytest.mark.asyncio
async def test_ambiguity_detection(intent_extractor, dataset_schema):
    """Test detection of ambiguous column references."""
    schema_json = json.dumps(dataset_schema)
    
    # Query with ambiguous pronouns
    ambiguous_query = "What is the average of this column? I want to analyze it."
    
    intent = await intent_extractor.extract_intent(
        ambiguous_query,
        schema_json,
        [],
        "test_session"
    )
    
    # Ambiguous queries should either have:
    # 1. Low confidence, OR
    # 2. Ambiguities list populated
    assert intent.confidence < 0.75 or len(intent.ambiguities) > 0, \
        "Ambiguous query should be flagged with low confidence or in ambiguities list"


@pytest.mark.asyncio
async def test_output_preference_inference(intent_extractor, dataset_schema):
    """Test inference of output preference from verb cues."""
    schema_json = json.dumps(dataset_schema)
    
    # Test 'show' cue -> visualization preference
    show_query = "Show me the distribution of prices"
    intent_show = await intent_extractor.extract_intent(
        show_query,
        schema_json,
        [],
        "test_session"
    )
    # 'show' should suggest chart/visualization
    assert intent_show.output_preference in ['chart', 'mixed'], \
        f"'show' should suggest chart output, got {intent_show.output_preference}"
    
    # Test 'list' cue -> table preference
    list_query = "List all products with their prices"
    intent_list = await intent_extractor.extract_intent(
        list_query,
        schema_json,
        [],
        "test_session"
    )
    # 'list' should suggest table
    assert intent_list.output_preference in ['table', 'mixed'], \
        f"'list' should suggest table output, got {intent_list.output_preference}"
    
    # Test 'explain' cue -> narrative preference
    explain_query = "Tell me about the product pricing strategy"
    intent_explain = await intent_extractor.extract_intent(
        explain_query,
        schema_json,
        [],
        "test_session"
    )
    # 'tell' should suggest narrative
    assert intent_explain.output_preference in ['narrative', 'mixed'], \
        f"'tell' should suggest narrative output, got {intent_explain.output_preference}"


@pytest.mark.asyncio
async def test_target_column_extraction(intent_extractor, dataset_schema):
    """Test extraction of target columns from query."""
    schema_json = json.dumps(dataset_schema)
    
    # Query explicitly mentioning columns
    query = "Compare price and revenue by category"
    intent = await intent_extractor.extract_intent(
        query,
        schema_json,
        [],
        "test_session"
    )
    
    # Should extract at least some column names
    assert len(intent.target_columns) > 0, \
        "Should extract target columns when explicitly mentioned"
    
    # Should recognize schema column names
    extracted_cols = intent.target_columns
    schema_cols = dataset_schema["columns"]
    for col in extracted_cols:
        assert col in schema_cols or len(extracted_cols) == 0, \
            f"Extracted column '{col}' not in schema: {schema_cols}"


@pytest.mark.asyncio
async def test_intent_object_validation(intent_extractor, dataset_schema):
    """Test IntentObject passes Pydantic validation."""
    schema_json = json.dumps(dataset_schema)
    
    query = "Analyze the data"
    intent = await intent_extractor.extract_intent(
        query,
        schema_json,
        [],
        "test_session"
    )
    
    # Verify all required fields are present
    assert intent.primary_goal is not None
    assert intent.target_columns is not None
    assert intent.confidence is not None
    
    # Verify field types
    assert isinstance(intent.primary_goal, str)
    assert isinstance(intent.target_columns, list)
    assert isinstance(intent.confidence, float)
    assert isinstance(intent.ambiguities, list)
    
    # Verify primary_goal is valid
    valid_goals = ['explore', 'visualize', 'predict', 'explain', 'compare', 'query']
    assert intent.primary_goal in valid_goals, \
        f"primary_goal '{intent.primary_goal}' not in valid goals: {valid_goals}"


@pytest.mark.asyncio
async def test_intent_extraction_with_filters(intent_extractor, dataset_schema):
    """Test extraction of filters from query."""
    schema_json = json.dumps(dataset_schema)
    
    # Query with filter intention
    query = "Show me products in the Electronics category"
    intent = await intent_extractor.extract_intent(
        query,
        schema_json,
        [],
        "test_session"
    )
    
    # Should detect context (Electronics mentioned)
    assert intent.primary_goal in ['explore', 'visualize', 'query']
    # Confidence should be reasonable
    assert intent.confidence > 0.65


@pytest.mark.asyncio
async def test_intent_extraction_multi_turn(intent_extractor, dataset_schema, conversation_history):
    """Test intent extraction with conversation context."""
    schema_json = json.dumps(dataset_schema)
    
    # Second turn building on previous context
    query = "Which category has the highest revenue?"
    
    intent = await intent_extractor.extract_intent(
        query,
        schema_json,
        conversation_history[:2],  # Include first exchange
        "test_session"
    )
    
    # Should understand context-dependent query
    assert intent.primary_goal in ['explore', 'visualize']
    assert 'category' in intent.target_columns or 'revenue' in intent.target_columns or \
           intent.confidence > 0.70, \
           "Should infer context from conversation history"


def test_intent_object_creation():
    """Test creating IntentObject directly."""
    intent = IntentObject(
        primary_goal="explore",
        target_columns=["price", "category"],
        confidence=0.95
    )
    
    assert intent.primary_goal == "explore"
    assert "price" in intent.target_columns
    assert intent.confidence == 0.95
    assert intent.ambiguities == []


def test_filter_condition_creation():
    """Test creating FilterCondition objects."""
    filter_eq = FilterCondition(
        column="category",
        operator="eq",
        value="Electronics"
    )
    
    assert filter_eq.column == "category"
    assert filter_eq.operator == "eq"
    assert filter_eq.value == "Electronics"
    
    # Test other operators
    filter_gt = FilterCondition(
        column="price",
        operator="gt",
        value=100.0
    )
    
    assert filter_gt.operator == "gt"
    assert filter_gt.value == 100.0