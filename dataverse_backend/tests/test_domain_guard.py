"""The retail-domain gate: non-retail uploads are refused with a clear message."""
from __future__ import annotations

import io

import pandas as pd
import pytest

from app.core.config import settings
from app.services.domain_guard import (
    RETAIL_DATASET_TYPES,
    UnsupportedDatasetDomainError,
    ensure_retail_domain,
)


def _csv(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def _retail_csv() -> bytes:
    return _csv(
        pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-01", periods=40, freq="D").strftime("%Y-%m-%d"),
                "Product": ["Rice", "Oil", "Sugar", "Tea"] * 10,
                "Category": ["Grocery"] * 40,
                "Quantity": [2, 1, 3, 4] * 10,
                "Unit_Price": [1450, 620, 170, 850] * 10,
                "Revenue": [2900, 620, 510, 3400] * 10,
            }
        )
    )


def _medical_csv() -> bytes:
    return _csv(
        pd.DataFrame(
            {
                "patient_id": range(1, 41),
                "age": [30 + (i % 40) for i in range(40)],
                "blood_pressure": [110 + (i % 30) for i in range(40)],
                "cholesterol": [180 + (i % 60) for i in range(40)],
                "diagnosis": ["healthy", "hypertension"] * 20,
            }
        )
    )


# ------------------------------------------------------------------ unit level
def test_guard_accepts_every_retail_type(monkeypatch):
    monkeypatch.setattr(settings, "RETAIL_ONLY_UPLOADS", True)
    for dtype in RETAIL_DATASET_TYPES:
        ensure_retail_domain({"dataset_type": dtype})  # must not raise


def test_guard_rejects_non_retail_types(monkeypatch):
    monkeypatch.setattr(settings, "RETAIL_ONLY_UPLOADS", True)
    for dtype in ("generic_tabular", "food_dataset", None):
        with pytest.raises(UnsupportedDatasetDomainError) as err:
            ensure_retail_domain({"dataset_type": dtype})
        assert "retail" in str(err.value).lower()


def test_guard_is_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "RETAIL_ONLY_UPLOADS", False)
    ensure_retail_domain({"dataset_type": "generic_tabular"})  # must not raise


# ------------------------------------------------------------------ API level
def test_upload_rejects_medical_dataset(client, monkeypatch):
    monkeypatch.setattr(settings, "RETAIL_ONLY_UPLOADS", True)
    sid = client.post("/api/sessions", json={"title": "guard"}).json()["session_id"]
    resp = client.post(
        f"/api/sessions/{sid}/datasets/upload?auto_analyze=false",
        files={"file": ("patients.csv", _medical_csv(), "text/csv")},
    )
    assert resp.status_code == 400
    assert "retail" in resp.json()["detail"].lower()


def test_upload_accepts_retail_dataset(client, monkeypatch):
    monkeypatch.setattr(settings, "RETAIL_ONLY_UPLOADS", True)
    sid = client.post("/api/sessions", json={"title": "guard-ok"}).json()["session_id"]
    resp = client.post(
        f"/api/sessions/{sid}/datasets/upload?auto_analyze=false",
        files={"file": ("mart_sales.csv", _retail_csv(), "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["row_count"] == 40


def test_sidebar_upload_route_also_rejects(client, monkeypatch):
    monkeypatch.setattr(settings, "RETAIL_ONLY_UPLOADS", True)
    resp = client.post(
        "/api/datasets/upload",
        files={"file": ("patients.csv", _medical_csv(), "text/csv")},
    )
    assert resp.status_code == 400
    assert "retail" in resp.json()["detail"].lower()
