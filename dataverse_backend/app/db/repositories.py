"""Repository layer: encapsulates DB access for persistence operations.

All functions accept an `AsyncSession` and perform focused, transactional
work. Agents and other higher-level modules should call these functions
instead of interacting with ORM/session directly to preserve separation of concerns.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError

from .models import Dataset, UserQuery, AgentRun, AnalysisResult, Report
from .session_models import Query, Session
from ..core.logger import logger


async def create_dataset(db: AsyncSession, filename: str, row_count: int, column_metadata: Dict[str, Any]) -> Dataset:
    """Persist dataset metadata and return the Dataset instance.

    This function encapsulates how dataset metadata is stored so callers
    don't need ORM details. It also logs errors and re-raises exceptions
    to let the caller handle HTTP responses or retries.
    """
    try:
        ds = Dataset(filename=filename, row_count=row_count, column_metadata=column_metadata)
        db.add(ds)
        await db.commit()
        await db.refresh(ds)
        logger.info("Dataset metadata persisted", extra={"dataset_id": str(ds.id), "filename": filename})
        return ds
    except SQLAlchemyError as e:
        await db.rollback()
        logger.exception("Failed to persist dataset metadata")
        raise


async def log_user_query(db: AsyncSession, query_text: str, parsed_intent: Optional[Dict[str, Any]] = None, dataset_id: Optional[str] = None) -> UserQuery:
    try:
        uq = UserQuery(dataset_id=dataset_id, query_text=query_text, parsed_intent=parsed_intent)
        db.add(uq)
        await db.commit()
        await db.refresh(uq)
        logger.info("User query logged", extra={"query_id": str(uq.id), "dataset_id": dataset_id})
        return uq
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("Failed to log user query")
        raise


async def log_query(db: AsyncSession, session_id: str, query_text: str, intent: str, confidence: Optional[Dict[str, Any]] = None) -> Query:
    """Log a query to the new queries table."""
    try:
        query = Query(
            session_id=session_id,
            query_text=query_text,
            intent=intent,
            confidence=confidence
        )
        db.add(query)
        await db.commit()
        await db.refresh(query)
        logger.info("Query logged", extra={"query_id": str(query.id), "session_id": session_id})
        return query
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("Failed to log query")
        raise


async def log_agent_run(db: AsyncSession, agent_name: str, action: str, reasoning: Optional[str] = None, dataset_id: Optional[str] = None) -> AgentRun:
    try:
        ar = AgentRun(agent_name=agent_name, action=action, reasoning=reasoning, dataset_id=dataset_id)
        db.add(ar)
        await db.commit()
        await db.refresh(ar)
        logger.info("Agent run persisted", extra={"agent_run_id": str(ar.id), "agent": agent_name})
        return ar
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("Failed to persist agent run")
        raise


async def save_analysis_result(db: AsyncSession, dataset_id: Optional[str], computed_metrics: Dict[str, Any]) -> AnalysisResult:
    try:
        ar = AnalysisResult(dataset_id=dataset_id, computed_metrics=computed_metrics)
        db.add(ar)
        await db.commit()
        await db.refresh(ar)
        logger.info("Analysis result saved", extra={"analysis_result_id": str(ar.id), "dataset_id": dataset_id})
        return ar
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("Failed to save analysis result")
        raise


async def save_report(db: AsyncSession, analysis_result_id: Optional[str], report_text: str, model_used: str) -> Report:
    try:
        rep = Report(analysis_result_id=analysis_result_id, report_text=report_text, model_used=model_used)
        db.add(rep)
        await db.commit()
        await db.refresh(rep)
        logger.info("Report saved", extra={"report_id": str(rep.id), "model": model_used})
        return rep
    except SQLAlchemyError:
        await db.rollback()
        logger.exception("Failed to save report")
        raise
