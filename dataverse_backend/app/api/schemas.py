"""Pydantic schemas for request and response payloads."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UploadResponse(BaseModel):
    session_id: str
    success: bool
    message: str
    is_retail: bool
    matched_keywords: Optional[List[str]] = None
    session_id: str
    success: bool
    message: str
    is_retail: bool
    matched_keywords: Optional[List[str]] = None


class QueryRequest(BaseModel):
    session_id: str
    query: str


class QueryResponse(BaseModel):
    session_id: str
    intent: Dict[str, Any]
    computed_facts: Dict[str, Any]
    report: str
    action_required: Optional[str] = None
    candidates: Optional[List[str]] = None
    is_retail: Optional[bool] = None


class SessionStatusResponse(BaseModel):
    session_id: str
    dataset_is_retail: Optional[bool] = None
    retail_validation: Optional[Dict[str, Any]] = None
    execution_trace: Optional[List[str]] = None
    eda_completed: Optional[bool] = None
    preprocessing_completed: Optional[bool] = None


class ConfirmColumnRequest(BaseModel):
    session_id: str
    column_name: str


class ConfirmColumnResponse(BaseModel):
    session_id: str
    column_name: str
    message: str


class HealthResponse(BaseModel):
    status: str
    details: Optional[Dict[str, Any]] = None


class DatasetProfileResponse(BaseModel):
    session_id: str
    profile: Dict[str, Any]


class CorrelationResponse(BaseModel):
    session_id: str
    correlations: Dict[str, Any]


class RecommendationResponse(BaseModel):
    session_id: str
    recommendations: List[str]
    key_findings: Dict[str, Any]


class TrainModelRequest(BaseModel):
    session_id: str
    target_column: str
    task_type: str = Field(default="classification", description="classification or regression")
    test_size: Optional[float] = Field(default=0.2, ge=0.1, le=0.5)


class TrainModelResponse(BaseModel):
    session_id: str
    task_type: str
    target_column: str
    status: str
    best_model: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    predictions_sample: Optional[List[Dict[str, Any]]] = None
    feature_importance: Optional[Dict[str, float]] = None
    error: Optional[str] = None
