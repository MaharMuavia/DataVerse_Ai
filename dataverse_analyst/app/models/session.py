from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pandas as pd


@dataclass
class AnalysisSession:
    session_id: str
    df: pd.DataFrame
    filename: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    model: Any | None = None
    results: dict[str, Any] = field(default_factory=dict)


class SessionStore:
    """Simple in-memory session store with UUID keys."""

    def __init__(self) -> None:
        self._sessions: dict[str, AnalysisSession] = {}

    def create(self, df: pd.DataFrame, filename: str) -> str:
        session_id = str(uuid4())
        self._sessions[session_id] = AnalysisSession(
            session_id=session_id,
            df=df.copy(),
            filename=filename,
        )
        return session_id

    def get(self, session_id: str) -> AnalysisSession | None:
        return self._sessions.get(session_id)

    def set_results(self, session_id: str, results: dict[str, Any]) -> None:
        session = self.get(session_id)
        if session is not None:
            session.results = results
            session.model = results.get("model_object")


session_store = SessionStore()
