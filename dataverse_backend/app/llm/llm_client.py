from typing import Dict, Any, Optional
import json
import asyncio
from .deepanalyze_client import DeepAnalyzeClient


class LLMClient:
    """Unified LLM client for the agent system."""

    def __init__(self, deepanalyze_client: Optional[DeepAnalyzeClient] = None):
        self.deepanalyze = deepanalyze_client or DeepAnalyzeClient()

    async def generate_text(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate text response from LLM."""
        # Run in thread pool since DeepAnalyzeClient is sync
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.deepanalyze.call_model, prompt, max_tokens)

        if result["ok"]:
            return result["text"]
        else:
            raise Exception(f"LLM call failed: {result['error']}")

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
            raise Exception(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            raise Exception(f"Failed to validate response model: {e}")

    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.deepanalyze.is_available()
