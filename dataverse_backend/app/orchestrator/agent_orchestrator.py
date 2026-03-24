"""Agent orchestrator coordinates agent execution and session orchestration.

Responsibilities:
- Decide which agents must run and in what order
- Ensure EDA & preprocessing run only once per session
- Maintain execution trace in session state
- For queries: parse intent via OpenAI, run analysis, call DeepAnalyze for interpretation
"""
from __future__ import annotations

from typing import Dict, Any, Optional

from ..core.logger import logger
from ..core.exceptions import DataNotFoundError, AgentError
from ..state.session_state import SessionState
from ..agents.ingestion_agent import IngestionAgent
from ..agents.eda_agent import EDAAgent
from ..agents.preprocessing_agent import PreprocessingAgent
from ..agents.analysis_agent import AnalysisAgent
from ..agents.deepanalyze_agent import DeepAnalyzeAgent
from ..agents.analytics_coordinator import AnalyticsCoordinator
from ..llm.intent_parser import IntentParser
from ..data.data_manager import DataManager
from ..db.repositories import log_agent_run, save_analysis_result, save_report, log_user_query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool


class AgentOrchestrator:
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)

    def _ensure_dataset_present(self, session_id: str) -> None:
        # Simple check: raw dataset must exist
        try:
            dm = DataManager(session_id=session_id)
            _ = dm.get_raw()
        except Exception:
            self.logger.error("Dataset not found for session %s", session_id)
            raise DataNotFoundError("Dataset not uploaded for session")

    async def _run_once(self, session_id: str, db: Optional[AsyncSession] = None) -> None:
        """Ensure ingestion, EDA, and preprocessing are executed once per session.

        This async variant runs any blocking agent.run() calls in a threadpool to
        avoid blocking the event loop. After each agent completes, an agent run
        record is persisted for auditability if a DB session is provided.
        """
        state = SessionState.get(session_id)

        # Ingestion & profile
        if not state.get_value("profile"):
            ing = IngestionAgent(session_id=session_id)
            await run_in_threadpool(ing.run)
            self._append_trace(session_id, "ingestion_completed")
            if db is not None:
                await log_agent_run(db, agent_name="IngestionAgent", action="ingestion_completed", reasoning=None, dataset_id=state.get_value("dataset_id"))

        # EDA
        if not state.get_value("eda_completed"):
            eda = EDAAgent(session_id=session_id)
            await run_in_threadpool(eda.run)
            self._append_trace(session_id, "eda_completed")
            if db is not None:
                await log_agent_run(db, agent_name="EDAAgent", action="eda_completed", reasoning=None, dataset_id=state.get_value("dataset_id"))

        # Preprocessing
        if not state.get_value("preprocessing_completed"):
            prep = PreprocessingAgent(session_id=session_id)
            await run_in_threadpool(prep.run)
            self._append_trace(session_id, "preprocessing_completed")
            if db is not None:
                await log_agent_run(db, agent_name="PreprocessingAgent", action="preprocessing_completed", reasoning=None, dataset_id=state.get_value("dataset_id"))

    def _append_trace(self, session_id: str, entry: str) -> None:
        state = SessionState.get(session_id)
        trace = state.get_value("execution_trace", [])
        trace.append(entry)
        state.set("execution_trace", trace)

    async def handle_query(self, session_id: str, user_query: str, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        # Validate dataset
        self._ensure_dataset_present(session_id)

        # Run pipeline once (ingestion, EDA, preprocessing) and persist agent runs
        await self._run_once(session_id, db=db)

        # Check retail dataset flag for user guidance
        state = SessionState.get(session_id)
        if state and not state.get_value("dataset_is_retail", True):
            self.logger.warning("Query executed on non-retail dataset", extra={"session_id": session_id})

        # Parse intent
        intent = IntentParser.parse(user_query)
        self.logger.info("Intent parsed", extra={"session_id": session_id, "intent": intent})

        # Persist the parsed intent into the earlier logged user query record if DB available.
        try:
            state = SessionState.get(session_id)
            dataset_id = state.get_value("dataset_id")
            if db is not None:
                await log_user_query(db, query_text=user_query, parsed_intent=intent, dataset_id=dataset_id)
        except Exception:
            self.logger.exception("Failed to persist parsed intent")

        # Execute analytics workflow (EDA, visualization, AutoML, XAI)
        analytics_coordinator = AnalyticsCoordinator(session_id=session_id)
        analytics_result = await run_in_threadpool(analytics_coordinator.execute_analytics_workflow, user_query, intent)

        # Store analytics results in session state for later reference
        state = SessionState.get(session_id)
        state.set("analytics_result", analytics_result)

        # If analytics workflow completed successfully, also run legacy analysis pipeline for compatibility
        legacy_computed = None
        try:
            analysis_agent = AnalysisAgent(session_id=session_id)
            legacy_computed = await run_in_threadpool(analysis_agent.run, intent)
        except Exception:
            self.logger.warning("Legacy analysis pipeline failed, continuing with analytics results")

        # Use analytics results as primary output, fallback to legacy if needed
        if analytics_result.get("status") == "completed":
            # Synthesize report from analytics results
            report = self._synthesize_analytics_report(analytics_result, intent, legacy_computed)

            # Persist analytics results
            analysis_record = None
            try:
                if db is not None:
                    dataset_id = state.get_value("dataset_id")
                    analysis_record = await save_analysis_result(db, dataset_id=dataset_id, computed_metrics=analytics_result.get("results", {}))
            except Exception:
                self.logger.exception("Failed to persist analytics result")

            try:
                if db is not None and analysis_record is not None:
                    await save_report(db, analysis_result_id=str(analysis_record.id), report_text=report, model_used="analytics_suite")
            except Exception:
                self.logger.exception("Failed to persist analytics report")

            return {"intent": intent, "computed_facts": analytics_result.get("results", {}), "report": report, "analytics": True}

        # Fallback to legacy analysis pipeline
        if legacy_computed and not legacy_computed.get("error"):
            analysis_record = None
            try:
                if db is not None:
                    dataset_id = state.get_value("dataset_id")
                    analysis_record = await save_analysis_result(db, dataset_id=dataset_id, computed_metrics=legacy_computed)
            except Exception:
                self.logger.exception("Failed to persist legacy analysis result")

            # Use DeepAnalyze to interpret computed facts
            deep_agent = DeepAnalyzeAgent(session_id=session_id)
            da_result = await run_in_threadpool(deep_agent.run, legacy_computed)

            if da_result.get("status") == "unavailable":
                self.logger.warning("Reasoning model unavailable; returning Pandas-only summary")
                report_obj = self._pandas_only_report(legacy_computed)
                import json
                report = json.dumps({"warning": "Reasoning model unavailable", **report_obj})
                try:
                    if db is not None and analysis_record is not None:
                        await save_report(db, analysis_result_id=str(analysis_record.id), report_text=report, model_used="fallback")
                except Exception:
                    self.logger.exception("Failed to persist fallback report")
                return {"intent": intent, "computed_facts": legacy_computed, "report": report}

            report = da_result.get("report")
            model_used = da_result.get("model", "DeepAnalyze")
            if isinstance(report, dict):
                import json
                report_text = json.dumps(report)
            else:
                report_text = str(report)

            try:
                if db is not None and analysis_record is not None:
                    await save_report(db, analysis_result_id=str(analysis_record.id), report_text=report_text, model_used=model_used)
            except Exception:
                self.logger.exception("Failed to persist final report")

            return {"intent": intent, "computed_facts": legacy_computed, "report": report_text}

        # Both workflows failed
        return {"intent": intent, "error": "Analytics and analysis pipelines both failed", "status": "failed"}

    def _synthesize_analytics_report(self, analytics_result: Dict[str, Any], intent: Dict[str, Any], legacy_result: Optional[Dict[str, Any]] = None) -> str:
        """Synthesize a narrative report from analytics workflow results.

        Combines EDA, visualization, AutoML, and XAI results into a
        coherent narrative explanation.
        """
        import json

        report_parts = []
        results = analytics_result.get("results", {})

        # EDA summary
        if "eda" in results and results["eda"].get("status") != "failed":
            eda = results["eda"]
            report_parts.append(f"Dataset Profile: {eda.get('dataset_shape', {}).get('rows')} rows, {eda.get('dataset_shape', {}).get('columns')} columns.")

            missing = eda.get("missing_values", {}).get("total_missing", 0)
            if missing > 0:
                report_parts.append(f"Missing values detected: {missing} instances.")

            outliers = eda.get("outliers", {}).get("total_outlier_instances", 0)
            if outliers > 0:
                report_parts.append(f"Outliers detected: {outliers} instances using IQR method.")

        # Visualization summary
        if "visualizations" in results and results["visualizations"]:
            viz_types = [v.get("viz_type", "unknown") for v in results["visualizations"] if v.get("status") != "failed"]
            report_parts.append(f"Generated visualizations: {', '.join(viz_types)}.")

        # AutoML summary
        if "automl" in results and results["automl"].get("status") == "success":
            automl = results["automl"]
            report_parts.append(f"Trained {automl.get('task_type')} model: {automl.get('best_model')}.")

            metrics = automl.get("metrics", {})
            if automl.get("task_type") == "classification" and "accuracy" in metrics:
                report_parts.append(f"Model accuracy: {metrics['accuracy']:.3f}.")
            elif automl.get("task_type") == "regression" and "rmse" in metrics:
                report_parts.append(f"Model RMSE: {metrics['rmse']:.3f}.")

        # XAI summary
        if "xai" in results and results["xai"].get("status") == "success":
            xai = results["xai"]
            top_features = xai.get("top_features", [])[:3]
            if top_features:
                report_parts.append(f"Top predictive features: {', '.join(top_features)}.")

        narrative = " ".join(report_parts) if report_parts else "Analytics workflow completed."

        return json.dumps({
            "narrative": narrative,
            "workflow": "automated_analytics",
            "eda_completed": "eda" in results,
            "visualizations_generated": len(results.get("visualizations", [])),
            "model_trained": "automl" in results and results["automl"].get("status") == "success",
            "explanations_computed": "xai" in results and results["xai"].get("status") == "success",
        })


    def _pandas_only_report(self, computed: Dict[str, Any]) -> Dict[str, Any]:
        """Create a conservative, human-readable report using only computed facts.

        This ensures the system provides business-friendly output even when the reasoning
        model is unavailable. No sensitive data or raw frames are passed to any model.
        """
        exec_summary = "Computed facts are provided; reasoning model was unavailable."
        insights = []
        actions = []
        assumptions = ["Report generated from computed aggregation results (no external reasoning model used)."]

        # Populate with whatever computed facts we have
        tp = computed.get("top_product")
        tmv = computed.get("top_metric_value")
        total = computed.get("total_metric_value")
        share = computed.get("revenue_share_percent")
        metric = computed.get("metric")
        timeframe = computed.get("time_period") or computed.get("intent", {}).get("time_filter")

        if tp:
            exec_summary = f"Top performer during the period was {tp} with {tmv} {metric} ({share}% share)."
            insights.append(f"Top performer: {tp} contributing {share}% of {metric}.")
            actions.append(f"Consider prioritizing stock and promotions for {tp}.")
        elif total:
            exec_summary = f"Total {metric} in the period: {total}."
            insights.append(f"Total {metric}: {total}.")

        if timeframe:
            insights.append(f"Timeframe applied: {timeframe}.")

        return {"executive_summary": exec_summary, "key_insights": insights, "actions": actions, "assumptions": assumptions}
