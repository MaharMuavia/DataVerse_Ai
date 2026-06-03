"""FastAPI application entrypoint for DataVerse AI."""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn
import traceback
import asyncio
from datetime import datetime, timezone

from .api import routes, auth_routes, stream, graph_routes, ai_routes, billing_routes, dashboard_routes
from .api import workspace_routes, dataset_routes, conversation_routes, analyze_routes
from .api.websocket import ws_chat_endpoint
from .core.config import settings
from .core.logger import logger
from .core.middleware import request_context_middleware, security_headers_middleware, redis_rate_limit_middleware
from .db import base as db_base
from sqlalchemy import text

try:
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover
    redis_async = None

SERVICE_START_TIME = datetime.now(timezone.utc)

if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.redis import RedisIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
            integrations=[FastApiIntegration(), SqlalchemyIntegration(), RedisIntegration()],
        )
        logger.info("Sentry monitoring initialized")
    except Exception as sentry_exc:
        logger.warning("Sentry initialization failed: %s", sentry_exc)

async def _startup_logic() -> None:
    logger.info("Starting DataVerse AI backend", extra={"environment": settings.ENVIRONMENT})

    if settings.DATABASE_URL and settings.DATABASE_STARTUP_CHECK_ENABLED:
        try:
            await asyncio.wait_for(
                _ensure_database_startup(),
                timeout=max(1.0, float(settings.DATABASE_CONNECT_TIMEOUT_SECONDS) + 2.0),
            )
        except asyncio.TimeoutError:
            logger.warning("Database startup check timed out; continuing without database readiness")
        except Exception as e:
            logger.warning(f"Database migration failed: {e}")
    elif settings.DATABASE_URL:
        logger.info("Database startup check disabled; request-scoped DB dependency will fail open if unavailable")
    else:
        logger.info("No DATABASE_URL configured, skipping database setup")


async def _ensure_database_startup() -> None:
    from .db.base import get_session_factory
    from .state.persistent_session_state import session_manager

    session_factory = get_session_factory()
    if session_factory:
        async with session_factory() as db:
            # Ensure the ORM tables exist without applying the full legacy SQL migration.
            from .db.session_models import Base as session_base
            from .db.models import Base as legacy_base

            engine = db_base.get_engine()
            if engine is not None:
                async with engine.begin() as conn:
                    await conn.run_sync(session_base.metadata.create_all)
                    await conn.run_sync(legacy_base.metadata.create_all)
                logger.info("DB schema ensured via SQLAlchemy Base.metadata.create_all")

            await session_manager.start_cleanup_task(session_factory)
            logger.info("Session cleanup task started")


async def _shutdown_logic() -> None:
    logger.info("Shutting down DataVerse AI backend")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001 - FastAPI lifespan signature
    await _startup_logic()
    try:
        yield
    finally:
        await _shutdown_logic()


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade Data Science BI Platform",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENABLE_OPENAPI_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_OPENAPI_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_OPENAPI_DOCS else None,
    lifespan=lifespan,
)

# Include routers
app.include_router(auth_routes.router, prefix="/api/auth", tags=["authentication"])
app.include_router(workspace_routes.router, prefix="/api/workspaces", tags=["workspaces"])
app.include_router(dataset_routes.router, prefix="/api/workspaces", tags=["datasets"])
app.include_router(conversation_routes.router, prefix="/api/workspaces", tags=["conversations"])
app.include_router(dashboard_routes.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(billing_routes.router, prefix="/api/billing", tags=["billing"])
app.include_router(ai_routes.router, prefix="/api/ai", tags=["ai"])
app.include_router(analyze_routes.router, prefix="/api/analyze", tags=["analysis"])
app.include_router(routes.router, prefix="/api", tags=["legacy"])
app.include_router(stream.router, prefix="/api/stream", tags=["streaming"])
app.include_router(graph_routes.router, prefix="/api/stream/graph", tags=["langgraph"])

# WebSocket endpoint
app.add_api_websocket_route("/ws/chat/{session_id}", ws_chat_endpoint)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list or ["*"])

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(request_context_middleware)
app.middleware("http")(security_headers_middleware)
app.middleware("http")(redis_rate_limit_middleware)


# Global exception handler to capture and log unexpected errors during requests
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error(
        "Unhandled exception during request",
        extra={"path": str(request.url), "method": request.method, "exception": str(exc), "traceback": tb},
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Simple request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Incoming request: {request.method} {request.url}")
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(f"Error processing request {request.method} {request.url}")
        raise
    logger.debug(f"Completed request: {request.method} {request.url} -> {response.status_code}")
    return response


@app.get("/health/live")
async def health_live():
    """Liveness endpoint used by container orchestrators."""
    return {
        "status": "alive",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "started_at": SERVICE_START_TIME.isoformat(),
    }


@app.get("/health/ready")
async def health_ready():
    """Readiness endpoint validating dependencies without failing optional local services."""
    checks = {
        "database": {"status": "unconfigured", "critical": False},
        "redis": {"status": "unconfigured", "critical": False},
    }

    # Database readiness
    engine = db_base.get_engine()
    if engine is not None:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"]["status"] = "ok"
        except Exception as exc:
            logger.warning("Readiness DB check failed: %s", exc)
            checks["database"]["status"] = f"degraded: {exc}"
            checks["database"]["critical"] = bool(settings.DATABASE_URL)

    # Redis readiness
    if redis_async and settings.REDIS_URL:
        try:
            client = redis_async.from_url(settings.REDIS_URL)
            pong = await client.ping()
            checks["redis"]["status"] = "ok" if pong else "unavailable: local rate limiter fallback active"
            await client.close()
        except Exception as exc:
            logger.warning("Readiness Redis check failed: %s", exc)
            checks["redis"]["status"] = f"unavailable: local rate limiter fallback active ({exc})"

    critical_down = any(
        check["critical"] and str(check["status"]).startswith(("degraded", "unavailable"))
        for check in checks.values()
    )
    is_degraded = any(check["status"] != "ok" for check in checks.values())
    return JSONResponse(
        status_code=503 if critical_down else 200,
        content={
            "status": "down" if critical_down else "degraded" if is_degraded else "ready",
            "checks": checks,
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
        },
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
