"""Simple test to verify test framework works."""
import pytest


def test_simple_addition():
    """Test basic Python."""
    assert 1 + 1 == 2


def test_simple_list():
    """Test list operations."""
    lst = [1, 2, 3]
    assert len(lst) == 3
    assert 2 in lst


@pytest.fixture
def sample_dict():
    """Provide a sample dictionary."""
    return {"key": "value", "number": 42}


def test_fixture_usage(sample_dict):
    """Test fixture usage."""
    assert sample_dict["key"] == "value"
    assert sample_dict["number"] == 42
