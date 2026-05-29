"""Billing routes for Stripe-ready subscription workflows."""
from __future__ import annotations

from pydantic import BaseModel, HttpUrl
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.schemas import User
from ..core.auth import get_current_user
from ..core.config import settings
from ..db.base import get_session
from ..db.models import User as UserModel
from ..services.billing_service import (
    BillingConfigurationError,
    build_billing_overview,
    create_checkout_request,
)

router = APIRouter()


class CheckoutSessionRequest(BaseModel):
    plan_id: str
    success_url: str | None = None
    cancel_url: str | None = None


@router.get("/overview", response_model=dict)
async def get_billing_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    plan = "free"
    if db is not None and current_user.id:
        user_model = await db.get(UserModel, current_user.id)
        if user_model and user_model.plan:
            plan = user_model.plan

    return build_billing_overview(
        user_id=current_user.id or "",
        email=current_user.email,
        current_plan=plan,
    )


@router.post("/checkout-session", response_model=dict)
async def create_billing_checkout_session(
    payload: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),  # noqa: ARG001 - reserved for future subscription persistence
):
    success_url = payload.success_url or f"{settings.APP_BASE_URL}/billing?success=1"
    cancel_url = payload.cancel_url or f"{settings.APP_BASE_URL}/billing?canceled=1"

    try:
        checkout_request = create_checkout_request(
            user_id=current_user.id or "",
            email=current_user.email,
            plan_id=payload.plan_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    try:
        import stripe
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe SDK is not installed. Add `stripe` to the backend environment.",
        ) from exc

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(**checkout_request)
    return {"id": session.id, "url": session.url, "mode": checkout_request["mode"]}
