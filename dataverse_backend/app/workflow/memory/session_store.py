"""Session store for managing conversation state across agent calls.

Persists workflow state in memory with optional Redis backing for distributed scenarios.
"""
from typing import Any, Dict, Optional
import json
import copy
from datetime import datetime
import redis.asyncio as aioredis
from ...core.config import settings
from ...core.logger import logger

# In-memory session cache
_SESSION_CACHE: Dict[str, Dict[str, Any]] = {}


def load_session(session_id: str) -> Dict[str, Any]:
    """Load session state from cache or Redis.
    
    Returns a dictionary with keys:
    - session_id: str
    - dataset_id: str
    - user_query: str
    - intent: Optional[Dict] - parsed intent from orchestrator
    - analysis_results: Optional[Dict] - output from analysis agent
    - viz_figure_json: Optional[Dict] - visualization spec
    - ml_task_id: Optional[str] - async ML job ID
    - eda_results: Optional[Dict] - EDA output
    - error_message: Optional[str]
    - final_response: Optional[str]
    - messages: List[Dict] - conversation history
    """
    try:
        # Try in-memory cache first
        if session_id in _SESSION_CACHE:
            logger.debug(f"Loaded session {session_id} from cache")
            return copy.deepcopy(_SESSION_CACHE[session_id])
        
        # Initialize new session
        session = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "dataset_id": None,
            "user_query": None,
            "intent": None,
            "analysis_results": None,
            "viz_figure_json": None,
            "ml_task_id": None,
            "eda_results": None,
            "error_message": None,
            "final_response": None,
            "messages": [],
        }
        
        _SESSION_CACHE[session_id] = session
        logger.debug(f"Initialized new session {session_id}")
        return copy.deepcopy(session)
        
    except Exception as e:
        logger.error(f"Error loading session {session_id}: {e}")
        return {"session_id": session_id, "error": str(e), "messages": []}


def save_session(session_id: str, state: Dict[str, Any]) -> None:
    """Save session state to cache and Redis.
    
    Args:
        session_id: Session identifier
        state: Full state dictionary to save
    """
    try:
        state["updated_at"] = datetime.utcnow().isoformat()
        _SESSION_CACHE[session_id] = copy.deepcopy(state)
        logger.debug(f"Saved session {session_id} to cache")
        
        # Optional: Save to Redis for distributed access
        # redis_client = aioredis.from_url(settings.REDIS_URL)
        # await redis_client.setex(f"session:{session_id}", 86400, json.dumps(state))
        
    except Exception as e:
        logger.error(f"Error saving session {session_id}: {e}")


def update_session(session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update specific fields in session without replacing entire state.
    
    Args:
        session_id: Session identifier
        updates: Dictionary of fields to update
        
    Returns:
        Updated session state
    """
    session = load_session(session_id)
    session.update(updates)
    session["updated_at"] = datetime.utcnow().isoformat()
    save_session(session_id, session)
    return session


def add_message(session_id: str, role: str, content: str, message_type: str = "text") -> None:
    """Add a message to session conversation history.
    
    Args:
        session_id: Session identifier
        role: 'user' or 'assistant'
        content: Message content
        message_type: Type of message (text, chart, table, insight, code)
    """
    session = load_session(session_id)
    message = {
        "role": role,
        "content": content,
        "type": message_type,
        "timestamp": datetime.utcnow().isoformat(),
    }
    session["messages"].append(message)
    save_session(session_id, session)


def get_conversation_history(session_id: str, limit: int = None) -> list:
    """Get conversation history for session.
    
    Args:
        session_id: Session identifier
        limit: Maximum number of messages to return (most recent first if positive)
        
    Returns:
        List of messages
    """
    session = load_session(session_id)
    messages = session.get("messages", [])
    
    if limit is None:
        return messages
    elif limit > 0:
        return messages[-limit:]
    else:
        return messages[:abs(limit)]


def clear_session(session_id: str) -> None:
    """Clear session from memory.
    
    Args:
        session_id: Session identifier
    """
    if session_id in _SESSION_CACHE:
        del _SESSION_CACHE[session_id]
        logger.debug(f"Cleared session {session_id}")


def get_all_sessions() -> Dict[str, str]:
    """Get all active session IDs and their creation times.
    
    Returns:
        Dictionary mapping session_id to created_at timestamp
    """
    return {
        session_id: session.get("created_at", "unknown")
        for session_id, session in _SESSION_CACHE.items()
    }
