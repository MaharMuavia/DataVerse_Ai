from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .rate_limiter import RateLimitTracker

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Raised when a provider call fails."""


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str


class ModelRouter:
    AGENT_MODEL_MAP: Dict[str, List[Dict[str, str]]] = {
        "orchestrator": [
            {"provider": "gemini", "model": "gemini-2.5-pro"},
            {"provider": "deepseek", "model": "deepseek-reasoner"},
            {"provider": "groq", "model": "llama-3.3-70b-versatile"},
        ],
        "data_analyst": [
            {"provider": "openai", "model": "gpt-4o"},
            {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},
            {"provider": "deepseek", "model": "deepseek-chat"},
        ],
        "visualizer": [
            {"provider": "gemini", "model": "gemini-2.5-flash"},
            {"provider": "groq", "model": "llama-3.3-70b-versatile"},
        ],
        "ml_agent": [
            {"provider": "deepseek", "model": "deepseek-chat"},
            {"provider": "together", "model": "Qwen/Qwen2.5-72B-Instruct-Turbo"},
        ],
        "insight_generator": [
            {"provider": "deepseek", "model": "deepseek-reasoner"},
            {"provider": "gemini", "model": "gemini-2.5-pro"},
        ],
        "anomaly_detector": [
            {"provider": "groq", "model": "llama-3.3-70b-versatile"},
            {"provider": "ollama", "model": "llama3.2"},
        ],
        "clarifier": [
            {"provider": "gemini", "model": "gemini-2.5-flash"},
            {"provider": "deepseek", "model": "deepseek-chat"},
        ],
    }

    def __init__(self, limiter: Optional[RateLimitTracker] = None) -> None:
        self.limiter = limiter or RateLimitTracker(
            daily_token_limits={
                "gemini": 1_000_000,
                "groq": 500_000,
                "deepseek": 2_000_000,
                "together": 300_000,
                "hf": 100_000,
                "ollama": 0,
            }
        )

    async def call(self, agent_name: str, messages: List[dict], **kwargs: Any) -> str:
        providers = self.AGENT_MODEL_MAP.get(agent_name)
        if not providers:
            raise ProviderError(f"Unknown agent: {agent_name}")

        last_error: Optional[Exception] = None
        for provider_conf in providers:
            provider = provider_conf["provider"]
            model = provider_conf["model"]

            if not self.limiter.can_use(provider):
                logger.warning("Skipping provider %s due to token cap", provider)
                continue

            try:
                response_text = await self._call_provider(provider, model, messages, **kwargs)
                estimated_tokens = max(1, len(response_text) // 4)
                self.limiter.record(provider, estimated_tokens)
                if self.limiter.nearing_limit(provider):
                    logger.warning("Provider %s is nearing daily free tier limits", provider)
                return response_text
            except Exception as exc:
                last_error = exc
                logger.warning("Provider %s failed for %s: %s", provider, agent_name, exc)
                continue

        raise ProviderError(f"All providers failed for agent '{agent_name}': {last_error}")

    async def _call_provider(self, provider: str, model: str, messages: List[dict], **kwargs: Any) -> str:
        if provider == "gemini":
            return await self._call_gemini(model, messages, **kwargs)
        if provider == "openai":
            return await self._call_openai_compatible(
                base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
                api_key=os.getenv("OPENAI_API_KEY"),
                model=model,
                messages=messages,
                **kwargs,
            )
        if provider == "anthropic":
            return await self._call_anthropic(model, messages, **kwargs)
        if provider == "groq":
            return await self._call_openai_compatible(
                base_url="https://api.groq.com/openai/v1",
                api_key=os.getenv("GROQ_API_KEY"),
                model=model,
                messages=messages,
                **kwargs,
            )
        if provider == "deepseek":
            return await self._call_openai_compatible(
                base_url="https://api.deepseek.com",
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                model=model,
                messages=messages,
                **kwargs,
            )
        if provider == "together":
            return await self._call_openai_compatible(
                base_url="https://api.together.xyz/v1",
                api_key=os.getenv("TOGETHER_API_KEY"),
                model=model,
                messages=messages,
                **kwargs,
            )
        if provider == "hf":
            return await self._call_hf(model, messages, **kwargs)
        if provider == "ollama":
            return await self._call_openai_compatible(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                api_key="ollama",
                model=model,
                messages=messages,
                **kwargs,
            )
        raise ProviderError(f"Unsupported provider: {provider}")

    async def _call_gemini(self, model: str, messages: List[dict], **kwargs: Any) -> str:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ProviderError("GOOGLE_API_KEY is not configured")

        try:
            import google.generativeai as genai
        except Exception as exc:  # pragma: no cover
            raise ProviderError("google-generativeai is not installed") from exc

        genai.configure(api_key=api_key)
        generation_config = kwargs.get("generation_config") or {
            "response_mime_type": kwargs.get("response_mime_type", "application/json")
        }

        prompt = self._messages_to_text(messages)
        gemini_model = genai.GenerativeModel(model_name=model, generation_config=generation_config)
        response = gemini_model.generate_content(prompt)
        text = getattr(response, "text", None)
        if text:
            return text

        candidates = getattr(response, "candidates", [])
        if candidates and candidates[0].content.parts:
            return candidates[0].content.parts[0].text
        raise ProviderError("Gemini returned empty response")

    async def _call_openai_compatible(
        self,
        *,
        base_url: str,
        api_key: Optional[str],
        model: str,
        messages: List[dict],
        **kwargs: Any,
    ) -> str:
        if not api_key:
            raise ProviderError(f"API key missing for base_url {base_url}")

        try:
            from openai import AsyncOpenAI
        except Exception as exc:  # pragma: no cover
            raise ProviderError("openai package is not installed") from exc

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.2),
        )

        content = response.choices[0].message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(getattr(item, "text", "") for item in content)
        return str(content)

    async def _call_anthropic(self, model: str, messages: List[dict], **kwargs: Any) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not configured")

        try:
            from anthropic import AsyncAnthropic
        except Exception as exc:  # pragma: no cover
            raise ProviderError("anthropic package is not installed") from exc

        client = AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 1024),
            messages=[
                {
                    "role": message.get("role", "user"),
                    "content": message.get("content", ""),
                }
                for message in messages
            ],
        )

        content = getattr(response, "content", [])
        if not content:
            raise ProviderError("Anthropic returned empty response")

        text_parts = []
        for block in content:
            text = getattr(block, "text", None)
            if text:
                text_parts.append(text)
        if text_parts:
            return "\n".join(text_parts)
        raise ProviderError("Anthropic returned empty text")

    async def _call_hf(self, model: str, messages: List[dict], **kwargs: Any) -> str:
        token = os.getenv("HF_TOKEN")
        if not token:
            raise ProviderError("HF_TOKEN is not configured")

        try:
            from huggingface_hub import InferenceClient
        except Exception as exc:  # pragma: no cover
            raise ProviderError("huggingface_hub is not installed") from exc

        client = InferenceClient(token=token)
        prompt = self._messages_to_text(messages)
        response = client.text_generation(
            model=model,
            prompt=prompt,
            max_new_tokens=kwargs.get("max_new_tokens", 1024),
        )
        return str(response)

    def _messages_to_text(self, messages: List[dict]) -> str:
        return "\n".join(
            f"{m.get('role', 'user').upper()}: {m.get('content', '')}"
            for m in messages
        )

    def get_langchain_llm(self, agent_name: str):
        providers = self.AGENT_MODEL_MAP.get(agent_name, [])
        if not providers:
            raise ProviderError(f"Unknown agent: {agent_name}")

        for provider_conf in providers:
            provider = provider_conf["provider"]
            model = provider_conf["model"]
            try:
                if provider == "gemini":
                    from langchain_google_genai import ChatGoogleGenerativeAI

                    return ChatGoogleGenerativeAI(model=model, google_api_key=os.getenv("GOOGLE_API_KEY"))
                if provider == "openai":
                    from langchain_openai import ChatOpenAI

                    return ChatOpenAI(
                        model=model,
                        base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
                        api_key=os.getenv("OPENAI_API_KEY"),
                    )
                if provider == "anthropic":
                    from langchain_anthropic import ChatAnthropic

                    return ChatAnthropic(model=model, anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"))
                if provider == "groq":
                    from langchain_groq import ChatGroq

                    return ChatGroq(model_name=model, groq_api_key=os.getenv("GROQ_API_KEY"))
                if provider in {"deepseek", "together", "ollama"}:
                    from langchain_openai import ChatOpenAI

                    if provider == "deepseek":
                        base_url = "https://api.deepseek.com"
                        api_key = os.getenv("DEEPSEEK_API_KEY")
                    elif provider == "together":
                        base_url = "https://api.together.xyz/v1"
                        api_key = os.getenv("TOGETHER_API_KEY")
                    else:
                        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
                        api_key = "ollama"

                    return ChatOpenAI(model=model, base_url=base_url, api_key=api_key)
            except Exception as exc:
                logger.warning("Unable to initialize %s (%s): %s", provider, model, exc)
                continue

        raise ProviderError(f"No LangChain model could be initialized for {agent_name}")
