"""Simple in-memory session state for agent memory and shared context.

This implementation is intentionally simple and suitable for a prototype or FYP. In production,
replace with persistent, multi-tenant storage and add authentication and TTLs.
"""
from __future__ import annotations

from typing import Any, Dict


class SessionState:
    _STORE: Dict[str, Dict[str, Any]] = {}

    def __init__(self, session_id: str):
        self.session_id = session_id
        if session_id not in self._STORE:
            self._STORE[session_id] = {}

    @classmethod
    def get(cls, session_id: str) -> "SessionState":
        if session_id not in cls._STORE:
            cls._STORE[session_id] = {}
        return SessionState(session_id)

    def set(self, key: str, value: Any) -> None:
        self._STORE[self.session_id][key] = value

    def get_value(self, key: str, default: Any = None) -> Any:
        return self._STORE[self.session_id].get(key, default)

    def dump(self) -> Dict[str, Any]:
        return dict(self._STORE[self.session_id])
