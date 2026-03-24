"""Planning agent for autonomous analytics workflow orchestration.

This agent parses user intent and creates an executable plan that decides:
- Whether to run automated EDA
- Whether to generate visualizations (and which types)
- Whether to run AutoML prediction tasks
- Whether to compute explainability (SHAP/LIME)

The planning agent is driven by the parsed intent from the user query and
the characteristics of the dataset, ensuring deterministic planning.
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional

from ..core.logger import logger
from ..llm.intent_parser import IntentParser


class PlanningAgent:
    """Orchestrates analytics tasks based on user intent.

    This agent determines the sequence of tools to execute by analyzing:
    1. User intent (parsed by IntentParser)
    2. Available operations (EDA, viz, prediction, XAI)
    3. Dataset characteristics (inferred from metadata)
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = logger.getChild(self.__class__.__name__)

    def create_plan(self, user_query: str, intent: Dict[str, Any], dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create an execution plan for analytics tasks.

        Args:
            user_query: Original user query text
            intent: Parsed intent from IntentParser (contains intent, metric, operations)
            dataset_info: Dataset metadata (columns, dtypes, row_count)

        Returns:
            Dict containing plan with tasks, reasoning, and execution order
        """
        plan = {
            "session_id": self.session_id,
            "user_query": user_query,
            "parsed_intent": intent,
            "tasks": [],
            "reasoning": "",
            "execution_order": [],
        }

        # Determine if EDA should run
        if self._should_run_eda(intent):
            plan["tasks"].append({
                "task_type": "eda",
                "tool": "ydata_profiling",
                "priority": 1,
                "parameters": {
                    "minimal": False,
                    "correlation_threshold": 0.7,
                    "missing_threshold": 0.5,
                }
            })

        # Determine visualization tasks
        viz_tasks = self._determine_visualizations(intent, dataset_info)
        for viz in viz_tasks:
            plan["tasks"].append(viz)

        # Determine if AutoML prediction task should run
        if self._should_run_automl(intent, dataset_info):
            plan["tasks"].append({
                "task_type": "automl",
                "tool": "pycaret",
                "priority": 2,
                "parameters": {
                    "target_column": self._infer_target_column(intent, dataset_info),
                    "task_type": self._determine_ml_task_type(intent, dataset_info),
                    "time_budget": 300,
                    "html": False,
                }
            })

        # Determine if explainability should be computed
        if self._should_run_xai(intent, plan):
            plan["tasks"].append({
                "task_type": "xai",
                "tool": "shap",
                "priority": 3,
                "parameters": {
                    "method": "tree",
                    "sample_size": 100,
                    "background_size": 50,
                }
            })

        # Sort tasks by priority and build execution order
        plan["tasks"].sort(key=lambda t: t.get("priority", 999))
        plan["execution_order"] = [t["task_type"] for t in plan["tasks"]]
        plan["reasoning"] = self._generate_reasoning(plan, intent)

        self.logger.info(
            "Plan created",
            extra={
                "session_id": self.session_id,
                "tasks": plan["execution_order"],
                "user_intent": intent.get("intent"),
            }
        )

        return plan

    def _should_run_eda(self, intent: Dict[str, Any]) -> bool:
        """Determine if EDA is needed based on intent.

        EDA is always run unless intent explicitly focuses only on a specific task.
        """
        operations = intent.get("operations", [])
        intent_text = intent.get("intent", "").lower()

        # Run EDA if user asks for general analysis, summary, or overview
        if any(kw in intent_text for kw in ["summary", "overview", "explore", "analyze", "understand", "profile"]):
            return True

        # Run EDA if no specific operations are defined
        if not operations or len(operations) == 0:
            return True

        # Do not skip EDA if visualization or prediction is requested (provide context)
        return True

    def _determine_visualizations(self, intent: Dict[str, Any], dataset_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Determine which visualizations to create.

        Visualization type is selected based on:
        - User intent (keywords in query)
        - Data types in dataset
        - Operations specified
        """
        viz_tasks = []
        intent_text = intent.get("intent", "").lower()
        dtypes = dataset_info.get("dtypes", {})
        metric = intent.get("metric")

        # Count numeric vs categorical columns
        numeric_cols = [c for c, t in dtypes.items() if "int" in t or "float" in t]
        categorical_cols = [c for c, t in dtypes.items() if "object" in t or "category" in t]

        # Determine visualization types based on intent and data
        viz_types = self._select_viz_types(intent_text, len(numeric_cols), len(categorical_cols), metric)

        priority = 1
        for viz_type in viz_types:
            viz_tasks.append({
                "task_type": "visualization",
                "tool": "matplotlib_seaborn",
                "priority": priority,
                "parameters": {
                    "viz_type": viz_type,
                    "target_column": metric,
                    "numeric_cols": numeric_cols[:3],  # Limit to 3 for clarity
                    "categorical_cols": categorical_cols[:3],
                }
            })
            priority += 1

        return viz_tasks

    def _select_viz_types(self, intent_text: str, n_numeric: int, n_categorical: int, metric: Optional[str]) -> List[str]:
        """Select visualization types based on intent and data characteristics."""
        viz_types = []

        # Distribution analysis
        if any(kw in intent_text for kw in ["distribution", "histogram", "frequency", "spread"]):
            if n_numeric > 0:
                viz_types.append("histogram")
        elif n_numeric > 0:
            viz_types.append("histogram")  # Default for numeric data

        # Correlation analysis
        if any(kw in intent_text for kw in ["correlation", "relationship", "correlated"]):
            if n_numeric >= 2:
                viz_types.append("heatmap")
        elif n_numeric >= 2 and metric is None:
            viz_types.append("heatmap")  # Default if multiple numeric columns

        # Categorical analysis
        if any(kw in intent_text for kw in ["category", "group", "segment", "distribution"]):
            if n_categorical > 0:
                viz_types.append("bar_chart")
        elif n_categorical > 0 and metric is None:
            viz_types.append("bar_chart")

        # Comparison/outlier analysis
        if any(kw in intent_text for kw in ["outlier", "anomaly", "comparison", "range"]):
            if n_numeric > 0:
                viz_types.append("boxplot")
        elif n_numeric > 1:
            viz_types.append("scatter")

        # Ensure at least one visualization is selected
        if not viz_types:
            if n_numeric > 0:
                viz_types.append("histogram")
            elif n_categorical > 0:
                viz_types.append("bar_chart")

        return list(dict.fromkeys(viz_types))  # Remove duplicates, preserve order

    def _should_run_automl(self, intent: Dict[str, Any], dataset_info: Dict[str, Any]) -> bool:
        """Determine if AutoML prediction task should run.

        AutoML runs if:
        - User asks for prediction/forecast/classification/regression
        - A target column can be inferred
        """
        intent_text = intent.get("intent", "").lower()
        metric = intent.get("metric")

        # Check for prediction keywords
        prediction_keywords = ["predict", "forecast", "model", "classify", "regress", "estimate", "target"]
        has_prediction_intent = any(kw in intent_text for kw in prediction_keywords)

        # Check if we can infer a target variable
        has_inferred_target = metric is not None

        return has_prediction_intent or has_inferred_target

    def _determine_ml_task_type(self, intent: Dict[str, Any], dataset_info: Dict[str, Any]) -> str:
        """Determine ML task type (classification vs regression).

        Heuristics:
        - If target column is numeric: regression
        - If target column is categorical: classification
        - If no target inferred: regression (default)
        """
        intent_text = intent.get("intent", "").lower()

        # Check for explicit classification keywords
        if any(kw in intent_text for kw in ["classify", "classification", "category", "class"]):
            return "classification"

        # Check for explicit regression keywords
        if any(kw in intent_text for kw in ["regress", "regression", "predict value", "estimate value"]):
            return "regression"

        # Default to regression for generic "predict"
        return "regression"

    def _infer_target_column(self, intent: Dict[str, Any], dataset_info: Dict[str, Any]) -> Optional[str]:
        """Infer target column for ML task.

        Returns:
        - The metric specified in intent if available
        - None if no target can be inferred
        """
        metric = intent.get("metric")
        if metric:
            columns = dataset_info.get("columns", [])
            if metric in columns:
                return metric
        return None

    def _should_run_xai(self, intent: Dict[str, Any], plan: Dict[str, Any]) -> bool:
        """Determine if explainability analysis should run.

        XAI runs if:
        - An AutoML task is planned
        - User asks for explanations/insights/reasons
        """
        intent_text = intent.get("intent", "").lower()
        has_automl = any(t["task_type"] == "automl" for t in plan.get("tasks", []))

        # Check for explainability keywords
        xai_keywords = ["explain", "why", "reason", "important", "feature importance", "what drives", "impact"]
        has_xai_intent = any(kw in intent_text for kw in xai_keywords)

        return has_automl and has_xai_intent

    def _generate_reasoning(self, plan: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """Generate natural language reasoning for the plan.

        This reasoning is logged for auditability and can be used by
        the explanation agent to contextualize results.
        """
        tasks = plan.get("tasks", [])
        task_names = [t["task_type"] for t in tasks]

        reasoning_parts = []

        if "eda" in task_names:
            reasoning_parts.append("Automated EDA will profile the dataset for distributions, missing values, and correlations.")

        if "visualization" in task_names:
            reasoning_parts.append("Visualizations will be generated to illustrate key patterns and distributions.")

        if "automl" in task_names:
            reasoning_parts.append("Machine learning model will be trained to make predictions on the target variable.")

        if "xai" in task_names:
            reasoning_parts.append("Feature importance and SHAP explanations will be computed to understand model decisions.")

        reasoning = " ".join(reasoning_parts) if reasoning_parts else "General data exploration plan."

        return reasoning
