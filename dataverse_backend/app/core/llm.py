"""LLM client factory for getting the appropriate language model.

Supports Claude (Anthropic) and OpenAI with graceful fallbacks when optional
LangChain provider packages are unavailable.
"""
from typing import Any, Optional
import logging
from .config import settings

logger = logging.getLogger(__name__)

# Global LLM instance cache
_llm_instance = None


async def get_llm():
    """Get the configured LLM instance.
    
    Returns the LLM client based on ANTHROPIC_API_KEY or falls back to OpenAI.
    Uses the Claude Sonnet 4 model (200K context window) as primary.
    """
    global _llm_instance
    
    if _llm_instance is not None:
        return _llm_instance
    
    # Try Claude/Anthropic first (preferred)
    if settings.ANTHROPIC_API_KEY:
        try:
            from langchain_anthropic import ChatAnthropic
            
            _llm_instance = ChatAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                model=settings.CLAUDE_MODEL,
                temperature=0.7,
                max_tokens=8192,
            )
            logger.info(f"Initialized Claude LLM: {settings.CLAUDE_MODEL}")
            return _llm_instance
            
        except ImportError:
            logger.warning("langchain-anthropic not installed, falling back to OpenAI")
    
    # Fallback to OpenAI
    if settings.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            
            _llm_instance = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_CHAT_MODEL,
                temperature=0.7,
                max_tokens=8192,
            )
            logger.info(f"Initialized OpenAI LLM: {settings.OPENAI_CHAT_MODEL}")
            return _llm_instance
            
        except ImportError:
            logger.warning("langchain-openai not installed, falling back to OpenAI SDK wrapper")
            try:
                from openai import AsyncOpenAI

                _llm_instance = SimpleOpenAIWrapper(
                    client=AsyncOpenAI(
                        api_key=settings.OPENAI_API_KEY,
                        base_url=settings.OPENAI_API_BASE or None,
                    ),
                    model=settings.OPENAI_CHAT_MODEL,
                )
                logger.info(f"Initialized OpenAI SDK wrapper: {settings.OPENAI_CHAT_MODEL}")
                return _llm_instance
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI SDK wrapper: {e}")
    
    # Final fallback - simple Anthropic SDK wrapper when Anthropic key exists.
    if settings.ANTHROPIC_API_KEY:
        try:
            from anthropic import AsyncAnthropic
            
            _llm_instance = SimpleLLMWrapper(client=AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY))
            logger.info(f"Initialized Anthropic SDK wrapper: {settings.CLAUDE_MODEL}")
            return _llm_instance
            
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic SDK wrapper: {e}")
    
    raise RuntimeError(
        "No LLM configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env and ensure provider SDK dependencies are installed."
    )


class SimpleLLMWrapper:
    """Simple wrapper for Anthropic client when using direct API."""
    
    def __init__(self, client):
        self.client = client
    
    async def ainvoke(self, message: str, **kwargs):
        """Call the LLM asynchronously."""
        try:
            response = await self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=8192,
                messages=[{"role": "user", "content": message}],
            )
            
            # Return in LangChain format
            return type('obj', (object,), {
                'content': response.content[0].text if response.content else ""
            })()
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise


class SimpleOpenAIWrapper:
    """Minimal OpenAI async wrapper with LangChain-like `ainvoke`."""

    def __init__(self, client, model: str):
        self.client = client
        self.model = model

    async def ainvoke(self, message: str, **kwargs):
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 8192)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": message}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "\n".join(getattr(item, "text", "") for item in content)
        else:
            text = str(content or "")

        return type("obj", (object,), {"content": text})()


def reset_llm():
    """Reset the global LLM instance (useful for testing)."""
    global _llm_instance
    _llm_instance = None
