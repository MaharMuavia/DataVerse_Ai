"""Test fixtures and shared configuration for DataVerse AI tests."""
from __future__ import annotations

import io
import os
import tempfile
import uuid
import urllib.parse
from typing import Any

import pandas as pd
import pytest
import httpx
from fastapi.testclient import TestClient

# Set test env before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_dataverse.db"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="dataverse_test_")
os.environ["ENVIRONMENT"] = "test"
os.environ["USE_LLM_NARRATION"] = "false"
os.environ["LLM_PROVIDER"] = "deterministic"
os.environ["INTENT_LLM_PROVIDER"] = "deterministic"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["RATE_LIMIT_PER_MINUTE"] = "100000"
# Legacy tests exercise non-retail datasets; the retail-domain gate is enabled
# explicitly in tests/test_domain_guard.py.
os.environ["RETAIL_ONLY_UPLOADS"] = "false"

# Mock Supabase credentials for tests (override any developer .env values,
# including SUPABASE_JWT_SECRET — a real secret would make auth_service try
# to verify the mock tokens locally instead of via the mocked Auth API)
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "mock_anon"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "mock_service"
os.environ["SUPABASE_JWT_SECRET"] = ""

from app.main import app  # noqa: E402


class MockResponse:
    """Mock HTTPResponse for httpx requests."""
    def __init__(self, status_code: int, json_data: dict[str, Any]):
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> dict[str, Any] | Any:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                message=f"Status {self.status_code} Error",
                request=httpx.Request("POST", "https://mock.supabase.co"),
                response=httpx.Response(self.status_code, json=self._json_data)
            )


@pytest.fixture(autouse=True)
def mock_supabase_and_auth(monkeypatch):
    """Autouse fixture to mock Supabase client database operations and Auth HTTP endpoints."""
    mock_db: dict[str, list[dict[str, Any]]] = {}
    mock_users: list[dict[str, Any]] = []
    mock_storage: dict[str, bytes] = {}
    app.state.mock_auth_users = mock_users

    from app.services.supabase_client import supabase_client

    def _get_table(table: str) -> list[dict[str, Any]]:
        if table not in mock_db:
            mock_db[table] = []
        return mock_db[table]

    async def mock_insert(table: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = _get_table(table)
        if "id" not in payload:
            payload["id"] = str(uuid.uuid4())
        rows.append(payload)
        return payload

    async def mock_select(table: str, query: str = "select=*") -> list[dict[str, Any]]:
        rows = _get_table(table)
        parsed = urllib.parse.unquote(query)
        if "id=eq." in parsed:
            parts = parsed.split("&")
            eq_id = None
            for p in parts:
                if p.startswith("id=eq."):
                    eq_id = p.split("id=eq.")[1]
                    break
            if eq_id:
                return [r for r in rows if str(r.get("id")) == eq_id]
        if "user_id=eq." in parsed:
            parts = parsed.split("&")
            user_id = None
            for p in parts:
                if p.startswith("user_id=eq."):
                    user_id = p.split("user_id=eq.")[1]
                    break
            if user_id:
                return [r for r in rows if str(r.get("user_id")) == user_id]
        return rows

    async def mock_update(table: str, row_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        rows = _get_table(table)
        for r in rows:
            if str(r.get("id")) == str(row_id):
                r.update(payload)
                return r
        return None

    async def mock_delete(table: str, row_id: str) -> None:
        rows = _get_table(table)
        mock_db[table] = [r for r in rows if str(r.get("id")) != str(row_id)]

    async def mock_upload_bytes(bucket: str, storage_path: str, content: bytes, content_type: str | None = None) -> str:
        mock_storage[storage_path] = content
        return storage_path

    async def mock_signed_url(bucket: str, storage_path: str, expires_in: int = 3600) -> str:
        return f"https://mock.supabase.co/storage/v1/object/sign/{bucket}/{storage_path}"

    # Apply mocks to global supabase_client instance
    monkeypatch.setattr(supabase_client, "insert", mock_insert)
    monkeypatch.setattr(supabase_client, "select", mock_select)
    monkeypatch.setattr(supabase_client, "update", mock_update)
    monkeypatch.setattr(supabase_client, "delete", mock_delete)
    monkeypatch.setattr(supabase_client, "upload_bytes", mock_upload_bytes)
    monkeypatch.setattr(supabase_client, "signed_url", mock_signed_url)
    monkeypatch.setattr(supabase_client, "mock_storage", mock_storage, raising=False)

    # Intercept HTTP requests in httpx
    orig_request = httpx.AsyncClient.request

    async def mock_request(self_client, method, url, **kwargs):
        url_str = str(url)
        if "https://mock.supabase.co/auth/v1" in url_str:
            if "/admin/users" in url_str:
                body = kwargs.get("json") or {}
                email = body.get("email")
                password = body.get("password")
                metadata = body.get("user_metadata") or {}
                # Check duplicate
                for u in mock_users:
                    if u["email"] == email:
                        return MockResponse(400, {"msg": "A user with this email already exists"})
                user_id = str(uuid.uuid4())
                mock_users.append({
                    "id": user_id,
                    "email": email,
                    "password": password,
                    "metadata": metadata
                })
                user_row = {
                    "id": user_id,
                    "email": email,
                    "name": metadata.get("name"),
                    "guest": bool(metadata.get("guest")),
                }
                if "users" not in mock_db:
                    mock_db["users"] = []
                mock_db["users"].append(user_row)

                return MockResponse(200, {
                    "id": user_id,
                    "email": email,
                    "user_metadata": metadata
                })
            elif "/signup" in url_str:
                body = kwargs.get("json") or {}
                email = body.get("email")
                password = body.get("password")
                metadata = body.get("data") or {}
                if any(u["email"] == email for u in mock_users):
                    return MockResponse(400, {"msg": "A user with this email already exists"})
                user_id = str(uuid.uuid4())
                mock_users.append({
                    "id": user_id,
                    "email": email,
                    "password": password,
                    "metadata": metadata,
                    "confirmed": False,
                })
                return MockResponse(200, {
                    "id": user_id,
                    "email": email,
                    "user_metadata": metadata,
                    "identities": [{"id": user_id}],
                })
            elif "/resend" in url_str:
                return MockResponse(200, {})
            elif "/token" in url_str:
                body = kwargs.get("json") or {}
                email = body.get("email")
                password = body.get("password")
                for u in mock_users:
                    if u["email"] == email and u["password"] == password and u.get("confirmed"):
                        return MockResponse(200, {
                            "access_token": f"mock-token-{u['id']}",
                            "token_type": "bearer",
                            "expires_in": 3600,
                            "refresh_token": "mock-refresh",
                            "user": {
                                "id": u["id"],
                                "email": u["email"],
                                "user_metadata": u["metadata"]
                            }
                        })
                return MockResponse(400, {"msg": "Invalid login credentials"})
            elif "/user" in url_str:
                auth_hdr = kwargs.get("headers", {}).get("Authorization") or self_client.headers.get("Authorization") or ""
                if auth_hdr.startswith("Bearer "):
                    token = auth_hdr[7:].strip()
                    if token.startswith("mock-token-"):
                        user_id = token[11:]
                        for u in mock_users:
                            if u["id"] == user_id:
                                return MockResponse(200, {
                                    "id": u["id"],
                                    "email": u["email"],
                                    "user_metadata": u["metadata"]
                                })
                return MockResponse(401, {"msg": "Invalid token"})

        return await orig_request(self_client, method, url, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "request", mock_request)


@pytest.fixture
def client():
    """Synchronous test client for FastAPI."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_csv_bytes() -> bytes:
    """Generate a simple sales CSV for testing."""
    df = pd.DataFrame({
        "Product": ["Widget A", "Widget B", "Gadget X", "Gadget Y", "Widget A",
                     "Widget B", "Gadget X", "Gadget Y", "Widget A", "Widget B",
                     "Gadget X", "Gadget Y", "Widget A", "Widget B", "Gadget X",
                     "Gadget Y", "Widget A", "Widget B", "Gadget X", "Gadget Y"],
        "Category": ["Widgets", "Widgets", "Gadgets", "Gadgets", "Widgets",
                      "Widgets", "Gadgets", "Gadgets", "Widgets", "Widgets",
                      "Gadgets", "Gadgets", "Widgets", "Widgets", "Gadgets",
                      "Gadgets", "Widgets", "Widgets", "Gadgets", "Gadgets"],
        "Revenue": [100, 200, 150, 80, 120, 210, 160, 90, 130, 220,
                    170, 85, 140, 230, 180, 95, 150, 240, 190, 100],
        "Quantity": [10, 20, 15, 8, 12, 21, 16, 9, 13, 22,
                     17, 8, 14, 23, 18, 9, 15, 24, 19, 10],
        "Date": pd.date_range("2024-01-01", periods=20, freq="W").strftime("%Y-%m-%d").tolist(),
        "Region": ["North", "South", "East", "West", "North",
                    "South", "East", "West", "North", "South",
                    "East", "West", "North", "South", "East",
                    "West", "North", "South", "East", "West"],
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


@pytest.fixture
def uploaded_dataset_id(client, sample_csv_bytes) -> str:
    """Upload a dataset and return its ID."""
    resp = client.post(
        "/api/datasets/upload",
        files={"file": ("test_data.csv", sample_csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    return resp.json()["dataset_id"]
