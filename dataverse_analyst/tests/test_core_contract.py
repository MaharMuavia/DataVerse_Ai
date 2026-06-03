from __future__ import annotations

import io
import uuid
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient


def test_agent_package_only_exposes_analysis_and_xai_agents():
    import app.agents as agents

    agent_files = {
        path.name
        for path in Path(agents.__file__).parent.glob("*.py")
        if path.name != "__init__.py"
    }

    assert agent_files == {"analysis_agent.py", "xai_agent.py"}
    assert agents.AnalysisAgent.__name__ == "AnalysisAgent"
    assert agents.XAIAgent.__name__ == "XAIAgent"


def test_detect_target_prefers_hint_names_then_highest_variance_numeric():
    from app.agents import AnalysisAgent

    hinted = pd.DataFrame(
        {
            "feature": [1, 2, 3, 4],
            "Revenue": [10, 20, 30, 40],
            "wild_value": [0, 500, 1000, 1500],
        }
    )
    fallback = pd.DataFrame(
        {
            "age": [21, 22, 23, 24],
            "score_spread": [0, 100, 200, 300],
            "small_number": [1, 1, 2, 2],
        }
    )

    agent = AnalysisAgent()

    assert agent.detect_target(hinted) == "Revenue"
    assert agent.detect_target(fallback) == "score_spread"


def test_session_ids_are_uuid4_and_store_dataframe_in_memory():
    from app.models.session import SessionStore

    store = SessionStore()
    session_id = store.create(pd.DataFrame({"x": [1, 2]}), filename="generic.csv")

    assert uuid.UUID(session_id).version == 4
    session = store.get(session_id)
    assert session is not None
    assert session.filename == "generic.csv"
    assert session.df.to_dict(orient="list") == {"x": [1, 2]}


def test_xai_returns_structured_error_when_model_is_missing():
    from app.agents import XAIAgent

    result = XAIAgent().explain(None, pd.DataFrame({"x": [1, 2, 3]}), pd.DataFrame({"x": [2]}))

    assert result["status"] == "error"
    assert result["importances"] == {}
    assert "error" in result


def test_upload_accepts_non_retail_csv_and_cors_allows_file_dashboard_origin():
    from app.main import app

    client = TestClient(app)
    content = b"patient_id,blood_pressure,age\n1,120,55\n2,130,64\n3,118,48\n"
    response = client.post(
        "/upload",
        files={"file": ("healthcare.csv", io.BytesIO(content), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert uuid.UUID(payload["session_id"]).version == 4
    assert payload["filename"] == "healthcare.csv"
    assert payload["columns"] == ["patient_id", "blood_pressure", "age"]

    cors = client.options(
        "/upload",
        headers={
            "Origin": "null",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert cors.status_code == 200
    assert cors.headers["access-control-allow-origin"] == "*"


def test_report_style_csv_with_metadata_preamble_is_parsed_as_table():
    from app.core.csv_parser import read_csv_bytes

    content = "\n".join(
        [
            "Report,AI Khata Muavia Mobile",
            "Generated,2026-06-03",
            "Owner,Muavia",
            "Currency,PKR",
            "Status,Final",
            "Filters,All",
            "Note,Exported from mobile",
            "Summary,",
            "Opening Balance,1000",
            "Closing Balance,1250",
            "Rows,3",
            "----,----",
            "Date,Description,Debit,Credit,Balance",
            "2026-06-01,Opening,0,1000,1000",
            "2026-06-02,Tea,50,0,950",
            "2026-06-03,Payment,0,300,1250",
        ]
    ).encode()

    df = read_csv_bytes(content)

    assert df.columns.tolist() == ["Date", "Description", "Debit", "Credit", "Balance"]
    assert df.shape == (3, 5)
    assert df.iloc[1]["Description"] == "Tea"


def test_analyze_returns_full_report_for_generic_csv(monkeypatch):
    import app.routers.analysis as analysis_router
    from app.main import app

    monkeypatch.setattr(
        analysis_router.analysis_agent,
        "generate_narrative",
        lambda eda, shap_importances, predictions: "## Executive Summary\nGeneric report.",
    )
    client = TestClient(app)
    content = "\n".join(
        [
            "student_id,study_hours,attendance,final_score",
            "1,1,0.70,55",
            "2,2,0.72,60",
            "3,3,0.74,64",
            "4,4,0.80,68",
            "5,5,0.82,72",
            "6,6,0.85,78",
            "7,7,0.88,83",
            "8,8,0.90,88",
            "9,9,0.95,92",
            "10,10,0.98,96",
            "11,11,0.99,99",
            "12,12,1.00,100",
        ]
    ).encode()

    upload_response = client.post(
        "/upload",
        files={"file": ("students.csv", io.BytesIO(content), "text/csv")},
    )
    session_id = upload_response.json()["session_id"]
    response = client.post("/analyze", data={"session_id": session_id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["eda"]["status"] == "success"
    assert payload["model"]["status"] == "success"
    assert payload["model"]["target_column"] == "final_score"
    assert payload["xai"]["status"] in {"success", "error"}
    assert payload["narrative"].startswith("## Executive Summary")
