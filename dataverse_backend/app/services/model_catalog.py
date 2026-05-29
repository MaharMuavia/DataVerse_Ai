from __future__ import annotations

from typing import Any, Dict

from ..core.config import settings


def get_model_catalog() -> Dict[str, Any]:
    """Return the supported provider catalog and task-oriented defaults."""
    mistral_chat = getattr(settings, "MISTRAL_CHAT_MODEL", "mistral-small-latest")
    mistral_reasoning = getattr(settings, "MISTRAL_REASONING_MODEL", "mistral-large-latest")
    return {
        "providers": [
            {
                "id": "openai",
                "label": "OpenAI",
                "models": [
                    {
                        "id": settings.OPENAI_CHAT_MODEL,
                        "role": "primary_chat",
                        "strengths": ["deep reasoning", "tool calling", "multi-step analysis"],
                    },
                    {
                        "id": settings.OPENAI_INTENT_MODEL,
                        "role": "fast_intent",
                        "strengths": ["classification", "routing", "low-latency parsing"],
                    },
                ],
            },
            {
                "id": "anthropic",
                "label": "Anthropic",
                "models": [
                    {
                        "id": settings.CLAUDE_MODEL,
                        "role": "high_quality_analysis",
                        "strengths": ["long context", "rich explanations", "agentic workflows"],
                    }
                ],
            },
            {
                "id": "mistral",
                "label": "Mistral",
                "models": [
                    {
                        "id": mistral_chat,
                        "role": "open_model_chat",
                        "strengths": ["cost efficiency", "tool use", "structured outputs"],
                    },
                    {
                        "id": mistral_reasoning,
                        "role": "open_model_reasoning",
                        "strengths": ["reasoning traces", "EDA planning", "ML suggestions"],
                    },
                ],
            },
        ],
        "defaults": {
            "chat": {"provider": "openai", "model": settings.OPENAI_CHAT_MODEL, "reasoning": "medium"},
            "reasoning": {"provider": "anthropic", "model": settings.CLAUDE_MODEL, "reasoning": "medium"},
            "budget": {"provider": "mistral", "model": mistral_chat, "reasoning": "low"},
        },
    }


def get_prompt_profiles() -> Dict[str, Dict[str, Any]]:
    """Prompt guidance optimized for data science assistant workflows."""
    return {
        "eda": {
            "objective": "Summarize dataset health and business-relevant patterns before proposing actions.",
            "focus": ["columns", "missingness", "distribution shifts", "outliers", "time coverage"],
            "guardrails": [
                "Call out uncertainty when schema or sampling limits confidence.",
                "Prefer ranked findings over long prose.",
                "Translate statistical findings into business implications.",
            ],
        },
        "cleaning": {
            "objective": "Recommend reversible cleaning steps that preserve auditability.",
            "focus": ["null handling", "type repair", "deduplication", "category normalization"],
            "guardrails": [
                "Never drop columns silently.",
                "Explain why each cleaning step is safe.",
                "Flag operations that could change business meaning.",
            ],
        },
        "visualization": {
            "objective": "Choose the clearest chart for the analytical question and audience.",
            "focus": ["chart type", "axes", "aggregation", "comparisons", "narrative title"],
            "guardrails": [
                "Use the simplest chart that answers the question.",
                "Avoid misleading dual-axis or 3D chart choices.",
                "Return chart-ready structure when possible.",
            ],
        },
        "ml_suggestions": {
            "objective": "Suggest practical baseline models and validation strategy for the dataset.",
            "focus": ["target leakage", "task framing", "baseline models", "feature risks", "evaluation metrics"],
            "guardrails": [
                "Recommend simple baselines before advanced models.",
                "Tie metrics to business outcomes.",
                "State when the dataset is not ready for modeling.",
            ],
        },
    }


def select_task_model(task: str) -> Dict[str, str]:
    """Return the recommended provider/model pair for a given product task."""
    normalized = (task or "").strip().lower()
    mistral_chat = getattr(settings, "MISTRAL_CHAT_MODEL", "mistral-small-latest")

    task_map = {
        "eda": {"provider": "anthropic", "model": settings.CLAUDE_MODEL, "reasoning": "medium"},
        "cleaning": {"provider": "openai", "model": settings.OPENAI_INTENT_MODEL, "reasoning": "low"},
        "visualization": {"provider": "mistral", "model": mistral_chat, "reasoning": "low"},
        "ml_suggestions": {"provider": "openai", "model": settings.OPENAI_CHAT_MODEL, "reasoning": "medium"},
    }
    selection = task_map.get(normalized, task_map["eda"]).copy()
    selection["task"] = normalized or "eda"
    return selection
