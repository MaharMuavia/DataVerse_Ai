"""Per-session progress event bus for live SSE streaming.

A tiny in-process pub/sub. `publish(session_id, event)` is fire-and-forget; SSE
consumers subscribe with `subscribe(session_id)` which yields events until a
`{"stage": "_done"}` sentinel is published or the consumer disconnects.

Kept intentionally minimal: no persistence, no fan-out across processes. Good
enough for a single-uvicorn dev server and for production when the analysis
endpoint runs in the same process as the SSE endpoint.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any


class ProgressBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._stage_starts: dict[str, dict[str, float]] = defaultdict(dict)

    def subscribe(self, session_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._queues[session_id].append(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        subscribers = self._queues.get(session_id)
        if not subscribers:
            return
        try:
            subscribers.remove(queue)
        except ValueError:
            pass
        if not subscribers:
            self._queues.pop(session_id, None)
            self._stage_starts.pop(session_id, None)

    def publish(self, session_id: str, event: dict[str, Any]) -> None:
        for queue in list(self._queues.get(session_id, [])):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop oldest, keep newest — UI never blocks the pipeline.
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except Exception:
                    pass

    def start_stage(self, session_id: str, stage: str, label: str | None = None, detail: str | None = None) -> None:
        self._stage_starts[session_id][stage] = time.monotonic()
        self.publish(
            session_id,
            {
                "stage": stage,
                "label": label or _humanize(stage),
                "status": "running",
                "detail": detail,
            },
        )

    def complete_stage(self, session_id: str, stage: str, detail: str | None = None) -> None:
        started = self._stage_starts.get(session_id, {}).pop(stage, None)
        elapsed_ms = int((time.monotonic() - started) * 1000) if started else None
        self.publish(
            session_id,
            {
                "stage": stage,
                "label": _humanize(stage),
                "status": "done",
                "elapsed_ms": elapsed_ms,
                "detail": detail,
            },
        )

    def fail_stage(self, session_id: str, stage: str, detail: str) -> None:
        started = self._stage_starts.get(session_id, {}).pop(stage, None)
        elapsed_ms = int((time.monotonic() - started) * 1000) if started else None
        self.publish(
            session_id,
            {
                "stage": stage,
                "label": _humanize(stage),
                "status": "error",
                "elapsed_ms": elapsed_ms,
                "detail": detail,
            },
        )

    def finish(self, session_id: str, detail: str | None = None) -> None:
        self.publish(session_id, {"stage": "_done", "status": "done", "detail": detail})

    async def stream(self, session_id: str, *, idle_timeout: float = 60.0) -> AsyncIterator[dict[str, Any]]:
        queue = self.subscribe(session_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=idle_timeout)
                except asyncio.TimeoutError:
                    yield {"stage": "_ping", "status": "ping"}
                    continue
                yield event
                if event.get("stage") == "_done":
                    return
        finally:
            self.unsubscribe(session_id, queue)


def _humanize(stage: str) -> str:
    if stage.startswith("_"):
        return stage
    return stage.replace("_", " ").strip().capitalize()


progress_bus = ProgressBus()
