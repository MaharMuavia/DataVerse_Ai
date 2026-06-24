"""ChatGPT-style chat session, dataset, analysis, and message routes."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from ..api.schemas import ChatMessageCreate, ChatSessionCreate, ChatSessionUpdate, DatasetCleanRequest, DatasetVerifyRequest, DatasetWhatIfRequest, SessionAnalyzeRequest
from ..core.config import settings
from ..services.progress_bus import progress_bus
from ..services.session_service import session_service


router = APIRouter()


@router.post("/sessions")
async def create_session(
    request: ChatSessionCreate,
    dataverse_user: str | None = Header(default=None, alias="X-Dataverse-User"),
) -> dict[str, Any]:
    return await session_service.create_session(title=request.title, user_id=dataverse_user)


@router.get("/sessions")
async def list_sessions(
    dataverse_user: str | None = Header(default=None, alias="X-Dataverse-User"),
) -> list[dict[str, Any]]:
    return await session_service.list_sessions(user_id=dataverse_user)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    try:
        return await session_service.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/sessions/{session_id}")
async def update_session(session_id: str, request: ChatSessionUpdate) -> dict[str, Any]:
    payload = {key: value for key, value in request.model_dump(exclude_unset=True).items() if value is not None}
    updated = await session_service.update_session(session_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    return updated


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict[str, Any]:
    await session_service.delete_session(session_id)
    return {"session_id": session_id, "deleted": True}


@router.post("/sessions/{session_id}/datasets/upload")
async def upload_dataset_to_session(
    session_id: str,
    file: UploadFile = File(...),
    auto_analyze: bool = Query(default=False),
    generate_report: bool = Query(default=False),
    run_xai: bool = Query(default=False),
) -> dict[str, Any]:
    contents = await file.read()
    filename = file.filename or "dataset.csv"
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(contents) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")
    if not filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    try:
        dataset = await session_service.upload_dataset(session_id, filename, contents)
        analysis = None
        if auto_analyze:
            analysis = await session_service.analyze(
                session_id,
                dataset_id=dataset["id"],
                user_prompt="Analyze this dataset",
                run_xai=run_xai,
                generate_report=generate_report,
            )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid dataset upload: {exc}") from exc
    return {
        "dataset_id": dataset["id"],
        "session_id": session_id,
        "filename": dataset["filename"],
        "row_count": dataset["row_count"],
        "column_count": dataset["column_count"],
        "columns": dataset["columns"],
        "status": dataset["status"],
        "dataset": dataset,
        "analysis": analysis,
    }


@router.get("/sessions/{session_id}/datasets")
async def list_session_datasets(session_id: str) -> list[dict[str, Any]]:
    return await session_service.list_session_datasets(session_id)


@router.post("/sessions/{session_id}/analyze")
async def analyze_session(session_id: str, request: SessionAnalyzeRequest) -> dict[str, Any]:
    try:
        return await session_service.analyze(
            session_id,
            dataset_id=request.dataset_id,
            user_prompt=request.user_prompt,
            run_xai=request.run_xai,
            generate_report=request.generate_report,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/datasets/{dataset_id}/clean")
async def clean_dataset(session_id: str, dataset_id: str, request: DatasetCleanRequest) -> dict[str, Any]:
    """Apply Data Quality Doctor fixes and return the re-analysis of the cleaned data."""
    try:
        return await session_service.clean_dataset(session_id, dataset_id, request.fix_ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/datasets/{dataset_id}/verify")
async def verify_dataset(session_id: str, dataset_id: str, request: DatasetVerifyRequest) -> dict[str, Any]:
    """Re-run the deterministic computation and verify it reproduces the certificate."""
    try:
        return await session_service.verify_dataset(session_id, dataset_id, request.certificate)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/datasets/{dataset_id}/whatif")
async def whatif_dataset(session_id: str, dataset_id: str, request: DatasetWhatIfRequest) -> dict[str, Any]:
    """Deterministic, receipt-backed what-if scenario on a numeric column."""
    try:
        return await session_service.whatif_dataset(session_id, dataset_id, request.column, request.pct_change)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/messages")
async def create_message(session_id: str, request: ChatMessageCreate) -> dict[str, Any]:
    try:
        return await session_service.chat_message(session_id, request.content, dataset_id=request.dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/progress/stream")
async def stream_progress(session_id: str) -> StreamingResponse:
    """Server-Sent Events stream of live pipeline-stage events for a session.

    Emits one `data: {json}` line per event. Sends a `_ping` event every ~60s
    when idle so proxies don't drop the connection, and closes on a `_done`
    sentinel.
    """

    async def event_source():
        async for event in progress_bus.stream(session_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/sessions/{session_id}/reports/{report_id}/renarrate")
async def renarrate_report(session_id: str, report_id: str) -> dict[str, Any]:
    """Re-run only the LLM narration pass on an existing report's facts."""
    try:
        return await session_service.renarrate_report(session_id, report_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/agent-runs")
async def list_agent_runs(session_id: str) -> list[dict[str, Any]]:
    session = await session_service.get_session(session_id)
    return session.get("agent_runs", [])


@router.get("/sessions/{session_id}/reports")
async def list_session_reports(session_id: str) -> list[dict[str, Any]]:
    return await session_service.list_reports(session_id)
