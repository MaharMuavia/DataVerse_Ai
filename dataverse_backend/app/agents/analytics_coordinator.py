"""Analytics coordinator orchestrates the complete analytics workflow.

This module coordinates:
1. Planning (decision on which tasks to run)
2. EDA (exploratory data analysis)
3. Visualization (plot generation)
4. AutoML (predictive modeling)
5. XAI (explainability)

Execution follows: NL → Plan → Tools → Results → Explanation (via LLM)
"""
from __future__ import annotations

from typing import Dict, Any, Optional
import json

from ..core.logger import logger
from ..agents.planning_agent import PlanningAgent
from ..agents.eda_analytics_agent import EDAAgent
from ..agents.visualization_agent import VisualizationAgent
from ..agents.automl_agent import AutoMLAgent
from ..agents.xai_agent import XAIAgent, LIMEAgent
from ..data.data_manager import DataManager


class AnalyticsCoordinator:
    """Orchestrates autonomous analytics workflow.

    Coordinates planning, execution, and result synthesis for:
    - Automated data profiling (EDA)
    - Visualization generation
    - Machine learning (AutoML)
    - Model explanation (SHAP/LIME)

    All computational results are deterministic and passed to LLM
    only for narrative explanation.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = logger.getChild(self.__class__.__name__)

    def execute_analytics_workflow(self, user_query: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete analytics workflow based on user query.

        Flow:
        1. Load dataset and extract info
        2. Create execution plan
        3. Run EDA
        4. Generate visualizations
        5. Train AutoML models (if applicable)
        6. Compute explanations (if applicable)
        7. Synthesize results

        Args:
            user_query: Original user query
            intent: Parsed intent from IntentParser

        Returns:
            Dict with all analytics results
        """
        # Step 1: Load dataset
        try:
            dm = DataManager(session_id=self.session_id)
            df = dm.get_raw()
            dataset_info = self._extract_dataset_info(df)
        except Exception as e:
            self.logger.error(f"Failed to load dataset: {e}")
            return {"error": str(e), "status": "failed"}

        # Step 2: Create plan
        planner = PlanningAgent(session_id=self.session_id)
        plan = planner.create_plan(user_query, intent, dataset_info)

        analytics_results = {
            "session_id": self.session_id,
            "user_query": user_query,
            "intent": intent,
            "plan": plan,
            "results": {},
        }

        # Step 3-6: Execute tasks in order
        execution_context = {
            "df": df,
            "model": None,
            "X_data": None,
            "y_data": None,
        }

        for task in plan.get("tasks", []):
            task_type = task.get("task_type")

            try:
                if task_type == "eda":
                    result = self._execute_eda(task)
                    analytics_results["results"]["eda"] = result

                elif task_type == "visualization":
                    result = self._execute_visualization(task)
                    if "visualizations" not in analytics_results["results"]:
                        analytics_results["results"]["visualizations"] = []
                    analytics_results["results"]["visualizations"].append(result)

                elif task_type == "automl":
                    result = self._execute_automl(task, execution_context)
                    analytics_results["results"]["automl"] = result

                elif task_type == "xai":
                    if execution_context["model"] is not None:
                        result = self._execute_xai(execution_context)
                        analytics_results["results"]["xai"] = result

            except Exception as e:
                self.logger.exception(f"Task {task_type} failed: {e}")
                analytics_results["results"][task_type] = {"error": str(e), "status": "failed"}

        analytics_results["status"] = "completed"
        self.logger.info("Analytics workflow completed", extra={"session_id": self.session_id})

        return analytics_results

    def _extract_dataset_info(self, df) -> Dict[str, Any]:
        """Extract basic dataset information."""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        return {
            "rows": len(df),
            "columns": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
        }

    def _execute_eda(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute EDA task."""
        self.logger.info("Executing EDA task")
        eda = EDAAgent(session_id=self.session_id)
        return eda.run()

    def _execute_visualization(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute visualization task."""
        params = task.get("parameters", {})
        viz_type = params.get("viz_type")

        self.logger.info(f"Executing visualization task: {viz_type}")

        viz_agent = VisualizationAgent(session_id=self.session_id)
        return viz_agent.run(
            viz_type=viz_type,
            target_column=params.get("target_column"),
            numeric_cols=params.get("numeric_cols"),
            categorical_cols=params.get("categorical_cols"),
        )

    def _execute_automl(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AutoML task."""
        params = task.get("parameters", {})
        task_type = params.get("task_type")
        target_column = params.get("target_column")

        if not target_column:
            return {"error": "No target column specified", "status": "failed"}

        self.logger.info(f"Executing AutoML task: {task_type} on {target_column}")

        automl = AutoMLAgent(session_id=self.session_id)
        result = automl.run(task_type=task_type, target_column=target_column)

        # Store model in context for XAI
        if result.get("status") == "success" and automl.model is not None:
            context["model"] = automl.model
            dm = DataManager(session_id=self.session_id)
            df = dm.get_raw()
            context["X_data"] = df.drop(columns=[target_column], errors='ignore')
            context["y_data"] = df[target_column]

        return result

    def _execute_xai(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute XAI task."""
        if context["model"] is None or context["X_data"] is None:
            return {"error": "No trained model available for explanation", "status": "failed"}

        self.logger.info("Executing XAI task (SHAP)")

        xai = XAIAgent(session_id=self.session_id)
        result = xai.run(
            model=context["model"],
            X_data=context["X_data"],
            y_true=context.get("y_data"),
            sample_size=100,
        )

        if result.get("status") != "success":
            self.logger.warning("SHAP XAI failed, falling back to LIME", extra={"session_id": self.session_id, "error": result.get("error")})
            lime_agent = LIMEAgent(session_id=self.session_id)
            result = lime_agent.run(
                model=context["model"],
                X_data=context["X_data"],
                num_features=10,
            )
            result["fallback_used"] = "lime"

        return result
