"""Unit tests for conversation memory."""
import pytest
from datetime import timedelta, datetime
from app.memory.conversation_memory import ConversationMemory, SessionContext
from app.agents.core.intent_extractor import IntentObject, FilterCondition


@pytest.fixture
def memory():
    """Create a conversation memory instance for testing."""
    return ConversationMemory()


def test_create_session(memory, dataset_schema):
    """Test creating a new session with valid data."""
    session_id = "test_session_1"
    session = memory.create_session(session_id, dataset_schema)
    
    # Verify session creation
    assert session is not None, "Session creation should return SessionContext"
    assert session.session_id == session_id, "Session ID should match"
    assert len(session.messages) == 0, "New session should have no messages"
    assert session.dataset_schema is not None, "Session should store schema"


def test_create_session_with_empty_schema(memory):
    """Test creating session with empty schema."""
    session = memory.create_session("test_session_empty", {})
    
    assert session.session_id == "test_session_empty"
    assert session.dataset_schema == {}


def test_get_session(memory, dataset_schema):
    """Test retrieving an existing session."""
    session_id = "test_session_2"
    memory.create_session(session_id, dataset_schema)
    
    # Retrieve the session
    retrieved = memory.get_session(session_id)
    
    assert retrieved is not None, "Should retrieve created session"
    assert retrieved.session_id == session_id, "Retrieved session should have correct ID"
    assert retrieved.dataset_schema == dataset_schema, "Schema should be preserved"


def test_get_nonexistent_session(memory):
    """Test retrieving non-existent session returns None."""
    retrieved = memory.get_session("non_existent_session_xyz")
    
    assert retrieved is None, "Retrieving non-existent session should return None"


def test_add_message_simple(memory, dataset_schema):
    """Test adding a simple message to session."""
    session_id = "test_session_3"
    memory.create_session(session_id, dataset_schema)
    
    # Add message
    memory.add_message(session_id, "user", "What is the average price?")
    
    # Verify message was added
    messages = memory.get_recent_messages(session_id)
    assert len(messages) >= 1, "Message should be added to session"
    assert messages[-1].role == "user", "Message role should be 'user'"
    assert "average price" in messages[-1].content, "Message content should be preserved"


def test_add_multiple_messages(memory, dataset_schema):
    """Test adding multiple messages in sequence."""
    session_id = "test_session_multi"
    memory.create_session(session_id, dataset_schema)
    
    # Add multiple messages
    memory.add_message(session_id, "user", "First question")
    memory.add_message(session_id, "assistant", "First answer")
    memory.add_message(session_id, "user", "Follow-up question")
    memory.add_message(session_id, "assistant", "Follow-up answer")
    
    # Verify all messages
    messages = memory.get_recent_messages(session_id)
    assert len(messages) >= 4, "All 4 messages should be added"
    
    # Verify order
    roles = [msg.role for msg in messages[-4:]]
    assert roles == ["user", "assistant", "user", "assistant"], \
        "Messages should maintain order"


def test_add_message_with_intent(memory, dataset_schema):
    """Test adding messages with intent objects."""
    session_id = "test_session_4"
    memory.create_session(session_id, dataset_schema)
    
    # Create intent object
    intent = IntentObject(
        primary_goal="explore",
        target_columns=["price", "category"],
        confidence=0.95,
        output_preference="chart"
    )
    
    # Add message with intent
    memory.add_message(
        session_id,
        "user",
        "Show me the distribution of prices",
        intent_object=intent
    )
    
    # Retrieve and verify
    messages = memory.get_recent_messages(session_id)
    assert messages[-1].intent_object is not None, \
        "Message should have intent_object attached"
    assert messages[-1].intent_object.primary_goal == "explore", \
        "Intent goal should be preserved"
    assert "price" in messages[-1].intent_object.target_columns, \
        "Intent target columns should be preserved"


def test_conversation_history(memory, dataset_schema):
    """Test retrieving complete conversation history."""
    session_id = "test_session_5"
    memory.create_session(session_id, dataset_schema)
    
    # Add conversation turns
    memory.add_message(session_id, "user", "What is the data shape?")
    memory.add_message(session_id, "assistant", "The dataset has 1000 rows and 9 columns")
    memory.add_message(session_id, "user", "What about missing values?")
    memory.add_message(session_id, "assistant", "About 5% of values are missing")
    
    # Get history
    history = memory.get_conversation_history(session_id)
    
    assert len(history) >= 4, "History should contain all 4 messages"
    
    # Verify structure
    first_msg = history[0]
    assert "role" in first_msg, "Each message should have role"
    assert "content" in first_msg, "Each message should have content"
    
    # Verify conversation alternation
    for i, msg in enumerate(history):
        if i % 2 == 0:
            assert msg["role"] == "user", f"Message {i} should be user"
        else:
            assert msg["role"] == "assistant", f"Message {i} should be assistant"


def test_active_filters(memory, dataset_schema):
    """Test filter management in session."""
    session_id = "test_session_6"
    memory.create_session(session_id, dataset_schema)
    
    # Create filters
    filter1 = FilterCondition(column="category", operator="eq", value="Electronics")
    filter2 = FilterCondition(column="price", operator="gt", value=100.0)
    filters = [filter1, filter2]
    
    # Update filters
    memory.update_active_filters(session_id, filters)
    
    # Retrieve and verify
    retrieved = memory.get_active_filters(session_id)
    
    assert len(retrieved) >= 2, "Both filters should be stored"
    assert retrieved[0].column == "category", "First filter column should match"
    assert retrieved[0].value == "Electronics", "First filter value should match"
    assert retrieved[1].column == "price", "Second filter column should match"
    assert retrieved[1].operator == "gt", "Second filter operator should match"


def test_update_filters_replaces_previous(memory, dataset_schema):
    """Test that updating filters replaces previous filters."""
    session_id = "test_session_filters"
    memory.create_session(session_id, dataset_schema)
    
    # Add initial filters
    filter1 = FilterCondition(column="category", operator="eq", value="Electronics")
    memory.update_active_filters(session_id, [filter1])
    
    # Add new filters (should replace)
    filter2 = FilterCondition(column="price", operator="gt", value=100.0)
    filter3 = FilterCondition(column="region", operator="eq", value="North")
    memory.update_active_filters(session_id, [filter2, filter3])
    
    # Verify old filter is replaced
    retrieved = memory.get_active_filters(session_id)
    assert len(retrieved) == 2, "Should have 2 filters (old one replaced)"
    
    col_names = [f.column for f in retrieved]
    assert "category" not in col_names, "Old category filter should be removed"
    assert "price" in col_names, "New price filter should exist"


def test_working_dataset_ref(memory, dataset_schema):
    """Test working dataset reference management."""
    session_id = "test_session_7"
    memory.create_session(session_id, dataset_schema)
    
    # Set working dataset reference
    ref = "data/filtered_dataset_v1.parquet"
    memory.set_working_dataset_ref(session_id, ref)
    
    # Retrieve and verify
    retrieved = memory.get_working_dataset_ref(session_id)
    assert retrieved == ref, "Working dataset reference should be preserved"


def test_working_dataset_ref_update(memory, dataset_schema):
    """Test updating working dataset reference."""
    session_id = "test_session_ref_update"
    memory.create_session(session_id, dataset_schema)
    
    # Set initial reference
    ref1 = "data/original.parquet"
    memory.set_working_dataset_ref(session_id, ref1)
    
    # Update reference
    ref2 = "data/filtered.parquet"
    memory.set_working_dataset_ref(session_id, ref2)
    
    # Verify new reference
    retrieved = memory.get_working_dataset_ref(session_id)
    assert retrieved == ref2, "Working dataset reference should be updated"


def test_session_ttl_cleanup(memory, dataset_schema):
    """Test session TTL and automatic cleanup."""
    session_id = "test_session_8"
    memory.create_session(session_id, dataset_schema)
    
    # Verify session exists
    session = memory.get_session(session_id)
    assert session is not None, "Session should exist initially"
    
    # Manually expire the session (simulate 3 hours old)
    session.last_activity = datetime.now() - timedelta(hours=3)
    
    # Run cleanup
    memory._cleanup_expired_sessions()
    
    # Verify session is removed
    expired_session = memory.get_session(session_id)
    assert expired_session is None, "Expired session should be cleaned up"


def test_session_ttl_not_expired(memory, dataset_schema):
    """Test that recent sessions are not cleaned up."""
    session_id = "test_session_recent"
    memory.create_session(session_id, dataset_schema)
    
    # Add recent activity
    memory.add_message(session_id, "user", "Recent message")
    
    # Run cleanup (session is recent, should NOT be removed)
    memory._cleanup_expired_sessions()
    
    # Verify session still exists
    session = memory.get_session(session_id)
    assert session is not None, "Recent session should not be cleaned up"


def test_session_summary(memory, dataset_schema):
    """Test getting session summary."""
    session_id = "test_session_9"
    memory.create_session(session_id, dataset_schema)
    
    # Add some messages
    memory.add_message(session_id, "user", "Message 1")
    memory.add_message(session_id, "assistant", "Response 1")
    
    # Get summary
    summary = memory.get_session_summary(session_id)
    
    # Verify summary structure
    assert summary is not None, "Summary should not be None"
    assert summary["session_id"] == session_id, "Summary should include session_id"
    assert summary["message_count"] >= 2, "Summary should count messages"
    assert "dataset_schema" in summary or "dataset_columns" in summary, \
        "Summary should include schema information"


def test_session_summary_empty_session(memory):
    """Test summary of session with no messages."""
    session_id = "test_session_empty_summary"
    memory.create_session(session_id, {})
    
    summary = memory.get_session_summary(session_id)
    
    assert summary["session_id"] == session_id
    assert summary.get("message_count", 0) == 0, "Empty session should have 0 messages"


def test_get_recent_messages_with_limit(memory, dataset_schema):
    """Test retrieving recent messages with limit."""
    session_id = "test_session_limit"
    memory.create_session(session_id, dataset_schema)
    
    # Add 5 messages
    for i in range(5):
        role = "user" if i % 2 == 0 else "assistant"
        memory.add_message(session_id, role, f"Message {i}")
    
    # Get last 2 messages
    recent = memory.get_recent_messages(session_id, limit=2)
    
    assert len(recent) == 2, "Should return only 2 messages with limit=2"
    # Verify they are the most recent
    assert "Message 3" in recent[0].content or "Message 4" in recent[1].content, \
        "Should return the most recent messages"


def test_message_timestamp_ordering(memory, dataset_schema):
    """Test that messages maintain timestamp order."""
    session_id = "test_session_order"
    memory.create_session(session_id, dataset_schema)
    
    # Add messages
    memory.add_message(session_id, "user", "First")
    memory.add_message(session_id, "assistant", "Second")
    memory.add_message(session_id, "user", "Third")
    
    # Get messages
    messages = memory.get_recent_messages(session_id)
    
    # Verify timestamps are ordered
    for i in range(len(messages) - 1):
        assert messages[i].timestamp <= messages[i + 1].timestamp, \
            "Messages should be ordered by timestamp"


@pytest.mark.asyncio
async def test_session_context_with_conversation_history(memory, dataset_schema, conversation_history):
    """Test session with realistic conversation history."""
    session_id = "test_session_realistic"
    memory.create_session(session_id, dataset_schema)
    
    # Simulate multi-turn conversation
    for turn in conversation_history:
        memory.add_message(
            session_id,
            turn.get("role", "user"),
            turn.get("content", "")
        )
    
    # Verify history
    history = memory.get_conversation_history(session_id)
    assert len(history) == len(conversation_history), \
        "All conversation turns should be stored"
    
    # Get summary
    summary = memory.get_session_summary(session_id)
    assert summary["message_count"] >= len(conversation_history), \
        "Summary should reflect all messages"