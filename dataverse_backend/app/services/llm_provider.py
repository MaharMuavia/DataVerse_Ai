"""Optional OpenAI/Gemini narrative provider with graceful fallback."""
from __future__ import annotations

import os
from collections.abc import Awaitable, Callable


Generator = Callable[[str], Awaitable[str]]


class LLMProvider:
    """Small provider wrapper used only for summarizing computed facts."""

    def __init__(
        self,
        provider: str | None = None,
        openai_api_key: str | None = None,
        gemini_api_key: str | None = None,
        openai_generate: Generator | None = None,
        gemini_generate: Generator | None = None,
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER") or "auto").strip().lower()
        self.openai_api_key = openai_api_key if openai_api_key is not None else os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = (
            gemini_api_key
            if gemini_api_key is not None
            else os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        )
        self._openai_generate = openai_generate
        self._gemini_generate = gemini_generate

    def configured_order(self) -> list[str]:
        requested = self.provider
        available = []
        if self.openai_api_key:
            available.append("openai")
        if self.gemini_api_key:
            available.append("gemini")

        if requested in {"openai", "gemini"}:
            return [requested] + [provider for provider in available if provider != requested]
        return available

    def is_configured(self) -> bool:
        return bool(self.configured_order())

    async def generate(self, prompt: str) -> str | None:
        errors = []
        for provider in self.configured_order():
            try:
                if provider == "openai":
                    return await self._generate_openai(prompt)
                if provider == "gemini":
                    return await self._generate_gemini(prompt)
            except Exception as exc:  # pragma: no cover - exercised with injected test callables
                errors.append(f"{provider}: {exc}")
        if errors:
            raise RuntimeError("; ".join(errors))
        return None

    async def _generate_openai(self, prompt: str) -> str:
        if self._openai_generate:
            return await self._openai_generate(prompt)
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.openai_api_key, base_url=os.getenv("OPENAI_API_BASE") or None)
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
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
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
        response = model.generate_content(prompt)
        return getattr(response, "text", "") or ""
