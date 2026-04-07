"""Persistent session management with PostgreSQL and Parquet storage.

This module replaces the in-memory SessionState with persistent storage:
- Session metadata stored in PostgreSQL
- DataFrames stored as Parquet files
- Automatic cleanup of expired sessions
"""
from __future__ import annotations

import asyncio
import importlib.util
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.sql import func

from ..core.logger import logger
from ..db.session_models import Session as SessionModel


try:
    import pyarrow as pa
    import pyarrow.parquet as pq

    PARQUET_ENGINE: Optional[str] = "pyarrow"
except ImportError:  # pragma: no cover - depends on local environment
    pa = None
    pq = None
    PARQUET_ENGINE = "fastparquet" if importlib.util.find_spec("fastparquet") else None


class PersistentSessionState:
    """Persistent session state with DB + Parquet storage."""

    def __init__(self, session_id: str, storage_path: str = "./session_storage"):
        self.session_id = session_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self._cache: Dict[str, Any] = {}
        self._loaded = False

    @property
    def session_dir(self) -> Path:
        """Directory for this session's data files."""
        return self.storage_path / self.session_id

    @property
    def dataset_path(self) -> Path:
        """Storage location for the session dataset."""
        filename = "dataset.parquet" if PARQUET_ENGINE else "dataset.pkl"
        return self.session_dir / filename

    def _write_dataframe(self, df: pd.DataFrame, dataset_path: Path) -> None:
        """Persist a DataFrame using the best available local storage format."""
        if PARQUET_ENGINE == "pyarrow" and pa is not None and pq is not None:
            table = pa.Table.from_pandas(df)
            pq.write_table(table, dataset_path)
            return

        if PARQUET_ENGINE:
            df.to_parquet(dataset_path, engine=PARQUET_ENGINE, index=False)
            return

        logger.warning(
            "No parquet engine installed; falling back to pickle storage for session datasets."
        )
        df.to_pickle(dataset_path)

    def _read_dataframe(self, dataset_path: Path) -> pd.DataFrame:
        """Load a persisted DataFrame regardless of the storage backend."""
        if dataset_path.suffix == ".pkl":
            return pd.read_pickle(dataset_path)

        if PARQUET_ENGINE == "pyarrow" and pq is not None:
            table = pq.read_table(dataset_path)
            return table.to_pandas()

        if PARQUET_ENGINE:
            return pd.read_parquet(dataset_path, engine=PARQUET_ENGINE)

        raise RuntimeError(
            f"Cannot read parquet dataset {dataset_path}: no parquet engine is installed."
        )

    async def _ensure_loaded(self, db: Optional[AsyncSession] = None) -> None:
        """Load session data from DB and Parquet if not already loaded."""
        if self._loaded:
            return

        if db is not None:
            # Load from DB
            stmt = select(SessionModel).where(SessionModel.id == self.session_id)
            result = await db.execute(stmt)
            session_record = result.scalar_one_or_none()

            if session_record:
                self._cache.update(session_record.session_metadata or {})

                # Load DataFrame from Parquet if exists
                dataset_path = Path(session_record.parquet_path) if session_record.parquet_path else self.dataset_path
                if not dataset_path.exists():
                    parquet_fallback = self.session_dir / "dataset.parquet"
                    pickle_fallback = self.session_dir / "dataset.pkl"
                    if parquet_fallback.exists():
                        dataset_path = parquet_fallback
                    elif pickle_fallback.exists():
                        dataset_path = pickle_fallback
                if dataset_path.exists():
                    try:
                        df = self._read_dataframe(dataset_path)
                        self._cache["raw_dataframe"] = df
                    except Exception as e:
                        logger.warning(f"Failed to load dataset from Parquet: {e}")

        self._loaded = True

    async def create_session(self, db: AsyncSession, filename: str, df: pd.DataFrame) -> None:
        """Create a new persistent session."""
        # Save DataFrame to Parquet
        self.session_dir.mkdir(exist_ok=True, parents=True)
        dataset_path = self.dataset_path
        self._write_dataframe(df, dataset_path)

        # Create DB record
        expires_at = datetime.utcnow() + timedelta(hours=24)
        session_record = SessionModel(
            id=self.session_id,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            expires_at=expires_at,
            dataset_filename=filename,
            dataset_rows=len(df),
            dataset_cols=len(df.columns),
            parquet_path=str(dataset_path),
            session_metadata=self._cache
        )

        db.add(session_record)
        await db.commit()

        self._cache["raw_dataframe"] = df
        self._loaded = True

        logger.info("Session created persistently", extra={
            "session_id": self.session_id,
            "rows": len(df),
            "cols": len(df.columns)
        })

    async def update_access_time(self, db: AsyncSession) -> None:
        """Update last accessed timestamp."""
        stmt = (
            update(SessionModel)
            .where(SessionModel.id == self.session_id)
            .values(last_accessed=datetime.utcnow())
        )
        await db.execute(stmt)
        await db.commit()

    def set(self, key: str, value: Any) -> None:
        """Set a value in session state."""
        self._cache[key] = value

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a value from session state."""
        return self._cache.get(key, default)

    def dump(self) -> Dict[str, Any]:
        """Dump all session data."""
        return dict(self._cache)

    async def persist_metadata(self, db: AsyncSession) -> None:
        """Persist current metadata to DB."""
        stmt = (
            update(SessionModel)
            .where(SessionModel.id == self.session_id)
            .values(session_metadata=self._cache, last_accessed=datetime.utcnow())
        )
        await db.execute(stmt)
        await db.commit()


class SessionManager:
    """Manager for persistent sessions with cleanup."""

    def __init__(self, storage_path: str = "./session_storage"):
        self.storage_path = Path(storage_path)
        self._sessions: Dict[str, PersistentSessionState] = {}

    def get_session(self, session_id: str) -> PersistentSessionState:
        """Get or create a session state instance."""
        if session_id not in self._sessions:
            self._sessions[session_id] = PersistentSessionState(session_id, self.storage_path)
        return self._sessions[session_id]

    async def cleanup_expired_sessions(self, db: AsyncSession) -> None:
        """Remove expired sessions from DB and filesystem."""
        try:
            # Find expired sessions
            cutoff = datetime.utcnow()
            stmt = select(SessionModel).where(SessionModel.expires_at < cutoff)
            result = await db.execute(stmt)
            expired_sessions = result.scalars().all()

            for session in expired_sessions:
                # Remove from filesystem
                session_dir = self.storage_path / session.id
                if session_dir.exists():
                    import shutil
                    shutil.rmtree(session_dir)

                # Remove from DB
                await db.delete(session)
                logger.info(f"Cleaned up expired session: {session.id}")

            if expired_sessions:
                await db.commit()

        except Exception as e:
            logger.exception(f"Session cleanup failed: {e}")

    async def start_cleanup_task(self, db_session_factory) -> None:
        """Start background task to cleanup expired sessions."""
        async def cleanup_loop():
            while True:
                try:
                    async with db_session_factory() as db:
                        await self.cleanup_expired_sessions(db)
                except Exception as e:
                    logger.exception(f"Cleanup task error: {e}")
                await asyncio.sleep(3600)  # Run every hour

        asyncio.create_task(cleanup_loop())


# Global session manager instance
session_manager = SessionManager()
