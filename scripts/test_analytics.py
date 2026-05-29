#!/usr/bin/env python3
"""Test analytics backend with sample queries."""

from __future__ import annotations

import json
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000/api"
REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATASET_PATH = REPO_ROOT / "data" / "sample_data.csv"


def test_upload() -> str:
    """Upload a sample CSV and return the created session_id."""
    print("\n=== Testing CSV Upload ===")

    if not SAMPLE_DATASET_PATH.exists():
        raise FileNotFoundError(f"Sample dataset not found at: {SAMPLE_DATASET_PATH}")

    with SAMPLE_DATASET_PATH.open("rb") as f:
        files = {"file": (SAMPLE_DATASET_PATH.name, f, "text/csv")}
        response = requests.post(f"{BASE_URL}/upload", files=files, timeout=30)

    response.raise_for_status()
    result = response.json()
    session_id = result.get("session_id")
    if not session_id:
        raise RuntimeError(f"No session_id returned: {json.dumps(result, indent=2)}")

    print(f"Upload succeeded: {json.dumps(result, indent=2)}")
    return session_id


def test_query(session_id: str, query: str) -> None:
    """Run a single query and print key parts of the response."""
    print(f"\n=== Testing Query: {query} ===")
    payload = {"session_id": session_id, "query": query}
    response = requests.post(f"{BASE_URL}/query", json=payload, timeout=90)

    response.raise_for_status()
    result = response.json()

    print(f"Intent: {result.get('intent')}")
    report = result.get("report")
    if isinstance(report, str) and len(report) > 400:
        report = report[:400] + "..."
    print(f"Report: {report}")

    analytics = result.get("analytics") or {}
    if analytics:
        print(f"  - EDA Status: {analytics.get('eda', {}).get('status', 'N/A')}")
        print(f"  - Visualizations: {len(analytics.get('visualizations', []))} generated")
        print(f"  - AutoML: {analytics.get('automl', {}).get('status', 'N/A')}")
        print(f"  - XAI: {analytics.get('xai', {}).get('status', 'N/A')}")


def main() -> None:
    print("Testing DataVerse Analytics Backend\n")

    session_id = test_upload()
    print(f"\nSession ID: {session_id}")

    queries = [
        "Analyze the loan approval patterns in this dataset",
        "Predict whether a new customer will get approved",
        "Show me the distribution of credit scores",
    ]

    for query in queries:
        test_query(session_id, query)


if __name__ == "__main__":
    main()
