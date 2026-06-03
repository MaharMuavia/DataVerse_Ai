"""Smoke test the automatic analysis pipeline without external LLM keys."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "dataverse_backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.analysis_pipeline import AnalysisPipeline  # noqa: E402
from app.services.report_narrator import ReportNarrator  # noqa: E402


class NoLLMProvider:
    async def generate(self, prompt: str):  # noqa: ARG002
        return None


def main() -> None:
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=40, freq="D"),
            "region": ["North", "South", "East", "West"] * 10,
            "category": ["Electronics", "Home"] * 20,
            "price": [20 + (idx % 7) for idx in range(40)],
            "quantity": [1 + (idx % 5) for idx in range(40)],
            "revenue": [100 + idx * 9 for idx in range(40)],
            "churned": ["yes" if idx % 6 == 0 else "no" for idx in range(40)],
        }
    )
    pipeline = AnalysisPipeline(narrator=ReportNarrator(llm_provider=NoLLMProvider()))
    report = pipeline.run_full_analysis(df, query="predict sales revenue", target_column="revenue")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
