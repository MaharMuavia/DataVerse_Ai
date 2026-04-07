"""
Pytest configuration and shared fixtures for DataVerse tests.

Provides:
- Mock DataFrames with realistic test data
- Mock LLM client with controlled responses
- Session contexts for tool testing
- Dataset schema fixtures
"""

import pytest
import pandas as pd
import numpy as np
import asyncio
import inspect
import sys
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_APP_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APP_ROOT))


# ============================================================================
# MOCK DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_dataframe():
    """
    Create a realistic sample DataFrame for testing.
    
    Simulates retail product sales data with:
    - Various data types (int, float, string, datetime)
    - Missing values
    - Outliers
    - Categorical columns
    """
    np.random.seed(42)
    n_rows = 1000
    
    dates = pd.date_range('2023-01-01', periods=n_rows, freq='D')
    
    df = pd.DataFrame({
        'date': dates,
        'product_id': np.random.randint(1000, 2000, n_rows),
        'category': np.random.choice(['Electronics', 'Clothing', 'Home', 'Books'], n_rows),
        'price': np.random.uniform(10, 500, n_rows),
        'quantity': np.random.randint(1, 100, n_rows),
        'revenue': None,  # Will calculate
        'customer_age': np.random.randint(18, 80, n_rows),
        'region': np.random.choice(['North', 'South', 'East', 'West'], n_rows),
        'is_premium': np.random.choice([True, False], n_rows),
    })
    
    # Add revenue column
    df['revenue'] = df['price'] * df['quantity']
    
    # Add some missing values
    missing_indices = np.random.choice(df.index, size=int(0.05 * len(df)), replace=False)
    df.loc[missing_indices, 'customer_age'] = np.nan
    
    # Add outliers
    outlier_indices = np.random.choice(df.index, size=int(0.02 * len(df)), replace=False)
    df.loc[outlier_indices, 'price'] = df.loc[outlier_indices, 'price'] * 5
    
    return df


@pytest.fixture
def dataset_schema(sample_dataframe):
    """Get schema information from sample DataFrame."""
    return {
        "columns": list(sample_dataframe.columns),
        # Keep schema JSON-serializable because intent tests pass it through
        # json.dumps before sending it to the extractor.
        "dtypes": {column: str(dtype) for column, dtype in sample_dataframe.dtypes.items()},
        "rows": int(len(sample_dataframe)),
        "memory_usage": int(sample_dataframe.memory_usage(deep=True).sum())
    }


@pytest.fixture
def sample_dataframe_csv(tmp_path, sample_dataframe):
    """
    Create a temporary CSV file with sample data.
    
    Returns path to the CSV file for integration testing.
    """
    csv_path = tmp_path / "test_data.csv"
    sample_dataframe.to_csv(csv_path, index=False)
    return str(csv_path)


# ============================================================================
# MOCK LLM CLIENT FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """
    Create a mock LLM client with controlled responses.
    
    Useful for testing LLM-dependent components without hitting API.
    """
    client = AsyncMock()
    
    # Mock generate_text responses
    async def mock_generate_text(prompt, max_tokens=512):
        if "trend" in prompt.lower():
            return "The data shows an upward trend over time with seasonal patterns."
        elif "top 3" in prompt.lower():
            return "The top 3 items are: Electronics (40%), Clothing (35%), Home (25%)."
        else:
            return "Analysis complete. Key finding: significant variation detected."
    
    # Mock generate_json responses
    async def mock_generate_json(prompt, response_model=None, max_tokens=512):
        if "intent" in prompt.lower():
            return {
                "primary_goal": "explore",
                "target_columns": ["price", "quantity"],
                "filters": [],
                "time_range": None,
                "output_preference": "mixed",
                "confidence": 0.92,
                "ambiguities": [],
                "follow_up_from": None
            }
        elif "plan" in prompt.lower():
            return {
                "reasoning": "User wants to analyze product categories",
                "steps": [
                    {
                        "step": 1,
                        "tool": "categorical_analysis",
                        "params": {"column": "category"},
                        "purpose": "Analyze product categories"
                    },
                    {
                        "step": 2,
                        "tool": "correlate_distribution",
                        "params": {"column_pairs": [["price", "revenue"]]},
                        "purpose": "Show relationship between price and revenue"
                    }
                ]
            }
        else:
            return {"result": "Processing complete"}
    
    client.generate_text = mock_generate_text
    client.generate_json = mock_generate_json
    client.is_available = AsyncMock(return_value=True)
    
    return client


# ============================================================================
# SESSION CONTEXT FIXTURES
# ============================================================================

@pytest.fixture
def session_context(sample_dataframe_csv):
    """
    Create a session context for tool testing.
    
    SessionContext contains:
    - session_id: Unique session identifier
    - dataset_path: Path to test CSV
    - working_dataset_path: Current working dataset (filtered or modified)
    """
    from app.agents.core.tool_registry import SessionContext
    
    return SessionContext(
        session_id="test_session_001",
        dataset_path=sample_dataframe_csv
    )


# ============================================================================
# MOCK DATA SCENARIOS
# ============================================================================

@pytest.fixture
def intent_test_cases():
    """
    Test cases for intent extraction evaluation.
    
    Each case has:
    - query: User query string
    - expected_goal: Expected primary_goal
    - expected_columns: Expected target columns
    - min_confidence: Minimum acceptable confidence
    """
    return [
        {
            "query": "What is the distribution of product prices?",
            "expected_goal": "visualize",
            "expected_columns": ["price"],
            "min_confidence": 0.85
        },
        {
            "query": "Show me the top categories by revenue",
            "expected_goal": "explore",
            "expected_columns": ["category", "revenue"],
            "min_confidence": 0.80
        },
        {
            "query": "Predict customer spending based on age",
            "expected_goal": "predict",
            "expected_columns": ["customer_age"],
            "min_confidence": 0.75
        },
        {
            "query": "Compare sales by region",
            "expected_goal": "compare",
            "expected_columns": ["region"],
            "min_confidence": 0.80
        },
        {
            "query": "Why are these products outliers?",
            "expected_goal": "explain",
            "expected_columns": [],
            "min_confidence": 0.70
        },
        {
            "query": "This is unclear",
            "expected_goal": "explore",
            "expected_columns": [],
            "min_confidence": 0.50,
            "expect_clarification": True
        }
    ]


@pytest.fixture
def tool_execution_test_cases(sample_dataframe_csv):
    """Test cases for tool execution."""
    return [
        {
            "tool": "dataset_profile",
            "params": {},
            "expected_keys": ["columns", "dtypes", "row_count"]
        },
        {
            "tool": "compute_statistics",
            "params": {},
            "expected_keys": ["mean", "median", "std"]
        },
        {
            "tool": "categorical_analysis",
            "params": {"column": "category"},
            "expected_keys": ["value_counts", "mode", "unique_count"]
        },
        {
            "tool": "group_aggregation",
            "params": {
                "group_columns": ["category"],
                "agg_column": "revenue",
                "agg_functions": ["sum", "mean"]
            },
            "expected_keys": ["group_count", "groups"]
        }
    ]


# ============================================================================
# INTEGRATION TEST FIXTURES
# ============================================================================

@pytest.fixture
def conversation_history():
    """
    Create a realistic conversation history.
    
    Simulates multi-turn conversation with intents and tool results.
    """
    return [
        {
            "role": "user",
            "content": "Analyze the products in our store",
            "intent": {
                "primary_goal": "explore",
                "target_columns": [],
                "confidence": 0.85
            }
        },
        {
            "role": "assistant",
            "content": "I found 1000 products across 4 categories. Here's the breakdown...",
            "tools_used": ["dataset_profile", "categorical_analysis"]
        },
        {
            "role": "user",
            "content": "Which category has the highest revenue?",
            "intent": {
                "primary_goal": "explore",
                "target_columns": ["category", "revenue"],
                "confidence": 0.92
            }
        },
        {
            "role": "assistant",
            "content": "Electronics leads with 45% of total revenue...",
            "tools_used": ["group_aggregation"]
        }
    ]


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def tmp_csv_file(tmp_path, sample_dataframe):
    """Create a temporary CSV file for testing."""
    csv_file = tmp_path / "test_data.csv"
    sample_dataframe.to_csv(csv_file, index=False)
    return str(csv_file)


@pytest.fixture
def temp_dataset_dir(tmp_path):
    """Create a temporary directory for dataset storage."""
    return str(tmp_path)


# ============================================================================
# SESSION SETUP/TEARDOWN
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_sessions():
    """Auto-cleanup sessions after each test."""
    yield
    # Cleanup code would go here (e.g., clear ConversationMemory)
    pass


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


def pytest_pyfunc_call(pyfuncitem):
    """Run async tests without requiring an external pytest-asyncio plugin."""
    test_func = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_func):
        kwargs = {
            name: pyfuncitem.funcargs[name]
            for name in pyfuncitem._fixtureinfo.argnames
            if name in pyfuncitem.funcargs
        }
        asyncio.run(test_func(**kwargs))
        return True
    return None
