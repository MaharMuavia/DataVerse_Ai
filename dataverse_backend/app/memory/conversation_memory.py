from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..agents.core.intent_extractor import IntentObject, FilterCondition
from ..agents.core.tool_registry import SessionContext


@dataclass
class Message:
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    intent_object: Optional[IntentObject] = None
    tool_results: Optional[List[Dict]] = None


@dataclass
class SessionState:
    session_id: str
    dataset_schema: Dict[str, Any]  # Schema snapshot
    messages: List[Message]
    active_filters: List[FilterCondition]  # For natural language filters
    last_activity: datetime
    working_dataset_ref: Optional[str] = None  # Reference to filtered dataset
    ttl_hours: int = 2


class ConversationMemory:
    """
    In-memory conversation memory store.
    For production, replace with Redis.
    """

    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}
        self.ttl_hours = 2

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session state, cleaning up expired sessions."""
        self._cleanup_expired_sessions()

        return self.sessions.get(session_id)

    def create_session(
        self,
        session_id: str,
        dataset_schema: Dict[str, Any]
    ) -> SessionState:
        """Create a new session."""
        session = SessionState(
            session_id=session_id,
            dataset_schema=dataset_schema,
            messages=[],
            active_filters=[],
            last_activity=datetime.now()
        )
        self.sessions[session_id] = session
        return session

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent_object: Optional[IntentObject] = None,
        tool_results: Optional[List[Dict]] = None
    ) -> None:
        """Add a message to the conversation."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            intent_object=intent_object,
            tool_results=tool_results
        )

        session.messages.append(message)
        session.last_activity = datetime.now()

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Message]:
        """Get recent messages for context."""
        session = self.get_session(session_id)
        if not session:
            return []

        return session.messages[-limit:]

    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history in format suitable for LLM prompts."""
        messages = self.get_recent_messages(session_id)
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "intent": (
                    msg.intent_object.model_dump()
                    if hasattr(msg.intent_object, "model_dump")
                    else msg.intent_object.dict()
                ) if msg.intent_object else None,
            }
            for msg in messages
        ]

    def update_active_filters(
        self,
        session_id: str,
        filters: List[FilterCondition]
    ) -> None:
        """Update active filters for the session."""
        session = self.get_session(session_id)
        if session:
            session.active_filters = filters
            session.last_activity = datetime.now()

    def get_active_filters(self, session_id: str) -> List[FilterCondition]:
        """Get current active filters."""
        session = self.get_session(session_id)
        return session.active_filters if session else []

    def set_working_dataset_ref(
        self,
        session_id: str,
        dataset_ref: Optional[str]
    ) -> None:
        """Set reference to filtered working dataset."""
        session = self.get_session(session_id)
        if session:
            session.working_dataset_ref = dataset_ref
            session.last_activity = datetime.now()

    def get_working_dataset_ref(self, session_id: str) -> Optional[str]:
        """Get reference to working dataset."""
        session = self.get_session(session_id)
        return session.working_dataset_ref if session else None

    def get_dataset_schema(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get dataset schema for the session."""
        session = self.get_session(session_id)
        return session.dataset_schema if session else None

    def _cleanup_expired_sessions(self) -> None:
        """Remove sessions that have exceeded TTL."""
        now = datetime.now()
        expired_sessions = []

        for session_id, session in self.sessions.items():
            if now - session.last_activity > timedelta(hours=session.ttl_hours):
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.sessions[session_id]

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the session for debugging/logging."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        columns = []
        schema_columns = session.dataset_schema.get("columns", {}) if session.dataset_schema else {}
        if isinstance(schema_columns, dict):
            columns = list(schema_columns.keys())
        elif isinstance(schema_columns, list):
            columns = list(schema_columns)

        return {
            "session_id": session.session_id,
            "message_count": len(session.messages),
            "active_filters_count": len(session.active_filters),
            "has_working_dataset": session.working_dataset_ref is not None,
            "last_activity": session.last_activity.isoformat(),
            "dataset_columns": columns,
        }


# Global in-process store used by the current prototype so agentic routes share
# the same conversational state across requests.
memory_store = ConversationMemory()


def get_memory_store() -> ConversationMemory:
    """Return the shared in-process conversation memory store."""
    return memory_store
