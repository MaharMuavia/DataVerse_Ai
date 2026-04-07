from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from jinja2 import Template

from .core.tool_registry import ChartSpec, NarrativeSpec, TableSpec
from ..llm.llm_client import LLMClient
from ..memory.conversation_memory import ConversationMemory
from ..reporting import ReportExporter


class ReportAgent:
    """Agent for generating and exporting comprehensive analysis reports."""

    def __init__(self, llm_client: LLMClient, export_dir: str = "./report_exports"):
        self.llm_client = llm_client
        self.exporter = ReportExporter(export_dir)

    async def generate_report(
        self,
        session_id: str,
        memory: ConversationMemory,
        output_format: str = "html",
    ) -> Dict[str, Any]:
        """Generate a comprehensive report and export it to the requested format."""
        session = memory.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        messages = memory.get_recent_messages(session_id, limit=100)
        analysis_results, charts, tables, narratives = self._collect_report_assets(messages)

        summary = await self._generate_executive_summary(analysis_results)
        recommendations = await self._generate_recommendations(analysis_results, tables, charts)

        report_data = {
            "session_id": session_id,
            "title": f"DataVerse Analysis Report - {session_id}",
            "executive_summary": summary,
            "dataset_overview": self._generate_dataset_overview(session, messages),
            "key_findings": analysis_results,
            "visualizations": charts,
            "tables": tables,
            "narratives": narratives,
            "recommendations": recommendations,
            "generated_at": str(pd.Timestamp.now()),
        }

        export_info = self.exporter.export(report_data, session_id, output_format)
        return {
            "report_data": report_data,
            "export": export_info,
        }

    def _collect_report_assets(self, messages: List[Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        """Extract report-ready findings, charts, tables, and narratives from stored tool results."""
        analysis_results: List[Dict[str, Any]] = []
        charts: List[Dict[str, Any]] = []
        tables: List[Dict[str, Any]] = []
        narratives: List[str] = []

        for msg in messages:
            if not msg.tool_results:
                continue

            for result in msg.tool_results:
                display_items = result.get("display")
                normalized_display = display_items if isinstance(display_items, list) else [display_items] if display_items else []

                extracted_narratives: List[str] = []
                for item in normalized_display:
                    normalized_item = self._normalize_display_item(item)
                    if isinstance(normalized_item, ChartSpec):
                        charts.append(
                            {
                                "title": normalized_item.title,
                                "type": normalized_item.type,
                                "x_label": normalized_item.x_label,
                                "y_label": normalized_item.y_label,
                            }
                        )
                    elif isinstance(normalized_item, TableSpec):
                        tables.append(
                            {
                                "title": normalized_item.title,
                                "columns": list(normalized_item.columns),
                                "data": list(normalized_item.data)[:10],
                            }
                        )
                    elif isinstance(normalized_item, NarrativeSpec):
                        extracted_narratives.append(normalized_item.content)
                        narratives.append(normalized_item.content)

                analysis_results.append(
                    {
                        "step": result.get("step"),
                        "tool": result.get("tool"),
                        "purpose": result.get("purpose"),
                        "summary": self._summarize_tool_result(result, extracted_narratives),
                        "success": result.get("success", False),
                        "result_preview": self._clip_result_preview(result.get("result", {})),
                    }
                )

        return analysis_results, charts, tables, narratives

    def _normalize_display_item(self, item: Any) -> Optional[Any]:
        """Normalize persisted display items back into their typed models when possible."""
        if item is None:
            return None
        if isinstance(item, (ChartSpec, TableSpec, NarrativeSpec)):
            return item
        if isinstance(item, dict):
            if "content" in item:
                return NarrativeSpec(**item)
            if "columns" in item and "data" in item:
                return TableSpec(**item)
            if "type" in item and "title" in item and "data" in item:
                return ChartSpec(**item)
        return None

    def _summarize_tool_result(self, result: Dict[str, Any], extracted_narratives: List[str]) -> str:
        """Create a concise, report-friendly summary of a tool execution."""
        if extracted_narratives:
            return extracted_narratives[0]

        tool_name = result.get("tool", "analysis_step")
        payload = result.get("result", {})
        if isinstance(payload, dict):
            if "error" in payload:
                return f"{tool_name} reported an error: {payload['error']}"
            preview_keys = list(payload.keys())[:5]
            if preview_keys:
                return f"{tool_name} produced structured outputs including: {', '.join(preview_keys)}."

        return f"{tool_name} completed with no narrative summary stored."

    def _clip_result_preview(self, payload: Any) -> Any:
        """Keep report previews compact enough for export."""
        if isinstance(payload, dict):
            preview: Dict[str, Any] = {}
            for key, value in list(payload.items())[:5]:
                if isinstance(value, list) and len(value) > 5:
                    preview[key] = value[:5]
                elif isinstance(value, dict) and len(value) > 5:
                    preview[key] = {k: v for k, v in list(value.items())[:5]}
                else:
                    preview[key] = value
            return preview
        return payload

    async def _generate_executive_summary(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Generate executive summary using LLM, with a safe fallback if unavailable."""
        template_path = Path(__file__).resolve().parents[1] / "prompts" / "executive_summary.j2"

        with template_path.open("r", encoding="utf-8") as handle:
            template_content = handle.read()

        prompt = Template(template_content).render(analysis_results=analysis_results[:20])

        try:
            summary = await self.llm_client.generate_text(prompt, max_tokens=512)
            if summary and summary.strip():
                return summary.strip()
        except Exception:
            pass

        if not analysis_results:
            return "The session does not yet contain completed analytical findings."

        highlights = [item.get("summary", "") for item in analysis_results[:3] if item.get("summary")]
        joined = " ".join(highlights).strip()
        return joined or "The analysis completed successfully and produced structured findings for review."

    async def _generate_recommendations(
        self,
        analysis_results: List[Dict[str, Any]],
        tables: List[Dict[str, Any]],
        charts: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate business recommendations from the report assets."""
        recommendations: List[str] = []

        missing_issues = [r for r in analysis_results if r.get("tool") == "missing_value_analysis"]
        if missing_issues:
            recommendations.append(
                "Address missing-value hotspots before deploying downstream decision support or ML workflows."
            )

        model_outputs = [
            r for r in analysis_results if r.get("tool") in {"train_classifier", "train_regressor"}
        ]
        if model_outputs:
            recommendations.append(
                "Validate the trained model against a business holdout sample before using predictions operationally."
            )

        if charts:
            recommendations.append(
                "Use the generated visual patterns to brief stakeholders on the main drivers and anomalies in the dataset."
            )

        if tables:
            recommendations.append(
                "Review the exported tables for segment-level actions and KPI monitoring candidates."
            )

        if not recommendations:
            recommendations.append(
                "Continue expanding the analysis with focused follow-up questions to translate findings into business decisions."
            )

        return recommendations

    def _generate_dataset_overview(self, session: Any, messages: List[Any]) -> Dict[str, Any]:
        """Generate dataset overview section."""
        schema_columns = session.dataset_schema.get("columns", {}) if session.dataset_schema else {}
        if isinstance(schema_columns, dict):
            column_names = list(schema_columns.keys())
        else:
            column_names = list(schema_columns)

        return {
            "columns": len(column_names),
            "rows": session.dataset_schema.get("rows", 0),
            "column_names": column_names,
            "active_filters": [
                item.model_dump() if hasattr(item, "model_dump") else item.dict()
                for item in getattr(session, "active_filters", [])
            ],
            "message_count": len(messages),
            "last_updated": str(pd.Timestamp.now()),
        }
