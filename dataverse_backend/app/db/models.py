"""SQLAlchemy ORM models for persistent system data.

These models are designed for PostgreSQL (use of UUID and JSONB) and
capture dataset metadata, user queries, agent execution traces, analysis
results, and final reports. Each model includes a brief comment explaining
its purpose to aid future maintainers.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Dataset(Base):
    """Stores metadata for each uploaded dataset.

    Why: datasets are the primary units of analysis and must be auditable.
    We store filename, row counts, JSON column metadata, and upload timestamp.
    """
    __tablename__ = "datasets"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(512), nullable=False)
    row_count = Column(Integer, nullable=False)
    column_metadata = Column(JSONB, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    queries = relationship("UserQuery", back_populates="dataset", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="dataset", cascade="all, delete-orphan")


class UserQuery(Base):
    """Represents a user-submitted query against a dataset.

    Why: queries must be recorded for auditability and explainability; parsed
    intent is stored as JSON to replay or inspect how decisions were made.
    """
    __tablename__ = "user_queries"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(PGUUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    query_text = Column(Text, nullable=False)
    parsed_intent = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dataset = relationship("Dataset", back_populates="queries")


class AgentRun(Base):
    """A single execution record for an agent step.

    Why: recording agent actions (name, action, reasoning) enables traceability
    and later debugging of how a report was produced.
    """
    __tablename__ = "agent_runs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(PGUUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    agent_name = Column(String(128), nullable=False)
    action = Column(String(256), nullable=False)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dataset = relationship("Dataset")


class AnalysisResult(Base):
    """Stores computed metrics and results from analysis agents.

    Why: analysis outputs are critical for explainability and for generating
    derived reports; store computed metrics as JSON to allow flexible schemas.
    """
    __tablename__ = "analysis_results"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(PGUUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    computed_metrics = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dataset = relationship("Dataset", back_populates="analysis_results")


class Report(Base):
    """Final narrative or structured report produced for an analysis.

    Why: persisting the final report (text or structured JSON) along with the
    model used and the link to the originating analysis enables provenance.
    """
    __tablename__ = "reports"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_result_id = Column(PGUUID(as_uuid=True), ForeignKey("analysis_results.id"), nullable=True)
    report_text = Column(Text, nullable=False)
    model_used = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis_result = relationship("AnalysisResult")
