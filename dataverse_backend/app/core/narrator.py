"""LLM-powered narration layer for converting analysis results into natural language explanations.

This module provides human-friendly explanations of complex data analysis results.
"""
from __future__ import annotations

import json
from typing import Dict, Any, Optional

from ..core.config import settings
from ..core.logger import logger


class Narrator:
    """Converts structured analysis results into natural language narratives."""

    SYSTEM_PROMPT = """You are a data analyst assistant. You receive structured computation results
(statistics, model metrics, chart descriptions) and write clear, friendly explanations for
non-technical users.

RULES:
- Never invent numbers. Only describe what is in the data you receive.
- Keep responses under 150 words.
- Be specific: mention actual column names, actual values from the data.
- Do not use jargon without explanation.
- Always start with the most important insight.
- Use conversational, friendly tone.
- Focus on actionable insights, not just raw numbers."""

    async def narrate(self, computation_result: Dict[str, Any], intent: str) -> str:
        """Generate natural language narration from computation results."""
        try:
            # Build prompt from computation result
            prompt = self._build_narration_prompt(computation_result, intent)

            # Get LLM response
            response_text = await self._call_llm(prompt)

            if not response_text:
                return self._fallback_narration(computation_result, intent)

            return response_text.strip()

        except Exception as e:
            logger.exception(f"Narration failed: {e}")
            return self._fallback_narration(computation_result, intent)

    def _build_narration_prompt(self, result: Dict[str, Any], intent: str) -> str:
        """Build a focused prompt for the LLM based on result type."""
        if intent == "eda":
            return self._build_eda_prompt(result)
        elif intent == "visualization":
            return self._build_viz_prompt(result)
        elif intent == "prediction":
            return self._build_prediction_prompt(result)
        elif intent == "xai":
            return self._build_xai_prompt(result)
        else:
            return self._build_general_prompt(result, intent)

    def _build_eda_prompt(self, result: Dict[str, Any]) -> str:
        """Build prompt for EDA results."""
        stats = result.get("statistics", {})
        shape = result.get("dataset_shape", {})

        prompt = f"""Explain these dataset statistics to a business user:

Dataset: {shape.get('rows', 'unknown')} rows, {shape.get('columns', 'unknown')} columns
Key metrics: {json.dumps(stats, indent=2)}

Focus on data quality, interesting patterns, and business implications."""

        return prompt

    def _build_viz_prompt(self, result: Dict[str, Any]) -> str:
        """Build prompt for visualization results."""
        viz_type = result.get("viz_type", "chart")
        stats = result.get("statistics", {})

        prompt = f"""Describe what this {viz_type} shows to a business user:

Chart details: {json.dumps(result, indent=2)}

Explain the key patterns, trends, or insights visible in the visualization."""

        return prompt

    def _build_prediction_prompt(self, result: Dict[str, Any]) -> str:
        """Build prompt for prediction/modeling results."""
        metrics = result.get("metrics", {})
        target = result.get("target_column", "target")

        prompt = f"""Explain these machine learning results to a business user:

Model performance: {json.dumps(metrics, indent=2)}
Target variable: {target}

Focus on model accuracy, reliability, and practical usefulness."""

        return prompt

    def _build_xai_prompt(self, result: Dict[str, Any]) -> str:
        """Build prompt for explainability results."""
        shap_values = result.get("global_feature_importance", {})

        prompt = f"""Explain what these feature importance scores mean:

Feature contributions: {json.dumps(shap_values, indent=2)}

Help the user understand which factors are most important for predictions."""

        return prompt

    def _build_general_prompt(self, result: Dict[str, Any], intent: str) -> str:
        """Build general prompt for other result types."""
        return f"""Explain these {intent} results to a business user:

Results: {json.dumps(result, indent=2)}

Provide clear, actionable insights from this analysis."""

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM for narration generation."""
        try:
            from ..llm.intent_parser import IntentParser

            # Use the same LLM provider logic as intent parsing
            provider = IntentParser._resolve_provider()
            if provider == "fallback":
                return None

            provider_cfg = IntentParser._provider_config(provider)
            if not provider_cfg:
                return None

            base_url, api_key, model = provider_cfg

            # Create a custom chat completion call with our system prompt
            endpoint = f"{base_url.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json",
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 200,
            }

            import requests
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=settings.INTENT_LLM_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return None

            message = choices[0].get("message", {})
            content = message.get("content", "")
            return content

        except Exception as e:
            logger.warning(f"LLM narration call failed: {e}")
            return None

    def _fallback_narration(self, result: Dict[str, Any], intent: str) -> str:
        """Generate basic narration when LLM is unavailable."""
        if intent == "eda":
            shape = result.get("dataset_shape", {})
            return f"Your dataset contains {shape.get('rows', 'unknown')} rows and {shape.get('columns', 'unknown')} columns. The analysis is complete and ready for further exploration."

        elif intent == "visualization":
            viz_type = result.get("viz_type", "chart")
            return f"I've created a {viz_type} visualization of your data. Check the chart above for visual insights into your dataset."

        elif intent == "prediction":
            metrics = result.get("metrics", {})
            accuracy = metrics.get("accuracy", metrics.get("r2_score", "unknown"))
            return f"The predictive model achieved a performance score of {accuracy:.3f}. The model is trained and ready for making predictions."

        elif intent == "xai":
            return "The explainability analysis shows which features are most important for the model's predictions. Features with higher importance scores have more influence on the results."

        else:
            return f"The {intent} analysis is complete. The results are shown above for your review."