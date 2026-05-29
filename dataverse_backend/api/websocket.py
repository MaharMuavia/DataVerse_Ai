"""Legacy websocket module kept for backwards-compatible imports.

The active implementation lives in app.api.websocket.
"""

from app.api.websocket import ws_chat_endpoint

__all__ = ["ws_chat_endpoint"]