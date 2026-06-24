"""Reproducibility Certificate: tamper-evident, re-verifiable proof of the numbers.

A certificate is two SHA-256 fingerprints — one over the raw dataset, one over
the deterministic results (KPIs / EDA / correlations / trends). Because every
number is computed deterministically in pandas, re-running the analysis on the
same data reproduces the exact same fingerprints. That lets anyone independently
verify a DataVerse report and detect if the data or the numbers were altered —
something an LLM-generated analysis cannot offer.

Model metrics are intentionally excluded from the results fingerprint: model
training can carry nondeterminism, so the certificate covers only the
guaranteed-reproducible deterministic core.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

DETERMINISTIC_CATEGORIES = ("kpi", "eda", "correlation", "trend")


def dataset_fingerprint(df: pd.DataFrame | None) -> str:
    if df is None:
        return hashlib.sha256(b"").hexdigest()
    canonical = df.to_csv(index=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _deterministic_entries(audit_trail: list[dict[str, Any]] | None) -> list[list[Any]]:
    rows = [
        [entry.get("metric_key"), entry.get("value")]
        for entry in (audit_trail or [])
        if entry.get("category") in DETERMINISTIC_CATEGORIES
    ]
    rows.sort(key=lambda row: str(row[0]))
    return rows


def results_fingerprint(audit_trail: list[dict[str, Any]] | None) -> str:
    canonical = json.dumps(_deterministic_entries(audit_trail), sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_certificate(df: pd.DataFrame | None, audit_trail: list[dict[str, Any]] | None) -> dict[str, Any]:
    return {
        "algorithm": "sha256",
        "tool": "DataVerse",
        "data_fingerprint": dataset_fingerprint(df),
        "results_fingerprint": results_fingerprint(audit_trail),
        "row_count": int(len(df)) if df is not None else 0,
        "column_count": int(df.shape[1]) if df is not None else 0,
        "verified_numbers": len(_deterministic_entries(audit_trail)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def verify_certificate(
    df: pd.DataFrame | None,
    audit_trail: list[dict[str, Any]] | None,
    certificate: dict[str, Any] | None,
) -> dict[str, Any]:
    certificate = certificate or {}
    data_actual = dataset_fingerprint(df)
    results_actual = results_fingerprint(audit_trail)
    data_match = data_actual == certificate.get("data_fingerprint")
    results_match = results_actual == certificate.get("results_fingerprint")
    return {
        "verified": bool(data_match and results_match),
        "data_match": bool(data_match),
        "results_match": bool(results_match),
        "verified_numbers": len(_deterministic_entries(audit_trail)),
        "expected": {
            "data_fingerprint": certificate.get("data_fingerprint"),
            "results_fingerprint": certificate.get("results_fingerprint"),
        },
        "actual": {
            "data_fingerprint": data_actual,
            "results_fingerprint": results_actual,
        },
    }
