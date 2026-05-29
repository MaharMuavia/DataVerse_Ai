"""Async database engine and session factory.

This module creates an async SQLAlchemy engine and a session factory using
SQLAlchemy 2.x and asyncpg. Provide `get_session` as a FastAPI dependency
that yields an `AsyncSession` for request-scoped use.
"""
from __future__ import annotations

from typing import AsyncGenerator
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from ..core.config import settings

# Only create engine if DATABASE_URL is configured. Engine creation is idempotent.
_engine = None
_async_session = None

def _create_engine():
    global _engine, _async_session
    if _engine is None:
        if not settings.DATABASE_URL:
            # No DB configured; leave engine as None. Callers must handle this.
            return None
        connect_args = {}
        if settings.DATABASE_URL.startswith("postgresql+asyncpg"):
            connect_args["timeout"] = float(settings.DATABASE_CONNECT_TIMEOUT_SECONDS)
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        _async_session = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine


def get_engine():
    """Return the created engine or None if DATABASE_URL missing."""
    return _engine or _create_engine()


def get_session_factory():
    """Return the Async session factory or None if not configured."""
    if _async_session is None:
        _create_engine()
    return _async_session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session for request handlers.

    Yields None if the database is not configured or not reachable,
    allowing endpoints to function without a database.
    """
    session_factory = get_session_factory()
    if session_factory is None:
        yield None
        return

    try:
        async with session_factory() as session:
            # Test the connection is actually usable
            from sqlalchemy import text
            await asyncio.wait_for(
                session.execute(text("SELECT 1")),
                timeout=max(1.0, float(settings.DATABASE_CONNECT_TIMEOUT_SECONDS)),
            )
            yield session
    except Exception:
        yield None
