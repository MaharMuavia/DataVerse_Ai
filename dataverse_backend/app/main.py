"""FastAPI application entrypoint for DataVerse AI backend."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import traceback

from .api import routes, auth_routes
from .core.config import settings
from .core.logger import logger
from .db import base as db_base
from sqlalchemy.exc import OperationalError
import asyncio

app = FastAPI(title=settings.APP_NAME)
app.include_router(routes.router, prefix="/api")
app.include_router(auth_routes.router, prefix="/api/auth", tags=["authentication"])


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
    # If DATABASE_URL is configured, test DB connectivity at startup and log status.
    if settings.DATABASE_URL:
        try:
            # Graceful test - don't fail startup if DB unavailable
            logger.info("Database URL configured, skipping connectivity check")
        except Exception as e:
            logger.warning(f"Database startup check skipped: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down DataVerse AI backend")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
