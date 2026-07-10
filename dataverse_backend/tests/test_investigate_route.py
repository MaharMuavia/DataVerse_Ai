"""End-to-end: /investigate route and root-cause answers in chat."""
from __future__ import annotations

import io

import pandas as pd
import pytest


@pytest.fixture
def two_month_sales_csv() -> bytes:
    rows = []
    april = [("Widget", 1000.0), ("Gadget", 500.0), ("Gizmo", 500.0)]
    may = [("Widget", 200.0), ("Gadget", 550.0), ("Gizmo", 450.0)]
    for product, amount in april:
        rows.append({"order_date": "2024-04-15", "product": product, "sales_amount": amount, "quantity": 10})
    for product, amount in may:
        rows.append({"order_date": "2024-05-15", "product": product, "sales_amount": amount, "quantity": 8})
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


@pytest.fixture
def session_with_dataset(client, two_month_sales_csv):
    session = client.post("/api/sessions", json={"title": "Investigate"}).json()
    upload = client.post(
        f"/api/sessions/{session['id']}/datasets/upload?auto_analyze=false",
        files={"file": ("sales.csv", two_month_sales_csv, "text/csv")},
    )
    assert upload.status_code == 200
    return session["id"], upload.json()["dataset_id"]


def test_investigate_route_finds_planted_driver(client, session_with_dataset):
    session_id, dataset_id = session_with_dataset
    resp = client.post(
        f"/api/sessions/{session_id}/datasets/{dataset_id}/investigate",
        json={"question": "Why did revenue drop in May?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "complete"
    assert body["drivers"][0]["value"] == "Widget"
    assert body["steps"]
    assert any(step.get("receipt") for step in body["steps"])


def test_investigate_route_unknown_dataset_404(client, session_with_dataset):
    session_id, _ = session_with_dataset
    resp = client.post(
        f"/api/sessions/{session_id}/datasets/nonexistent/investigate",
        json={"question": "why did revenue drop?"},
    )
    assert resp.status_code == 404


def test_chat_why_question_returns_root_cause(client, session_with_dataset):
    session_id, dataset_id = session_with_dataset
    resp = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "Why did revenue drop in May?", "dataset_id": dataset_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    root_cause = body.get("root_cause")
    assert root_cause and root_cause["status"] == "complete"
    assert root_cause["drivers"][0]["value"] == "Widget"
    # Offline (no LLM in tests): the answer itself must lead with the finding.
    assert "Widget" in body["answer"]


def test_chat_normal_question_has_no_root_cause(client, session_with_dataset):
    session_id, dataset_id = session_with_dataset
    resp = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "top products", "dataset_id": dataset_id},
    )
    assert resp.status_code == 200
    assert resp.json().get("root_cause") is None
