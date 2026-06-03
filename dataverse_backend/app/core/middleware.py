"""Production middleware utilities for security and observability."""
from __future__ import annotations

import time
import uuid
import asyncio
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

try:
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover
    redis_async = None

from .config import settings

_rate_limit_client = None
_LOCAL_WINDOWS: dict[str, deque[float]] = defaultdict(deque)


async def _get_rate_limit_client():
    global _rate_limit_client
    if _rate_limit_client is None and redis_async is not None and settings.REDIS_URL:
        _rate_limit_client = redis_async.from_url(settings.REDIS_URL)
    return _rate_limit_client


def _extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_local_rate_limit(ip: str, window_seconds: int) -> tuple[bool, int]:
    now = time.time()
    key = f"local:{ip}"
    window = _LOCAL_WINDOWS[key]
    while window and now - window[0] > window_seconds:
        window.popleft()

    limit = int(settings.RATE_LIMIT_REQUESTS)
    if len(window) >= limit:
        return False, 0

    window.append(now)
    return True, max(0, limit - len(window))


async def request_context_middleware(request: Request, call_next: Callable):
    """Attach request id and duration metadata to responses."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()

    response: Response = await call_next(request)
    duration_ms = int((time.perf_counter() - start) * 1000)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response


async def security_headers_middleware(request: Request, call_next: Callable):
    """Apply conservative web security headers when enabled."""
    response: Response = await call_next(request)

    if settings.SECURE_HEADERS_ENABLED:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.headers.setdefault("X-XSS-Protection", "0")

    return response


async def redis_rate_limit_middleware(request: Request, call_next: Callable):
    """Limit API request rate using Redis counters in a fixed-size window."""
    if not settings.RATE_LIMIT_ENABLED:
        return await call_next(request)

    path = request.url.path or ""
    if not path.startswith(settings.RATE_LIMIT_PATH_PREFIX):
        return await call_next(request)

    # Skip health and docs endpoints.
    if path.startswith("/health") or path.startswith("/api/health") or path.startswith("/docs") or path.startswith("/openapi"):
        return await call_next(request)

    ip = _extract_client_ip(request)
    window = max(1, int(settings.RATE_LIMIT_WINDOW_SECONDS))
    now = int(time.time())
    bucket = now // window
    key = f"ratelimit:{ip}:{bucket}"

    try:
        client = await _get_rate_limit_client()
        if client is not None:
            current = await asyncio.wait_for(
                client.incr(key),
                timeout=max(0.1, float(settings.REDIS_CONNECT_TIMEOUT_SECONDS)),
            )
            if current == 1:
                await asyncio.wait_for(
                    client.expire(key, window + 1),
                    timeout=max(0.1, float(settings.REDIS_CONNECT_TIMEOUT_SECONDS)),
                )

            remaining = max(0, int(settings.RATE_LIMIT_REQUESTS) - int(current))
            if current > int(settings.RATE_LIMIT_REQUESTS):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please retry shortly."},
                    headers={
                        "Retry-After": str(window),
                        "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Window": str(window),
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Window"] = str(window)
            return response
    except Exception:
        client = None

    allowed, remaining = _enforce_local_rate_limit(ip, window)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please retry shortly."},
            headers={
                "Retry-After": str(window),
                "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Window": str(window),
                "X-RateLimit-Backend": "local",
            },
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Window"] = str(window)
    response.headers["X-RateLimit-Backend"] = "local" if client is None else "redis"
    return response
