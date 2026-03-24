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
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            future=True,
            pool_pre_ping=True,
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

    Example usage in a route:
        async def handler(db: AsyncSession = Depends(get_session)):
            await repo.create_dataset(db, ...)
    """
    session_factory = get_session_factory()
    if session_factory is None:
        # Yield nothing if DB not configured; callers should check and raise if required.
        yield None
        return

    async with session_factory() as session:
        yield session
