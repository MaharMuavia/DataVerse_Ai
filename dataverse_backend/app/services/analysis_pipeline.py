"""Clean deterministic AI data analyst pipeline."""
from __future__ import annotations

from typing import Any

import pandas as pd

from .data_profiler import profile_dataframe
from .ai_khata import AI_KHATA_TYPES, business_summary, monthly_sales_revenue
from .business_metrics import answer_business_query, build_kpi_cards, calculate_business_metrics, compute_product_trends
from .progress_bus import progress_bus
from .data_quality import (
    build_chart_specs,
    compute_correlations,
    compute_data_quality,
    compute_eda,
    compute_outliers,
    compute_trends,
    json_safe,
    normalize_chart_specs,
)
from .modeling import train_prediction
from .query_planner import QueryPlanner
from .report_narrator import ReportNarrator
from .semantic_mapper import SemanticMapper
from .session_store import create_session_id, persist_dataframe_for_session
from .xai import explain_model

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False



class AnalysisPipeline:
    """Run profile, quality, EDA, trends, prediction, XAI, charts, and narration."""

    def __init__(self, narrator: ReportNarrator | None = None):
        self.narrator = narrator or ReportNarrator()

    def run_full_analysis(
        self,
        df: pd.DataFrame,
        query: str | None = None,
        target_column: str | None = None,
        task_type: str | None = None,
        run_predictions: bool = True,
        run_xai: bool = True,
        session_id: str | None = None,
        filename: str | None = None,
        use_llm: bool = True,
        provider: str | None = None,
        semantic_map: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        semantic_map = semantic_map or SemanticMapper().map_dataframe(df, filename=filename, query=query)
        query_plan = QueryPlanner().plan(query or "dataset overview", semantic_map, None)
        facts = self._compute(
            df,
            query=query,
            target_column=target_column,
            task_type=task_type,
            run_predictions=run_predictions,
            run_xai=run_xai,
            session_id=session_id,
            filename=filename,
            semantic_map=semantic_map,
            query_plan=query_plan,
        )
        narration = self.narrator.narrate(facts, use_llm=use_llm, provider=provider)
        return self._merge_narration(facts, narration)

    async def run_full_analysis_async(
        self,
        df: pd.DataFrame,
        query: str | None = None,
        target_column: str | None = None,
        task_type: str | None = None,
        run_predictions: bool = True,
        run_xai: bool = True,
        session_id: str | None = None,
        filename: str | None = None,
        use_llm: bool = True,
        provider: str | None = None,
        semantic_map: dict[str, Any] | None = None,
        progress_session_id: str | None = None,
    ) -> dict[str, Any]:
        semantic_map = semantic_map or await SemanticMapper().map_dataframe_async(df, filename=filename, query=query)
        query_plan = await QueryPlanner().plan_async(query or "dataset overview", semantic_map, None)
        facts = self._compute(
            df,
            query=query,
            target_column=target_column,
            task_type=task_type,
            run_predictions=run_predictions,
            run_xai=run_xai,
            session_id=session_id,
            filename=filename,
            semantic_map=semantic_map,
            query_plan=query_plan,
            progress_session_id=progress_session_id,
        )
        if progress_session_id:
            progress_bus.start_stage(progress_session_id, "narration", "Polishing narration", f"provider: {provider or 'auto'}")
        narration = await self.narrator.narrate_async(facts, use_llm=use_llm, provider=provider)
        if progress_session_id:
            progress_bus.complete_stage(
                progress_session_id,
                "narration",
                f"provider: {narration.get('narration_provider', 'deterministic')}",
            )
        return self._merge_narration(facts, narration)

    def _compute(
        self,
        df: pd.DataFrame,
        *,
        query: str | None,
        target_column: str | None,
        task_type: str | None,
        run_predictions: bool,
        run_xai: bool,
        session_id: str | None,
        filename: str | None,
        semantic_map: dict[str, Any] | None = None,
        query_plan: dict[str, Any] | None = None,
        progress_session_id: str | None = None,
    ) -> dict[str, Any]:
        if df is None or df.empty or len(df.columns) == 0:
            raise ValueError("Dataset is empty or has no columns")
        work = df.copy()

        def _emit_start(stage: str, label: str, detail: str | None = None) -> None:
            if progress_session_id:
                progress_bus.start_stage(progress_session_id, stage, label, detail)

        def _emit_done(stage: str, detail: str | None = None) -> None:
            if progress_session_id:
                progress_bus.complete_stage(progress_session_id, stage, detail)

        _emit_start("metrics", "Computing business metrics")
        dataset_profile = self.profile_dataset(work)
        if filename:
            dataset_profile["filename"] = filename
        semantic_map = semantic_map or SemanticMapper().map_dataframe(work, filename=filename, query=query)
        dataset_profile["semantic_map_dataset_type"] = semantic_map.get("dataset_type")
        query_plan = query_plan or QueryPlanner().plan(query or "dataset overview", semantic_map, dataset_profile)
        business_metrics = calculate_business_metrics(work, semantic_map)
        product_analysis = compute_product_trends(work, semantic_map, business_metrics)
        query_answer = answer_business_query(query_plan, business_metrics)
        food_analysis = _food_catalog_analysis(work, semantic_map)
        if food_analysis:
            product_analysis = _merge_food_analysis(product_analysis, food_analysis)
            query_answer = _food_query_answer(query, food_analysis) or query_answer
        _emit_done("metrics")

        _emit_start("quality", "Scoring data quality")
        data_quality = self.compute_data_quality(work)
        dataset_profile["data_quality_score"] = data_quality.get("data_quality_score")
        if isinstance(dataset_profile.get("quality"), dict):
            dataset_profile["quality"]["score"] = data_quality.get("data_quality_score")
        _emit_done("quality", f"score: {data_quality.get('data_quality_score')}")

        _emit_start("eda", "Running EDA + outliers")
        outliers = self.compute_outliers(work)
        eda = self.compute_eda(work, outliers=outliers)
        eda.setdefault(
            "missing_values",
            {
                "total_missing": data_quality.get("missing_cells", 0),
                "columns": data_quality.get("missing_values_by_column", {}),
            },
        )
        _emit_done("eda", f"{outliers.get('total_outlier_cells', 0)} outlier flags")

        _emit_start("trends", "Detecting trends + correlations")
        trends = self.compute_trends(work)
        correlations = self.compute_correlations(work)
        _emit_done(
            "trends",
            f"{len(trends.get('series', []))} trend series · {len(correlations.get('strong_pairs', []))} strong pairs",
        )

        effective_target, effective_task, effective_run_predictions = _prediction_request(
            df=work,
            query_plan=query_plan,
            query=query,
            target_column=target_column,
            task_type=task_type,
            run_predictions=run_predictions,
        )
        _emit_start(
            "modeling",
            "Training prediction model" if effective_run_predictions else "Checking prediction readiness",
            f"target: {effective_target or 'auto'}",
        )
        prediction, trained_bundle, target_suggestions = self.train_model(
            work,
            query=query,
            target_column=effective_target,
            task_type=effective_task,
            run_predictions=effective_run_predictions,
        )
        _emit_done(
            "modeling",
            f"{prediction.get('selected_model', 'n/a')} · status: {prediction.get('status', 'skipped')}",
        )

        _emit_start("xai", "Computing XAI explanations" if (run_xai and effective_run_predictions) else "Skipping XAI")
        xai = self.run_xai(trained_bundle, prediction, run_xai=run_xai and effective_run_predictions)
        _emit_done("xai", f"top features: {len(xai.get('top_features', []))}")
        report_mode = str(query_plan.get("report_mode") or "focused_answer_report")
        charts = _report_charts_for_query(
            query_plan=query_plan,
            business_metrics=business_metrics,
            product_analysis=product_analysis,
            generic_charts=self.generate_charts(work, trends, correlations, outliers, prediction, xai),
            report_mode=report_mode,
        )
        is_ai_khata = dataset_profile.get("dataset_type") in AI_KHATA_TYPES or semantic_map.get("dataset_type") in AI_KHATA_TYPES
        summary = business_summary(work) if is_ai_khata else {}
        if summary:
            sales_revenue_by_month = monthly_sales_revenue(work, period="M")
            if not sales_revenue_by_month and business_metrics.get("revenue_by_month"):
                sales_revenue_by_month = [
                    {"period": row["period"], "sales_revenue": row["revenue"]}
                    for row in business_metrics.get("revenue_by_month", [])
                ]
            trends["business_revenue_by_month"] = sales_revenue_by_month
            charts.append(
                {
                    "type": "line",
                    "title": "Sales revenue by month",
                    "x_key": "period",
                    "y_key": "sales_revenue",
                    "data": sales_revenue_by_month,
                    "filter": "Category == SALES",
                }
            )
        warnings = list(dict.fromkeys(
            data_quality.get("warnings", [])
            + business_metrics.get("data_limitations", [])
            + food_analysis.get("warnings", [])
            + prediction.get("limitations", [])
            + xai.get("warnings", [])
        ))
        automl_alias = self._legacy_automl_alias(prediction)
        financial_analysis = _financial_dataset_analysis(work)
        return {
            "session_id": session_id,
            "filename": filename,
            "dataset_profile": dataset_profile,
            "column_roles": dataset_profile.get("column_roles", {}),
            "semantic_map": semantic_map,
            "business_summary": summary,
            "business_metrics": business_metrics,
            "product_analysis": product_analysis,
            "food_analysis": food_analysis,
            "financial_analysis": financial_analysis,
            "query_plan": query_plan,
            "query_answer": query_answer,
            "kpis": query_answer.get("kpis") or _default_kpis(business_metrics),
            "data_quality": data_quality,
            "eda": eda,
            "trends": trends,
            "correlations": correlations,
            "outliers": outliers,
            "target_suggestions": target_suggestions,
            "prediction": prediction,
            "automl": automl_alias,
            "xai": xai,
            "charts": charts,
            "warnings": list(dict.fromkeys(warnings + product_analysis.get("warnings", []))),
            "report_mode": report_mode,
        }

    def _legacy_automl_alias(self, prediction: dict[str, Any]) -> dict[str, Any]:
        alias = dict(prediction)
        if alias.get("status") == "complete":
            alias["status"] = "success"
            alias["best_model"] = alias.get("selected_model")
            alias["metrics"] = alias.get("test_metrics") or alias.get("model_metrics") or {}
        return alias

    def _merge_narration(self, facts: dict[str, Any], narration: dict[str, Any]) -> dict[str, Any]:
        normalized_charts, chart_warnings = normalize_chart_specs(facts.get("charts") or [], limit=20)
        result = {
            **facts,
            "executive_summary": narration["executive_summary"],
            "key_insights": narration["key_insights"],
            "recommendations": list(dict.fromkeys(narration["recommendations"] + (facts.get("product_analysis") or {}).get("recommendations", []))),
            "warnings": list(dict.fromkeys(facts.get("warnings", []) + narration.get("warnings", []) + chart_warnings)),
            "next_questions": list(dict.fromkeys(narration["next_questions"] + (facts.get("product_analysis") or {}).get("next_questions", []))),
            "report_sections": narration.get("report_sections", {}),
            "narration": narration,
        }
        result["charts"] = normalized_charts
        return json_safe(result)

    def profile_dataset(self, df: pd.DataFrame) -> dict[str, Any]:
        return profile_dataframe(df)

    def compute_data_quality(self, df: pd.DataFrame) -> dict[str, Any]:
        return compute_data_quality(df)

    def compute_eda(self, df: pd.DataFrame, outliers: dict[str, Any] | None = None) -> dict[str, Any]:
        return compute_eda(df, outliers=outliers)

    def compute_trends(self, df: pd.DataFrame) -> dict[str, Any]:
        return compute_trends(df)

    def compute_correlations(self, df: pd.DataFrame) -> dict[str, Any]:
        return compute_correlations(df)

    def compute_outliers(self, df: pd.DataFrame) -> dict[str, Any]:
        return compute_outliers(df)

    def train_model(
        self,
        df: pd.DataFrame,
        *,
        query: str | None,
        target_column: str | None,
        task_type: str | None,
        run_predictions: bool,
    ):
        return train_prediction(
            df,
            query=query,
            target_column=target_column,
            task_type=task_type,
            run_predictions=run_predictions,
        )

    def run_xai(self, trained_bundle: Any, prediction: dict[str, Any], run_xai: bool = True) -> dict[str, Any]:
        if not SHAP_AVAILABLE and prediction.get("status") == "complete":
            importance = prediction.get("feature_importance", [])
            if not importance:
                return {
                    "status": "limited",
                    "method": None,
                    "global_feature_importance": [],
                    "top_features": [],
                    "local_explanations": [],
                    "plain_english_explanation": "XAI could not be generated because the model did not expose valid feature importance.",
                    "warnings": ["Feature importance was unavailable."],
                }
            warnings = ["SHAP unavailable; used feature importance fallback."]
            warnings.extend(str(item) for item in prediction.get("limitations", []) if "leakage" in str(item).lower())
            return {
                "status": "fallback",
                "method": "feature_importance",
                "global_feature_importance": importance,
                "top_features": [item["feature"] for item in importance[:5]],
                "local_explanations": [],
                "plain_english_explanation": (
                    "Method used: feature importance fallback. "
                    "SHAP was unavailable, so model feature importance was used. "
                    f"Top features: {', '.join(item['feature'] for item in importance[:5])}."
                ),
                "warnings": list(dict.fromkeys(warnings)),
            }
        return explain_model(trained_bundle, prediction, run_xai=run_xai)

    def generate_charts(
        self,
        df: pd.DataFrame,
        trends: dict[str, Any],
        correlations: dict[str, Any],
        outliers: dict[str, Any],
        prediction: dict[str, Any],
        xai: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return build_chart_specs(df, trends, correlations, outliers, prediction, xai)


def _normalize_charts(charts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized, _warnings = normalize_chart_specs(charts, limit=20)
    return normalized


def _food_catalog_analysis(df: pd.DataFrame, semantic_map: dict[str, Any]) -> dict[str, Any]:
    if semantic_map.get("dataset_type") != "food_dataset":
        return {}
    columns = {str(column).lower(): str(column) for column in df.columns}
    frequency_specs = [
        ("food_name", "Most frequent food item", "food_name"),
        ("category", "Most common category", "category"),
        ("cuisine", "Most common cuisine", "cuisine"),
        ("main_ingredient", "Most common main ingredient", "main_ingredient"),
        ("spice_level", "Spice level distribution", "spice_level"),
    ]
    charts: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    insights: list[str] = []
    for lookup, title, key in frequency_specs:
        column = columns.get(lookup)
        if not column:
            continue
        rows = _frequency_rows(df, column, key)
        if not rows:
            continue
        charts.append({"type": "bar", "title": title, "x_key": key, "y_key": "count", "data": rows[:12]})
        tables.append({"title": title, "columns": [key, "count"], "rows": rows[:12]})
        leader = rows[0]
        insights.append(f"{title}: {leader[key]} appears {leader['count']} rows.")

    calories_col = columns.get("calories")
    calories_stats: dict[str, Any] = {}
    if calories_col:
        series = pd.to_numeric(df[calories_col], errors="coerce").dropna()
        if not series.empty:
            calories_stats = {
                "min": int(series.min()) if float(series.min()).is_integer() else round(float(series.min()), 2),
                "max": int(series.max()) if float(series.max()).is_integer() else round(float(series.max()), 2),
                "mean": round(float(series.mean()), 2),
                "median": round(float(series.median()), 2),
            }
            insights.append(
                "Calories range from "
                f"{calories_stats['min']} to {calories_stats['max']}, with mean {calories_stats['mean']} "
                f"and median {calories_stats['median']}."
            )

    limitation = (
        "This dataset does not contain sales, revenue, profit, quantity, order date, or transaction columns. "
        "Therefore revenue analysis, most-sold product analysis, sales trends, and profit analysis cannot be calculated."
    )
    return {
        "dataset_kind": "food_classification_catalog",
        "calories_stats": calories_stats,
        "charts": charts,
        "tables": tables,
        "insights": insights,
        "warnings": [limitation],
        "recommendations": [
            "Use frequency analysis for catalog composition, not sales performance.",
            "Collect order quantity, revenue, cost, and timestamps before asking sales or profit questions.",
            "Validate any category model on external food items before trusting perfect accuracy.",
        ],
        "next_questions": [
            "Which cuisines have the highest average calories?",
            "How does spice level vary by cuisine or main ingredient?",
            "Which categories are duplicated or overly deterministic?",
        ],
    }


def _merge_food_analysis(product_analysis: dict[str, Any], food_analysis: dict[str, Any]) -> dict[str, Any]:
    merged = dict(product_analysis)
    merged["charts"] = [*food_analysis.get("charts", []), *product_analysis.get("charts", [])]
    merged["tables"] = [*food_analysis.get("tables", []), *product_analysis.get("tables", [])]
    merged["insights"] = [*food_analysis.get("insights", []), *product_analysis.get("insights", [])]
    merged["recommendations"] = [*food_analysis.get("recommendations", []), *product_analysis.get("recommendations", [])]
    merged["next_questions"] = [*food_analysis.get("next_questions", []), *product_analysis.get("next_questions", [])]
    merged["warnings"] = [*food_analysis.get("warnings", []), *product_analysis.get("warnings", [])]
    return {key: list(dict.fromkeys(value)) if isinstance(value, list) and all(isinstance(item, str) for item in value) else value for key, value in merged.items()}


def _food_query_answer(query: str | None, food_analysis: dict[str, Any]) -> dict[str, Any] | None:
    q = (query or "").lower()
    if not q or not any(term in q for term in ["most sold", "best selling", "top selling", "sold product", "sales", "revenue", "profit"]):
        return None
    tables = [table for table in food_analysis.get("tables", []) if table.get("title") == "Most frequent food item"]
    charts = [chart for chart in food_analysis.get("charts", []) if chart.get("title") == "Most frequent food item"]
    return {
        "intent": "food_frequency_fallback",
        "answer": (
            "This dataset does not contain sales or quantity columns, so I cannot calculate the most sold product. "
            "I can show the most frequent food item instead."
        ),
        "tables": tables,
        "charts": charts,
        "warnings": food_analysis.get("warnings", []),
        "follow_up_ideas": [
            "Show the most common category.",
            "Show cuisine distribution.",
            "Show calories distribution.",
        ],
    }


def _frequency_rows(df: pd.DataFrame, column: str, key: str) -> list[dict[str, Any]]:
    counts = df[column].astype(str).str.strip().replace("", pd.NA).dropna().value_counts().head(20)
    return [{key: str(label), "count": int(count)} for label, count in counts.items()]


def _prediction_request(
    *,
    df: pd.DataFrame,
    query_plan: dict[str, Any],
    query: str | None,
    target_column: str | None,
    task_type: str | None,
    run_predictions: bool,
) -> tuple[str | None, str | None, bool]:
    if target_column or task_type:
        return target_column, task_type, run_predictions
    if not run_predictions:
        return None, None, False
    intent = str(query_plan.get("intent") or "")
    metric = str(query_plan.get("metric") or "revenue")
    report_mode = str(query_plan.get("report_mode") or "focused_answer_report")
    if intent == "prediction":
        if metric == "profit":
            target = _first_existing_column(df, ("profit", "total_profit", "net_profit"))
            return target, "regression", bool(target)
        if metric == "quantity":
            target = _first_existing_column(df, ("quantity", "total_quantity"))
            return target, "regression", bool(target)
        if "category" in (query or "").lower():
            target = _first_existing_column(df, ("category", "subcategory"))
            return target, "classification", bool(target)
        target = _first_existing_column(df, ("total_sales", "revenue", "sales", "net_sales"))
        return target, "regression", bool(target)
    if report_mode == "full_analysis_report" or intent == "full_report":
        return None, None, True
    else:
        return None, None, False


def _default_kpis(business_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return build_kpi_cards(business_metrics)


def _report_charts_for_query(
    *,
    query_plan: dict[str, Any],
    business_metrics: dict[str, Any],
    product_analysis: dict[str, Any],
    generic_charts: list[dict[str, Any]],
    report_mode: str,
) -> list[dict[str, Any]]:
    intent = str(query_plan.get("intent") or "dataset_overview")
    product_charts = list(product_analysis.get("charts") or [])
    fallback_charts = [*product_charts, *generic_charts]
    if intent == "total_sales":
        return [
            _line_chart("Sales by month", business_metrics.get("revenue_by_month") or [], "period", "revenue"),
            _bar_chart("Sales by category", business_metrics.get("revenue_by_category") or [], "category", "revenue"),
            _bar_chart("Sales by region", business_metrics.get("top_regions") or [], "region", "revenue"),
        ]
    if intent in {"revenue_by_month", "revenue_trend"}:
        return [_line_chart("Revenue by month", business_metrics.get("revenue_by_month") or [], "period", "revenue")]
    if intent in {"top_product", "top_products"}:
        focused_charts = [
            _bar_chart("Top products by revenue", business_metrics.get("top_products") or [], "product", "revenue"),
            _bar_chart("Top products by quantity", business_metrics.get("top_products_by_quantity") or [], "product", "quantity"),
        ]
        if any(chart.get("data") for chart in focused_charts):
            return focused_charts
        return fallback_charts
    if intent == "category_performance":
        return [_bar_chart("Category revenue", business_metrics.get("top_categories") or [], "category", "revenue")]
    if intent == "region_performance":
        return [_bar_chart("Region revenue", business_metrics.get("top_regions") or [], "region", "revenue")]
    if intent in {"profit_summary", "dataset_overview"} and report_mode != "full_analysis_report":
        return []
    return fallback_charts


def _bar_chart(title: str, data: list[dict[str, Any]], x_key: str, y_key: str) -> dict[str, Any]:
    return {"type": "bar", "title": title, "x_key": x_key, "y_key": y_key, "data": data}


def _line_chart(title: str, data: list[dict[str, Any]], x_key: str, y_key: str) -> dict[str, Any]:
    return {"type": "line", "title": title, "x_key": x_key, "y_key": y_key, "data": data}


def _first_existing_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    by_normalized = {str(column).lower(): str(column) for column in df.columns}
    for candidate in candidates:
        match = by_normalized.get(candidate.lower())
        if match:
            return match
    return None


def _financial_dataset_analysis(df: pd.DataFrame) -> dict[str, Any]:
    """Detect and compute company-year financial metrics if dataset looks financial.

    Returns an empty dict for non-financial datasets so callers can check
    ``result.get("is_financial")`` safely.
    """
    cols_lower = {c.lower().strip(): c for c in df.columns}

    year_col = next(
        (cols_lower[k] for k in ("year", "fiscal year", "fiscal_year", "period") if k in cols_lower),
        None,
    )
    entity_col = next(
        (cols_lower[k] for k in ("company", "entity", "organization", "firm") if k in cols_lower),
        None,
    )
    if not year_col or not entity_col:
        return {}

    def _find(*candidates: str) -> str | None:
        for c in candidates:
            if c.lower() in cols_lower:
                return cols_lower[c.lower()]
        return None

    revenue_col = _find("total revenue", "revenue", "net revenue", "sales")
    income_col = _find("net income", "net profit", "profit after tax")
    assets_col = _find("total assets", "assets")
    liabilities_col = _find("total liabilities", "liabilities")
    cashflow_col = _find(
        "cash flow from operating activities",
        "operating cash flow",
        "cash flow from operations",
    )

    if not revenue_col:
        return {}

    entities = sorted(df[entity_col].dropna().astype(str).unique())
    years_raw = sorted(df[year_col].dropna().unique())

    def _to_year_str(y: Any) -> str:
        try:
            fval = float(y)
            return str(int(fval)) if fval == int(fval) else str(y)
        except (TypeError, ValueError):
            return str(y)

    years = [_to_year_str(y) for y in years_raw]

    revenue_by_year: list[dict[str, Any]] = []
    for yr_raw, yr in zip(years_raw, years):
        mask = df[year_col] == yr_raw
        rev = float(df.loc[mask, revenue_col].sum())
        income = float(df.loc[mask, income_col].sum()) if income_col else None
        cf = float(df.loc[mask, cashflow_col].sum()) if cashflow_col else None
        revenue_by_year.append({"year": yr, "total_revenue": rev, "total_net_income": income, "total_cashflow": cf})

    company_metrics: list[dict[str, Any]] = []
    for entity in entities:
        mask = df[entity_col].astype(str) == entity
        ent = df[mask]
        row: dict[str, Any] = {"entity": entity}
        row["total_revenue"] = float(ent[revenue_col].sum())
        if income_col:
            row["total_net_income"] = float(ent[income_col].sum())
            if row["total_revenue"]:
                row["profit_margin"] = round(row["total_net_income"] / row["total_revenue"] * 100, 2)
        if assets_col:
            row["total_assets"] = float(ent[assets_col].sum())
        if liabilities_col:
            row["total_liabilities"] = float(ent[liabilities_col].sum())
            if assets_col and row.get("total_assets"):
                row["liability_ratio"] = round(row["total_liabilities"] / row["total_assets"] * 100, 2)
        if cashflow_col:
            row["total_cashflow"] = float(ent[cashflow_col].sum())
        if len(years_raw) >= 2:
            first_rev = float(ent.loc[ent[year_col] == years_raw[0], revenue_col].sum())
            last_rev = float(ent.loc[ent[year_col] == years_raw[-1], revenue_col].sum())
            if first_rev:
                row["revenue_growth_pct"] = round((last_rev - first_rev) / abs(first_rev) * 100, 2)
        company_metrics.append(row)

    company_metrics.sort(key=lambda x: x.get("total_revenue", 0), reverse=True)

    grouped_data: list[dict[str, Any]] = []
    for yr_raw, yr in zip(years_raw, years):
        for entity in entities:
            mask = (df[entity_col].astype(str) == entity) & (df[year_col] == yr_raw)
            rev = float(df.loc[mask, revenue_col].sum())
            grouped_data.append({"company": entity, "year": yr, "revenue": rev})

    total_revenue = float(df[revenue_col].sum())
    total_net_income = float(df[income_col].sum()) if income_col else None
    total_cashflow = float(df[cashflow_col].sum()) if cashflow_col else None

    revenue_growth_pct: float | None = None
    if len(revenue_by_year) >= 2:
        first_rev = revenue_by_year[0]["total_revenue"]
        last_rev = revenue_by_year[-1]["total_revenue"]
        if first_rev:
            revenue_growth_pct = round((last_rev - first_rev) / abs(first_rev) * 100, 2)

    return {
        "is_financial": True,
        "year_column": year_col,
        "entity_column": entity_col,
        "revenue_column": revenue_col,
        "income_column": income_col,
        "assets_column": assets_col,
        "liabilities_column": liabilities_col,
        "cashflow_column": cashflow_col,
        "entities": entities,
        "years": years,
        "company_metrics": company_metrics,
        "revenue_by_year": revenue_by_year,
        "grouped_revenue_data": grouped_data,
        "total_revenue_all": total_revenue,
        "total_net_income_all": total_net_income,
        "total_cashflow_all": total_cashflow,
        "revenue_growth_pct": revenue_growth_pct,
    }


__all__ = ["AnalysisPipeline", "create_session_id", "persist_dataframe_for_session"]
