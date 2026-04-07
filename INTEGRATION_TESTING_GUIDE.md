# Integration Testing Guide for Agentic LLM Core

## Overview
Comprehensive integration testing strategy for DataVerse AI agent loop, covering all phases from intent extraction through report generation.

## Test Environment Setup

### Prerequisites
```bash
# 1. Database setup
python dataverse_backend/setup_database.py

# 2. Sample dataset
cp retail_mart_processed_v1.csv /tmp/test_data.csv

# 3. Redis (optional, for production)
# docker run -d -p 6379:6379 redis:latest

# 4. Install test dependencies
pip install pytest pytest-asyncio pytest-cov responses
```

### DeepAnalyze/Ollama Verification
```bash
# Check LLM is running
curl http://localhost:11434/api/tags

# Expected response: {"models": [...]}
```

## Integration Test Suite Structure

### 1. End-to-End Query Flow Tests

```python
# tests/integration/test_full_query_flow.py

@pytest.mark.asyncio
async def test_simple_exploration_query():
    """E2E test: User asks exploratory question → Agent plans → Executes tools → Returns response"""
    
    # Setup
    session_id = "test_session_001"
    dataset_path = "/tmp/test_data.csv"
    query = "What is the distribution of product categories?"
    
    # Initialize agent
    from app.agents.core.agent_loop import AgentLoop
    from app.agents.core.tool_registry import ToolRegistry
    from app.memory.conversation_memory import ConversationMemory
    
    memory = ConversationMemory()
    registry = ToolRegistry()
    loop = AgentLoop(registry=registry, memory=memory, max_iterations=5)
    
    # Execute
    response = await loop.run(query, session_id, dataset_path)
    
    # Validate
    assert response.narrative, "Should return narrative"
    assert len(response.charts) > 0 or len(response.tables) > 0, "Should have charts or tables"
    assert response.narrative.lower() not in ["no results", "error"]
    assert len(response.narrative) > 50, "Narrative should be substantial"


@pytest.mark.asyncio
async def test_complex_prediction_flow():
    """E2E test: Prediction query → Model train → Explanation"""
    
    query = "Build a model to predict product sales and explain what drives it"
    session_id = "test_session_002"
    
    loop = AgentLoop(...)
    response = await loop.run(query, session_id, dataset_path)
    
    # Should execute multiple tools in sequence
    assert "model" in response.narrative.lower() or len(response.model_results) > 0
    assert response.explanation  # Should have XAI output
    assert "feature" in response.explanation.lower() or response.narrative.lower()


@pytest.mark.asyncio
async def test_clarification_flow():
    """E2E test: Ambiguous query → Clarification request → Follow-up"""
    
    # Ambiguous query
    query = "Analyze it"
    session_id = "test_session_003"
    
    loop = AgentLoop(...)
    response = await loop.run(query, session_id, dataset_path)
    
    # Should trigger clarification
    # Response should indicate clarification needed or ask_clarification tool was called
    assert "clarif" in response.narrative.lower() or response.explanation is None


@pytest.mark.asyncio
async def test_error_recovery_flow():
    """E2E test: Tool error → Agent recovery → Alternative approach"""
    
    # Query that might cause tool error
    query = "Forecast the next 100 years of data"
    session_id = "test_session_004"
    
    loop = AgentLoop(...)
    response = await loop.run(query, session_id, dataset_path)
    
    # Should handle gracefully without crashing
    assert response is not None
    assert response.narrative  # Should have fallback response
```

### 2. Tool Integration Tests

```python
# tests/integration/test_tools_integration.py

@pytest.mark.asyncio
async def test_analysis_tool_chain():
    """Tools can chain: profile → statistics → distribution"""
    
    from app.agents.tools import (
        DatasetProfileTool, ComputeStatisticsTool, DistributionPlotTool
    )
    
    dataset_path = "/tmp/test_data.csv"
    session = {"session_id": "test", "dataset_path": dataset_path}
    
    # Step 1: Profile
    profile = DatasetProfileTool()
    result1 = await profile.execute({}, session)
    assert result1.success, f"Profile failed: {result1.error_message}"
    
    # Step 2: Statistics
    stats = ComputeStatisticsTool()
    result2 = await stats.execute({}, session)
    assert result2.success
    
    # Step 3: Distribution
    dist = DistributionPlotTool()
    result3 = await dist.execute({"columns": ["price", "quantity"]}, session)
    assert result3.success
    assert result3.display  # Should have chart


@pytest.mark.asyncio
async def test_ml_model_pipeline():
    """ML tools can chain: train → explain"""
    
    from app.agents.tools import TrainClassifierTool, ExplainModelGlobalTool
    
    session = {"session_id": "test", "dataset_path": "/tmp/test_data.csv"}
    
    # Train model
    trainer = TrainClassifierTool()
    train_result = await trainer.execute(
        {"target": "category", "test_size": 0.2},
        session
    )
    assert train_result.success
    model_id = train_result.data.get("model_id")
    
    # Explain model
    explainer = ExplainModelGlobalTool()
    explain_result = await explainer.execute(
        {"model_id": model_id},
        session
    )
    assert explain_result.success
    assert "top_features" in explain_result.data


@pytest.mark.asyncio
async def test_filter_and_analyze():
    """Filter dataset then analyze: filter → profile"""
    
    from app.agents.tools import FilterDatasetTool, DatasetProfileTool
    
    session = {"session_id": "test", "dataset_path": "/tmp/test_data.csv"}
    
    # Filter
    filterer = FilterDatasetTool()
    filter_result = await filterer.execute(
        {"filters": [{"column": "category", "operator": "eq", "value": "Electronics"}]},
        session
    )
    assert filter_result.success
    
    # Update session with filtered dataset
    filtered_ref = filter_result.data.get("filtered_dataset_path")
    session["dataset_path"] = filtered_ref
    
    # Profile filtered data
    profiler = DatasetProfileTool()
    profile_result = await profiler.execute({}, session)
    assert profile_result.success
```

### 3. Memory & Session Tests

```python
# tests/integration/test_memory_integration.py

@pytest.mark.asyncio
async def test_multi_turn_conversation():
    """Multi-turn conversation maintains context"""
    
    from app.memory.conversation_memory import ConversationMemory
    from app.agents.core.intent_extractor import IntentExtractor
    
    memory = ConversationMemory()
    session_id = "test_session"
    schema = {"columns": ["price", "category", "quantity"]}
    
    # Turn 1: Create session
    memory.create_session(session_id, schema)
    
    # Turn 2: User asks question
    intent1 = IntentExtractor().extract_intent(
        "What are the categories?",
        json.dumps(schema),
        [],
        session_id
    )
    memory.add_message(session_id, "user", "What are the categories?", intent1, [])
    memory.add_message(session_id, "assistant", "Categories: A, B, C", None, [])
    
    # Turn 3: Follow-up question with context
    history = memory.get_conversation_history(session_id)
    assert len(history) == 2, "Should have 2 turns"
    
    intent2 = IntentExtractor().extract_intent(
        "Filter to category A",
        json.dumps(schema),
        history,
        session_id
    )
    # Should infer 'category' from context
    assert "category" in intent2.target_columns or intent2.confidence > 0.7
    
    memory.add_message(session_id, "user", "Filter to category A", intent2, [])
    
    # Turn 4: Verify session state
    session = memory.get_session(session_id)
    assert len(session.messages) == 4
```

### 4. API Integration Tests

```python
# tests/integration/test_api_integration.py

@pytest.mark.asyncio
async def test_upload_and_query_flow():
    """E2E: Upload file → Query → Get response via API"""
    
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    # Upload dataset
    with open("/tmp/test_data.csv", "rb") as f:
        response = client.post(
            "/upload",
            files={"file": ("test.csv", f)}
        )
    
    assert response.status_code == 200
    upload_data = response.json()
    session_id = upload_data.get("session_id")
    assert session_id, "Should return session_id"
    
    # Query with new agent endpoint
    query_response = client.post(
        "/agent/query",
        json={"session_id": session_id, "query": "Analyze this dataset"}
    )
    
    assert query_response.status_code == 200
    result = query_response.json()
    assert "narrative" in result
    assert result["narrative"]


@pytest.mark.asyncio
async def test_proactive_insights_endpoint():
    """Proactive insights generated after upload"""
    
    client = TestClient(app)
    
    # Upload
    response = client.post(
        "/upload",
        files={"file": ("test.csv", open("/tmp/test_data.csv", "rb"))}
    )
    session_id = response.json()["session_id"]
    
    # Get proactive insights
    insights_response = client.get(f"/session/{session_id}/proactive-insights")
    
    assert insights_response.status_code == 200
    insights = insights_response.json()
    assert "insights" in insights
    assert len(insights["insights"]) >= 1


@pytest.mark.asyncio
async def test_report_generation_endpoint():
    """Report generated from session analysis"""
    
    client = TestClient(app)
    
    # Query first
    response = client.post(
        "/agent/query",
        json={"session_id": "test_session", "query": "Analyze data"}
    )
    
    # Generate report
    report_response = client.post(
        "/generate-report",
        json={"session_id": "test_session", "format": "json"}
    )
    
    assert report_response.status_code == 200
    report = report_response.json()
    assert "executive_summary" in report
    assert "sections" in report
```

### 5. Performance & Load Tests

```python
# tests/integration/test_performance.py

@pytest.mark.asyncio
async def test_query_response_time():
    """Queries complete within SLA"""
    
    import time
    from app.agents.core.agent_loop import AgentLoop
    
    loop = AgentLoop(...)
    
    queries = [
        "What is the distribution?",
        "Show top categories",
        "Compute statistics"
    ]
    
    times = []
    for query in queries:
        start = time.time()
        response = await loop.run(query, "session", "/tmp/test_data.csv")
        elapsed = time.time() - start
        times.append(elapsed)
        
        assert elapsed <= 10, f"Query took {elapsed:.1f}s, SLA is 10s"
    
    mean_time = sum(times) / len(times)
    print(f"Mean query time: {mean_time:.2f}s")
    assert mean_time <= 5.0, f"Mean {mean_time:.2f}s exceeds target 5.0s"


@pytest.mark.asyncio
async def test_concurrent_queries():
    """Multiple queries can run concurrently"""
    
    import asyncio
    from app.agents.core.agent_loop import AgentLoop
    
    loop = AgentLoop(...)
    
    # Launch 5 concurrent queries
    tasks = [
        loop.run(f"Query {i}", f"session_{i}", "/tmp/test_data.csv")
        for i in range(5)
    ]
    
    responses = await asyncio.gather(*tasks)
    assert len(responses) == 5
    assert all(r.narrative for r in responses)


@pytest.mark.asyncio
async def test_memory_usage():
    """Sessions don't leak memory over time"""
    
    import psutil
    import os
    from app.memory.conversation_memory import ConversationMemory
    
    memory = ConversationMemory()
    process = psutil.Process(os.getpid())
    
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Create many sessions
    for i in range(100):
        session_id = f"session_{i}"
        memory.create_session(session_id, {"columns": ["a", "b", "c"]})
        for j in range(10):
            memory.add_message(session_id, "user", f"Message {j}", None, [])
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    growth = final_memory - initial_memory
    
    print(f"Memory growth: {growth:.1f} MB")
    assert growth < 100, "Memory growth should be < 100 MB"
```

## Running the Tests

### Run all integration tests
```bash
pytest tests/integration/ -v --tb=short
```

### Run specific test file
```bash
pytest tests/integration/test_full_query_flow.py -v
```

### Run with coverage
```bash
pytest tests/integration/ --cov=app --cov-report=html
```

### Run with detailed output
```bash
pytest tests/integration/ -vv -s --tb=long
```

## Success Criteria

| Category | Metric | Target | Status |
|----------|--------|--------|--------|
| **Intent Extraction** | Primary goal accuracy | 80% | TBD |
| **Planning** | Valid JSON plans | 100% | TBD |
| **Task Completion** | End-to-end success | 90% | TBD |
| **Tools** | Tool chain execution | 95% | TBD |
| **Memory** | Multi-turn context preservation | 100% | TBD |
| **API** | Endpoint response codes | 200/201 | TBD |
| **Performance** | Mean query time | <5s | TBD |
| **Concurrency** | Parallel query execution | 5+ concurrent | TBD |
| **Memory Usage** | Growth per session | <1 MB | TBD |

## Debugging Failed Tests

### Query Returns Null Narrative
```python
# Check if LLM is running
curl http://localhost:11434/api/tags

# Verify dataset exists
ls -la /tmp/test_data.csv

# Check logs
tail -100 logs/dataverse_backend.log
```

### Tool Execution Fails
```python
# Test tool directly
async def test_tool():
    tool = DistributionPlotTool()
    result = await tool.execute({"columns": ["price"]}, session)
    print(result.error_message)  # See detailed error
```

### Memory Leak Detected
```python
# Clear expired sessions manually
memory._cleanup_expired_sessions()

# Check session count
sessions = memory.sessions  # Direct access for debugging
print(f"Active sessions: {len(sessions)}")
```

## Continuous Integration

### GitHub Actions Workflow
```yaml
name: Integration Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
      ollama:
        image: ollama/ollama
    steps:
      - uses: actions/checkout@v2
      - name: Run Integration Tests
        run: pytest tests/integration/ -v --tb=short
      - name: Upload Coverage
        uses: codecov/codecov-action@v2
```

## Performance Optimization Checklist

- [ ] Query response time < 5s mean
- [ ] P95 response time < 15s
- [ ] Tool execution parallelization
- [ ] Memory cleanup on session expiration
- [ ] Database indexing on frequently queried columns
- [ ] LLM response caching for same queries
- [ ] Tool result caching for repeated analyses
