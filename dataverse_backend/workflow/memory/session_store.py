import redis
import json
from workflow.state import AnalysisState
from core.config import settings

r = redis.from_url(settings.REDIS_URL, decode_responses=True)
SESSION_TTL = 3600  # 1 hour

def save_session(session_id: str, state: dict) -> None:
    # Only serialize serializable fields. Skip dataframes.
    serializable = {k: v for k, v in state.items()
        if isinstance(v, (str, int, float, list, dict, type(None)))}
    r.setex(f"session:{session_id}", SESSION_TTL, json.dumps(serializable))

def load_session(session_id: str) -> dict:
    raw = r.get(f"session:{session_id}")
    if raw:
        return json.loads(raw)
    return {}  # empty dict = new session, graph uses defaults

def extend_session_ttl(session_id: str) -> None:
    r.expire(f"session:{session_id}", SESSION_TTL)