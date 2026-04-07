"""FastAPI application entrypoint for DataVerse AI backend."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import traceback
from pathlib import Path

from .api import routes, auth_routes, stream
from .api.websocket import ws_chat_endpoint
from .core.config import settings
from .core.logger import logger
from .db import base as db_base
from sqlalchemy.exc import OperationalError
import asyncio

app = FastAPI(title=settings.APP_NAME)
app.include_router(routes.router, prefix="/api")
app.include_router(auth_routes.router, prefix="/api/auth", tags=["authentication"])
app.include_router(stream.router, prefix="/api/stream", tags=["streaming"])

# WebSocket endpoint
app.add_websocket_route("/ws/chat/{session_id}", ws_chat_endpoint)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.on_event("startup")
async def startup_event():
    logger.info("Starting DataVerse AI backend", extra={"environment": settings.ENVIRONMENT})

    # Run database migration if configured
    if settings.DATABASE_URL:
        try:
            from .db.base import get_session_factory
            from .state.persistent_session_state import session_manager
            import aiofiles

            session_factory = get_session_factory()
            if session_factory:
                async with session_factory() as db:
                    # Run migration SQL script if available
                    migration_path = Path(__file__).parent / "db" / "migrations" / "001_full_schema.sql"
                    if migration_path.exists():
                        async with aiofiles.open(migration_path, 'r') as f:
                            migration_sql = await f.read()
                        from sqlalchemy import text
                        await db.execute(text(migration_sql))
                        await db.commit()
                        logger.info("Database migration completed")

                    # Fallback: ensure ORM model tables exist
                    try:
                        from .db.session_models import Base as session_base
                        from .db.models import Base as legacy_base
                        engine = db_base.get_engine()
                        if engine is not None:
                            async with engine.begin() as conn:
                                await conn.run_sync(session_base.metadata.create_all)
                                await conn.run_sync(legacy_base.metadata.create_all)
                            logger.info("DB schema ensured via SQLAlchemy Base.metadata.create_all")
                    except Exception as e:
                        logger.warning(f"Fallback table creation via ORM Base failed: {e}")

                    # Start session cleanup task
                    await session_manager.start_cleanup_task(session_factory)
                    logger.info("Session cleanup task started")

        except Exception as e:
            logger.warning(f"Database migration failed: {e}")
    else:
        logger.info("No DATABASE_URL configured, skipping database setup")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down DataVerse AI backend")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
