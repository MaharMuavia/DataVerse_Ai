from pydantic import BaseModel, Field
from typing import Any, List, Optional, Literal
from jinja2 import Template
import os
from ...llm.llm_client import LLMClient


class FilterCondition(BaseModel):
    column: str
    operator: Literal['eq', 'neq', 'gt', 'lt', 'gte', 'lte', 'in', 'contains']
    value: Any  # Supports numeric, text, boolean, or list-like filter values


class TimeRange(BaseModel):
    start: Optional[str] = None  # ISO format date string
    end: Optional[str] = None


class IntentObject(BaseModel):
    primary_goal: Literal['explore', 'visualize', 'predict', 'explain', 'compare', 'query']
    target_columns: List[str] = Field(default_factory=list)
    filters: List[FilterCondition] = Field(default_factory=list)
    time_range: Optional[TimeRange] = None
    output_preference: Literal['chart', 'table', 'narrative', 'mixed'] = 'mixed'
    confidence: float = Field(ge=0.0, le=1.0)
    ambiguities: List[str] = Field(default_factory=list)
    follow_up_from: Optional[str] = None  # Previous query ID


class IntentExtractor:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def extract_intent(
        self,
        user_query: str,
        schema_json: dict,
        conversation_history: List[dict],
        session_id: str
    ) -> IntentObject:
        """
        Extract structured intent from user query using LLM.
        """
        prompt = self._build_intent_prompt(user_query, schema_json, conversation_history)

        # Call LLM to get JSON response
        response = await self.llm_client.generate_json(prompt, IntentObject)
        if isinstance(response, IntentObject):
            intent = response
        else:
            intent = IntentObject(**response)
        return self._apply_query_heuristics(intent, user_query, schema_json, conversation_history)

    def _build_intent_prompt(
        self,
        user_query: str,
        schema_json: dict,
        conversation_history: List[dict]
    ) -> str:
        """
        Build the intent extraction prompt using Jinja2 template.
        """
        template_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "prompts",
            "intent_extraction.j2"
        )

        with open(template_path, 'r') as f:
            template_content = f.read()

        template = Template(template_content)
        return template.render(
            user_query=user_query,
            schema_json=schema_json,
            conversation_history=conversation_history
        )

    def _apply_query_heuristics(
        self,
        intent: IntentObject,
        user_query: str,
        schema_json: dict,
        conversation_history: List[dict],
    ) -> IntentObject:
        """Refine LLM output with deterministic schema-aware heuristics."""
        query_lower = user_query.lower()
        schema_columns = self._extract_schema_columns(schema_json)
        schema_columns_lower = {col.lower(): col for col in schema_columns}

        mentioned_columns = [
            original
            for lowered, original in schema_columns_lower.items()
            if lowered in query_lower
        ]
        if mentioned_columns:
            deduped = list(dict.fromkeys(intent.target_columns + mentioned_columns))
            intent.target_columns = deduped

        output_pref = self._infer_output_preference(query_lower)
        if output_pref:
            intent.output_preference = output_pref

        primary_goal = self._infer_primary_goal(query_lower)
        if primary_goal:
            intent.primary_goal = primary_goal

        unresolved_references = any(token in query_lower for token in [" this ", " it ", " that "])
        if unresolved_references and not conversation_history:
            intent.ambiguities.append("Unclear reference to a previous column or result")

        if "unclear" in query_lower or "something" in query_lower:
            intent.ambiguities.append("Query is too vague to map confidently")

        validated_columns = []
        for col in intent.target_columns:
            if col in schema_columns:
                validated_columns.append(col)
            else:
                intent.ambiguities.append(f"Unknown column reference: {col}")
        intent.target_columns = list(dict.fromkeys(validated_columns))
        intent.ambiguities = list(dict.fromkeys(intent.ambiguities))

        if intent.ambiguities:
            intent.confidence = min(intent.confidence, 0.55)
        elif mentioned_columns:
            intent.confidence = max(intent.confidence, 0.8)

        return intent

    def _extract_schema_columns(self, schema_json: dict) -> List[str]:
        """Extract a flat list of schema columns from mixed schema formats."""
        if isinstance(schema_json, str):
            try:
                import json
                schema_json = json.loads(schema_json)
            except Exception:
                return []

        columns = schema_json.get("columns", []) if isinstance(schema_json, dict) else []
        if isinstance(columns, dict):
            return list(columns.keys())
        if isinstance(columns, list):
            return [str(col) for col in columns]
        return []

    def _infer_output_preference(self, query_lower: str) -> Optional[str]:
        if "show me" in query_lower or "plot" in query_lower or "chart" in query_lower:
            return "chart"
        if query_lower.startswith("list") or "list " in query_lower or "table" in query_lower:
            return "table"
        if "tell me" in query_lower or "explain" in query_lower or "why" in query_lower:
            return "narrative"
        return None

    def _infer_primary_goal(self, query_lower: str) -> Optional[str]:
        if any(word in query_lower for word in ["predict", "forecast", "classify"]):
            return "predict"
        if any(word in query_lower for word in ["explain", "why"]):
            return "explain"
        if any(word in query_lower for word in ["compare", "versus", "vs "]):
            return "compare"
        if any(word in query_lower for word in ["show", "plot", "chart", "distribution"]):
            return "visualize"
        if any(word in query_lower for word in ["query", "filter", "where"]):
            return "query"
        if any(word in query_lower for word in ["analyze", "explore", "summary", "top"]):
            return "explore"
        return None
