"""Optional narrative LLM provider chain with graceful fallback."""
from __future__ import annotations

import os
import asyncio
from collections.abc import Awaitable, Callable

from ..core.config import settings


Generator = Callable[[str], Awaitable[str]]


class LLMProvider:
    """Provider wrapper used only for summarizing computed facts.

    Provider order is intentionally conservative:
    OpenAI -> Gemini -> Anthropic -> local DeepAnalyze/Ollama.
    If every provider is unavailable, callers receive ``None`` and should use a
    deterministic template.
    """

    def __init__(
        self,
        provider: str | None = None,
        openai_api_key: str | None = None,
        gemini_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        deepanalyze_base_url: str | None = None,
        openai_generate: Generator | None = None,
        gemini_generate: Generator | None = None,
        anthropic_generate: Generator | None = None,
        local_generate: Generator | None = None,
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER") or "auto").strip().lower()
        self.openai_api_key = openai_api_key if openai_api_key is not None else settings.OPENAI_API_KEY
        self.gemini_api_key = (
            gemini_api_key
            if gemini_api_key is not None
            else settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY")
        )
        self.anthropic_api_key = (
            anthropic_api_key if anthropic_api_key is not None else settings.ANTHROPIC_API_KEY
        )
        self.deepanalyze_base_url = deepanalyze_base_url or settings.DEEPANALYZE_BASE_URL
        self._openai_generate = openai_generate
        self._gemini_generate = gemini_generate
        self._anthropic_generate = anthropic_generate
        self._local_generate = local_generate
        self.last_provider: str | None = None
        self.last_errors: list[str] = []

    def configured_order(self) -> list[str]:
        requested = self.provider
        available = []
        if self.openai_api_key:
            available.append("openai")
        if self.gemini_api_key:
            available.append("gemini")
        if self.anthropic_api_key:
            available.append("anthropic")
        if self.deepanalyze_base_url:
            available.append("local")

        if requested in {"openai", "gemini", "anthropic", "local"}:
            return [requested] + [provider for provider in available if provider != requested]
        return available

    def is_configured(self) -> bool:
        return bool(self.configured_order())

    async def generate(self, prompt: str) -> str | None:
        errors = []
        self.last_provider = None
        for provider in self.configured_order():
            try:
                if provider == "openai":
                    text = await self._generate_openai(prompt)
                elif provider == "gemini":
                    text = await self._generate_gemini(prompt)
                elif provider == "anthropic":
                    text = await self._generate_anthropic(prompt)
                else:
                    text = await self._generate_local(prompt)
                if text:
                    self.last_provider = provider
                    return text
            except Exception as exc:  # pragma: no cover - exercised with injected test callables
                errors.append(f"{provider}: {exc}")
        self.last_errors = errors
        return None

    async def _generate_openai(self, prompt: str) -> str:
        if self._openai_generate:
            return await self._openai_generate(prompt)
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.openai_api_key,
            base_url=os.getenv("OPENAI_API_BASE") or None,
            timeout=3.0,
            max_retries=0,
        )
        response = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You explain already-computed business analytics. Do not invent numbers.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    async def _generate_gemini(self, prompt: str) -> str:
        if self._gemini_generate:
            return await self._gemini_generate(prompt)
        if not self.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        try:
            import google.generativeai as genai
        except Exception as exc:
            raise RuntimeError("google-generativeai is not installed") from exc

        genai.configure(api_key=self.gemini_api_key)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt, request_options={"timeout": 3})
        return getattr(response, "text", "") or ""

    async def _generate_anthropic(self, prompt: str) -> str:
        if self._anthropic_generate:
            return await self._anthropic_generate(prompt)
        if not self.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")

        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.anthropic_api_key, timeout=3.0, max_retries=0)
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=700,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [getattr(part, "text", "") for part in response.content]
        return "\n".join(part for part in parts if part)

    async def _generate_local(self, prompt: str) -> str:
        if self._local_generate:
            return await self._local_generate(prompt)
        from ..llm.deepanalyze_client import DeepAnalyzeClient

        client = DeepAnalyzeClient(timeout=1)
        result = await asyncio.to_thread(client.call_model, prompt, 700)
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "local LLM unavailable")
        return result.get("text") or ""
