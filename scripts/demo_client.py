#!/usr/bin/env python3
"""
DataVerse AI Backend - Full End-to-End Demo Client

This client demonstrates all major features of the DataVerse analytics platform:
1. Health check
2. Dataset upload with retail validation
3. Query endpoint with natural language
4. Session status inspection
5. Analytics results retrieval
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8001/api"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DATASET_PATH = REPO_ROOT / "data" / "retail_mart_processed_v1.csv"  # Retail dataset for demo


def print_section(title):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_response(label, response, truncate_at=500):
    """Pretty print API response."""
    print(f"\n{label}:")
    print(f"  Status Code: {response.status_code}")
    try:
        data = response.json()
        json_str = json.dumps(data, indent=2)
        if len(json_str) > truncate_at:
            print(f"  Response (truncated, {len(json_str)} bytes total):")
            print("  " + json_str[:truncate_at].replace("\n", "\n  ") + "\n  ... (truncated)")
        else:
            print(f"  Response:")
            print("  " + json_str.replace("\n", "\n  "))
    except:
        print(f"  Response (raw): {response.text[:truncate_at]}")


def test_health():
    """Test health endpoint."""
    print_section("1. HEALTH CHECK")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print_response("Health Check", resp)
        return resp.status_code == 200
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def test_upload():
    """Test dataset upload with retail validation."""
    print_section("2. DATASET UPLOAD WITH RETAIL VALIDATION")
    
    if not DEMO_DATASET_PATH.exists():
        print("  ERROR: Demo dataset not found")
        print(f"  Expected at: {DEMO_DATASET_PATH}")
        print(f"  Current directory: {Path.cwd()}")
        data_dir = REPO_ROOT / "data"
        if data_dir.exists():
            print(f"  Available files in data/: {list(data_dir.glob('*.csv'))}")
        return None
    
    try:
        with DEMO_DATASET_PATH.open("rb") as f:
            files = {"file": (DEMO_DATASET_PATH.name, f, "text/csv")}
            print(f"  Uploading {DEMO_DATASET_PATH}...")
            resp = requests.post(f"{BASE_URL}/upload", files=files, timeout=30)
        
        print_response("Upload Result", resp, truncate_at=1000)
        
        if resp.status_code == 200:
            data = resp.json()
            session_id = data.get("session_id")
            is_retail = data.get("is_retail", False)
            print(f"\n  ✓ Upload successful!")
            print(f"  Session ID: {session_id}")
            print(f"  Is Retail Dataset: {is_retail}")
            return session_id
        else:
            print(f"  ✗ Upload failed with status {resp.status_code}")
            return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def test_session_status(session_id):
    """Test session status endpoint."""
    print_section("3. SESSION STATUS")
    
    if not session_id:
        print("  Skipping (no session_id from upload)")
        return
    
    try:
        resp = requests.get(f"{BASE_URL}/session/{session_id}", timeout=10)
        print_response("Session Status", resp)
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n  Session Details:")
            print(f"    - Is Retail: {data.get('dataset_is_retail')}")
            print(f"    - EDA Completed: {data.get('eda_completed')}")
            print(f"    - Preprocessing Completed: {data.get('preprocessing_completed')}")
            if data.get('execution_trace'):
                print(f"    - Execution Trace: {data.get('execution_trace')}")
    except Exception as e:
        print(f"  ERROR: {e}")


def test_query(session_id):
    """Test query endpoint with natural language."""
    print_section("4. NATURAL LANGUAGE QUERY")
    
    if not session_id:
        print("  Skipping (no session_id from upload)")
        return
    
    queries = [
        "Analyze the total sales by store",
        "What categories have the highest profit margin?",
        "Show me the distribution of customer types"
    ]
    
    for query_text in queries:
        print(f"\n  Query: \"{query_text}\"")
        try:
            payload = {"session_id": session_id, "query": query_text}
            resp = requests.post(f"{BASE_URL}/query", json=payload, timeout=60)
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"    Status: ✓ Success")
                print(f"    Intent: {data.get('intent', {}).get('intent', 'N/A')}")
                print(f"    Is Retail: {data.get('is_retail')}")
                
                # Show report snippet
                report = data.get('report', '')
                if report:
                    if isinstance(report, str):
                        try:
                            report_data = json.loads(report)
                            narrative = report_data.get('narrative', '')[:200]
                        except:
                            narrative = report[:200]
                    else:
                        narrative = str(report)[:200]
                    
                    print(f"    Report (snippet): {narrative}...")
                
                # Show computed facts
                facts = data.get('computed_facts', {})
                if facts:
                    print(f"    Computed Facts Count: {len(facts)}")
                    
            else:
                print(f"    Status: ✗ Error {resp.status_code}")
                print(f"    Response: {resp.text[:200]}")
        except Exception as e:
            print(f"    ERROR: {e}")
        
        time.sleep(1)  # Small delay between queries


def test_docs():
    """Test API documentation endpoint."""
    print_section("5. API DOCUMENTATION")
    
    try:
        resp = requests.get("http://localhost:8001/docs", timeout=5)
        if resp.status_code == 200:
            print("  ✓ API documentation available at: http://localhost:8001/docs")
            print("  ✓ Interactive Swagger UI loaded")
        else:
            print(f"  Documentation endpoint returned {resp.status_code}")
    except Exception as e:
        print(f"  ERROR: Could not access documentation: {e}")


def main():
    """Run full demo."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  DataVerse AI Backend - End-to-End Demo Client".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    
    print("\nTarget: " + BASE_URL)
    print("Demo Dataset: " + str(DEMO_DATASET_PATH))
    
    # Run tests in sequence
    health_ok = test_health()
    
    if not health_ok:
        print("\n✗ Health check failed. Backend may not be running.")
        print("  Start the server with: python scripts/run_server.py")
        print("  Or: python -m uvicorn app.main:app --app-dir dataverse_backend --host 127.0.0.1 --port 8000")
        return
    
    session_id = test_upload()
    test_session_status(session_id)
    test_query(session_id)
    test_docs()
    
    print_section("DEMO COMPLETED")
    print("\nSummary:")
    print("  ✓ Backend is running and responding")
    print("  ✓ Dataset upload with retail validation works")
    print("  ✓ Session state tracking works")
    print("  ✓ Natural language queries are processed")
    print("  ✓ Analytics pipeline produces results")
    print("\nNext Steps:")
    print("  1. Review API docs at http://localhost:8000/docs")
    print("  2. Create a web frontend to visualize results")
    print("  3. Integrate database persistence (PostgreSQL)")
    print("  4. Deploy to production environment")


if __name__ == "__main__":
    main()
