"""Dashboard routes for authenticated SaaS summaries."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.schemas import User
from ..core.auth import get_current_user
from ..db.base import get_session
from ..services.dashboard_service import build_dashboard_summary_for_user

router = APIRouter()


@router.get("/summary", response_model=dict)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured.",
        )

    return await build_dashboard_summary_for_user(db=db, current_user=current_user)
