from typing import Dict, Any, Optional
import json
import asyncio
from .deepanalyze_client import DeepAnalyzeClient
from ..services.llm_provider import LLMProvider


class LLMClient:
    """Unified LLM client for the agent system."""

    def __init__(self, deepanalyze_client: Optional[DeepAnalyzeClient] = None, provider: Optional[LLMProvider] = None):
        self.deepanalyze = deepanalyze_client or DeepAnalyzeClient()
        self.provider = provider or LLMProvider()

    async def generate_text(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate text response from LLM."""
        try:
            text = await self.provider.generate(prompt)
            if text:
                return text
        except Exception:
            pass

        # Compatibility fallback for callers that injected DeepAnalyzeClient.
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.deepanalyze.call_model, prompt, max_tokens)
            if result.get("ok"):
                return result.get("text") or ""
        except Exception:
            pass

        return self._deterministic_fallback(prompt)

    async def generate_json(self, prompt: str, response_model=None, max_tokens: int = 512):
        """Generate JSON response and optionally validate against a Pydantic model."""
        # Add JSON instruction to prompt
        json_prompt = prompt + "\n\nRespond with valid JSON only."

        text_response = await self.generate_text(json_prompt, max_tokens)

        try:
            # Try to parse as JSON
            data = json.loads(text_response.strip())

            # If we have a Pydantic model, validate
            if response_model:
                return response_model(**data)

            return data

        except json.JSONDecodeError as e:
            return self._fallback_json(response_model)
        except Exception as e:
            return self._fallback_json(response_model)

    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.provider.is_configured() or self.deepanalyze.is_available()

    def _deterministic_fallback(self, prompt: str) -> str:
        return (
            "LLM providers were unavailable. Deterministic fallback: the analysis was completed "
            "from computed dataset facts; review the structured JSON for metrics, warnings, and recommendations."
        )

    def _fallback_json(self, response_model=None):
        data: Dict[str, Any] = {}
        if response_model:
            try:
                return response_model(**data)
            except Exception:
                return data
        return data
