"""Security: JWT auth, per-user session isolation (IDOR), headers, rate limits,
path traversal, and XSS escaping in generated reports."""
from __future__ import annotations

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.session_service import session_service
from app.services.supabase_client import LocalPersistence


@pytest.fixture
def iso_client(tmp_path, monkeypatch):
    """Client with isolated local persistence so user/session rows don't leak."""
    monkeypatch.setattr(session_service.supabase, "url", "")
    monkeypatch.setattr(session_service.supabase, "service_role_key", None)
    monkeypatch.setattr(session_service, "local", LocalPersistence(tmp_path / "sec_store"))
    with TestClient(app) as c:
        yield c


def _csv_bytes() -> bytes:
    df = pd.DataFrame({
        "product": ["A", "B", "C", "D"],
        "revenue": [100, 200, 300, 400],
        "quantity": [1, 2, 3, 4],
    })
    return df.to_csv(index=False).encode()


def _signup(client, email="alice@example.com", password="S3curePass!x", name="Alice"):
    return client.post("/api/auth/signup", json={"email": email, "password": password, "name": name})


def _confirm_mock_user(client, email: str) -> None:
    user = next(user for user in client.app.state.mock_auth_users if user["email"] == email)
    user["confirmed"] = True


def _signup_and_confirm(client, email="alice@example.com", password="S3curePass!x", name="Alice"):
    signup = _signup(client, email, password, name)
    assert signup.status_code == 200, signup.text
    _confirm_mock_user(client, email)
    return client.post("/api/auth/login", json={"email": email, "password": password})


# ---------------------------------------------------------------- auth basics

def test_signup_login_me_roundtrip(iso_client):
    r = _signup(iso_client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"requires_verification": True, "email": "alice@example.com"}

    pending_login = iso_client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "S3curePass!x"}
    )
    assert pending_login.status_code == 401

    _confirm_mock_user(iso_client, "alice@example.com")

    login = iso_client.post("/api/auth/login", json={"email": "alice@example.com", "password": "S3curePass!x"})
    assert login.status_code == 200
    token = login.json()["token"]

    me = iso_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_me_falls_back_to_supabase_for_non_hs256_token(iso_client, monkeypatch):
    """A configured legacy secret must not reject newer Supabase token types."""
    token = _signup_and_confirm(iso_client).json()["token"]
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "legacy-secret")

    me = iso_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_wrong_password_and_bad_token_rejected(iso_client):
    _signup_and_confirm(iso_client)
    bad = iso_client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong"})
    assert bad.status_code == 401
    me = iso_client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert me.status_code == 401


def test_guest_auth_endpoint_is_removed(iso_client):
    assert iso_client.post("/api/auth/guest").status_code == 404


def test_duplicate_signup_rejected(iso_client):
    assert _signup(iso_client).status_code == 200
    assert _signup(iso_client).status_code == 400


@pytest.mark.parametrize("password", [
    "Short1!",
    "alllowercase1!",
    "ALLUPPERCASE1!",
    "NoSpecial1234",
    "NoNumberHere!",
    "aliceSecure1!",
])
def test_signup_rejects_weak_passwords_server_side(iso_client, password):
    response = _signup(iso_client, password=password)
    assert response.status_code == 400


# ---------------------------------------------------------------- isolation (IDOR)

def test_users_cannot_access_each_others_sessions(iso_client):
    token_a = _signup_and_confirm(iso_client, "a@x.com", "PasswordA1!x", "A").json()["token"]
    token_b = _signup_and_confirm(iso_client, "b@x.com", "PasswordB1!x", "B").json()["token"]
    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    sid = iso_client.post("/api/sessions", json={"title": "A's data"}, headers=auth_a).json()["session_id"]
    up = iso_client.post(
        f"/api/sessions/{sid}/datasets/upload?auto_analyze=false",
        files={"file": ("sales.csv", _csv_bytes(), "text/csv")}, headers=auth_a,
    )
    assert up.status_code == 200
    dataset_id = up.json()["dataset_id"]

    # owner can read
    assert iso_client.get(f"/api/sessions/{sid}", headers=auth_a).status_code == 200
    # other user cannot read, message, or clean
    assert iso_client.get(f"/api/sessions/{sid}", headers=auth_b).status_code == 403
    assert iso_client.post(
        f"/api/sessions/{sid}/messages", json={"content": "total sales", "dataset_id": dataset_id}, headers=auth_b,
    ).status_code == 403
    assert iso_client.post(
        f"/api/sessions/{sid}/datasets/{dataset_id}/clean", json={"fix_ids": ["duplicates"]}, headers=auth_b,
    ).status_code == 403
    # unauthenticated caller cannot read an owned session either
    assert iso_client.get(f"/api/sessions/{sid}").status_code == 403
    # sessions list stays private
    listed_b = iso_client.get("/api/sessions", headers=auth_b).json()
    assert all(s.get("id") != sid for s in listed_b)


def test_legacy_anonymous_sessions_remain_accessible(iso_client):
    sid = iso_client.post("/api/sessions", json={"title": "anon"}).json()["session_id"]
    assert iso_client.get(f"/api/sessions/{sid}").status_code == 200


# ---------------------------------------------------------------- headers & limits

def test_security_headers_present(iso_client):
    r = iso_client.get("/api/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "strict-origin" in (r.headers.get("Referrer-Policy") or "")


def test_rate_limit_kicks_in(iso_client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 3)
    from app.services import rate_limiter
    rate_limiter.reset()
    statuses = [
        iso_client.post("/api/auth/login", json={"email": "nobody@x.com", "password": "nope"}).status_code
        for _ in range(5)
    ]
    assert 429 in statuses, statuses


# ---------------------------------------------------------------- hardening

def test_path_traversal_filename_is_neutralized(iso_client, tmp_path):
    sid = iso_client.post("/api/sessions", json={"title": "trav"}).json()["session_id"]
    r = iso_client.post(
        f"/api/sessions/{sid}/datasets/upload?auto_analyze=false",
        files={"file": ("..\\..\\evil.csv", _csv_bytes(), "text/csv")},
    )
    assert r.status_code == 200
    stored = r.json()["dataset"]["filename"]
    assert ".." not in stored and "/" not in stored and "\\" not in stored


def test_report_html_escapes_malicious_cell_values(iso_client):
    sid = iso_client.post("/api/sessions", json={"title": "xss"}).json()["session_id"]
    df = pd.DataFrame({
        "product": ["<script>alert(1)</script>", "B", "C", "D"],
        "revenue": [400, 300, 200, 100],
        "quantity": [4, 3, 2, 1],
    })
    up = iso_client.post(
        f"/api/sessions/{sid}/datasets/upload?auto_analyze=true&generate_report=true",
        files={"file": ("xss.csv", df.to_csv(index=False).encode(), "text/csv")},
    ).json()
    rid = ((up.get("analysis") or {}).get("report") or {}).get("report_id")
    assert rid, "report should generate"
    html = iso_client.get(f"/api/reports/{rid}/download?format=html").text
    assert "<script>alert(1)</script>" not in html, "raw script tag leaked into report HTML"
