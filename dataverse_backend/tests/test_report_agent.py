import zipfile

import pytest

from app.agents.core.tool_registry import ChartSpec, NarrativeSpec, TableSpec
from app.agents.report_agent import ReportAgent
from app.memory.conversation_memory import ConversationMemory


def _build_memory_session() -> ConversationMemory:
    memory = ConversationMemory()
    memory.create_session(
        "report_session",
        {
            "columns": ["price", "quantity", "revenue"],
            "dtypes": {"price": "float64", "quantity": "int64", "revenue": "float64"},
            "rows": 100,
            "file_path": "sample.csv",
        },
    )
    memory.add_message(
        "report_session",
        "assistant",
        "Completed the revenue analysis.",
        tool_results=[
            {
                "step": 1,
                "tool": "group_aggregation",
                "purpose": "Summarize revenue by category.",
                "success": True,
                "result": {"group_count": 3, "top_category": "Electronics"},
                "display": [
                    TableSpec(
                        columns=["category", "revenue"],
                        data=[
                            {"category": "Electronics", "revenue": 120000},
                            {"category": "Clothing", "revenue": 85000},
                        ],
                        title="Revenue by Category",
                    ),
                    NarrativeSpec(
                        content="Electronics leads revenue generation by a comfortable margin.",
                        tone="professional",
                    ),
                    ChartSpec(
                        type="bar",
                        data={"data": [], "layout": {}},
                        title="Revenue Comparison",
                    ),
                ],
            }
        ],
    )
    return memory


@pytest.mark.asyncio
async def test_generate_html_report_exports_file(tmp_path, mock_llm_client):
    memory = _build_memory_session()
    agent = ReportAgent(mock_llm_client, export_dir=str(tmp_path))

    result = await agent.generate_report("report_session", memory, output_format="html")

    assert "report_data" in result
    assert "export" in result
    assert result["report_data"]["dataset_overview"]["rows"] == 100
    assert result["report_data"]["recommendations"]
    export_path = tmp_path / "report_session" / result["export"]["filename"]
    assert export_path.exists()
    assert export_path.suffix == ".html"
    assert "DataVerse Analysis Report" in export_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_generate_docx_report_exports_valid_package(tmp_path, mock_llm_client):
    memory = _build_memory_session()
    agent = ReportAgent(mock_llm_client, export_dir=str(tmp_path))

    result = await agent.generate_report("report_session", memory, output_format="docx")

    export_path = tmp_path / "report_session" / result["export"]["filename"]
    assert export_path.exists()
    assert export_path.suffix == ".docx"

    with zipfile.ZipFile(export_path, "r") as archive:
        names = set(archive.namelist())

    assert "[Content_Types].xml" in names
    assert "word/document.xml" in names
