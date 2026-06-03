"""Narrate computed analysis facts without exposing raw datasets to LLMs."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from .llm_provider import LLMProvider


class ReportNarrator:
    """Create executive summaries from computed facts with graceful LLM fallback."""

    def __init__(self, llm_provider: Any | None = None):
        self.llm_provider = llm_provider if llm_provider is not None else LLMProvider()

    def narrate(self, computed_facts: dict[str, Any]) -> dict[str, Any]:
        """Synchronous convenience wrapper used by scripts and tests."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.narrate_async(computed_facts))
        return self._fallback(computed_facts)

    async def narrate_async(self, computed_facts: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(computed_facts)
        try:
            text = await asyncio.wait_for(self.llm_provider.generate(prompt), timeout=0.75)
            if text:
                fallback = self._fallback(computed_facts)
                fallback["executive_summary"] = text.strip()
                fallback["narration_provider"] = getattr(self.llm_provider, "last_provider", "llm")
                return fallback
        except Exception:
            pass
        return self._fallback(computed_facts)

    def _build_prompt(self, facts: dict[str, Any]) -> str:
        safe_facts = {
            "dataset_profile": facts.get("dataset_profile"),
            "eda": facts.get("eda"),
            "trends": facts.get("trends"),
            "correlations": facts.get("correlations"),
            "outliers": facts.get("outliers"),
            "target_suggestions": facts.get("target_suggestions"),
            "automl": facts.get("automl"),
            "xai": facts.get("xai"),
            "warnings": facts.get("warnings"),
        }
        return (
            "Write a concise AI data analyst report from these computed facts only. "
            "Do not invent values and do not ask for the raw dataset.\n"
            f"{json.dumps(safe_facts, default=str)[:12000]}"
        )

    def _fallback(self, facts: dict[str, Any]) -> dict[str, Any]:
        profile = facts.get("dataset_profile") or {}
        eda = facts.get("eda") or {}
        missing = (eda.get("missing_values") or {}).get("total_missing", 0)
        duplicate_rows = (eda.get("duplicates") or {}).get("duplicate_rows", 0)
        suggestions = facts.get("target_suggestions") or []
        automl = facts.get("automl") or {}
        xai = facts.get("xai") or {}

        rows = profile.get("row_count", 0)
        cols = profile.get("column_count", 0)
        report_summary = profile.get("report_summary") or {}
        report_metadata = profile.get("report_metadata") or {}
        summary_parts = [
            f"Dataset contains {rows} rows and {cols} columns.",
            f"Data quality scan found {missing} missing values and {duplicate_rows} duplicate rows.",
        ]
        if report_metadata.get("Shop Name"):
            summary_parts.append(f"Shop: {report_metadata['Shop Name']}.")
        for key in ("Total Sales", "Total Expenses", "Udhaar Outstanding", "Net Profit", "Profit Status"):
            if key in report_summary:
                summary_parts.append(f"{key}: {report_summary[key]}.")
        if suggestions:
            top = suggestions[0]
            summary_parts.append(
                f"The strongest prediction candidate is {top['column']} for {top['task_type']}."
            )
        if automl.get("status") == "success":
            summary_parts.append(
                f"A {automl.get('task_type')} model was trained for {automl.get('target_column')}."
            )
        if xai.get("status") in {"success", "fallback"}:
            features = xai.get("top_features") or list((xai.get("feature_importance") or {}).keys())[:3]
            if features:
                summary_parts.append(f"Most influential features include {', '.join(map(str, features[:3]))}.")

        recommendations = [
            "Review columns with missing values before operational use.",
            "Validate suggested prediction targets with a domain owner.",
            "Use the chart specs to render trend, distribution, and category views in the frontend.",
        ]
        if automl.get("status") == "success":
            recommendations.append("Compare model metrics against a business baseline before deployment.")
        elif suggestions:
            recommendations.append("Select a suggested target to run prediction and explainability.")

        warnings = list(facts.get("warnings") or [])
        if missing:
            warnings.append("Missing data may bias statistics or model training.")
        if duplicate_rows:
            warnings.append("Duplicate rows can inflate aggregate statistics.")

        return {
            "executive_summary": " ".join(summary_parts),
            "key_insights": summary_parts,
            "trend_explanation": self._trend_text(facts.get("trends") or {}),
            "prediction_explanation": self._prediction_text(automl),
            "xai_explanation": self._xai_text(xai),
            "warnings": warnings,
            "recommendations": recommendations,
            "narration_provider": "deterministic",
        }

    def _trend_text(self, trends: dict[str, Any]) -> str:
        if not trends.get("date_columns"):
            return "No date or time column was detected, so trend analysis was skipped."
        return f"Trend analysis used date column(s): {', '.join(trends['date_columns'])}."

    def _prediction_text(self, automl: dict[str, Any]) -> str:
        if not automl:
            return "Prediction was not run because no valid target was selected or inferred."
        if automl.get("status") != "success":
            return automl.get("message") or automl.get("error") or "Prediction did not complete."
        return f"AutoML selected {automl.get('best_model')} for {automl.get('target_column')}."

    def _xai_text(self, xai: dict[str, Any]) -> str:
        if not xai:
            return "Explainability was skipped because no trained model was available."
        if xai.get("status") == "success":
            return "SHAP explanations were computed for the trained model."
        if xai.get("status") == "fallback":
            return "SHAP was unavailable, so feature importance was used as the explanation fallback."
        return xai.get("message") or "Explainability did not complete."
