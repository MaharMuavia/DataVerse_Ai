"""LangGraph runtime - stub module.

The full LangGraph integration requires a `graph.dataverse_graph` package which
is not yet implemented. This stub prevents import errors while the rest of the
application uses the simpler pandas-based query processing pipeline.
"""
from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logger import logger


async def run_graph_query(
    session_id: str,
    user_query: str,
    db: Optional[AsyncSession] = None,
    thread_id: Optional[str] = None,
    dataset_path_override: Optional[str] = None,
) -> Dict[str, Any]:
    raise NotImplementedError("LangGraph runtime is not configured. Using legacy stream processor.")


async def stream_graph_query_events(
    session_id: str,
    user_query: str,
    db: Optional[AsyncSession] = None,
    thread_id: Optional[str] = None,
    dataset_path_override: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    raise NotImplementedError("LangGraph runtime is not configured.")
    yield  # make it a generator
