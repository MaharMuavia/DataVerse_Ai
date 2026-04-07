from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from jinja2 import Template
from pydantic import BaseModel, Field

from .intent_extractor import IntentExtractor
from .tool_registry import ChartSpec, NarrativeSpec, SessionContext, TableSpec, ToolRegistry
from ...llm.llm_client import LLMClient
from ...memory.conversation_memory import get_memory_store

if TYPE_CHECKING:
    from ...memory.conversation_memory import ConversationMemory


@dataclass
class AgentResponse:
    narrative: str
    charts: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    model_results: List[Dict[str, Any]]
    explanation: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    clarification: Optional[Dict[str, Any]] = None
    active_filters: List[Dict[str, Any]] = field(default_factory=list)


class PlanStep(BaseModel):
    step: int
    tool: str
    params: Dict[str, Any] = Field(default_factory=dict)
    purpose: Optional[str] = None


class AgentPlan(BaseModel):
    reasoning: str
    steps: List[PlanStep]


class ObserveDecision(BaseModel):
    decision: str
    reason: Optional[str] = None


class ReflectResponse(BaseModel):
    revised_plan: Optional[List[PlanStep]] = None
    clarification_question: Optional[str] = None
    give_up: bool = False
    message: Optional[str] = None


class AgentLoop:
    """Main agent loop implementing a lightweight Plan-and-Execute + ReAct flow."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: Optional[ToolRegistry] = None,
        memory_store: Optional["ConversationMemory"] = None,
        max_iterations: int = 8,
    ):
        self.llm_client = llm_client
        self.tool_registry = tool_registry or ToolRegistry()
        self.memory = memory_store or get_memory_store()
        self.max_iterations = max_iterations

    async def run(self, user_query: str, session_id: str, dataset_path: str) -> AgentResponse:
        """Execute the agent loop for a user query."""
        session = self.memory.get_session(session_id)
        if not session:
            schema = {"columns": {}, "dtypes": {}, "file_path": dataset_path}
            session = self.memory.create_session(session_id, schema)

        session_context = SessionContext(
            session_id=session_id,
            dataset_path=dataset_path,
            working_dataset_path=session.working_dataset_ref,
        )

        intent = await IntentExtractor(self.llm_client).extract_intent(
            user_query=user_query,
            schema_json=session.dataset_schema,
            conversation_history=self.memory.get_conversation_history(session_id),
            session_id=session_id,
        )
        self.memory.update_active_filters(session_id, intent.filters)
        self.memory.add_message(session_id, "user", user_query, intent_object=intent)

        if intent.confidence < 0.6 or intent.ambiguities:
            question = (
                f"I need clarification: {', '.join(intent.ambiguities)}"
                if intent.ambiguities
                else "I need clarification before proceeding."
            )
            return AgentResponse(
                narrative=question,
                charts=[],
                tables=[],
                model_results=[],
                explanation="Clarification requested due to low-confidence intent extraction.",
                clarification={
                    "type": "clarification",
                    "question": question,
                    "options": None,
                    "session_id": session_id,
                },
                active_filters=[
                    item.model_dump() if hasattr(item, "model_dump") else item.dict()
                    for item in self.memory.get_active_filters(session_id)
                ],
            )

        plan = await self._generate_plan(user_query, session)
        execution_results = await self._execute_plan(plan, session_context, user_query, session)
        final_response = await self._generate_final_response(user_query, execution_results)
        final_response.steps = execution_results
        final_response.active_filters = [
            item.model_dump() if hasattr(item, "model_dump") else item.dict()
            for item in self.memory.get_active_filters(session_id)
        ]

        clarification_step = next(
            (
                item.get("result")
                for item in execution_results
                if item.get("tool") == "ask_clarification" and isinstance(item.get("result"), dict)
            ),
            None,
        )
        final_response.clarification = clarification_step

        self.memory.add_message(
            session_id,
            "assistant",
            final_response.narrative,
            tool_results=execution_results,
        )
        return final_response

    async def _generate_plan(self, user_query: str, session) -> AgentPlan:
        """Generate and validate an execution plan using the planning prompt."""
        plan_prompt = self._render_prompt(
            "plan.j2",
            user_query=user_query,
            schema_json=session.dataset_schema,
            row_count=session.dataset_schema.get("rows", 0),
            col_count=len(session.dataset_schema.get("columns", {}))
            if isinstance(session.dataset_schema.get("columns", {}), dict)
            else len(session.dataset_schema.get("columns", [])),
            session_id=session.session_id,
            tool_descriptions=self.tool_registry.get_tool_descriptions_for_llm(),
            conversation_history=self.memory.get_conversation_history(session.session_id),
        )

        raw_plan = await self.llm_client.generate_json(plan_prompt, max_tokens=1024)
        return AgentPlan(**raw_plan)

    async def _execute_plan(
        self,
        plan: AgentPlan,
        session: SessionContext,
        user_query: str,
        memory_session,
    ) -> List[Dict[str, Any]]:
        """Execute plan steps and observe outcomes after each tool call."""
        results: List[Dict[str, Any]] = []
        steps = list(plan.steps)
        iterations = 0

        while steps and iterations < self.max_iterations:
            step = steps.pop(0)
            iterations += 1

            result = await self.tool_registry.call_tool(step.tool, step.params, session)
            result_entry = {
                "step": step.step,
                "tool": step.tool,
                "params": step.params,
                "purpose": step.purpose,
                "result": result.data,
                "display": result.display,
                "success": result.success,
                "error_message": result.error_message,
            }
            results.append(result_entry)

            if step.tool == "filter_dataset" and result.success:
                dataset_ref = result.data.get("dataset_ref")
                if dataset_ref:
                    session.working_dataset_path = dataset_ref
                    self.memory.set_working_dataset_ref(session.session_id, dataset_ref)

            if step.tool == "ask_clarification":
                break

            decision = await self._observe_step(step, result_entry, steps)
            if decision.decision == "done":
                break

            if decision.decision == "reflect":
                reflection = await self._reflect_step(step, decision.reason or "Tool result was unsatisfactory.", user_query, memory_session)
                if reflection.clarification_question:
                    clarification_result = await self.tool_registry.call_tool(
                        "ask_clarification",
                        {"question": reflection.clarification_question, "options": None},
                        session,
                    )
                    results.append(
                        {
                            "step": step.step + 1,
                            "tool": "ask_clarification",
                            "params": {"question": reflection.clarification_question, "options": None},
                            "purpose": "Clarify missing information before continuing.",
                            "result": clarification_result.data,
                            "display": clarification_result.display,
                            "success": clarification_result.success,
                            "error_message": clarification_result.error_message,
                        }
                    )
                    break

                if reflection.revised_plan:
                    steps = list(reflection.revised_plan) + steps
                    continue

                if reflection.give_up:
                    results.append(
                        {
                            "step": step.step + 1,
                            "tool": "agent_reflection",
                            "params": {},
                            "purpose": "Stop execution because recovery was not possible.",
                            "result": {"message": reflection.message or "Unable to recover from tool failure."},
                            "display": None,
                            "success": False,
                            "error_message": reflection.message or "Unable to recover from tool failure.",
                        }
                    )
                    break

        return results

    async def _observe_step(
        self,
        step: PlanStep,
        result_entry: Dict[str, Any],
        remaining_steps: List[PlanStep],
    ) -> ObserveDecision:
        """Ask the LLM whether to continue, reflect, or stop."""
        if not result_entry["success"]:
            return ObserveDecision(decision="reflect", reason=result_entry.get("error_message") or "Tool execution failed")

        prompt = self._render_prompt(
            "observe.j2",
            tool_name=step.tool,
            tool_result_json=json.dumps(result_entry["result"], default=str),
            remaining_steps=json.dumps([item.model_dump() for item in remaining_steps], default=str),
        )
        try:
            decision = await self.llm_client.generate_json(prompt, max_tokens=256)
            return ObserveDecision(**decision)
        except Exception:
            return ObserveDecision(decision="continue")

    async def _reflect_step(
        self,
        failed_step: PlanStep,
        failure_reason: str,
        user_query: str,
        session,
    ) -> ReflectResponse:
        """Recover from a failed or poor-quality step."""
        prompt = self._render_prompt(
            "reflect.j2",
            failed_step_json=json.dumps(failed_step.model_dump(), default=str),
            failure_reason=failure_reason,
            user_query=user_query,
            schema_json=session.dataset_schema,
        )
        try:
            reflection = await self.llm_client.generate_json(prompt, max_tokens=512)
            return ReflectResponse(**reflection)
        except Exception:
            return ReflectResponse(give_up=True, message=failure_reason)

    async def _generate_final_response(
        self,
        user_query: str,
        execution_results: List[Dict[str, Any]],
    ) -> AgentResponse:
        """Generate the final narrative plus display artifacts."""
        charts: List[Dict[str, Any]] = []
        tables: List[Dict[str, Any]] = []
        narratives: List[str] = []
        model_results: List[Dict[str, Any]] = []

        for entry in execution_results:
            display = entry.get("display")
            if not display:
                continue

            display_items = display if isinstance(display, list) else [display]
            for item in display_items:
                if isinstance(item, ChartSpec):
                    charts.append(item.data)
                elif isinstance(item, TableSpec):
                    tables.append({"columns": item.columns, "data": item.data, "title": item.title})
                elif isinstance(item, NarrativeSpec):
                    narratives.append(item.content)

            if entry["tool"] in {"train_classifier", "train_regressor", "explain_model_global", "explain_prediction_local", "explain_counterfactual", "counterfactual_explainer"}:
                model_results.append(entry["result"])

        prompt = self._render_prompt(
            "synthesize.j2",
            user_query=user_query,
            all_results_json=json.dumps(
                [{"tool": item["tool"], "result": item["result"]} for item in execution_results],
                default=str,
            ),
            chart_summaries=json.dumps([item.get("title", "Chart") for item in charts], default=str),
        )

        try:
            narrative = await self.llm_client.generate_text(prompt, max_tokens=256)
        except Exception:
            narrative = " ".join(narratives).strip() or "Analysis completed."

        return AgentResponse(
            narrative=narrative.strip() or "Analysis completed.",
            charts=charts,
            tables=tables,
            model_results=model_results,
            explanation="Agentic plan executed successfully.",
        )

    def _render_prompt(self, template_name: str, **context: Any) -> str:
        """Render a Jinja2 prompt template from the prompts directory."""
        template_path = Path(__file__).resolve().parents[2] / "prompts" / template_name
        with template_path.open("r", encoding="utf-8") as handle:
            template = Template(handle.read())
        return template.render(**context)
