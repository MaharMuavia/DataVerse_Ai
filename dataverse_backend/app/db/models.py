"""SQLAlchemy ORM models for persistent system data.

These models are designed for PostgreSQL (use of UUID and JSONB) and
capture users, datasets, conversations, messages, ML jobs, and agent traces.
Each model includes a brief comment explaining its purpose to aid future maintainers.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """Represents a platform user with authentication credentials.
    
    Why: Users must be authenticated and isolated; their datasets, conversations,
    and analyses are scoped to their workspace. JWT tokens reference the user_id.
    """
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(128), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    plan = Column(String(50), default="free", nullable=False)  # free, pro, enterprise
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    workspaces = relationship("Workspace", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Workspace(Base):
    """Groups datasets and analyses under a user's organization.
    
    Why: Users can have multiple analysis workspaces; each workspace
    organizes datasets and conversations for a particular project.
    """
    __tablename__ = "workspaces"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="workspaces")
    datasets = relationship("Dataset", back_populates="workspace", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")


class Dataset(Base):
    """Stores metadata for each uploaded dataset.

    Why: datasets are the primary units of analysis and must be auditable.
    We store original filename, row/column counts, schema, profiling results,
    storage path, and upload timestamp. Status tracks profiling progress.
    """
    __tablename__ = "datasets"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(PGUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    original_filename = Column(String(512), nullable=False)
    storage_path = Column(Text, nullable=False)  # S3/MinIO path
    file_type = Column(String(10), nullable=False)  # csv, xlsx, json, parquet
    row_count = Column(Integer, nullable=True)
    col_count = Column(Integer, nullable=True)
    schema_json = Column(JSONB, nullable=True)  # {col_name: dtype, ...}
    profile_json = Column(JSONB, nullable=True)  # YData profiling summary
    status = Column(String(50), default="uploaded", nullable=False)  # uploaded, profiling, ready, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    workspace = relationship("Workspace", back_populates="datasets")
    conversations = relationship("Conversation", back_populates="dataset", cascade="all, delete-orphan")
    ml_jobs = relationship("MLJob", back_populates="dataset", cascade="all, delete-orphan")


class UserQuery(Base):
    """Legacy dataset-level user query record."""

    __tablename__ = "user_queries"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(PGUUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True, index=True)
    query_text = Column(Text, nullable=False)
    parsed_intent = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentRun(Base):
    """Legacy agent execution audit record."""

    __tablename__ = "agent_runs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(PGUUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True, index=True)
    agent_name = Column(String(128), nullable=False)
    action = Column(String(256), nullable=False)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AnalysisResult(Base):
    """Legacy analysis output record."""

    __tablename__ = "analysis_results"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(PGUUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True, index=True)
    computed_metrics = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Report(Base):
    """Legacy generated report record."""

    __tablename__ = "reports"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_result_id = Column(PGUUID(as_uuid=True), ForeignKey("analysis_results.id"), nullable=True, index=True)
    report_text = Column(Text, nullable=False)
    model_used = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Conversation(Base):
    """Represents a chat session between user and AI agents for a dataset.
    
    Why: Conversations group messages, maintain context, and track which
    dataset was analyzed. Enables conversation history and context recovery.
    """
    __tablename__ = "conversations"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(PGUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    dataset_id = Column(PGUUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="conversations")
    workspace = relationship("Workspace", back_populates="conversations")
    dataset = relationship("Dataset", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    agent_logs = relationship("AgentLog", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Individual message in a conversation (user, assistant, agent).
    
    Why: Messages need to be persisted for conversation replay, context recovery,
    search history. Different message types (text, chart, table, insight) require
    flexible payload storage.
    """
    __tablename__ = "messages"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(PGUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, agent
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text", nullable=False)  # text, chart, table, insight, model_result, code
    payload_json = Column(JSONB, nullable=True)  # chart spec, table data, metrics, etc
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class MLJob(Base):
    """Represents an ML task (classification, regression, clustering, forecast).
    
    Why: ML jobs are async and long-running; status tracking, result persistence,
    and metrics storage are needed for job monitoring and result recovery.
    """
    __tablename__ = "ml_jobs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(PGUUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False, index=True)
    conversation_id = Column(PGUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True, index=True)
    task_type = Column(String(50), nullable=False)  # classification, regression, clustering, forecast
    target_column = Column(String(255), nullable=False)
    feature_columns = Column(JSONB, nullable=True)  # ["col1", "col2", ...]
    status = Column(String(50), default="queued", nullable=False)  # queued, running, complete, failed
    best_model = Column(String(255), nullable=True)
    metrics_json = Column(JSONB, nullable=True)  # {rmse, r2, mae, accuracy, etc}
    feature_importance = Column(JSONB, nullable=True)  # [{feature, importance}, ...]
    shap_values = Column(JSONB, nullable=True)  # SHAP summary data
    predictions_sample = Column(JSONB, nullable=True)  # Sample predictions
    model_path = Column(Text, nullable=True)  # S3/MinIO path to saved model
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    dataset = relationship("Dataset", back_populates="ml_jobs")
    conversation = relationship("Conversation")


class AgentLog(Base):
    """Execution trace for each agent action.
    
    Why: Detailed logging enables debugging, auditing, and understanding how
    results were produced. Each agent step is recorded with inputs/outputs.
    """
    __tablename__ = "agent_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(PGUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    agent_name = Column(String(128), nullable=False)
    action = Column(String(256), nullable=False)
    input_json = Column(JSONB, nullable=True)
    output_json = Column(JSONB, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String(50), default="success", nullable=False)  # success, failed, timeout
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("Conversation", back_populates="agent_logs")
