"""Intent parsing using configurable LLM providers.

Supports DeepSeek and OpenAI through OpenAI-compatible chat completion APIs.
If no provider credentials are configured, falls back to deterministic keyword parsing.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

import requests

from ..core.config import settings
from ..core.logger import logger


class IntentParser:
    """Parses user queries into a structured plan."""

    @staticmethod
    def _is_ollama_base_url(base_url: str) -> bool:
        lowered = base_url.lower()
        return "localhost:11434" in lowered or "127.0.0.1:11434" in lowered

    @staticmethod
    def _build_prompt(query: str) -> str:
        return f"""
You are an intent parser that must always respond with strict JSON.
Input: A user query about a dataset.
Output JSON schema:
{{
  "intent": "<string>",
  "time_filter": {{"start": "YYYY-MM-DD"|null, "end": "YYYY-MM-DD"|null}}|null,
  "metric": "<column_name>"|null,
  "operations": ["<operation_names>"],
  "notes": "<optional notes>"
}}

User query: "{query}"

Return only valid JSON with the fields described above. Never include explanatory text.
"""

    @staticmethod
    def _fallback_intent(query: str, note: str) -> Dict[str, Any]:
        """Simple keyword-based intent extraction fallback."""
        query_lower = query.lower()
        operations = []
        if any(w in query_lower for w in ["predict", "forecast", "model", "classify", "regress"]):
            operations.append("prediction")
        if any(w in query_lower for w in ["explai", "why", "feature import", "shap", "lime"]):
            operations.append("explanation")
        if any(w in query_lower for w in ["distrib", "histogram", "scatter", "heatmap", "plot", "visual"]):
            operations.append("visualization")
        if any(w in query_lower for w in ["analyz", "profile", "eda", "describe", "summary"]):
            operations.append("analysis")

        return {
            "intent": query[:100],
            "time_filter": None,
            "metric": None,
            "operations": operations if operations else ["analysis"],
            "notes": note,
        }

    @staticmethod
    def _resolve_provider() -> str:
        """Pick intent provider based on config and available credentials."""
        provider = (settings.INTENT_LLM_PROVIDER or "auto").strip().lower()
        if provider in {"deepseek", "openai"}:
            return provider

        if provider == "auto":
            if settings.DEEPSEEK_API_KEY:
                return "deepseek"
            if settings.OPENAI_API_KEY:
                return "openai"
            return "fallback"

        logger.warning("Unknown INTENT_LLM_PROVIDER '%s'; using fallback parser", provider)
        return "fallback"

    @staticmethod
    def _provider_config(provider: str) -> Optional[Tuple[str, str, str]]:
        if provider == "deepseek":
            if not settings.DEEPSEEK_API_KEY and not IntentParser._is_ollama_base_url(settings.DEEPSEEK_API_BASE):
                return None
            return (
                settings.DEEPSEEK_API_BASE,
                settings.DEEPSEEK_API_KEY or "",
                settings.DEEPSEEK_INTENT_MODEL,
            )

        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                return None
            return (
                settings.OPENAI_API_BASE or "https://api.openai.com/v1",
                settings.OPENAI_API_KEY,
                settings.OPENAI_INTENT_MODEL,
            )

        return None

    @staticmethod
    def _chat_completion(base_url: str, api_key: str, model: str, prompt: str) -> str:
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You extract dataset-query intent and return strict JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 300,
        }
        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=settings.INTENT_LLM_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("No choices returned by LLM provider")

            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, list):
                # Some providers may return content as parts.
                text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
                content = "".join(text_parts)

            if not isinstance(content, str) or not content.strip():
                raise ValueError("Provider returned empty content")
            return content
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code != 404 or not IntentParser._is_ollama_base_url(base_url):
                raise
        except requests.RequestException:
            if not IntentParser._is_ollama_base_url(base_url):
                raise

        # Fallback path for local Ollama-style deployments.
        ollama_endpoint = f"{base_url.rstrip('/')}/api/generate"
        ollama_payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        ollama_response = requests.post(
            ollama_endpoint,
            json=ollama_payload,
            timeout=settings.INTENT_LLM_TIMEOUT,
        )
        ollama_response.raise_for_status()
        ollama_data = ollama_response.json()
        content = ollama_data.get("response", "")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama returned empty response")
        return content

    @staticmethod
    def _parse_json_output(text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(
                line for line in cleaned.splitlines() if not line.strip().startswith("```")
            ).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                return json.loads(cleaned[start : end + 1])
            raise

    @staticmethod
    def parse(query: str) -> Dict[str, Any]:
        provider = IntentParser._resolve_provider()
        if provider == "fallback":
            return IntentParser._fallback_intent(
                query,
                "Fallback intent from keyword matching (no LLM provider configured)",
            )

        provider_cfg = IntentParser._provider_config(provider)
        if provider_cfg is None:
            logger.warning("%s provider selected but API key is missing; using fallback parser", provider)
            return IntentParser._fallback_intent(
                query,
                f"Fallback intent from keyword matching ({provider} key missing)",
            )

        base_url, api_key, model = provider_cfg
        prompt = IntentParser._build_prompt(query)
        try:
            text = IntentParser._chat_completion(
                base_url=base_url,
                api_key=api_key,
                model=model,
                prompt=prompt,
            )
            parsed = IntentParser._parse_json_output(text)
            operations = parsed.get("operations", [])
            if not isinstance(operations, list):
                operations = []

            time_filter = parsed.get("time_filter")
            if time_filter is not None and not isinstance(time_filter, dict):
                time_filter = None

            return {
                "intent": parsed.get("intent") or query[:100],
                "time_filter": time_filter,
                "metric": parsed.get("metric"),
                "operations": operations,
                "notes": parsed.get("notes") or f"Intent parsed by {provider}",
            }
        except Exception:
            logger.exception("Failed to parse intent with %s provider", provider)
            return IntentParser._fallback_intent(
                query,
                f"Fallback intent from keyword matching ({provider} call failed)",
            )
