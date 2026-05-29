from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ..core.config import settings


class BillingConfigurationError(RuntimeError):
    """Raised when billing actions are requested before Stripe is configured."""


@dataclass(frozen=True)
class BillingPlan:
    id: str
    name: str
    price_monthly: int
    description: str
    features: List[str]
    price_id: str | None = None


def _plan_catalog() -> List[BillingPlan]:
    return [
        BillingPlan(
            id="free",
            name="Free",
            price_monthly=0,
            description="Single-user exploration for early validation.",
            features=["1 workspace", "basic chat", "local dataset uploads", "community support"],
        ),
        BillingPlan(
            id="pro",
            name="Pro",
            price_monthly=49,
            description="Production workspace for a single analyst or founder.",
            features=["10 workspaces", "priority models", "history retention", "email support"],
            price_id=settings.STRIPE_PRICE_PRO_MONTHLY,
        ),
        BillingPlan(
            id="team",
            name="Team",
            price_monthly=199,
            description="Shared environment for cross-functional data teams.",
            features=["Unlimited workspaces", "shared billing", "team handoff", "priority support"],
            price_id=settings.STRIPE_PRICE_TEAM_MONTHLY,
        ),
    ]


def _serialize_plan(plan: BillingPlan, current_plan: str) -> Dict[str, Any]:
    return {
        "id": plan.id,
        "name": plan.name,
        "price_monthly": plan.price_monthly,
        "description": plan.description,
        "features": plan.features,
        "is_current": plan.id == current_plan,
        "is_checkout_enabled": bool(plan.price_id and settings.STRIPE_SECRET_KEY),
    }


def build_billing_overview(*, user_id: str, email: str, current_plan: str) -> Dict[str, Any]:
    plans = _plan_catalog()
    return {
        "user_id": user_id,
        "email": email,
        "current_plan": current_plan,
        "stripe_configured": bool(settings.STRIPE_SECRET_KEY),
        "customer_portal_configured": bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET),
        "plans": [_serialize_plan(plan, current_plan) for plan in plans],
    }


def create_checkout_request(
    *,
    user_id: str,
    email: str,
    plan_id: str,
    success_url: str,
    cancel_url: str,
) -> Dict[str, Any]:
    if not settings.STRIPE_SECRET_KEY:
        raise BillingConfigurationError("Stripe is not configured. Set STRIPE_SECRET_KEY first.")

    plan = next((candidate for candidate in _plan_catalog() if candidate.id == plan_id), None)
    if plan is None or plan.id == "free":
        raise BillingConfigurationError("Only paid plans can create a checkout session.")
    if not plan.price_id:
        raise BillingConfigurationError(f"Stripe price id missing for plan '{plan_id}'.")

    return {
        "mode": "subscription",
        "client_reference_id": user_id,
        "customer_email": email,
        "line_items": [{"price": plan.price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"plan_id": plan.id, "product": settings.APP_NAME},
    }
