"""WebSocket chat endpoint for DataVerse AI."""
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging

logger = logging.getLogger(__name__)


async def ws_chat_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat communication."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Echo back for now - in production this would be processed by agents
            response = {
                "type": "message",
                "content": f"Echo: {message.get('content', '')}",
                "session_id": session_id
            }
            
            await websocket.send_text(json.dumps(response))
            
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1000)
