"""Local/demo automatic analysis endpoints."""
from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..api.upload_parsing import parse_uploaded_dataframe
from ..core.config import settings
from ..core.logger import logger
from ..services.analysis_pipeline import AnalysisPipeline, create_session_id, persist_dataframe_for_session
from ..state.persistent_session_state import session_manager
from ..state.session_state import SessionState


router = APIRouter()


class AnalyzeQueryRequest(BaseModel):
    session_id: str
    query: str
    target_column: str | None = None


def _load_session_dataframe(session_id: str) -> pd.DataFrame | None:
    persistent = session_manager.get_session(session_id)
    df = persistent.get_value("raw_dataframe")
    if df is not None:
        return df.copy()

    simple = SessionState.get(session_id)
    df = simple.get_value("raw_dataframe")
    if df is not None:
        return df.copy()

    for candidate in (persistent.session_dir / "dataset.parquet", persistent.session_dir / "dataset.pkl"):
        if candidate.exists():
            if candidate.suffix == ".pkl":
                df = pd.read_pickle(candidate)
            else:
                df = persistent._read_dataframe(candidate)
            persistent.set("raw_dataframe", df.copy())
            simple.set("raw_dataframe", df.copy())
            return df
    return None


@router.post("/upload")
async def analyze_upload(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a dataset and immediately return a full automatic analysis report.

    Auth is intentionally optional here for local/demo analysis. In production,
    wrap this router with ``get_current_active_user`` or mount it behind a
    protected workspace route.
    """
    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")
    if not (file.filename or "").lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    try:
        df = parse_uploaded_dataframe(file.filename or "upload.csv", contents)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid file upload: {exc}") from exc

    session_id = create_session_id()
    try:
        dataset_path = persist_dataframe_for_session(session_id, df, filename=file.filename)
        report = await AnalysisPipeline().run_full_analysis_async(
            df,
            query="analyze uploaded dataset",
            session_id=session_id,
        )
        report["session_id"] = session_id
        report["dataset_path"] = str(dataset_path)
        return report
    except Exception as exc:
        logger.exception("Automatic upload analysis failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/query")
async def analyze_query(request: AnalyzeQueryRequest) -> dict[str, Any]:
    """Run query-specific analysis against an already uploaded local/demo dataset.

    Auth is intentionally optional for local development; production deployments
    should add JWT/workspace authorization before exposing user data.
    """
    df = _load_session_dataframe(request.session_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Session or dataset not found")

    try:
        report = await AnalysisPipeline().run_full_analysis_async(
            df,
            query=request.query,
            target_column=request.target_column,
            session_id=request.session_id,
        )
        report["session_id"] = request.session_id
        return report
    except Exception as exc:
        logger.exception("Query-specific analysis failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
