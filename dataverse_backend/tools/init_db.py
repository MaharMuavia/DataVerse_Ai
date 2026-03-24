#!/usr/bin/env python3
"""Initialize database schema for DataVerse AI.

This script creates all tables defined in app.db.models using SQLAlchemy ORM.
Run this once after configuring DATABASE_URL in .env.

Usage:
    python tools/init_db.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logger import logger
from app.db.base import get_engine
from app.db.models import Base
from sqlalchemy.exc import OperationalError


async def initialize_database():
    """Create all tables in the database if they don't exist."""
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL is not configured. Set it in .env file.")
        logger.error("Example: DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dataverse_db")
        return False

    engine = get_engine()
    if engine is None:
        logger.error("Failed to create engine. Check DATABASE_URL format.")
        return False

    try:
        # Test connectivity first
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database connection successful")

        # Create all tables (idempotent: only creates missing tables)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully")
        logger.info("Tables created: datasets, user_queries, agent_runs, analysis_results, reports")
        return True

    except OperationalError as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error("Ensure PostgreSQL is running and DATABASE_URL is correct")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error during initialization: {e}")
        return False


async def main():
    success = await initialize_database()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
