"""Custom exceptions used across DataVerse AI backend.

Exceptions are explicit and documented to aid robust error handling.
"""
from __future__ import annotations

class DataVerseError(Exception):
    """Base class for domain errors in DataVerse."""


class DataLoadError(DataVerseError):
    """Raised when a CSV or dataset cannot be loaded."""


class DataNotFoundError(DataVerseError):
    """Raised when a dataset is not found in DataManager or session."""


class AgentError(DataVerseError):
    """Raised when an agent fails to complete its task."""


class ModelUnavailableError(DataVerseError):
    """Raised when an external model (e.g., DeepAnalyze) is unavailable or returns invalid responses."""
