"""Hardened Intent Router with confidence scoring and rule-based overrides.

This router provides robust intent classification with:
- Rule-based pre-filtering for high-confidence matches
- LLM classification with structured output
- Confidence thresholding and fallback logic
- Rule overrides when rules disagree with LLM but have high confidence
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from ..core.config import settings
from ..core.logger import logger


@dataclass
class IntentResult:
    """Result of intent classification."""
    intent: str
    params: Dict[str, Any]
    confidence: float
    message: Optional[str] = None


class IntentRouter:
    """Hardened intent router with rule-based and LLM classification."""

    # Rule patterns for high-confidence keyword matching
    RULE_PATTERNS = {
        "eda": [
            r"profile", r"describe", r"summary", r"missing", r"distribution",
            r"correlation", r"outlier", r"statistics", r"overview", r"explore"
        ],
        "visualization": [
            r"chart", r"plot", r"graph", r"visuali", r"show me", r"histogram",
            r"boxplot", r"scatter", r"bar chart", r"heatmap", r"display"
        ],
        "prediction": [
            r"predict", r"forecast", r"train", r"model", r"classify", r"regression",
            r"machine learning", r"ml", r"ai", r"automl"
        ],
        "xai": [
            r"explain", r"why", r"feature importance", r"shap", r"lime",
            r"contribution", r"interpret", r"understand"
        ],
        "aggregation": [
            r"top \d+", r"average", r"total", r"sum", r"count", r"group by",
            r"by region", r"by category", r"aggregate", r"pivot"
        ],
    }

    FALLBACK_INTENTS = ["eda", "visualization", "prediction", "xai", "aggregation", "general_question"]

    def _apply_rules(self, query: str) -> Optional[str]:
        """Apply rule-based pattern matching for high-confidence intents."""
        query_lower = query.lower()

        # Count matches for each intent
        intent_scores = {}
        for intent, patterns in self.RULE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if pattern.lower() in query_lower:
                    score += 1
            if score > 0:
                intent_scores[intent] = score

        if not intent_scores:
            return None

        # Return highest scoring intent if it has at least 2 matches
        best_intent = max(intent_scores, key=intent_scores.get)
        if intent_scores[best_intent] >= 2:
            return best_intent

        return None

    async def _classify_with_llm(self, query: str, dataset_columns: List[str]) -> IntentResult:
        """Classify intent using LLM with structured output."""
        from ..llm.intent_parser import IntentParser

        # Build prompt for structured classification
        system_prompt = f"""You are an intent classifier for a data analytics platform. Given a user query and dataset column names, classify the intent into exactly one of: {", ".join(self.FALLBACK_INTENTS)}.

Respond ONLY with this JSON, no other text:
{{"intent": "<intent>", "params": {{"target_column": "<col or null>", "chart_type": "<type or null>", "group_by": "<col or null>"}}, "confidence": <0.0-1.0>}}"""

        user_prompt = f"Query: {query}\nColumns: {', '.join(dataset_columns)}"

        # Try to get LLM response
        try:
            provider = IntentParser._resolve_provider()
            if provider == "fallback":
                # Use keyword fallback
                fallback_result = IntentParser._fallback_intent(query, "LLM unavailable")
                return IntentResult(
                    intent=fallback_result.get("intent", "eda"),
                    params={},
                    confidence=0.5
                )

            # Get LLM response
            provider_cfg = IntentParser._provider_config(provider)
            if not provider_cfg:
                raise ValueError("Provider config missing")

            base_url, api_key, model = provider_cfg
            prompt = f"{system_prompt}\n\n{user_prompt}"

            text = IntentParser._chat_completion(
                base_url=base_url,
                api_key=api_key,
                model=model,
                prompt=prompt,
            )

            # Parse JSON response
            parsed = IntentParser._parse_json_output(text)

            intent = parsed.get("intent", "eda")
            params = parsed.get("params", {})
            confidence = parsed.get("confidence", 0.5)

            # Validate intent
            if intent not in self.FALLBACK_INTENTS:
                intent = "eda"
                confidence = 0.3

            return IntentResult(
                intent=intent,
                params=params,
                confidence=min(max(confidence, 0.0), 1.0)
            )

        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            # Fallback to keyword matching
            fallback_result = IntentParser._fallback_intent(query, f"LLM failed: {e}")
            return IntentResult(
                intent=fallback_result.get("intent", "eda"),
                params={},
                confidence=0.4
            )

    def _suggest_alternatives(self, query: str) -> str:
        """Suggest alternative queries when confidence is low."""
        suggestions = []
        query_lower = query.lower()

        if any(word in query_lower for word in ["predict", "model", "train"]):
            suggestions.append("Try: 'train a model to predict [column]'")
        if any(word in query_lower for word in ["chart", "plot", "show"]):
            suggestions.append("Try: 'show me a chart of [column]'")
        if any(word in query_lower for word in ["explain", "why"]):
            suggestions.append("Try: 'explain why [column] affects [target]'")

        if not suggestions:
            suggestions = [
                "Try: 'describe my dataset'",
                "Try: 'show me a chart of [column]'",
                "Try: 'predict [target] using [features]'"
            ]

        return " or ".join(suggestions[:2])

    async def route(self, query: str, dataset_columns: List[str]) -> IntentResult:
        """Route query to appropriate intent with confidence scoring."""
        # Step 1: Rule-based pre-filter (fast, no API call)
        rule_match = self._apply_rules(query)

        # Step 2: LLM classification with structured output
        llm_result = await self._classify_with_llm(query, dataset_columns)

        # Step 3: Confidence check
        if llm_result.confidence < 0.72:
            return IntentResult(
                intent="clarification_needed",
                message=f"I'm not sure what you want. Did you mean: {self._suggest_alternatives(query)}?",
                confidence=llm_result.confidence
            )

        # Step 4: Rule overrides LLM if they disagree AND rule confidence is high
        final_intent = llm_result.intent
        if rule_match and rule_match != llm_result.intent:
            logger.info(f"Rule override: {rule_match} vs LLM {llm_result.intent}")
            final_intent = rule_match  # trust rules for clear keyword matches

        return IntentResult(
            intent=final_intent,
            params=llm_result.params,
            confidence=llm_result.confidence
        )