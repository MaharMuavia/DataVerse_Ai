import os
import requests
import json
import time
from pathlib import Path

BASE = 'http://localhost:8000/api'
REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATASET_PATH = REPO_ROOT / "data" / "sample_data.csv"

if "PYTEST_CURRENT_TEST" in os.environ:
    import pytest
    pytest.skip("Integration script; run standalone", allow_module_level=True)


def run_full_test() -> None:
    # Step 1: Upload CSV
    print("=== UPLOADING CSV ===")
    with SAMPLE_DATASET_PATH.open('rb') as f:
        resp = requests.post(BASE + '/upload', files={'file': f})
    print(f"Upload Status: {resp.status_code}")
    result = resp.json()
    print(json.dumps(result, indent=2))
    sid = result['session_id']

    print(f"\nSession ID: {sid}\n")

    # Step 2: Run queries
    for q in ['Analyze the loan approval patterns', 'Predict approval', 'Show distributions']:
        print(f"\n=== QUERY: {q} ===")
        time.sleep(0.5)  # Small delay to avoid rate limit
        resp = requests.post(BASE + '/query', json={'session_id': sid, 'query': q}, timeout=60)
        print(f"Status: {resp.status_code}")
        try:
            data = resp.json()
            print(f"Intent: {data.get('intent', {}).get('intent', 'N/A')}")
            print(f"Report: {data.get('report', '')[:200]}")
            if 'analytics' in data and data['analytics']:
                a = data['analytics']
                print("Analytics computed:")
                print(f"  - EDA: {a.get('eda', {}).get('status', 'N/A')}")
                print(f"  - Visualizations: {len(a.get('visualizations', []))} generated")
                print(f"  - AutoML: {a.get('automl', {}).get('status', 'N/A')}")
                print(f"  - XAI: {a.get('xai', {}).get('status', 'N/A')}")
            else:
                print("No analytics in response")
        except Exception as e:
            print(f"Error: {e}\nResponse: {resp.text[:300]}")


if __name__ == "__main__":
    run_full_test()

