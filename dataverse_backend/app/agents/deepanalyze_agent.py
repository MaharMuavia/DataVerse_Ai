"""Agent that uses DeepAnalyze-8B to interpret computed facts and generate business-level reports.

This agent strictly adheres to the constraint that DeepAnalyze should only receive structured
summaries / computed facts and not raw CSV or DataFrames. It constructs a clear prompt
instructing the model to reason step-by-step and to produce structured, explainable output.
"""
from __future__ import annotations

import json
from typing import Dict, Any

from .base_agent import BaseAgent
from ..llm.deepanalyze_client import DeepAnalyzeClient
from ..core.logger import logger
from ..core.exceptions import ModelUnavailableError


class DeepAnalyzeAgent(BaseAgent):
    def __init__(self, session_id: str, client: DeepAnalyzeClient | None = None):
        super().__init__(name="deepanalyze_agent", description="Uses DeepAnalyze for reasoning and report generation", session_id=session_id)
        self.client = client or DeepAnalyzeClient()

    def _build_prompt(self, facts: Dict[str, Any]) -> str:
        # The prompt enforces structured output and instructs the model to avoid technical jargon.
        # It also instructs the model to reason step-by-step, provide key insights, and suggest actions.
        # DO NOT pass raw data; only pass computed facts and concise summaries.
        facts_json = json.dumps(facts, indent=2, ensure_ascii=False)
        prompt = f"""
You are DeepAnalyze, a professional business analyst. You will receive a JSON object containing computed facts
from an analytical computation. DO NOT perform numeric computations or ingest raw CSV or DataFrames - use only
these provided facts.

Instructions:
- Use simple business language. Avoid technical jargon.
- Provide a short executive summary (2-3 sentences).
- List top 3 key insights based on the facts (each with short reasoning sentences).
- Provide 2-3 concrete business actions the user can take.
- Explain any assumptions you relied upon.
- Output must be JSON with fields: "executive_summary", "key_insights" (list), "actions" (list), "assumptions" (list).

Input facts:
{facts_json}

Return only valid JSON. Do not add extra commentary outside the JSON.
"""
        return prompt

    def run(self, computed_facts: Dict[str, Any]) -> Dict[str, Any]:
        self.log_action("calling_deepanalyze", {"summary_keys": list(computed_facts.keys())})

        prompt = self._build_prompt(computed_facts)
        # Summarize prompt for logs (avoid logging raw sensitive data)
        self.log_action("deepanalyze_prompt_built", {"prompt_length": len(prompt)})

        result = self.client.call_model(prompt=prompt)

        # Result is a dict {'ok': bool, 'text': str} or {'ok': False, 'error': str}
        if not isinstance(result, dict) or not result.get("ok"):
            err = result.get("error") if isinstance(result, dict) else "Unknown error"
            logger.warning("DeepAnalyze unavailable or returned error: %s", err)
            self.log_action("deepanalyze_failed", {"reason": err})
            # Return a clear unavailable status and do NOT raise; upstream orchestrator decides fallback behavior
            return {"status": "unavailable", "report": {"executive_summary": "Reasoning model unavailable.", "key_insights": [], "actions": [], "assumptions": [str(err)]}}

        text = result.get("text", "")
        # Try to parse structured JSON output from model
        try:
            parsed = json.loads(text)
            self.log_action("deepanalyze_completed", {"insights_keys": list(parsed.keys())})
            return {"status": "success", "report": parsed}
        except json.JSONDecodeError:
            # If model returned non-JSON, capture raw text and return as plain narrative
            logger.warning("DeepAnalyze returned non-JSON text; returning raw narrative")
            self.log_action("deepanalyze_completed_raw", {"text_length": len(text)})
            return {"status": "success", "report": {"executive_summary": text, "key_insights": [], "actions": [], "assumptions": ["Model returned plain text"]}}
