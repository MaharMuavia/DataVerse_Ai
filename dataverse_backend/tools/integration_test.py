import io
import json
import sys
import os
from pathlib import Path

# Ensure project root is on PYTHONPATH so imports like `app` resolve when running scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if "PYTEST_CURRENT_TEST" in os.environ:
    import pytest
    pytest.skip("Integration script; run standalone", allow_module_level=True)

from fastapi.testclient import TestClient
from app.main import app


def run_integration_test() -> None:
    client = TestClient(app)

    # Upload CSV
    repo_root = Path(__file__).resolve().parent.parent.parent
    path = repo_root / "data" / "retail_mart_processed_v1.csv"
    if not path.exists():
        raise FileNotFoundError(f"Expected dataset at {path}")

    with path.open("rb") as f:
        files = {"file": ("retail_mart_processed_v1.csv", f, "text/csv")}
        r = client.post("/api/upload", files=files)
        print("Upload status_code:", r.status_code)
        print("Upload response:", r.json())
        if r.status_code != 200:
            raise SystemExit("Upload failed")

    session_id = r.json().get("session_id")
    if not session_id:
        raise RuntimeError("Session ID missing after upload")

    # Inspect raw dataset to auto-detect product and metric columns
    from app.data.data_manager import DataManager
    from app.llm.intent_parser import IntentParser
    import datetime

    dm = DataManager(session_id=session_id)
    df_raw = dm.get_raw()
    print('Detected columns:', df_raw.columns.tolist())

    # Heuristics to find product and metric columns
    product_candidates = [c for c in df_raw.columns if any(k in c.lower() for k in ['product','item','category','subcategory'])]
    metric_candidates = [c for c in df_raw.columns if any(k in c.lower() for k in ['units','quantity','qty','sales','revenue','amount','total_sales','profit'])]

    product_col = product_candidates[0] if product_candidates else (df_raw.columns[0] if df_raw.shape[1]>0 else None)
    metric_col = metric_candidates[0] if metric_candidates else None

    if metric_col is None:
        numeric_cols = df_raw.select_dtypes(include=['number']).columns.tolist()
        metric_col = numeric_cols[0] if numeric_cols else None

    print(f"Chosen product_col={product_col}, metric_col={metric_col}")

    # Determine last month period relative to today
    today = datetime.date.today()
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month - datetime.timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    # Monkeypatch IntentParser.parse to avoid calling external OpenAI during tests
    def fake_parse(query: str):
        return {
            "intent": "hot_selling_product",
            "time_filter": {"start": last_month_start.isoformat(), "end": last_month_end.isoformat()},
            "metric": metric_col,
            "operations": ["top_n"],
            "notes": "Auto-generated intent for testing"
        }

    IntentParser.parse = staticmethod(fake_parse)

    # Perform query (DeepAnalyze unavailable scenario)
    payload = {"session_id": session_id, "query": "Give me the hot selling product last month"}
    r2 = client.post("/api/query", json=payload)
    print("Query status_code:", r2.status_code)
    print(json.dumps(r2.json(), indent=2))

    # If the analysis required column confirmation, confirm it now
    resp = r2.json()
    if resp.get("action_required") == "confirm_product_column":
        candidates = resp.get("computed_facts", {}).get("candidates", [])
        chosen = candidates[0] if candidates else None
        print("Confirming product column:", chosen)
        confirm_payload = {"session_id": session_id, "column_name": chosen}
        r_confirm = client.post("/api/confirm_column", json=confirm_payload)
        print("Confirm response:", r_confirm.status_code, r_confirm.json())

    # Now simulate DeepAnalyze being available by monkeypatching the DeepAnalyze client
    from app.llm.deepanalyze_client import DeepAnalyzeClient

    example_report = {
        "executive_summary": "In the requested month, the top-selling category was identified with significant share of units sold.",
        "key_insights": [
            "Top category: ExampleCategory with 25.37% of units sold.",
            "Total units sold in period: 69546.",
            "Analysis based on quantity metric; date filtering applied for last month."
        ],
        "actions": [
            "Increase stock and prioritize replenishment for the top category.",
            "Run targeted promotions to boost secondary categories.",
        ],
        "assumptions": ["All timestamps were correctly parsed; computations are derived from cleaned dataset."]
    }

    orig_call = DeepAnalyzeClient.call_model

    def fake_call_model(self, prompt: str, max_tokens: int = 512):
        return {"ok": True, "text": json.dumps(example_report)}

    DeepAnalyzeClient.call_model = fake_call_model

    r3 = client.post("/api/query", json=payload)
    print('\nAfter monkeypatching DeepAnalyzeClient.call_model to return a valid report:')
    print("Query status_code:", r3.status_code)
    print(json.dumps(r3.json(), indent=2))

    DeepAnalyzeClient.call_model = orig_call

    from app.state.session_state import SessionState
    s = SessionState.get(session_id)
    print('\nSession execution_trace:', s.get_value('execution_trace'))
    print('EDA completed:', s.get_value('eda_completed'))
    print('Preprocessing completed:', s.get_value('preprocessing_completed'))
    print('Computed facts:', s.get_value('computed_facts'))
    print('Final report stored in response above (report field).')


if __name__ == "__main__":
    run_integration_test()

