import redis
import json
import os
from workflow.state import AnalysisState
from app.core.config import settings

# Redis is optional - use memory fallback if not configured
try:
    redis_url = getattr(settings, 'REDIS_URL', os.getenv('REDIS_URL', None))
    r = redis.from_url(redis_url, decode_responses=True) if redis_url else None
except Exception:
    r = None

SESSION_TTL = 3600  # 1 hour
_memory_sessions = {}  # Fallback in-memory storage

def save_session(session_id: str, state: dict) -> None:
    # Only serialize serializable fields. Skip dataframes.
    serializable = {k: v for k, v in state.items()
        if isinstance(v, (str, int, float, list, dict, type(None)))}
    
    if r:
        r.setex(f"session:{session_id}", SESSION_TTL, json.dumps(serializable))
    else:
        _memory_sessions[f"session:{session_id}"] = serializable

def load_session(session_id: str) -> dict:
    if r:
        raw = r.get(f"session:{session_id}")
        if raw:
            return json.loads(raw)
    else:
        return _memory_sessions.get(f"session:{session_id}", {})

def extend_session_ttl(session_id: str) -> None:
    r.expire(f"session:{session_id}", SESSION_TTL)