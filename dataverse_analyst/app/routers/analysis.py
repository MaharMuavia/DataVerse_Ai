from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents import AnalysisAgent, XAIAgent
from app.core.csv_parser import read_csv_bytes
from app.models.session import session_store


router = APIRouter()
analysis_agent = AnalysisAgent()
xai_agent = XAIAgent()


@router.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        df = read_csv_bytes(await file.read())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {exc}") from exc
    session_id = session_store.create(df, file.filename or "uploaded.csv")
    return {
        "session_id": session_id,
        "filename": file.filename,
        "rows": int(df.shape[0]),
        "columns": [str(column) for column in df.columns],
    }


@router.post("/analyze")
async def analyze(session_id: str = Form(...), target_column: str | None = Form(default=None)) -> dict[str, Any]:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    analysis = analysis_agent.run(session.df, target_column)
    eda = analysis["eda"]
    trends = analysis["trends"]
    model_result = analysis["model_result"]
    public_model = analysis["public_model"]

    if model_result.get("status") == "success":
        xai = xai_agent.explain(model_result["model"], model_result["X_train"], model_result["X_test"].head(50))
    else:
        xai = {"status": "skipped", "error": "Model training did not complete", "importances": {}}

    narrative = analysis_agent.generate_narrative(eda, xai.get("importances", {}), public_model)
    report = {
        "session_id": session_id,
        "filename": session.filename,
        "eda": eda,
        "trends": trends,
        "model": public_model,
        "xai": xai,
        "lime": analysis["lime"],
        "narrative": narrative,
    }
    session_store.set_results(session_id, report)
    return report


@router.get("/report/{session_id}")
async def report(session_id: str) -> dict[str, Any]:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if not session.results:
        raise HTTPException(status_code=404, detail="report not generated yet")
    return session.results
