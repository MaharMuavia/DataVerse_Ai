"""New session management models for persistent data storage.

These models handle session persistence, query logging, and background ML jobs.
They are separate from the legacy models to avoid SQLAlchemy conflicts.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Session(Base):
    """Stores active session metadata for persistence across restarts.

    Why: Sessions need to survive server restarts with DataFrame data
    stored as Parquet files and metadata in JSONB.
    """
    __tablename__ = "sessions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    dataset_filename = Column(String(512), nullable=False)
    dataset_rows = Column(Integer, nullable=False)
    dataset_cols = Column(Integer, nullable=False)
    parquet_path = Column(String(1024), nullable=False)
    session_metadata = Column(JSONB, nullable=False, default=dict)

    # Relationships
    queries = relationship("Query", back_populates="session", cascade="all, delete-orphan")
    ml_jobs = relationship("MLJob", back_populates="session", cascade="all, delete-orphan")


class Query(Base):
    """Stores user queries and their results.

    Why: Track all user interactions for auditability and analytics.
    """
    __tablename__ = "queries"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(PGUUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    query_text = Column(Text, nullable=False)
    intent = Column(String(128), nullable=True)
    confidence = Column(JSONB, nullable=True)  # Store confidence scores
    result_json = Column(JSONB, nullable=True)
    narration = Column(Text, nullable=True)
    chart_spec = Column(Text, nullable=True)  # JSON string for Plotly specs
    execution_ms = Column(Integer, nullable=True)

    session = relationship("Session", back_populates="queries")


class MLJob(Base):
    """Tracks background ML training jobs.

    Why: AutoML training can take time, so we run it asynchronously
    and track progress.
    """
    __tablename__ = "ml_jobs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(PGUUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(32), nullable=False, default="pending")  # pending, running, complete, failed
    task_type = Column(String(32), nullable=True)  # classification or regression
    target_column = Column(String(128), nullable=True)
    best_model = Column(String(128), nullable=True)
    metrics = Column(JSONB, nullable=True)
    shap_values = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)

    session = relationship("Session", back_populates="ml_jobs")