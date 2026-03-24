"""API routes for DataVerse AI."""
from __future__ import annotations

import io
import uuid
import pandas as pd
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..db.base import get_session
from ..db.repositories import create_dataset, log_user_query

from ..core.auth import get_current_active_user
from ..api.schemas import User
from ..core.exceptions import DataLoadError, DataNotFoundError
from ..data.data_manager import DataManager
from ..state.session_state import SessionState
from ..orchestrator.agent_orchestrator import AgentOrchestrator
from ..agents.retail_detector_agent import RetailDetectorAgent
from ..agents.eda_analytics_agent import EDAAgent
from ..agents.automl_agent import AutoMLAgent
from .schemas import (
    UploadResponse,
    QueryRequest,
    QueryResponse,
    HealthResponse,
    SessionStatusResponse,
    ConfirmColumnRequest,
    ConfirmColumnResponse,
    DatasetProfileResponse,
    CorrelationResponse,
    RecommendationResponse,
    TrainModelRequest,
    TrainModelResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok", details={"app": "DataVerse AI backend"})


@router.get("/session/{session_id}", response_model=SessionStatusResponse)
def session_status(session_id: str):
    state = SessionState.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionStatusResponse(
        session_id=session_id,
        dataset_is_retail=state.get_value("dataset_is_retail"),
        retail_validation=state.get_value("retail_validation"),
        execution_trace=state.get_value("execution_trace"),
        eda_completed=state.get_value("eda_completed"),
        preprocessing_completed=state.get_value("preprocessing_completed"),
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Optional[AsyncSession] = Depends(get_session)
):
    # Assign a new session id for each upload
    session_id = str(uuid.uuid4())
    try:
        content = file.file.read()
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        logger.exception("Failed to read uploaded CSV file")
        raise HTTPException(status_code=400, detail=f"Invalid CSV upload: {e}")

    try:
        dm = DataManager(session_id=session_id)
        dm.save_raw(df)
        logger.info("Dataset uploaded and saved", extra={"session_id": session_id})

        # Retail dataset validation (informative)
        retail_agent = RetailDetectorAgent(session_id=session_id)
        validation = retail_agent.run()
        is_retail = validation.get("is_retail", False)
        # keep this validation in session state for orchestration decisions
        state = SessionState.get(session_id)
        state.set("dataset_is_retail", is_retail)
        state.set("retail_validation", validation)

        # Persist dataset metadata if DB is configured and session provided
        if db is not None:
            try:
                # Build a minimal column metadata structure
                col_meta = {"columns": df.columns.tolist(), "dtypes": {c: str(dt) for c, dt in df.dtypes.items()}}
                ds = await create_dataset(db, filename=file.filename or "upload.csv", row_count=len(df), column_metadata=col_meta)
                # Save mapping in session state for later reference
                state = SessionState.get(session_id)
                state.set("dataset_id", str(ds.id))
            except Exception as e:
                logger.warning(f"Failed to persist dataset metadata: {e}")
                # Continue anyway - graceful degradation

        if is_retail:
            msg = "Upload successful and dataset appears to be retail-mart related."
        else:
            msg = "Upload successful but dataset appears non-retail; downstream analytics may be generic."

        return UploadResponse(
            session_id=session_id,
            success=True,
            message=msg,
            is_retail=is_retail,
            matched_keywords=validation.get("matched_keywords", []),
        )
    except Exception as e:
        logger.exception("Failed during DataManager save operation")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm_column", response_model=ConfirmColumnResponse)
async def confirm_column(request: ConfirmColumnRequest):
    """Endpoint for users to confirm ambiguous column choices (e.g., product column)."""
    state = SessionState.get(request.session_id)
    # Validate column exists in uploaded dataset
    try:
        dm = DataManager(session_id=request.session_id)
        df = dm.get_raw()
    except Exception:
        raise HTTPException(status_code=404, detail="Session or dataset not found")

    if request.column_name not in df.columns:
        raise HTTPException(status_code=400, detail="Column not found in dataset")

    state.set("product_override", request.column_name)
    logger.info("Product column confirmed by user", extra={"session_id": request.session_id, "column": request.column_name})
    return ConfirmColumnResponse(session_id=request.session_id, column_name=request.column_name, message="Column confirmed")


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Optional[AsyncSession] = Depends(get_session)
):
    orchestrator = AgentOrchestrator()
    try:
        # Log user query early for auditability
        session_state = SessionState.get(request.session_id)
        dataset_id = session_state.get_value("dataset_id") if session_state else None
        if db is not None and dataset_id:
            try:
                await log_user_query(db, query_text=request.query, parsed_intent=None, dataset_id=dataset_id)
            except Exception as e:
                logger.warning(f"Failed to log user query: {e}")

        result = await orchestrator.handle_query(session_id=request.session_id, user_query=request.query, db=db)

        return QueryResponse(
            session_id=request.session_id,
            intent=result.get("intent"),
            computed_facts=result.get("computed_facts", {}),
            report=result.get("report", ""),
            action_required=result.get("action_required"),
            candidates=result.get("candidates"),
            is_retail=session_state.get_value("dataset_is_retail") if session_state else None,
        )
    except DataNotFoundError as e:
        logger.error("Data not found for query", exc_info=e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in query endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dataset/profile", response_model=DatasetProfileResponse)
def dataset_profile(session_id: str):
    try:
        dm = DataManager(session_id=session_id)
        profile = dm.generate_profile()
        return DatasetProfileResponse(session_id=session_id, profile=profile.to_dict())
    except Exception as e:
        logger.exception("Failed to generate dataset profile")
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/dataset/correlation", response_model=CorrelationResponse)
def dataset_correlation(session_id: str):
    try:
        eda_agent = EDAAgent(session_id=session_id)
        eda_result = eda_agent.run()
        corr = eda_result.get("correlations", {})
        return CorrelationResponse(session_id=session_id, correlations=corr)
    except Exception as e:
        logger.exception("Failed to compute correlation")
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/dataset/recommendations", response_model=RecommendationResponse)
def dataset_recommendations(session_id: str):
    try:
        dm = DataManager(session_id=session_id)
        eda_agent = EDAAgent(session_id=session_id)
        eda_result = eda_agent.run()

        missing = eda_result.get("missing_values", {})
        high_corr = eda_result.get("correlations", {}).get("high_correlations", [])
        numeric = eda_result.get("profile_summary", {}).get("numeric_columns", 0)

        recs = []
        if missing.get("total_missing", 0) > 0:
            recs.append("Impute missing values for columns with missing data")
        else:
            recs.append("No missing values detected; proceed with modeling")

        if high_corr:
            recs.append("Check multicollinearity among highly correlated features")

        if numeric >= 1:
            recs.append("Consider scaling numeric features before modeling")

        recs.append("Based on query intent, run AutoML to select best model")

        key_findings = {
            "dataset_shape": eda_result.get("dataset_shape"),
            "missing_summary": missing,
            "high_correlations": high_corr,
            "variable_summary": eda_result.get("profile_summary"),
        }

        return RecommendationResponse(session_id=session_id, recommendations=recs, key_findings=key_findings)
    except Exception as e:
        logger.exception("Failed to generate recommendations")
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/dataset/train", response_model=TrainModelResponse)
async def dataset_train(request: TrainModelRequest):
    try:
        automl = AutoMLAgent(session_id=request.session_id)
        result = automl.run(task_type=request.task_type, target_column=request.target_column, test_size=request.test_size)

        if result.get("status") != "success":
            return TrainModelResponse(
                session_id=request.session_id,
                task_type=request.task_type,
                target_column=request.target_column,
                status="failed",
                error=result.get("error"),
            )

        return TrainModelResponse(
            session_id=request.session_id,
            task_type=request.task_type,
            target_column=request.target_column,
            status="success",
            best_model=result.get("best_model"),
            metrics=result.get("metrics"),
            predictions_sample=result.get("predictions_sample"),
            feature_importance=result.get("feature_importance"),
        )
    except Exception as e:
        logger.exception("AutoML training failed")
        raise HTTPException(status_code=500, detail=str(e))

