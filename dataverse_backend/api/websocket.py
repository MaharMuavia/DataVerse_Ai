from fastapi import WebSocket, WebSocketDisconnect
from workflow.graph import ANALYSIS_GRAPH
from workflow.memory.session_store import load_session, save_session
import asyncio
import redis.asyncio as aioredis
import json
from core.config import settings

async def ws_chat_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # Subscribe to Redis channels for async task results
    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe(
        f"session:{session_id}:ml_result",
        f"session:{session_id}:xai_result"
    )

    # Background task: forward Redis messages to WebSocket
    async def redis_listener():
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_json({
                    "type": "async_result",
                    "data": json.loads(message["data"])
                })

    listener_task = asyncio.create_task(redis_listener())

    try:
        while True:
            data = await websocket.receive_json()
            user_query = data["message"]
            dataset_id = data.get("dataset_id", "")

            # Load existing session state
            existing_state = load_session(session_id)

            # Build state for this turn
            current_state = {
                **existing_state,
                "session_id": session_id,
                "user_query": user_query,
                "dataset_id": dataset_id,
                # Clear per-turn result fields
                "viz_figure_json": None,
                "ml_task_id": None,
                "error_message": None,
                "final_response": None,
            }

            # Run LangGraph workflow
            await websocket.send_json({"type": "thinking", "data": "Analyzing..."})

            result = await ANALYSIS_GRAPH.ainvoke(current_state)

            # Save updated state
            save_session(session_id, result)

            # Send response back
            await websocket.send_json({
                "type": "response",
                "data": {
                    "text": result.get("final_response", ""),
                    "intent": result.get("intent", ""),
                    "viz": result.get("viz_figure_json"),
                    "eda": result.get("eda_results"),
                    "task_id": result.get("ml_task_id"),
                    "error": result.get("error_message"),
                }
            })

    except WebSocketDisconnect:
        listener_task.cancel()
        await pubsub.unsubscribe()
        await r.aclose()