from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.services.billing_service import (
    BillingConfigurationError,
    build_billing_overview,
    create_checkout_request,
)
from app.services.dashboard_service import assemble_dashboard_summary
from app.services.model_catalog import get_model_catalog, get_prompt_profiles, select_task_model


def test_model_catalog_includes_latest_supported_providers():
    catalog = get_model_catalog()

    provider_ids = {provider["id"] for provider in catalog["providers"]}
    assert {"openai", "anthropic", "mistral"} <= provider_ids
    assert catalog["defaults"]["chat"]["model"] == settings.OPENAI_CHAT_MODEL
    assert catalog["defaults"]["reasoning"]["provider"] in {"openai", "anthropic", "mistral"}


def test_prompt_profiles_cover_core_data_science_tasks():
    profiles = get_prompt_profiles()

    assert {"eda", "cleaning", "visualization", "ml_suggestions"} <= set(profiles)
    assert "columns" in profiles["eda"]["focus"]
    assert "chart" in " ".join(profiles["visualization"]["guardrails"]).lower()


def test_select_task_model_prefers_reasoning_models_for_ml_guidance():
    selection = select_task_model("ml_suggestions")

    assert selection["task"] == "ml_suggestions"
    assert selection["provider"] in {"openai", "anthropic", "mistral"}
    assert selection["reasoning"] in {"low", "medium", "high"}


def test_billing_overview_reports_stripe_readiness(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", None)
    monkeypatch.setattr(settings, "STRIPE_PRICE_PRO_MONTHLY", None)
    monkeypatch.setattr(settings, "STRIPE_PRICE_TEAM_MONTHLY", None)

    overview = build_billing_overview(
        user_id="user-1",
        email="owner@dataverse.dev",
        current_plan="free",
    )

    assert overview["current_plan"] == "free"
    assert overview["stripe_configured"] is False
    assert {plan["id"] for plan in overview["plans"]} == {"free", "pro", "team"}


def test_checkout_request_requires_stripe_configuration(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", None)
    monkeypatch.setattr(settings, "STRIPE_PRICE_PRO_MONTHLY", None)

    with pytest.raises(BillingConfigurationError):
        create_checkout_request(
            user_id="user-1",
            email="owner@dataverse.dev",
            plan_id="pro",
            success_url="https://app.dataverse.dev/billing?success=1",
            cancel_url="https://app.dataverse.dev/billing?canceled=1",
        )


def test_dashboard_summary_aggregates_workspace_health():
    now = datetime.now(timezone.utc)

    summary = assemble_dashboard_summary(
        user={"id": "user-1", "username": "owner", "email": "owner@dataverse.dev", "full_name": "Owner"},
        workspaces=[
            {
                "id": "ws-1",
                "name": "Northwind",
                "description": "Retail workspace",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ],
        datasets=[
            {
                "id": "ds-1",
                "workspace_id": "ws-1",
                "name": "sales.csv",
                "status": "ready",
                "row_count": 1200,
                "col_count": 18,
                "updated_at": now.isoformat(),
            }
        ],
        conversations=[
            {
                "id": "conv-2",
                "workspace_id": "ws-1",
                "title": "Forecast revenue",
                "updated_at": now.isoformat(),
            },
            {
                "id": "conv-1",
                "workspace_id": "ws-1",
                "title": "Clean missing values",
                "updated_at": (now - timedelta(hours=1)).isoformat(),
            },
        ],
        billing_overview={"current_plan": "pro", "stripe_configured": False, "plans": []},
        model_catalog={"defaults": {"chat": {"provider": "openai", "model": "gpt-5.2"}}},
    )

    assert summary["stats"] == {
        "workspace_count": 1,
        "dataset_count": 1,
        "conversation_count": 2,
        "ready_dataset_count": 1,
    }
    assert summary["workspaces"][0]["dataset_count"] == 1
    assert summary["workspaces"][0]["conversation_count"] == 2
    assert summary["recent_conversations"][0]["id"] == "conv-2"
    assert summary["billing"]["current_plan"] == "pro"
