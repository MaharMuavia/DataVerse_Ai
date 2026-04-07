"""SSE streaming endpoint for real-time query processing.

Provides server-sent events for streaming analysis progress and results.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logger import logger
from ..core.intent_router import IntentRouter
from ..core.narrator import Narrator
from ..orchestrator.agent_orchestrator import AgentOrchestrator
from ..state.persistent_session_state import session_manager
from ..db.base import get_session


router = APIRouter()


@dataclass
class StreamEvent:
    """Event for SSE streaming."""
    step: str
    message: str
    data: Optional[Dict[str, Any]] = None


class StreamProcessor:
    """Processes queries with streaming events."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.queue = asyncio.Queue()

    async def send_event(self, step: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Send an event to the stream."""
        event = StreamEvent(step=step, message=message, data=data)
        await self.queue.put(event)

    async def process_query(self, query: str, db: Optional[AsyncSession] = None):
        """Process query with streaming events."""
        try:
            # Step 1: Intent parsing
            await self.send_event("intent_parsed", "Understanding your question...")

            # Get dataset columns for intent routing
            session_state = session_manager.get_session(self.session_id)
            await session_state._ensure_loaded(db)

            df = session_state.get_value("raw_dataframe")
            if df is None:
                await self.send_event("error", "No dataset found for session")
                return

            columns = df.columns.tolist()

            # Route intent
            router = IntentRouter()
            intent_result = await router.route(query, columns)

            if intent_result.intent == "clarification_needed":
                await self.send_event("clarification_needed", intent_result.message or "Need clarification")
                return

            await self.send_event("intent_parsed", f"Intent: {intent_result.intent}", {
                "intent": intent_result.intent,
                "confidence": intent_result.confidence
            })

            # Step 2: Run analysis pipeline
            orchestrator = AgentOrchestrator()
            await self.send_event("analysis_running", "Running analysis pipeline...")

            # Run the analysis (this will take time)
            result = await orchestrator.handle_query(self.session_id, query, db)

            # Send results as they become available
            if "computed_facts" in result:
                await self.send_event("analysis_complete", "Analysis complete", {
                    "computed_facts": result["computed_facts"]
                })

            # Step 3: Generate visualization if applicable
            if intent_result.intent == "visualization" or "chart" in query.lower():
                await self.send_event("visualization_ready", "Generating visualization...")
                # Visualization logic would go here
                # For now, send a placeholder
                await self.send_event("visualization_ready", "Chart ready", {
                    "chart_spec": {}  # Plotly JSON would go here
                })

            # Step 4: Generate narration
            await self.send_event("narration", "Writing summary...")
            narrator = Narrator()
            narration = await narrator.narrate(result, intent_result.intent)
            await self.send_event("narration", narration, {
                "narration": narration
            })

            # Step 5: Complete
            await self.send_event("complete", "Query processing complete")

        except Exception as e:
            logger.exception(f"Stream processing failed: {e}")
            await self.send_event("error", f"Processing failed: {str(e)}")


async def generate_events(session_id: str, query: str, db: Optional[AsyncSession] = None):
    """Generate SSE events for the stream."""
    processor = StreamProcessor(session_id)

    # Start processing in background
    asyncio.create_task(processor.process_query(query, db))

    # Yield events as they come
    while True:
        try:
            event = await asyncio.wait_for(processor.queue.get(), timeout=30.0)
            data = {
                "step": event.step,
                "message": event.message
            }
            if event.data:
                data.update(event.data)

            yield f"data: {json.dumps(data)}\n\n"

            if event.step in ["complete", "error", "clarification_needed"]:
                break

        except asyncio.TimeoutError:
            # Send heartbeat
            yield f"data: {json.dumps({'step': 'heartbeat', 'message': 'Processing...'})}\n\n"


@router.get("/query")
async def stream_query(
    session_id: str = Query(..., description="Session ID"),
    query: str = Query(..., description="User query"),
    db: Optional[AsyncSession] = Depends(get_session)
):
    """Stream query processing results via SSE."""

    # Validate session exists
    session_state = session_manager.get_session(session_id)
    await session_state._ensure_loaded(db)

    if session_state.get_value("raw_dataframe") is None:
        raise HTTPException(404, "Session not found or dataset not loaded")

    return StreamingResponse(
        generate_events(session_id, query, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )
