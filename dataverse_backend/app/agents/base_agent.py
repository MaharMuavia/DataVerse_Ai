"""Abstract BaseAgent used by all agents.

Provides a uniform interface, logging helpers, and a place to implement shared behavior such as
accessing session state or writing trace logs.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict
from ..core.logger import logger


class BaseAgent(ABC):
    def __init__(self, name: str, description: str, session_id: str):
        self.name = name
        self.description = description
        self.session_id = session_id
        self.logger = logger.getChild(self.__class__.__name__)

    @abstractmethod
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """Run the agent's primary behavior. Must return a dictionary with results and metadata."""
        raise NotImplementedError

    def log_action(self, action: str, details: Dict[str, Any] | None = None) -> None:
        """Log an action taken by the agent and include structured details. This helps create an audit trail."""
        self.logger.info(f"Agent action: {action}", extra={"session_id": self.session_id, "details": details or {}})
