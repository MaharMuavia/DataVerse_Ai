"""Dedicated LangGraph execution routes."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import get_current_active_user
from ..core.logger import logger
from ..db.base import get_session
from .schemas import GraphExecuteRequest, GraphExecuteResponse, User  # noqa: F401
from ..workflow.langgraph_runtime import run_graph_query, stream_graph_query_events

router = APIRouter()


@router.post("/execute", response_model=GraphExecuteResponse)
async def execute_graph(
    request: GraphExecuteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Optional[AsyncSession] = Depends(get_session),
):
    """Execute LangGraph query with checkpointer persistence scoped by thread_id."""
    _ = current_user
    try:
        thread_id = request.thread_id or request.session_id
        result = await run_graph_query(
            session_id=request.session_id,
            user_query=request.query,
            db=db,
            thread_id=thread_id,
            dataset_path_override=request.dataset_path_override,
        )

        return GraphExecuteResponse(
            session_id=request.session_id,
            thread_id=thread_id,
            final_response=result.get("final_response"),
            insights=result.get("insights", []),
            visualizations=result.get("visualizations", []),
            ml_results=result.get("ml_results"),
            error=result.get("error"),
            iteration_count=int(result.get("iteration_count", 0)),
        )
    except Exception as exc:
        logger.exception("LangGraph execute endpoint failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/execute/stream")
async def execute_graph_stream(
    session_id: str = Query(..., description="Session ID"),
    query: str = Query(..., description="User query"),
    thread_id: Optional[str] = Query(None, description="LangGraph thread_id for memory"),
    dataset_path_override: Optional[str] = Query(None, description="Optional dataset path override"),
    db: Optional[AsyncSession] = Depends(get_session),
):
    """Stream LangGraph events via SSE for token/agent updates."""

    async def event_generator():
        try:
            async for event in stream_graph_query_events(
                session_id=session_id,
                user_query=query,
                db=db,
                thread_id=thread_id or session_id,
                dataset_path_override=dataset_path_override,
            ):
                yield f"data: {json.dumps(event)}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'session_id': session_id})}\n\n"
        except Exception as exc:
            logger.exception("LangGraph stream endpoint failed: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
