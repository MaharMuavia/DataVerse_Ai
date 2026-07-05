"""Sliding-window in-memory rate limiter for abuse-prone endpoints."""
from __future__ import annotations

import time
from collections import defaultdict, deque

_WINDOW_SECONDS = 60.0
_hits: dict[str, deque[float]] = defaultdict(deque)


def allow(key: str, limit: int) -> bool:
    """True if `key` is under `limit` events in the last 60 seconds."""
    if limit <= 0:
        return True  # limiter disabled
    now = time.monotonic()
    window = _hits[key]
    while window and now - window[0] > _WINDOW_SECONDS:
        window.popleft()
    if len(window) >= limit:
        return False
    window.append(now)
    return True


def reset() -> None:
    """Clear all counters (used by tests)."""
    _hits.clear()
