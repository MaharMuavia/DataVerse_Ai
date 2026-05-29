from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import ai_routes, billing_routes, dashboard_routes
from app.api.schemas import User
from app.core.auth import get_current_user
from app.db.base import get_session
from app.main import app


def _override_current_user() -> User:
    return User(
        id="user-1",
        username="owner",
        email="owner@dataverse.dev",
        full_name="Owner",
    )


async def _override_session():
    yield object()


def test_dashboard_summary_endpoint_returns_aggregated_payload(monkeypatch):
    async def _fake_dashboard_summary(**_):
        return {
            "stats": {"workspace_count": 1, "dataset_count": 2, "conversation_count": 3, "ready_dataset_count": 2},
            "workspaces": [],
            "recent_conversations": [],
            "billing": {"current_plan": "pro"},
            "ai_catalog": {"defaults": {"chat": {"model": "gpt-5.2"}}},
            "user": {"id": "user-1"},
        }

    monkeypatch.setattr(
        dashboard_routes,
        "build_dashboard_summary_for_user",
        _fake_dashboard_summary,
    )

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_session] = _override_session
    try:
        with TestClient(app) as client:
            response = client.get("/api/dashboard/summary")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["stats"]["workspace_count"] == 1
    assert response.json()["billing"]["current_plan"] == "pro"


def test_billing_overview_endpoint_exposes_plan_catalog(monkeypatch):
    monkeypatch.setattr(
        billing_routes,
        "build_billing_overview",
        lambda **_: {
            "current_plan": "free",
            "stripe_configured": False,
            "plans": [{"id": "free"}, {"id": "pro"}],
        },
    )

    app.dependency_overrides[get_current_user] = _override_current_user
    try:
        with TestClient(app) as client:
            response = client.get("/api/billing/overview")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["stripe_configured"] is False
    assert response.json()["plans"][1]["id"] == "pro"


def test_ai_catalog_endpoint_returns_prompt_profiles():
    app.dependency_overrides[get_current_user] = _override_current_user
    try:
        with TestClient(app) as client:
            response = client.get("/api/ai/catalog")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["catalog"]["defaults"]["chat"]["model"]
    assert "eda" in payload["prompt_profiles"]
