#!/usr/bin/env python3
"""Test analytics backend with sample queries."""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

def test_upload():
    """Test CSV upload."""
    print("\n=== Testing CSV Upload ===")
    with open("c:/Users/mouav/OneDrive/Desktop/FINAL3/sample_data.csv", "rb") as f:
        files = {"file": f}
        response = requests.post(f"{BASE_URL}/upload", files=files)

    assert response.status_code == 200, f"Upload endpoint failed with {response.status_code}"
    result = response.json()
    assert isinstance(result, dict), "Upload response not valid JSON"
    assert result.get("session_id"), "No session_id returned"
    print(f"Upload succeeded: {json.dumps(result, indent=2)}")

    return result.get("session_id")


def test_query_end_to_end():
    session_id = test_upload()
    assert session_id is not None

    queries = [
        "Analyze the loan approval patterns in this dataset",
        "Predict whether a new customer will get approved",
        "Show me the distribution of credit scores",
    ]

    for query in queries:
        print(f"\n=== Testing Query: {query} ===")
        payload = {"session_id": session_id, "query": query}
        response = requests.post(f"{BASE_URL}/query", json=payload)

        assert response.status_code == 200, f"Query failed with {response.status_code}"
        result = response.json()
        assert isinstance(result, dict)
        print(f"Intent: {result.get('intent')}")
        print(f"Report: {result.get('report')}")
        if result.get('analytics'):
            analytics = result.get('analytics', {})
            print(f"  - EDA Status: {analytics.get('eda', {}).get('status', 'N/A')}")
            print(f"  - Visualizations: {len(analytics.get('visualizations', []))} generated")
            print(f"  - AutoML: {analytics.get('automl', {}).get('status', 'N/A')}")
            print(f"  - XAI: {analytics.get('xai', {}).get('status', 'N/A')}")

if __name__ == "__main__":
    print("Testing DataVerse Analytics Backend\n")
    
    # Step 1: Upload data
    session_id = test_upload()
    if not session_id:
        print("Upload failed, cannot continue")
        exit(1)
    
    print(f"\nSession ID: {session_id}")
    
    # Step 2: Test queries
    test_query(session_id, "Analyze the loan approval patterns in this dataset")
    test_query(session_id, "Predict whether a new customer will get approved")
    test_query(session_id, "Show me the distribution of credit scores")
