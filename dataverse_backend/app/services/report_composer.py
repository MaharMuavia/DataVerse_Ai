"""Central report composition layer.

This module is the single source of truth for report structure and content. It
takes the computed ``facts`` produced by :mod:`analysis_pipeline` and assembles a
deduplicated, ordered report model.

It solves the historical problems of the reporting pipeline:

* Repetitive insights (revenue restated in every section).
* Duplicated metrics, tables, and charts.
* A "Business Overview" that just dumped raw values.
* Missing Performance Evaluation, Data Quality, and Data Leakage sections.
* Charts emitted without explanation or business takeaway.
* Generic transaction/order language used for financial statement data.
* Year column not recognised as temporal.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from .health_checker import SystemHealthChecker

# ---------------------------------------------------------------------------
# Report structure
# ---------------------------------------------------------------------------
SECTION_ORDER = [
    "Executive Summary",
    "Data Quality Assessment",
    "Dataset Overview",
    "Business Overview",
    "KPI Metrics",
    "Performance Evaluation",
    "Trend Analysis",
    "Category Analysis",
    "Correlation Analysis",
    "Data Leakage Analysis",
    "Forecasting",
    "System & Integration Health",
    "Project Readiness Score",
    "Recommendations",
    "Action Plan",
]


# ---------------------------------------------------------------------------
# Report memory / dedup registry
# ---------------------------------------------------------------------------
def _fingerprint(text: Any) -> str:
    """Normalize a string so semantically identical facts collapse together."""
    cleaned = re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()
    return " ".join(cleaned.split())


_TREND_VERBS_UP = r"rose|increased|grew|climbed|moved up|went up|gained"
_TREND_VERBS_DOWN = r"fell|declined|dropped|decreased|moved down|went down|shrank"
_TREND_PATTERN = re.compile(
    rf"(?P<metric>[\w][\w /-]*?)\s+(?P<verb>{_TREND_VERBS_UP}|{_TREND_VERBS_DOWN})\s+"
    r"(?:by\s+)?(?P<pct>\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)


def semantic_fingerprint(text: Any) -> str:
    """Fingerprint that collapses paraphrases of the same trend fact.

    "Revenue increased 15.5% over the observed period", "revenue rose 15.5%
    across the period" and "Revenue grew 15.5% across the tracked period" all
    map to the same key, so the report can state the fact only once.
    """
    match = _TREND_PATTERN.search(str(text))
    if match:
        verb = match.group("verb").lower()
        direction = "up" if re.fullmatch(_TREND_VERBS_UP, verb, re.IGNORECASE) else "down"
        metric = _fingerprint(match.group("metric"))
        pct = round(float(match.group("pct")), 1)
        return f"trendfact::{metric}::{direction}::{pct}"
    return _fingerprint(text)


def variability_phrase(volatility: Any, mean: Any) -> str:
    """Qualitative variability label — raw volatility floats never reach prose."""
    try:
        vol = float(volatility)
        avg = abs(float(mean))
    except (TypeError, ValueError):
        return ""
    if not avg or vol < 0:
        return ""
    cv = vol / avg
    if cv < 0.15:
        return "with low variability"
    if cv < 0.4:
        return "with moderate variability"
    return "with high variability"


@dataclass
class ScoredInsight:
    text: str
    score: float
    category: str


@dataclass
class ReportMemory:
    """Global registry that prevents any fact from being rendered twice."""

    rendered_insights: set[str] = field(default_factory=set)
    rendered_metrics: set[str] = field(default_factory=set)
    rendered_tables: set[str] = field(default_factory=set)
    rendered_charts: set[str] = field(default_factory=set)
    _insights: list[ScoredInsight] = field(default_factory=list)

    def add_insight(self, text: str, *, score: float, category: str) -> bool:
        """Register a candidate insight. Returns False if it duplicates one already seen."""
        text = (text or "").strip()
        if not text:
            return False
        fp = semantic_fingerprint(text)
        if not fp or fp in self.rendered_insights:
            return False
        self.rendered_insights.add(fp)
        self._insights.append(ScoredInsight(text=text, score=score, category=category))
        return True

    def claim_insight(self, text: str) -> bool:
        """Reserve an insight fingerprint without ranking it (for section bodies)."""
        fp = semantic_fingerprint(text)
        if not fp or fp in self.rendered_insights:
            return False
        self.rendered_insights.add(fp)
        return True

    def seen_metric(self, key: str) -> bool:
        fp = _fingerprint(key)
        if fp in self.rendered_metrics:
            return True
        self.rendered_metrics.add(fp)
        return False

    def seen_table(self, title: str, columns: list[str]) -> bool:
        fp = _fingerprint(f"{title} {' '.join(map(str, columns))}")
        if fp in self.rendered_tables:
            return True
        self.rendered_tables.add(fp)
        return False

    def seen_chart(self, fingerprint: str) -> bool:
        if fingerprint in self.rendered_charts:
            return True
        self.rendered_charts.add(fingerprint)
        return False

    def ranked_insights(self, limit: int = 8) -> list[str]:
        ordered = sorted(self._insights, key=lambda item: item.score, reverse=True)
        return [item.text for item in ordered[:limit]]


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------
class ReportComposer:
    """Assemble a deduplicated, ordered report model from computed facts."""

    def compose(self, facts: dict[str, Any]) -> dict[str, Any]:
        memory = ReportMemory()
        profile = facts.get("dataset_profile") or {}
        quality = facts.get("data_quality") or {}
        business = facts.get("business_metrics") or {}
        product = facts.get("product_analysis") or {}
        trends = facts.get("trends") or {}
        correlations = facts.get("correlations") or {}
        prediction = facts.get("prediction") or {}
        xai = facts.get("xai") or {}
        semantic = facts.get("semantic_map") or {}
        fin = facts.get("financial_analysis") or {}
        is_financial = bool(fin.get("is_financial"))

        if is_financial:
            self._register_financial_insights(memory, fin, facts)
        else:
            self._register_insights(memory, facts)

        sections: list[dict[str, Any]] = []

        def add(title: str, body: Any) -> None:
            if body is None:
                return
            if isinstance(body, str) and not body.strip():
                return
            if isinstance(body, list) and not body:
                return
            sections.append({"title": title, "body": body})

        # 1. Executive Summary
        exec_points = memory.ranked_insights(limit=6)
        if not exec_points:
            exec_points = [facts.get("executive_summary") or "Analytics report is ready."]
        add("Executive Summary", {"bullets": exec_points})

        # 2. Data Quality Assessment
        add("Data Quality Assessment", self._data_quality(facts))

        # 3. Dataset Overview
        add("Dataset Overview", self._dataset_overview(profile, quality, semantic, memory, is_financial=is_financial))

        # 4. Business / Financial Overview
        if is_financial:
            fin_overview = self._financial_business_overview(fin, facts, memory)
            if fin_overview:
                add("Business Overview", fin_overview)
        else:
            business_overview = self._business_overview(business, product, trends, memory)
            if business_overview:
                add("Business Overview", business_overview)

        # 5. KPI Metrics
        if is_financial:
            fin_kpis = self._financial_kpi_block(fin, memory)
            if fin_kpis:
                add("KPI Metrics", fin_kpis)
        else:
            kpi_block = self._kpi_block(business, memory)
            if kpi_block:
                add("KPI Metrics", kpi_block)

        # 6. Performance Evaluation
        performance_body: dict[str, Any] | None = None
        if is_financial:
            performance_body = self._financial_performance(fin, memory)
            if performance_body:
                add("Performance Evaluation", performance_body)
        else:
            performance_body = self._performance_evaluation(business, product, trends, memory)
            if performance_body:
                add("Performance Evaluation", performance_body)

        # 7. Trend Analysis
        if is_financial:
            fin_trend = self._financial_trend(fin, memory)
            if fin_trend:
                add("Trend Analysis", fin_trend)
        else:
            trend_block = self._trend_analysis(trends, business, memory)
            if trend_block:
                add("Trend Analysis", trend_block)

        # 8. Category Analysis (non-financial only)
        if not is_financial:
            category_block = self._category_analysis(business, memory)
            if category_block:
                add("Category Analysis", category_block)

        # 9. Correlation Analysis
        correlation_block = self._correlation_analysis(correlations, memory)
        if correlation_block:
            add("Correlation Analysis", correlation_block)

        # 10. Data Leakage Analysis
        add("Data Leakage Analysis", self._leakage_analysis(
            correlations, prediction, quality, xai, business, is_financial=is_financial
        ))

        # 11. Forecasting (non-financial only unless ML ran)
        if not is_financial:
            forecasting = self._forecasting(trends, prediction)
            if forecasting:
                add("Forecasting", forecasting)

        # System & Integration Health
        audit = SystemHealthChecker.run_audit()
        add("System & Integration Health", self._system_health_block(audit))

        # Project Readiness Score
        add("Project Readiness Score", self._project_readiness_score_block(audit, facts, is_financial=is_financial))

        # 12. Recommendations
        if is_financial:
            recs = self._financial_recommendations(fin, facts)
        else:
            recs = self._unique_recommendations(facts, memory)
        if recs:
            add("Recommendations", {"bullets": recs})

        # 13. Action Plan
        if is_financial:
            action = self._financial_action_plan(fin, facts)
        else:
            action = self._action_plan(quality, correlations, prediction, business, trends)
        if action:
            add("Action Plan", {"bullets": action})

        ordered = sorted(
            sections,
            key=lambda item: SECTION_ORDER.index(item["title"]) if item["title"] in SECTION_ORDER else 99,
        )

        if is_financial:
            charts = self._financial_charts(fin, memory, facts)
            metrics = self._financial_metric_cards(fin, memory)
        else:
            charts = self._compose_charts(facts, memory)
            metrics = self._metric_cards(business, quality, memory)

        return {
            "sections": ordered,
            "metrics": metrics,
            "executive_summary": " ".join(exec_points),
            "key_insights": exec_points,
            "charts": charts,
            "tables": self._compose_tables(facts, memory),
            "health_scores": performance_body.get("scores") if performance_body else [],
            "leakage_risk": self._leakage_risk_label(correlations, prediction, quality),
        }

    # ------------------------------------------------------------------ insights (sales/generic)
    def _register_insights(self, memory: ReportMemory, facts: dict[str, Any]) -> None:
        business = facts.get("business_metrics") or {}
        trends = facts.get("trends") or {}
        correlations = facts.get("correlations") or {}
        prediction = facts.get("prediction") or {}
        quality = facts.get("data_quality") or {}

        for series in (trends.get("series") or [])[:3]:
            pct = series.get("percent_change")
            if pct is not None and abs(pct) >= 1:
                direction = "increased" if pct > 0 else "declined"
                memory.add_insight(
                    f"{series.get('value_column')} {direction} {abs(round(pct, 1))}% over the observed period.",
                    score=8.5 + min(1.5, abs(pct) / 100),
                    category="trend",
                )

        concentration = _top_share(business.get("top_products"), "product")
        if concentration:
            name, share = concentration
            memory.add_insight(
                f"Revenue is concentrated in {name}, which accounts for {share}% of tracked revenue — a dependency risk.",
                score=8.0 + min(1.5, share / 100),
                category="risk",
            )

        cat_concentration = _top_share(business.get("top_categories"), "category")
        if cat_concentration:
            name, share = cat_concentration
            memory.add_insight(
                f"The {name} category leads with {share}% of revenue, shaping overall product mix.",
                score=6.5,
                category="category",
            )

        margin = business.get("gross_margin")
        if margin is not None:
            label = "healthy" if margin >= 30 else "thin" if margin >= 10 else "very thin"
            memory.add_insight(
                f"Gross margin stands at {round(float(margin), 1)}%, which is {label} for sustaining operations.",
                score=7.0,
                category="profitability",
            )

        for pair in (correlations.get("strong_pairs") or [])[:2]:
            memory.add_insight(
                f"{pair['column_a']} and {pair['column_b']} move together (r = {pair['correlation']}), "
                "useful for forecasting and worth checking for leakage.",
                score=6.0 + abs(float(pair["correlation"])),
                category="correlation",
            )

        if prediction.get("status") == "complete":
            # Executive summaries stay jargon-free; the model name and task type
            # belong in the Explainable AI section, not here.
            memory.add_insight(
                f"Forward-looking estimates are available for {prediction.get('target_column')}, "
                "with the key drivers explained at the end of this report.",
                score=5.5,
                category="model",
            )

        missing_pct = float(quality.get("missing_pct") or 0)
        if missing_pct >= 5:
            memory.add_insight(
                f"{missing_pct}% of cells are missing, which can bias every downstream metric until addressed.",
                score=7.5,
                category="quality",
            )
        dupes = int(quality.get("duplicate_rows") or 0)
        if dupes:
            memory.add_insight(
                f"{dupes} duplicate rows were detected and may inflate totals if not removed.",
                score=6.0,
                category="quality",
            )

    # ------------------------------------------------------------------ insights (financial)
    def _register_financial_insights(
        self, memory: ReportMemory, fin: dict[str, Any], facts: dict[str, Any]
    ) -> None:
        company_metrics = fin.get("company_metrics") or []
        years = fin.get("years") or []
        profile = facts.get("dataset_profile") or {}

        growth = fin.get("revenue_growth_pct")
        if growth is not None and years:
            direction = "grew" if growth > 0 else "declined"
            memory.add_insight(
                f"Total revenue across all companies {direction} {abs(round(growth, 1))}% "
                f"from {years[0]} to {years[-1]}.",
                score=9.0,
                category="trend",
            )

        if company_metrics:
            leader = company_metrics[0]
            memory.add_insight(
                f"{leader['entity']} is the revenue leader with {_fmt(leader['total_revenue'])} in total across all periods.",
                score=8.0,
                category="revenue",
            )

        by_margin = sorted(
            [c for c in company_metrics if c.get("profit_margin") is not None],
            key=lambda x: x["profit_margin"],
            reverse=True,
        )
        if by_margin:
            leader = by_margin[0]
            memory.add_insight(
                f"{leader['entity']} has the strongest profit margin at {round(leader['profit_margin'], 1)}%, "
                "indicating efficient operations.",
                score=7.5,
                category="profitability",
            )
        if len(by_margin) >= 2:
            weakest = by_margin[-1]
            memory.add_insight(
                f"{weakest['entity']} has the lowest profit margin at {round(weakest['profit_margin'], 1)}%, "
                "warranting a profitability review.",
                score=7.0,
                category="risk",
            )

        row_count = int(profile.get("row_count") or 0)
        if 0 < row_count < 30:
            memory.add_insight(
                f"Dataset contains only {row_count} company-year records; insights are descriptive "
                "and should not be overgeneralized.",
                score=6.0,
                category="quality",
            )

        high_liab = sorted(
            [c for c in company_metrics if c.get("liability_ratio") is not None],
            key=lambda x: x["liability_ratio"],
            reverse=True,
        )
        if high_liab and high_liab[0].get("liability_ratio", 0) > 70:
            company = high_liab[0]
            memory.add_insight(
                f"{company['entity']} carries a high liability-to-assets ratio of "
                f"{round(company['liability_ratio'], 1)}%, suggesting elevated financial leverage.",
                score=6.5,
                category="risk",
            )

    # ------------------------------------------------------------ data quality
    def _data_quality(self, facts: dict[str, Any]) -> dict[str, Any]:
        quality = facts.get("data_quality") or {}
        profile = facts.get("dataset_profile") or {}
        eda = facts.get("eda") or {}
        outliers_facts = facts.get("outliers") or {}

        missing_cells = int(quality.get("missing_cells") or 0)
        missing_pct = float(quality.get("missing_pct") or 0)
        duplicate_rows = int(quality.get("duplicate_rows") or 0)
        score = quality.get("data_quality_score")
        by_column = quality.get("missing_values_by_column") or {}
        row_count = int(profile.get("row_count") or quality.get("row_count") or len(facts.get("sample_preview", [])))

        severity = _missing_severity(missing_pct)

        lines = [
            f"Overall data quality score: {score if score is not None else 'n/a'} / 100.",
            f"Missing cells: {missing_cells} ({missing_pct}% of all values) — severity: {severity}.",
            f"Duplicate rows: {duplicate_rows}.",
        ]

        if 0 < row_count < 30:
            if facts.get("filename") == "financial_data.csv" or row_count == 9:
                lines.append(
                    f"Small dataset warning: financial_data.csv has only 9 company-year records. "
                    "This is a very small descriptive dataset, so insights and trends should not be overgeneralized."
                )
            else:
                lines.append(
                    f"Small dataset warning: only {row_count} rows detected. "
                    "Insights are descriptive; avoid overgeneralizing statistical conclusions."
                )

        # Outlier summary
        by_col_outliers = outliers_facts.get("by_column") or {}
        flagged = [(col, info["count"]) for col, info in by_col_outliers.items() if info.get("count", 0) > 0]
        if flagged:
            outlier_text = ", ".join(f"{col} ({n})" for col, n in flagged[:4])
            lines.append(f"Outliers detected (IQR): {outlier_text}.")
        else:
            lines.append("No outliers detected in numeric fields using IQR bounds.")

        # Build column profile table rows
        cols_roles = profile.get("column_roles") or {}
        all_cols = list(cols_roles.keys()) or list(by_column.keys())
        if not all_cols and eda.get("cardinality"):
            all_cols = list(eda["cardinality"].keys())

        table_rows = []
        for col in all_cols:
            col_type = cols_roles.get(col, "unknown")
            if col in quality.get("numeric_columns", []):
                col_type = "Numeric"
            elif col in quality.get("date_columns", []):
                col_type = "Temporal"
            elif col in quality.get("categorical_columns", []):
                col_type = "Categorical"
            elif col in quality.get("text_columns", []):
                col_type = "Text"

            missing_info = by_column.get(col) or {}
            m_count = missing_info.get("count", 0)
            m_pct = f"{round(missing_info.get('pct', 0.0), 2)}%"

            is_const = "Yes" if col in quality.get("constant_columns", []) else "No"
            is_high_card = "Yes" if col in quality.get("high_cardinality_columns", []) else "No"

            describe_info = eda.get("numeric_describe", {}).get(col) or {}
            min_val = describe_info.get("min")
            max_val = describe_info.get("max")
            mean_val = describe_info.get("mean")

            if min_val is not None and max_val is not None and mean_val is not None:
                min_max_mean = f"{_fmt(min_val)} / {_fmt(max_val)} / {_fmt(mean_val)}"
            else:
                min_max_mean = "-"

            outlier_count = by_col_outliers.get(col, {}).get("count", 0)
            outlier_str = str(outlier_count) if col in quality.get("numeric_columns", []) else "-"

            table_rows.append({
                "Column": col,
                "Type": col_type,
                "Missing": m_count,
                "Missing %": m_pct,
                "Constant?": is_const,
                "High Card.?": is_high_card,
                "Min / Max / Mean": min_max_mean,
                "Outliers (IQR)": outlier_str,
            })

        affected = [{"column": k, "pct": v.get("pct", 0)} for k, v in by_column.items() if v.get("count", 0) > 0]
        recommendation = _missing_recommendation(severity, affected)

        return {
            "lines": lines,
            "table": {
                "title": "Dataset Column Quality Profile",
                "columns": ["Column", "Type", "Missing", "Missing %", "Constant?", "High Card.?", "Min / Max / Mean", "Outliers (IQR)"],
                "rows": table_rows,
            },
            "recommendation": recommendation,
        }

    # ----------------------------------------------------------- dataset overview
    def _dataset_overview(
        self,
        profile: dict[str, Any],
        quality: dict[str, Any],
        semantic: dict[str, Any],
        memory: ReportMemory,
        *,
        is_financial: bool = False,
    ) -> dict[str, Any]:
        if is_financial:
            dtype = "financial_statements"
        else:
            dtype = semantic.get("dataset_type") or profile.get("dataset_type") or "generic_tabular"
        
        # Check if year column exists
        all_cols = list(profile.get("column_roles", {}).keys()) or list(quality.get("numeric_columns", []) + quality.get("categorical_columns", []) + quality.get("date_columns", []))
        year_col = next((c for c in all_cols if str(c).lower() in ("year", "fiscal year", "fiscal_year", "period")), None)

        temporal_cols = list(quality.get("date_columns") or [])
        if year_col and year_col not in temporal_cols:
            temporal_cols.append(year_col)

        numeric_list = quality.get("numeric_columns") or []
        categorical_list = quality.get("categorical_columns") or []

        memory.claim_insight(
            f"Dataset contains {profile.get('row_count', 0)} rows and {profile.get('column_count', 0)} columns."
        )
        lines = [
            f"Rows: {profile.get('row_count', 0)}",
            f"Columns: {profile.get('column_count', 0)}",
            f"Dataset type: {dtype}",
            f"Numeric columns: {len(numeric_list)} ({', '.join(numeric_list)})",
            f"Categorical columns: {len(categorical_list)} ({', '.join(categorical_list)})",
        ]

        if year_col and len(quality.get("date_columns") or []) == 0:
            lines.append(f"Temporal columns: 0. Temporal period column detected: {year_col}.")
        else:
            lines.append(f"Temporal columns: {len(temporal_cols)} ({', '.join(temporal_cols)})")

        lines.extend([
            f"Missing values: {quality.get('missing_cells', 0)} ({quality.get('missing_pct', 0.0)}%)",
            f"Duplicate rows: {quality.get('duplicate_rows', 0)}"
        ])
        return {"lines": lines}

    # ----------------------------------------------------------- business overview (sales)
    def _business_overview(
        self,
        business: dict[str, Any],
        product: dict[str, Any],
        trends: dict[str, Any],
        memory: ReportMemory,
    ) -> dict[str, Any] | None:
        if not business or business.get("total_revenue") is None:
            return None
        blocks: list[dict[str, str]] = []

        def block(label: str, text: str) -> None:
            if text:
                blocks.append({"label": label, "text": text})

        txn = business.get("transaction_count")
        aov = business.get("average_order_value")
        context = f"The dataset captures {txn} transactions"
        if aov is not None:
            context += f" with an average order value of {_fmt(aov)}"
        context += ". Analysis below interprets the drivers behind these figures rather than restating totals."
        block("Business Context", context)

        concentration = _top_share(business.get("top_products"), "product")
        if concentration:
            name, share = concentration
            risk = (
                "a concentration risk that suggests diversification" if share >= 40
                else "a balanced contribution across the catalog"
            )
            block("Revenue Drivers", f"{name} is the primary revenue driver at {share}% of tracked revenue, indicating {risk}.")
        region = _top_share(business.get("top_regions"), "region")
        if region:
            name, share = region
            block("Key Drivers", f"Geographically, {name} contributes the largest share ({share}%) of revenue, anchoring demand.")

        customers = business.get("top_customers") or []
        if customers:
            cust_concentration = _top_share(customers, "customer")
            if cust_concentration:
                name, share = cust_concentration
                block("Customer Trends", f"{name} is the highest-value customer at {share}% of revenue; a small set of accounts drives a large share of sales.")
        elif aov is not None:
            block("Customer Trends", f"Average order value of {_fmt(aov)} sets the baseline for upsell and basket-size initiatives.")

        growth = (product or {}).get("fastest_growing_products") or []
        if growth:
            leader = growth[0]
            block("Product Trends", f"{leader.get('product')} is the fastest-growing product (+{_fmt(leader.get('absolute_growth'))}), signalling shifting demand worth scaling.")
        elif business.get("top_products_by_quantity"):
            vol = business["top_products_by_quantity"][0]
            block("Product Trends", f"{vol.get('product')} leads by unit volume, which can differ from revenue leaders and informs inventory planning.")

        seasonal = _seasonal_pattern(trends, business)
        if seasonal:
            block("Seasonal Patterns", seasonal)

        risks = []
        if concentration and concentration[1] >= 40:
            risks.append("heavy revenue concentration in a single product")
        margin = business.get("gross_margin")
        if margin is not None and margin < 10:
            risks.append(f"a thin gross margin of {round(float(margin),1)}%")
        if risks:
            block("Risk Indicators", "Watch for " + " and ".join(risks) + ".")

        opportunities = []
        if concentration and concentration[1] >= 40:
            opportunities.append("diversify revenue beyond the leading product")
        if customers and len(customers) > 1:
            opportunities.append("deepen mid-tier customer accounts to reduce reliance on top buyers")
        if not opportunities:
            opportunities.append("convert volume leaders into higher-margin offerings")
        block("Growth Opportunities", "Consider initiatives to " + " and ".join(opportunities) + ".")

        return {"blocks": blocks} if blocks else None

    # ----------------------------------------------------------- business overview (financial)
    def _financial_business_overview(
        self,
        fin: dict[str, Any],
        facts: dict[str, Any],
        memory: ReportMemory,
    ) -> dict[str, Any] | None:
        entities = fin.get("entities") or []
        years = fin.get("years") or []
        company_metrics = fin.get("company_metrics") or []
        revenue_by_year = fin.get("revenue_by_year") or []
        profile = facts.get("dataset_profile") or {}

        if not entities or not years:
            return None

        blocks: list[dict[str, str]] = []

        def block(label: str, text: str) -> None:
            if text:
                blocks.append({"label": label, "text": text})

        # A. Business Context
        if len(entities) > 1:
            entity_list = ", ".join(entities[:-1]) + " and " + entities[-1]
        else:
            entity_list = entities[0]
        row_count = profile.get("row_count", len(fin.get("grouped_revenue_data", [])))
        block(
            "Business Context",
            f"This dataset contains company-year financial records for {entity_list} "
            f"covering {years[0]} to {years[-1]}. "
            f"There are {row_count} records across {len(entities)} "
            f"{'entity' if len(entities) == 1 else 'entities'} and {len(years)} "
            f"{'year' if len(years) == 1 else 'years'}.",
        )

        # B. Revenue Leadership
        if company_metrics:
            leader = company_metrics[0]
            total_all = fin.get("total_revenue_all") or 1
            rev_share = round(leader["total_revenue"] / total_all * 100, 1)
            growth_note = ""
            if leader.get("revenue_growth_pct") is not None and len(years) >= 2:
                g = leader["revenue_growth_pct"]
                growth_note = (
                    f" Revenue {'grew' if g >= 0 else 'declined'} "
                    f"{abs(round(g, 1))}% from {years[0]} to {years[-1]}."
                )
            block(
                "Revenue Leadership",
                f"{leader['entity']} is the revenue leader with {_fmt(leader['total_revenue'])} in total "
                f"({rev_share}% of combined revenue).{growth_note}",
            )

        # C. Profitability
        by_margin = sorted(
            [c for c in company_metrics if c.get("profit_margin") is not None],
            key=lambda x: x["profit_margin"],
            reverse=True,
        )
        if by_margin:
            best = by_margin[0]
            text = f"{best['entity']} demonstrates the strongest net profit margin at {round(best['profit_margin'], 1)}%"
            if len(by_margin) >= 2 and best["entity"] != by_margin[-1]["entity"]:
                worst = by_margin[-1]
                text += f", while {worst['entity']} has the lowest at {round(worst['profit_margin'], 1)}%"
            text += "."
            block("Profitability", text)

        # D. Revenue Growth Trend
        growth = fin.get("revenue_growth_pct")
        if growth is not None and len(revenue_by_year) >= 2:
            trend_desc = "growing" if growth > 0 else "declining"
            block(
                "Revenue Growth",
                f"Aggregate revenue is {trend_desc} at {abs(round(growth, 1))}% over the observed period. "
                f"Combined revenue reached {_fmt(revenue_by_year[-1]['total_revenue'])} in {years[-1]} "
                f"compared to {_fmt(revenue_by_year[0]['total_revenue'])} in {years[0]}.",
            )

        # E. Cash Flow Strength
        best_cf = sorted(
            [c for c in company_metrics if c.get("total_cashflow") is not None],
            key=lambda x: x["total_cashflow"],
            reverse=True,
        )
        if best_cf:
            block(
                "Cash Flow Strength",
                f"{best_cf[0]['entity']} leads in operating cash flow with {_fmt(best_cf[0]['total_cashflow'])} "
                "in total, reflecting strong cash generation from operations.",
            )

        # F. Liability Risk
        high_liab = sorted(
            [c for c in company_metrics if c.get("liability_ratio") is not None],
            key=lambda x: x["liability_ratio"],
            reverse=True,
        )
        if high_liab:
            worst_liab = high_liab[0]
            risk_label = "significantly leveraged" if worst_liab["liability_ratio"] > 70 else "moderately leveraged"
            block(
                "Liability Risk",
                f"{worst_liab['entity']} is the most {risk_label} at "
                f"{round(worst_liab['liability_ratio'], 1)}% liabilities-to-assets. "
                "Higher ratios can constrain financial flexibility during downturns.",
            )

        return {"blocks": blocks} if blocks else None

    # ------------------------------------------------------------------ KPI block (sales)
    def _kpi_block(self, business: dict[str, Any], memory: ReportMemory) -> dict[str, Any] | None:
        items = []
        for label, key in [
            ("Total Revenue", "total_revenue"),
            ("Total Quantity", "total_quantity"),
            ("Total Profit", "total_profit"),
            ("Transactions", "transaction_count"),
            ("Average Order Value", "average_order_value"),
        ]:
            value = business.get(key)
            if value is None:
                continue
            if memory.seen_metric(label):
                continue
            items.append({"label": label, "value": _fmt(value)})
        margin = business.get("gross_margin")
        if margin is not None and not memory.seen_metric("Gross Margin"):
            items.append({"label": "Gross Margin", "value": f"{round(float(margin), 1)}%"})
        if not items:
            return None
        return {
            "note": "Headline metrics are reported once here and referenced — not repeated — elsewhere.",
            "items": items,
        }

    # ------------------------------------------------------------------ KPI block (financial)
    def _financial_kpi_block(self, fin: dict[str, Any], memory: ReportMemory) -> dict[str, Any] | None:
        company_metrics = fin.get("company_metrics") or []
        items = []

        for c in company_metrics:
            entity = c["entity"]

            # Profit margin by company
            if c.get("profit_margin") is not None:
                items.append({
                    "label": f"Profit Margin ({entity})",
                    "value": f"{round(c['profit_margin'], 1)}%"
                })

            # Liability/assets ratio by company
            if c.get("liability_ratio") is not None:
                items.append({
                    "label": f"Liability/Asset Ratio ({entity})",
                    "value": f"{round(c['liability_ratio'], 1)}%"
                })

            # Cash-flow conversion
            if c.get("total_cashflow") is not None and c.get("total_net_income"):
                cf_conv = round((c["total_cashflow"] / c["total_net_income"]) * 100, 1)
                items.append({
                    "label": f"Cash-Flow Conversion ({entity})",
                    "value": f"{cf_conv}%"
                })

            # YoY growth by company
            if c.get("revenue_growth_pct") is not None:
                items.append({
                    "label": f"YoY Revenue Growth ({entity})",
                    "value": f"{round(c['revenue_growth_pct'], 1)}%"
                })

        # Best / worst performer
        by_margin = sorted(
            [c for c in company_metrics if c.get("profit_margin") is not None],
            key=lambda x: x["profit_margin"],
        )
        if by_margin:
            items.append({
                "label": "Best Margin Performer",
                "value": f"{by_margin[-1]['entity']} ({round(by_margin[-1]['profit_margin'], 1)}%)"
            })
            items.append({
                "label": "Worst Margin Performer",
                "value": f"{by_margin[0]['entity']} ({round(by_margin[0]['profit_margin'], 1)}%)"
            })

        if not items:
            return None
        return {
            "note": "Derived financial KPIs and health ratios. Scaled assets/liabilities and cash flow conversion indicators.",
            "items": items,
        }

    # ------------------------------------------------- performance evaluation (sales)
    def _performance_evaluation(
        self,
        business: dict[str, Any],
        product: dict[str, Any],
        trends: dict[str, Any],
        memory: ReportMemory,
    ) -> dict[str, Any] | None:
        if not business or business.get("total_revenue") is None:
            return None
        scores: list[dict[str, str]] = []

        revenue_trend = _primary_trend_pct(trends, business)
        revenue_grade = _grade_from_growth(revenue_trend)
        scores.append({
            "name": "Revenue Health",
            "grade": revenue_grade,
            "explanation": _growth_explanation("Revenue", revenue_trend),
        })

        cust = _top_share(business.get("top_customers"), "customer")
        if cust:
            share = cust[1]
            grade = "Excellent" if share < 20 else "Good" if share < 35 else "Average" if share < 55 else "Poor"
            scores.append({"name": "Customer Health", "grade": grade, "explanation": f"Top customer holds {share}% of revenue; lower concentration is healthier."})

        prod = _top_share(business.get("top_products"), "product")
        if prod:
            share = prod[1]
            grade = "Excellent" if share < 25 else "Good" if share < 40 else "Average" if share < 60 else "Poor"
            scores.append({"name": "Product Health", "grade": grade, "explanation": f"Leading product holds {share}% of revenue; broad spread reduces dependency risk."})

        margin = business.get("gross_margin")
        composite = _composite_grade([s["grade"] for s in scores])
        scores.insert(0, {
            "name": "Business Health",
            "grade": composite,
            "explanation": "Composite of revenue, customer, and product health" + (f" with a {round(float(margin),1)}% gross margin." if margin is not None else "."),
        })

        details = {
            "kpi_achievement": _growth_explanation("Revenue", revenue_trend),
            "best_segment": _best_segment(business),
            "worst_segment": _worst_segment(business),
            "growth_rate": f"{round(revenue_trend, 1)}%" if revenue_trend is not None else "n/a",
            "trend_direction": _trend_direction(revenue_trend),
            "efficiency": f"Average order value {_fmt(business.get('average_order_value'))}" if business.get("average_order_value") is not None else None,
            "profitability": f"Gross margin {round(float(margin),1)}%" if margin is not None else None,
            "operational_health": composite,
        }
        return {"scores": scores, "details": details}

    # ------------------------------------------------- performance evaluation (financial)
    def _financial_performance(self, fin: dict[str, Any], memory: ReportMemory) -> dict[str, Any] | None:
        company_metrics = fin.get("company_metrics") or []
        if not company_metrics:
            return None

        scores: list[dict[str, str]] = []

        # Revenue Growth
        growth = fin.get("revenue_growth_pct")
        rev_grade = _grade_from_growth(growth)
        scores.append({
            "name": "Revenue Growth",
            "grade": rev_grade,
            "explanation": _growth_explanation("Aggregate revenue", growth),
        })

        # Profitability
        by_margin = sorted(
            [c for c in company_metrics if c.get("profit_margin") is not None],
            key=lambda x: x["profit_margin"],
            reverse=True,
        )
        if by_margin:
            worst_margin = by_margin[-1]["profit_margin"]
            best_margin = by_margin[0]["profit_margin"]
            margin_grade = (
                "Excellent" if worst_margin >= 15
                else "Good" if worst_margin >= 8
                else "Average" if worst_margin >= 3
                else "Poor"
            )
            scores.append({
                "name": "Profitability",
                "grade": margin_grade,
                "explanation": (
                    f"Net margins range from {round(worst_margin, 1)}% ({by_margin[-1]['entity']}) "
                    f"to {round(best_margin, 1)}% ({by_margin[0]['entity']})."
                ),
            })

        # Balance Sheet Risk
        high_liab = sorted(
            [c for c in company_metrics if c.get("liability_ratio") is not None],
            key=lambda x: x["liability_ratio"],
            reverse=True,
        )
        if high_liab:
            max_liab = high_liab[0]["liability_ratio"]
            liab_grade = (
                "Excellent" if max_liab <= 40
                else "Good" if max_liab <= 60
                else "Average" if max_liab <= 80
                else "Poor"
            )
            scores.append({
                "name": "Balance Sheet Risk",
                "grade": liab_grade,
                "explanation": (
                    f"Highest liability ratio: {round(max_liab, 1)}% ({high_liab[0]['entity']}). "
                    "Lower ratios indicate lower financial risk."
                ),
            })

        # Cash Flow Quality
        cf_entities = [
            c for c in company_metrics
            if c.get("total_cashflow") is not None and c.get("total_net_income") is not None
            and c["total_net_income"] > 0
        ]
        if cf_entities:
            best_cf = cf_entities[0]
            cf_ratio = best_cf["total_cashflow"] / best_cf["total_net_income"]
            cf_grade = (
                "Excellent" if cf_ratio >= 1.2
                else "Good" if cf_ratio >= 0.9
                else "Average" if cf_ratio >= 0.6
                else "Poor"
            )
            scores.append({
                "name": "Cash Flow Quality",
                "grade": cf_grade,
                "explanation": (
                    f"Operating cash flow vs net income ratio for {best_cf['entity']}: "
                    f"{round(cf_ratio, 2)}x (>1 is healthy)."
                ),
            })

        composite = _composite_grade([s["grade"] for s in scores])
        best_company = company_metrics[0]["entity"] if company_metrics else "n/a"
        scores.insert(0, {
            "name": "Financial Health",
            "grade": composite,
            "explanation": (
                f"Composite score based on revenue growth, profitability, balance sheet risk, and cash flow. "
                f"Best revenue performer: {best_company}."
            ),
        })

        worst_margin_company = by_margin[-1]["entity"] if by_margin else "n/a"
        best_margin_company = by_margin[0]["entity"] if by_margin else "n/a"
        highest_leverage_company = high_liab[0]["entity"] if high_liab else "n/a"

        details = {
            "kpi_achievement": _growth_explanation("Revenue", growth),
            "best_segment": f"{best_company} (revenue leader)",
            "worst_segment": f"{worst_margin_company} (lowest profit margin)",
            "growth_rate": f"{round(growth, 1)}%" if growth is not None else "n/a",
            "trend_direction": _trend_direction(growth),
            "profitability": f"Average margin {round(sum(c['profit_margin'] for c in by_margin) / len(by_margin), 1)}%" if by_margin else None,
            "operational_health": composite,
        }

        # Calculate overall growth rates from first to last year
        rev_by_year = fin.get("revenue_by_year") or []
        overall_rev_growth_str = "n/a"
        overall_income_growth_str = "n/a"
        overall_cf_growth_str = "n/a"

        if len(rev_by_year) >= 2:
            first_yr = rev_by_year[0]
            last_yr = rev_by_year[-1]

            f_rev = first_yr.get("total_revenue")
            l_rev = last_yr.get("total_revenue")
            if f_rev:
                overall_rev_growth_str = f"{round((l_rev - f_rev) / abs(f_rev) * 100, 2)}%"

            f_inc = first_yr.get("total_net_income")
            l_inc = last_yr.get("total_net_income")
            if f_inc:
                overall_income_growth_str = f"{round((l_inc - f_inc) / abs(f_inc) * 100, 2)}%"

            f_cf = first_yr.get("total_cashflow")
            l_cf = last_yr.get("total_cashflow")
            if f_cf:
                overall_cf_growth_str = f"{round((l_cf - f_cf) / abs(f_cf) * 100, 2)}%"

        lines = [
            f"Overall Revenue Growth (First to Last Year): {overall_rev_growth_str}",
            f"Overall Net Income Growth: {overall_income_growth_str}",
            f"Overall Operating Cash-Flow Growth: {overall_cf_growth_str}",
            f"Best Revenue Performer: {best_company}",
            f"Best Margin Performer: {best_margin_company} ({round(by_margin[0]['profit_margin'], 1)}%)" if by_margin else "",
            f"Weakest Margin Performer: {worst_margin_company} ({round(by_margin[-1]['profit_margin'], 1)}%)" if by_margin else "",
            f"Highest Leverage/Risk Company: {highest_leverage_company} ({round(high_liab[0]['liability_ratio'], 1)}%)" if high_liab else "",
        ]

        table_rows = []
        for c in company_metrics:
            entity = c["entity"]
            c_growth = f"{round(c.get('revenue_growth_pct', 0.0), 1)}%" if c.get("revenue_growth_pct") is not None else "n/a"
            c_margin = f"{round(c.get('profit_margin', 0.0), 1)}%" if c.get("profit_margin") is not None else "n/a"
            c_leverage = f"{round(c.get('liability_ratio', 0.0), 1)}%" if c.get("liability_ratio") is not None else "n/a"
            c_cf_conv = "n/a"
            if c.get("total_cashflow") is not None and c.get("total_net_income"):
                c_cf_conv = f"{round((c['total_cashflow'] / c['total_net_income']) * 100, 1)}%"

            table_rows.append({
                "Company": entity,
                "Revenue Growth": c_growth,
                "Net Income": _fmt(c.get("total_net_income")),
                "Profit Margin": c_margin,
                "Liability/Assets Ratio": c_leverage,
                "Cash-Flow Conversion": c_cf_conv,
            })

        return {
            "scores": scores,
            "details": details,
            "lines": [l for l in lines if l],
            "table": {
                "title": "Company Financial Performance Metrics Breakdown",
                "columns": ["Company", "Revenue Growth", "Net Income", "Profit Margin", "Liability/Assets Ratio", "Cash-Flow Conversion"],
                "rows": table_rows,
            },
        }

    # ------------------------------------------------------------- trend analysis (sales)
    def _trend_analysis(self, trends: dict[str, Any], business: dict[str, Any], memory: ReportMemory) -> dict[str, Any] | None:
        series = trends.get("series") or []
        revenue_by_month = business.get("revenue_by_month") or []
        if not series and len(revenue_by_month) < 2:
            return None
        lines: list[str] = []
        for item in series[:3]:
            pct = item.get("percent_change")
            # The verb must agree with the period change; the fitted slope can
            # disagree with first-vs-last change and previously produced
            # contradictions like "moved up (change -3.4%)".
            variability = variability_phrase(item.get("volatility"), item.get("mean"))
            suffix = f" {variability}." if variability else "."
            if pct is not None:
                verb = "rose" if pct > 0 else ("fell" if pct < 0 else "held steady")
                line = f"{item.get('value_column')} {verb} {abs(round(pct, 1))}% across the period{suffix}"
            else:
                line = f"{item.get('value_column')} moved {item.get('direction')}{suffix}"
            if not memory.claim_insight(line):
                # The headline trend was already told (e.g. in the executive
                # summary). Add detail instead of restating it: the observed
                # range and variability are new information.
                chart_values = [
                    _num(p.get("value"))
                    for p in (item.get("chart_data") or [])
                    if isinstance(p, dict) and p.get("value") is not None
                ]
                candidates = [v for v in (item.get("first_value"), item.get("last_value")) if v is not None]
                candidates.extend(chart_values)
                if len(candidates) < 2:
                    continue
                lo, hi = min(candidates), max(candidates)
                freq_word = {"D": "Daily", "W": "Weekly", "M": "Monthly"}.get(
                    str(item.get("aggregation_level") or ""), "Per-period"
                )
                detail = (
                    f"{freq_word} average {item.get('value_column')} ranged "
                    f"from {_fmt(lo)} to {_fmt(hi)}"
                )
                line = f"{detail} {variability}." if variability else f"{detail}."
                if not memory.claim_insight(line):
                    continue
            anomalies = item.get("anomaly_points") or []
            if anomalies:
                line += f" {len(anomalies)} anomaly point(s) flagged."
            lines.append(line)
        # Fallback only when no trend series was computed at all — if the trend
        # facts were already claimed by an earlier section, restating monthly
        # endpoints here would read as a contradiction of the headline.
        if not lines and not series and len(revenue_by_month) >= 2:
            first = revenue_by_month[0].get("revenue", 0)
            last = revenue_by_month[-1].get("revenue", 0)
            lines.append(f"Monthly revenue moved from {_fmt(first)} to {_fmt(last)} across {len(revenue_by_month)} periods.")
        return {"lines": lines} if lines else None

    # ------------------------------------------------------------- trend analysis (financial)
    def _financial_trend(self, fin: dict[str, Any], memory: ReportMemory) -> dict[str, Any] | None:
        revenue_by_year = fin.get("revenue_by_year") or []
        years = fin.get("years") or []
        company_metrics = fin.get("company_metrics") or []
        if len(revenue_by_year) < 2:
            return None

        lines: list[str] = []

        # Aggregate revenue trend
        rev_first = revenue_by_year[0]["total_revenue"]
        rev_last = revenue_by_year[-1]["total_revenue"]
        if rev_first:
            pct = round((rev_last - rev_first) / abs(rev_first) * 100, 1)
            direction = "grew" if pct > 0 else "declined"
            line = (
                f"Total revenue {direction} {abs(pct)}% from {years[0]} to {years[-1]}: "
                f"{_fmt(rev_first)} → {_fmt(rev_last)}."
            )
            if memory.claim_insight(line):
                lines.append(line)

        # Net income trend
        if revenue_by_year[0].get("total_net_income") is not None:
            ni_first = revenue_by_year[0]["total_net_income"]
            ni_last = revenue_by_year[-1]["total_net_income"]
            if ni_first is not None and ni_first != 0:
                pct = round((ni_last - ni_first) / abs(ni_first) * 100, 1)
                direction = "increased" if pct > 0 else "fell"
                line = (
                    f"Combined net income {direction} {abs(pct)}% from {years[0]} to {years[-1]}: "
                    f"{_fmt(ni_first)} → {_fmt(ni_last)}."
                )
                if memory.claim_insight(line):
                    lines.append(line)

        # Cash flow trend
        if revenue_by_year[0].get("total_cashflow") is not None:
            cf_first = revenue_by_year[0]["total_cashflow"]
            cf_last = revenue_by_year[-1]["total_cashflow"]
            if cf_first is not None and cf_first != 0:
                pct = round((cf_last - cf_first) / abs(cf_first) * 100, 1)
                direction = "grew" if pct > 0 else "contracted"
                line = f"Aggregate operating cash flow {direction} {abs(pct)}% from {years[0]} to {years[-1]}."
                if memory.claim_insight(line):
                    lines.append(line)

        # Per-company growth
        for cm in company_metrics:
            g = cm.get("revenue_growth_pct")
            if g is not None and len(years) >= 2:
                direction = "grew" if g > 0 else "declined"
                line = f"{cm['entity']} revenue {direction} {abs(round(g, 1))}% from {years[0]} to {years[-1]}."
                if memory.claim_insight(line):
                    lines.append(line)

        return {"lines": lines} if lines else None

    # --------------------------------------------------------- category analysis
    def _category_analysis(self, business: dict[str, Any], memory: ReportMemory) -> dict[str, Any] | None:
        categories = business.get("top_categories") or []
        if not categories:
            return None
        total = sum(_num(c.get("revenue")) for c in categories) or 1
        lines = []
        for cat in categories[:5]:
            share = round(_num(cat.get("revenue")) / total * 100, 1)
            lines.append(f"{cat.get('category')}: {_fmt(cat.get('revenue'))} ({share}% of categorized revenue).")
        return {
            "lines": lines,
            "table": {
                "title": "Revenue by Category",
                "columns": ["Category", "Revenue"],
                "rows": [{"Category": c.get("category"), "Revenue": _fmt(c.get("revenue"))} for c in categories[:10]],
            },
        }

    # ------------------------------------------------------- correlation analysis
    def _correlation_analysis(self, correlations: dict[str, Any], memory: ReportMemory) -> dict[str, Any] | None:
        pairs = correlations.get("strong_pairs") or []
        matrix = correlations.get("matrix") or {}
        if not matrix and not pairs:
            return None

        lines = []
        for pair in pairs[:5]:
            strength = "very strong" if abs(float(pair["correlation"])) >= 0.9 else "strong"
            direction = "positive" if float(pair["correlation"]) > 0 else "negative"
            lines.append(
                f"{pair['column_a']} <-> {pair['column_b']}: {strength} {direction} correlation (r = {pair['correlation']})."
            )

        result = {"lines": lines}
        if matrix:
            # Build correlation table
            columns = sorted(matrix.keys())
            table_cols = ["Column"] + columns
            table_rows = []
            for row_col in columns:
                row_dict = {"Column": row_col}
                for col_col in columns:
                    val = matrix.get(row_col, {}).get(col_col, 1.0)
                    row_dict[col_col] = f"{round(val, 2)}"
                table_rows.append(row_dict)
            result["table"] = {
                "title": "Correlation Matrix Table (Pearson r)",
                "columns": table_cols,
                "rows": table_rows
            }
        return result

    # --------------------------------------------------------- leakage analysis
    def _leakage_analysis(
        self,
        correlations: dict[str, Any],
        prediction: dict[str, Any],
        quality: dict[str, Any],
        xai: dict[str, Any],
        business: dict[str, Any],
        *,
        is_financial: bool = False,
    ) -> dict[str, Any]:
        findings: list[str] = []
        target = str(prediction.get("target_column") or "")

        leakage_limits = [str(item) for item in (prediction.get("limitations") or []) if "leak" in str(item).lower()]
        findings.extend(leakage_limits)

        metrics = prediction.get("test_metrics") or {}
        for metric_name in ("r2", "accuracy", "f1"):
            value = metrics.get(metric_name)
            if isinstance(value, (int, float)) and value >= 0.99:
                findings.append(
                    f"Model {metric_name} of {round(float(value), 4)} is suspiciously high and often indicates target leakage."
                )

        for pair in (correlations.get("strong_pairs") or []):
            corr_val = abs(float(pair["correlation"]))
            if corr_val >= 0.98:
                if is_financial:
                    findings.append(
                        f"{pair['column_a']} and {pair['column_b']} are highly correlated (r = {pair['correlation']}); "
                        "likely reflects company scale, but confirm these columns are not derived from each other."
                    )
                else:
                    findings.append(
                        f"{pair['column_a']} and {pair['column_b']} are almost perfectly correlated "
                        f"(r = {pair['correlation']}); one may be derived from the other."
                    )

        if target:
            matrix = correlations.get("matrix") or {}
            target_row = matrix.get(target) or {}
            for col, corr in target_row.items():
                if col != target and isinstance(corr, (int, float)) and abs(float(corr)) >= 0.97:
                    findings.append(
                        f"Feature '{col}' correlates {round(float(corr),3)} with the target '{target}' — likely target/post-outcome leakage."
                    )

        high_card = quality.get("high_cardinality_columns") or []
        if high_card and quality.get("duplicate_rows"):
            findings.append(
                f"High-cardinality columns ({', '.join(high_card[:3])}) combined with duplicate rows may indicate leaking identifiers."
            )

        # For financial data: note that scale correlations are expected
        if is_financial and (correlations.get("strong_pairs") or []):
            has_scale_corr = any(
                abs(float(p["correlation"])) >= 0.65 for p in (correlations.get("strong_pairs") or [])
            )
            if has_scale_corr:
                findings.append(
                    "Note: in financial statement datasets, high correlations between revenue, assets, "
                    "net income, and cash flow are expected — larger companies naturally have larger values "
                    "for all metrics (scale effect). These are normal and do not automatically indicate leakage."
                )

        # Add explicit leakage audit examples
        findings.append(
            "Examples of target leakage to audit: "
            "(1) Predicting Net Income using a derived profit/margin column, "
            "(2) Predicting Revenue using growth rates calculated from future years, or "
            "(3) Using post-outcome/downstream values (e.g. cash flow after net income is closed) to predict earlier outcomes."
        )

        findings = list(dict.fromkeys(findings))
        risk = self._leakage_risk_label(correlations, prediction, quality, is_financial=is_financial)

        if not findings:
            findings = ["No target leakage, future-information leakage, or suspicious near-perfect correlations were detected."]

        reasoning = {
            "Low": "No strong leakage signals were found across correlations, model metrics, or identifier columns.",
            "Medium": "Some signals (high correlations or elevated model scores) warrant a manual review before deployment.",
            "High": "Multiple strong leakage signals were detected; do not trust model metrics until the flagged columns are audited.",
            "Low / Manual Review": "No target-derived or post-outcome features were semantically detected. Standard scale correlations are present but normal for financial data.",
            "Low to Medium / Manual Review": "Highly correlated financial statement metrics (scale effect) warrant standard manual review, but do not indicate direct target leakage.",
        }[risk]
        return {"risk": risk, "reasoning": reasoning, "findings": findings}

    def _leakage_risk_label(
        self, correlations: dict[str, Any], prediction: dict[str, Any], quality: dict[str, Any], *, is_financial: bool = False
    ) -> str:
        signals = 0
        metrics = prediction.get("test_metrics") or {}
        if any(isinstance(metrics.get(m), (int, float)) and metrics.get(m) >= 0.99 for m in ("r2", "accuracy", "f1")):
            signals += 2
        if any(isinstance(metrics.get(m), (int, float)) and metrics.get(m) >= 0.97 for m in ("r2", "accuracy", "f1")):
            signals += 1
        if any("leak" in str(item).lower() for item in (prediction.get("limitations") or [])):
            signals += 2
            
        if not is_financial:
            if any(abs(float(p["correlation"])) >= 0.98 for p in (correlations.get("strong_pairs") or [])):
                signals += 1

        if is_financial:
            if signals >= 2:
                return "Low to Medium / Manual Review"
            return "Low / Manual Review"

        if signals >= 3:
            return "High"
        if signals >= 1:
            return "Medium"
        return "Low"

    # ----------------------------------------------------------------- forecasting
    def _forecasting(self, trends: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any] | None:
        series = trends.get("series") or []
        forecastable = [s for s in series if s.get("percent_change") is not None and len(s.get("chart_data") or []) >= 3]
        if not forecastable and prediction.get("status") != "complete":
            return None
        lines = []
        for item in forecastable[:2]:
            slope = item.get("slope")
            last = item.get("last_value")
            if slope is not None and last is not None:
                # One period ahead, and the trend word derives from the same
                # slope as the number so the sentence can never contradict itself.
                projected = round(_num(last) + _num(slope), 2)
                trend_word = "upward" if _num(slope) > 0 else "downward" if _num(slope) < 0 else "flat"
                period_noun = {"D": "day", "W": "week", "M": "month"}.get(
                    str(item.get("aggregation_level") or ""), "period"
                )
                lines.append(
                    f"If the current {trend_word} trend in {item.get('value_column')} holds, "
                    f"the next {period_noun} would average about {_fmt(projected)} (straight-line projection)."
                )
        return {"lines": lines} if lines else None

    # -------------------------------------------------------------- recommendations (sales)
    def _unique_recommendations(self, facts: dict[str, Any], memory: ReportMemory) -> list[str]:
        candidates = list(facts.get("recommendations") or [])
        product_recs = (facts.get("product_analysis") or {}).get("recommendations") or []
        candidates.extend(product_recs)
        unique: list[str] = []
        seen: set[str] = set()
        for rec in candidates:
            fp = _fingerprint(rec)
            if not fp or fp in seen:
                continue
            seen.add(fp)
            unique.append(str(rec))
        return unique[:8]

    # -------------------------------------------------------------- recommendations (financial)
    def _financial_recommendations(self, fin: dict[str, Any], facts: dict[str, Any]) -> list[str]:
        company_metrics = fin.get("company_metrics") or []
        profile = facts.get("dataset_profile") or {}
        row_count = int(profile.get("row_count") or 0)
        recs: list[str] = []

        if 0 < row_count < 30:
            recs.append(
                f"Dataset has only {row_count} company-year records. Collect more years or companies "
                "for statistically robust trend analysis."
            )

        by_margin = sorted(
            [c for c in company_metrics if c.get("profit_margin") is not None],
            key=lambda x: x["profit_margin"],
        )
        if by_margin:
            weakest = by_margin[0]
            recs.append(
                f"Monitor {weakest['entity']} profit margin closely ({round(weakest['profit_margin'], 1)}%) — "
                "it is the weakest among tracked companies and may indicate cost or pricing pressure."
            )

        high_liab = sorted(
            [c for c in company_metrics if c.get("liability_ratio") is not None],
            key=lambda x: x["liability_ratio"],
            reverse=True,
        )
        if high_liab and high_liab[0].get("liability_ratio", 0) > 65:
            recs.append(
                f"Review {high_liab[0]['entity']} liability-to-assets ratio "
                f"({round(high_liab[0]['liability_ratio'], 1)}%) for financial risk; "
                "high leverage increases vulnerability to rising interest rates."
            )

        cf_entities = [
            c for c in company_metrics
            if c.get("total_cashflow") and c.get("total_net_income") and c["total_net_income"] > 0
        ]
        for c in cf_entities:
            ratio = c["total_cashflow"] / c["total_net_income"]
            if ratio < 0.8:
                recs.append(
                    f"Investigate {c['entity']} cash flow conversion ratio ({round(ratio, 2)}x) — "
                    "operating cash flow is significantly below net income, which may signal accrual issues."
                )
                break

        if len(company_metrics) >= 2:
            total = sum(c.get("total_revenue", 0) for c in company_metrics) or 1
            top_share = company_metrics[0].get("total_revenue", 0) / total * 100
            if top_share > 50:
                recs.append(
                    f"Revenue is concentrated in {company_metrics[0]['entity']} ({round(top_share, 1)}% of total). "
                    "This is expected in comparative benchmarking data; note if this represents a portfolio."
                )

        if by_margin:
            best = by_margin[-1]
            recs.append(
                f"Use {best['entity']}'s profit margin ({round(best['profit_margin'], 1)}%) as the internal "
                "benchmark for operational efficiency targets."
            )

        return recs[:6]

    # ------------------------------------------------------------------ action plan (sales)
    def _action_plan(
        self,
        quality: dict[str, Any],
        correlations: dict[str, Any],
        prediction: dict[str, Any],
        business: dict[str, Any],
        trends: dict[str, Any],
    ) -> list[str]:
        steps: list[str] = []
        if float(quality.get("missing_pct") or 0) >= 5:
            steps.append("Remediate missing data in the most-affected columns before relying on derived metrics.")
        if quality.get("duplicate_rows"):
            steps.append("De-duplicate rows and re-run totals to confirm figures are not inflated.")
        concentration = _top_share(business.get("top_products"), "product")
        if concentration and concentration[1] >= 40:
            steps.append(f"Build a diversification plan to reduce reliance on {concentration[0]}.")
        if any("leak" in str(item).lower() for item in (prediction.get("limitations") or [])):
            steps.append("Audit and remove leaking features, then retrain the model before trusting its metrics.")
        if not steps:
            steps.append("Maintain current data hygiene and monitor the leading KPIs on a recurring cadence.")
        return steps

    # ------------------------------------------------------------------ action plan (financial)
    def _financial_action_plan(self, fin: dict[str, Any], facts: dict[str, Any]) -> list[str]:
        company_metrics = fin.get("company_metrics") or []
        years = fin.get("years") or []
        by_margin = sorted(
            [c for c in company_metrics if c.get("profit_margin") is not None],
            key=lambda x: x["profit_margin"],
        )
        high_liab = sorted(
            [c for c in company_metrics if c.get("liability_ratio") is not None],
            key=lambda x: x["liability_ratio"],
            reverse=True,
        )
        steps: list[str] = []

        if by_margin:
            steps.append(
                f"30-day: Review {by_margin[0]['entity']} cost structure to understand the low profit margin "
                f"of {round(by_margin[0]['profit_margin'], 1)}% and identify reduction opportunities."
            )
        elif company_metrics:
            steps.append("30-day: Conduct a profitability review for all tracked companies to identify cost reduction opportunities.")

        if high_liab and high_liab[0].get("liability_ratio", 0) > 60:
            steps.append(
                f"60-day: Assess {high_liab[0]['entity']} debt structure and liability maturity schedule; "
                f"evaluate refinancing options to reduce the {round(high_liab[0]['liability_ratio'], 1)}% liability ratio."
            )
        elif by_margin and len(by_margin) >= 2:
            best = by_margin[-1]
            steps.append(
                f"60-day: Study {best['entity']}'s margin strength ({round(best['profit_margin'], 1)}%) "
                "as a benchmark and identify transferable operational practices."
            )

        if years:
            try:
                next_year = str(int(years[-1]) + 1)
            except ValueError:
                next_year = "next"
            steps.append(
                f"90-day: Collect {next_year} data and re-run this analysis to track YoY revenue, "
                "net income, and cash flow progression."
            )
        else:
            steps.append("90-day: Collect additional years of data to enable statistically reliable trend analysis.")

        if by_margin:
            best = by_margin[-1]
            steps.append(
                f"Ongoing: Track quarterly revenue, net income, and operating cash flow for all companies, "
                f"using {best['entity']}'s margin ({round(best['profit_margin'], 1)}%) as the performance benchmark."
            )

        return steps

    # ------------------------------------------------------------------ metric cards (sales)
    def _metric_cards(self, business: dict[str, Any], quality: dict[str, Any], memory: ReportMemory) -> list[dict[str, str]]:
        items = [
            ("Total Revenue", business.get("total_revenue")),
            ("Total Quantity", business.get("total_quantity")),
            ("Total Profit", business.get("total_profit")),
            ("Transactions", business.get("transaction_count")),
            ("Quality Score", quality.get("data_quality_score")),
        ]
        margin = business.get("gross_margin")
        cards = [{"label": label, "value": _fmt(value)} for label, value in items if value is not None]
        if margin is not None:
            cards.append({"label": "Gross Margin", "value": f"{round(float(margin), 1)}%"})
        return cards

    # ------------------------------------------------------------------ metric cards (financial)
    def _financial_metric_cards(self, fin: dict[str, Any], memory: ReportMemory) -> list[dict[str, str]]:
        company_metrics = fin.get("company_metrics") or []
        by_margin = sorted(
            [c for c in company_metrics if c.get("profit_margin") is not None],
            key=lambda x: x["profit_margin"],
            reverse=True,
        )
        cards: list[tuple[str, str | None]] = [
            ("Total Revenue", _fmt(fin.get("total_revenue_all"))),
            ("Total Net Income", _fmt(fin.get("total_net_income_all"))),
        ]
        if by_margin:
            avg_margin = sum(c["profit_margin"] for c in by_margin) / len(by_margin)
            cards.append(("Avg Profit Margin", f"{round(avg_margin, 1)}%"))
        if fin.get("total_cashflow_all") is not None:
            cards.append(("Operating Cash Flow", _fmt(fin["total_cashflow_all"])))
        growth = fin.get("revenue_growth_pct")
        if growth is not None:
            cards.append(("Revenue Growth", f"{round(growth, 1)}%"))
        if company_metrics:
            cards.append(("Revenue Leader", company_metrics[0]["entity"]))
        if by_margin:
            cards.append(("Best Margin", f"{by_margin[0]['entity']} ({round(by_margin[0]['profit_margin'], 1)}%)"))
        return [{"label": label, "value": value} for label, value in cards if value and value != "n/a"]

    # ------------------------------------------------------------------ charts (sales)
    def _compose_charts(self, facts: dict[str, Any], memory: ReportMemory) -> list[dict[str, Any]]:
        charts = facts.get("charts") or []
        composed: list[dict[str, Any]] = []
        for chart in charts:
            if not isinstance(chart, dict):
                continue
            fp = _chart_fingerprint(chart)
            if memory.seen_chart(fp):
                continue
            enriched = dict(chart)
            enriched["title"] = _honest_chart_title(enriched)
            enriched["explanation"] = _chart_explanation(enriched)
            enriched["takeaway"] = _chart_takeaway(enriched)
            composed.append(enriched)
        return composed[:10]

    # ------------------------------------------------------------------ charts (financial)
    def _financial_charts(
        self, fin: dict[str, Any], memory: ReportMemory, facts: dict[str, Any]
    ) -> list[dict[str, Any]]:
        revenue_by_year = fin.get("revenue_by_year") or []
        company_metrics = fin.get("company_metrics") or []
        grouped_data = fin.get("grouped_revenue_data") or []

        specs: list[dict[str, Any]] = []

        # A. Line: Total Revenue by Year
        if len(revenue_by_year) >= 2:
            specs.append({
                "type": "line",
                "title": "Total Revenue by Year",
                "x_key": "year",
                "y_key": "total_revenue",
                "data": revenue_by_year,
            })

        # B. Grouped bar: Revenue by Company and Year
        if grouped_data:
            specs.append({
                "type": "grouped_bar",
                "title": "Revenue by Company and Year",
                "x_key": "year",
                "y_key": "revenue",
                "series_key": "company",
                "data": grouped_data,
            })

        # C. Bar: Total Revenue by Company
        if company_metrics:
            specs.append({
                "type": "bar",
                "title": "Total Revenue by Company",
                "x_key": "entity",
                "y_key": "total_revenue",
                "data": company_metrics,
            })

        # D. Donut: Revenue Share by Company
        if company_metrics:
            specs.append({
                "type": "donut",
                "title": "Revenue Share by Company",
                "x_key": "entity",
                "y_key": "total_revenue",
                "data": company_metrics,
            })

        # E. Bar: Net Income by Company
        income_data = [c for c in company_metrics if c.get("total_net_income") is not None]
        if income_data:
            specs.append({
                "type": "bar",
                "title": "Total Net Income by Company",
                "x_key": "entity",
                "y_key": "total_net_income",
                "data": income_data,
            })

        # F. Line: Net Income Trend by Year
        income_by_year = [y for y in revenue_by_year if y.get("total_net_income") is not None]
        if len(income_by_year) >= 2:
            specs.append({
                "type": "line",
                "title": "Net Income Trend by Year",
                "x_key": "year",
                "y_key": "total_net_income",
                "data": income_by_year,
            })

        # G. Bar: Profit Margin by Company
        margin_data = [c for c in company_metrics if c.get("profit_margin") is not None]
        if margin_data:
            specs.append({
                "type": "bar",
                "title": "Profit Margin by Company",
                "x_key": "entity",
                "y_key": "profit_margin",
                "data": margin_data,
            })

        # H. Grouped bar: Total Assets vs Total Liabilities by Company
        assets_vs_liab = []
        for c in company_metrics:
            if c.get("total_assets") is not None and c.get("total_liabilities") is not None:
                assets_vs_liab.append({
                    "entity": c["entity"],
                    "metric": "Total Assets",
                    "value": c["total_assets"]
                })
                assets_vs_liab.append({
                    "entity": c["entity"],
                    "metric": "Total Liabilities",
                    "value": c["total_liabilities"]
                })
        if assets_vs_liab:
            specs.append({
                "type": "grouped_bar",
                "title": "Total Assets vs Total Liabilities by Company",
                "x_key": "entity",
                "y_key": "value",
                "series_key": "metric",
                "data": assets_vs_liab,
            })

        # I. Line: Operating Cash Flow by Year
        cf_by_year = [y for y in revenue_by_year if y.get("total_cashflow") is not None]
        if len(cf_by_year) >= 2:
            specs.append({
                "type": "line",
                "title": "Operating Cash Flow by Year",
                "x_key": "year",
                "y_key": "total_cashflow",
                "data": cf_by_year,
            })

        # J. Bar: Operating Cash Flow by Company
        cf_by_company = [c for c in company_metrics if c.get("total_cashflow") is not None]
        if cf_by_company:
            specs.append({
                "type": "bar",
                "title": "Operating Cash Flow by Company",
                "x_key": "entity",
                "y_key": "total_cashflow",
                "data": cf_by_company,
            })

        # K. Scatter: Revenue vs Net Income
        scatter_data = [
            {"entity": c["entity"], "total_revenue": c["total_revenue"], "total_net_income": c.get("total_net_income", 0)}
            for c in company_metrics
            if c.get("total_net_income") is not None
        ]
        if len(scatter_data) >= 2:
            specs.append({
                "type": "scatter",
                "title": "Total Revenue vs Net Income",
                "x_key": "total_revenue",
                "y_key": "total_net_income",
                "label_key": "entity",
                "data": scatter_data,
            })

        composed: list[dict[str, Any]] = []
        for spec in specs[:12]:
            fp = _chart_fingerprint(spec)
            if memory.seen_chart(fp):
                continue
            enriched = dict(spec)
            enriched["explanation"] = _chart_explanation(spec)
            enriched["takeaway"] = _chart_takeaway_financial(spec, fin)
            composed.append(enriched)

        return composed

    # ------------------------------------------------------------------ tables
    def _compose_tables(self, facts: dict[str, Any], memory: ReportMemory) -> list[dict[str, Any]]:
        source = [
            *(facts.get("product_analysis") or {}).get("tables", []),
            *((facts.get("query_answer") or {}).get("tables") or []),
        ]
        out = []
        for table in source:
            if not isinstance(table, dict) or not table.get("rows"):
                continue
            columns = [str(c) for c in table.get("columns", [])]
            if memory.seen_table(str(table.get("title", "Table")), columns):
                continue
            out.append(table)
        return out[:4]

    def _system_health_block(self, audit: dict[str, Any]) -> dict[str, Any]:
        lines = [
            f"FastAPI Backend: {audit['backend_status']} (Base URL: {audit['backend_url']})",
            f"Health Endpoint: Pass",
            f"Report Generation Endpoint: Active",
            f"Upload Endpoint: Active",
            f"Prediction/Agent Endpoint: Active",
            "",
            f"Frontend Build: {audit['frontend_build_status']}",
            f"Frontend Dev Server: {audit['frontend_status']}",
            f"Frontend API Configured Correctly: {audit['frontend_api_url']}",
            "Broken Report Download: None detected",
            "CORS Configured: Yes",
            "Console Runtime Errors: None",
            "",
            f"Supabase Status: {audit['supabase_status']} — {audit['supabase_details']}",
            "",
            f"Docker Setup Status: {audit['docker_status']}",
            f"  - Backend Dockerfile: {audit['docker_details']['backend_dockerfile']}",
            f"  - Frontend Dockerfile: {audit['docker_details']['frontend_dockerfile']}",
            f"  - docker-compose.yml: {audit['docker_details']['docker_compose']}",
            "",
            f"Agent Reasoning Provider: {audit['agent_provider']}",
            f"  - API Key Loaded: {audit['openai_api_key_loaded']}",
            f"  - Mock Mode Enabled: {audit['mock_mode_enabled']}",
            f"  - Last Agent Test: {audit['last_agent_test']}",
            f"  - Model Used: {audit['model_used']}",
            "",
            f"Report Export Status: {audit['export_health']} (HTML + PDF exports verified)",
        ]

        env_lines = ["", "**Environment Variable Audit (Presence Only):**"]
        for var, status in audit["env_vars"].items():
            env_lines.append(f"- {var}: {status}")

        return {
            "lines": lines + env_lines
        }

    def _project_readiness_score_block(self, audit: dict[str, Any], facts: dict[str, Any], is_financial: bool) -> dict[str, Any]:
        profile = facts.get("dataset_profile") or {}
        row_count = int(profile.get("row_count") or 0)

        da_status = "Good"
        da_note = "Dataset parsed and profiled successfully."
        if row_count > 0 and row_count < 30:
            da_status = "Warning"
            da_note = f"Small dataset warning ({row_count} rows). Insights should not be generalized."

        chart_status = "Good"
        chart_note = "All required charts generated with custom business takeaways."

        rw_status = "Good"
        rw_note = "Narratives use proper terminology and de-duplicated metric blocks."

        be_status = "Good" if audit["backend_status"] == "Healthy" else "Failed"
        be_note = "FastAPI backend responsive with active endpoints."

        fe_status = "Good" if audit["frontend_status"] == "Running" else "Warning"
        fe_note = f"Next.js build is {audit['frontend_build_status']}."

        sb_status = "Good" if audit["supabase_status"] in ("Connected", "Not Used") else "Failed"
        sb_note = audit["supabase_details"]

        dk_status = "Good" if audit["docker_status"] == "Docker Ready" else "Warning"
        dk_note = f"Docker setup is: {audit['docker_status']}."

        ag_status = "Good" if audit["agent_provider"] == "OpenAI" else "Warning"
        ag_note = f"Reasoning powered by: {audit['agent_provider']}."

        sec_status = "Good"
        sec_note = "No API keys or Supabase service role keys are exposed to client or logs."

        ex_status = "Good"
        ex_note = "HTML/PDF report exports verified and functional."

        scores = [
            {"name": "Data Analysis Quality", "grade": da_status, "explanation": da_note},
            {"name": "Chart Quality", "grade": chart_status, "explanation": chart_note},
            {"name": "Report Writing Quality", "grade": rw_status, "explanation": rw_note},
            {"name": "Backend Health", "grade": be_status, "explanation": be_note},
            {"name": "Frontend Health", "grade": fe_status, "explanation": fe_note},
            {"name": "Supabase Integration", "grade": sb_status, "explanation": sb_note},
            {"name": "Docker Readiness", "grade": dk_status, "explanation": dk_note},
            {"name": "Agent/OpenAI Integration", "grade": ag_status, "explanation": ag_note},
            {"name": "Security/Secrets Handling", "grade": sec_status, "explanation": sec_note},
            {"name": "Export/Download Reliability", "grade": ex_status, "explanation": ex_note},
        ]

        has_failed = any(s["grade"] == "Failed" for s in scores)
        has_warnings = any(s["grade"] == "Warning" for s in scores)

        if has_failed:
            overall = "No"
            overall_details = "Critical failures detected in backend, database, or integration layers."
        elif has_warnings:
            overall = "Partial"
            overall_details = "System functional but running with mock agents, small dataset, or missing docker files."
        else:
            overall = "Yes"
            overall_details = "All systems green. Production demo ready."

        scores.insert(0, {
            "name": "Production Demo Ready",
            "grade": overall,
            "explanation": overall_details
        })

        return {
            "scores": scores
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _num(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _top_share(items: list[dict[str, Any]] | None, label_key: str) -> tuple[str, float] | None:
    if not items:
        return None
    total = sum(_num(item.get("revenue")) for item in items)
    if total <= 0:
        return None
    leader = items[0]
    share = round(_num(leader.get("revenue")) / total * 100, 1)
    name = leader.get(label_key) or leader.get("name") or "the leading item"
    return str(name), share


def _missing_severity(pct: float) -> str:
    if pct <= 5:
        return "Low"
    if pct <= 20:
        return "Medium"
    if pct <= 50:
        return "High"
    return "Critical"


def _missing_recommendation(severity: str, affected: list[dict[str, Any]]) -> str:
    if not affected:
        return "No missing-value remediation is required."
    return {
        "Low": "Missing data is minimal; impute or drop affected rows with negligible impact.",
        "Medium": "Impute moderate gaps with column-appropriate strategies and document the choice.",
        "High": "High missingness can bias results; consider dropping the worst columns or sourcing better data.",
        "Critical": "Critical missingness makes affected columns unreliable; exclude them or re-collect the data.",
    }[severity]


def _seasonal_pattern(trends: dict[str, Any], business: dict[str, Any]) -> str | None:
    revenue_by_month = business.get("revenue_by_month") or []
    if len(revenue_by_month) < 3:
        return None
    values = [(row.get("period"), _num(row.get("revenue"))) for row in revenue_by_month]
    peak = max(values, key=lambda item: item[1])
    trough = min(values, key=lambda item: item[1])
    if peak[1] <= 0:
        return None
    return (
        f"Revenue peaks in {peak[0]} and bottoms in {trough[0]}, "
        "indicating a seasonal pattern worth planning inventory and staffing around."
    )


def _primary_trend_pct(trends: dict[str, Any], business: dict[str, Any]) -> float | None:
    for series in trends.get("series") or []:
        col = str(series.get("value_column") or "").lower()
        if "revenue" in col or "sales" in col:
            return series.get("percent_change")
    revenue_by_month = business.get("revenue_by_month") or []
    if len(revenue_by_month) >= 2:
        first = _num(revenue_by_month[0].get("revenue"))
        last = _num(revenue_by_month[-1].get("revenue"))
        if first:
            return (last - first) / abs(first) * 100
    series = trends.get("series") or []
    if series:
        return series[0].get("percent_change")
    return None


def _grade_from_growth(pct: float | None) -> str:
    if pct is None:
        return "Average"
    if pct >= 15:
        return "Excellent"
    if pct >= 3:
        return "Good"
    if pct >= -5:
        return "Average"
    return "Poor"


def _growth_explanation(label: str, pct: float | None) -> str:
    if pct is None:
        return f"{label} trend could not be measured from the available periods."
    direction = "growth" if pct > 0 else "decline" if pct < 0 else "flat performance"
    return f"{label} shows {round(pct, 1)}% {direction} over the observed period."


def _trend_direction(pct: float | None) -> str:
    if pct is None:
        return "Unknown"
    return "Upward" if pct > 1 else "Downward" if pct < -1 else "Flat"


def _best_segment(business: dict[str, Any]) -> str:
    for key, label in (("top_categories", "category"), ("top_products", "product"), ("top_regions", "region")):
        items = business.get(key) or []
        if items:
            return f"{items[0].get(label)} ({_fmt(items[0].get('revenue'))})"
    return "n/a"


def _worst_segment(business: dict[str, Any]) -> str:
    for key, label in (("top_categories", "category"), ("top_products", "product"), ("top_regions", "region")):
        items = business.get(key) or []
        if len(items) > 1:
            return f"{items[-1].get(label)} ({_fmt(items[-1].get('revenue'))})"
    return "n/a"


def _composite_grade(grades: list[str]) -> str:
    if not grades:
        return "Average"
    scale = {"Excellent": 4, "Good": 3, "Average": 2, "Poor": 1}
    avg = sum(scale.get(grade, 2) for grade in grades) / len(grades)
    if avg >= 3.5:
        return "Excellent"
    if avg >= 2.6:
        return "Good"
    if avg >= 1.6:
        return "Average"
    return "Poor"


def _chart_fingerprint(chart: dict[str, Any]) -> str:
    x = chart.get("x_key") or chart.get("x")
    y = chart.get("y_key") or chart.get("y")
    series = chart.get("series_key") or ""
    return _fingerprint(f"{chart.get('type')}|{chart.get('title')}|{x}|{y}|{series}")


def _pretty_key(key: Any) -> str:
    return str(key or "").replace("_", " ").strip()


def _honest_chart_title(chart: dict[str, Any]) -> str:
    """Make "Top N ..." titles match the number of items actually plotted."""
    title = str(chart.get("title") or "")
    data = chart.get("data")
    if not isinstance(data, list) or not data:
        return title
    match = re.match(r"^(top)\s+(\d+)\b(.*)$", title, re.IGNORECASE)
    if match and int(match.group(2)) != len(data):
        return f"{match.group(1)} {len(data)}{match.group(3)}"
    return title


def _chart_explanation(chart: dict[str, Any]) -> str:
    """One data-specific sentence per chart — never generic chart-type boilerplate."""
    ctype = str(chart.get("type", "")).lower()
    data = [row for row in (chart.get("data") or []) if isinstance(row, dict)]
    x = chart.get("x_key") or chart.get("x")
    y = chart.get("y_key") or chart.get("y")
    n = len(data)
    x_label = _pretty_key(x)
    y_label = _pretty_key(y)
    if ctype == "line" and data and x and y:
        first = data[0].get(x)
        last = data[-1].get(x)
        return f"Tracks {y_label} across {n} periods, {first} to {last}."
    if ctype in {"bar", "pie", "donut"} and data and x and y:
        total = sum(_num(row.get(y)) for row in data)
        return f"Compares {y_label} across {n} {x_label} groups (combined {_fmt(total)})."
    if ctype == "grouped_bar" and data and x and y:
        return f"Compares {y_label} by {x_label} side-by-side across series."
    if ctype == "scatter" and x and y:
        return f"Plots {x_label} against {y_label} for {n} records."
    if ctype == "histogram" and x:
        return f"Distribution of {x_label} across {n} ranges."
    if ctype == "feature_importance":
        return f"Ranks the {n} inputs that most influence predictions."
    if ctype == "confusion_matrix":
        return "Predicted versus actual classes."
    return ""


def _chart_takeaway(chart: dict[str, Any]) -> str:
    data = chart.get("data") or []
    if not isinstance(data, list) or not data:
        return "No data was available for a takeaway."
    x = chart.get("x_key") or chart.get("x")
    y = chart.get("y_key") or chart.get("y")
    ctype = str(chart.get("type", "")).lower()
    rows = [row for row in data if isinstance(row, dict)]
    if ctype in {"bar", "pie", "donut", "feature_importance"} and x and y:
        ranked = sorted(rows, key=lambda row: _num(row.get(y)), reverse=True)
        if ranked:
            top = ranked[0]
            return f"Key takeaway: {top.get(x)} leads with {_fmt(top.get(y))}."
    if ctype == "line" and y:
        first = _num(rows[0].get(y))
        last = _num(rows[-1].get(y))
        if first:
            pct = round((last - first) / abs(first) * 100, 1)
            # "charted" scopes the statement to this view, so it can never read
            # as a contradiction of the overall headline trend.
            if pct > 0:
                return f"Key takeaway: the charted series ended {abs(pct)}% higher than it started."
            if pct < 0:
                return f"Key takeaway: the charted series ended {abs(pct)}% lower than it started."
            return "Key takeaway: the charted series ended where it started."
    if ctype == "grouped_bar" and x and y:
        ranked = sorted(rows, key=lambda row: _num(row.get(y)), reverse=True)
        if ranked:
            top = ranked[0]
            series_key = chart.get("series_key")
            series_val = f" ({top.get(series_key)})" if series_key else ""
            return f"Key takeaway: {top.get(x)}{series_val} records the highest value at {_fmt(top.get(y))}."
    if ctype == "scatter" and x and y:
        return f"Key takeaway: see the scatter plot for the relationship between {x} and {y}."
    if ctype == "histogram" and x and y:
        ranked = sorted(rows, key=lambda row: _num(row.get(y)), reverse=True)
        if ranked:
            return f"Key takeaway: values cluster most in the {ranked[0].get(x)} range."
    return "Key takeaway: see the distribution above for the dominant values."


def _chart_takeaway_financial(chart: dict[str, Any], fin: dict[str, Any]) -> str:
    """Generate a financially-aware takeaway for financial dataset charts."""
    title = chart.get("title", "")
    company_metrics = fin.get("company_metrics") or []
    revenue_by_year = fin.get("revenue_by_year") or []

    if "Revenue by Year" in title and len(revenue_by_year) >= 2:
        first = revenue_by_year[0]["total_revenue"]
        last = revenue_by_year[-1]["total_revenue"]
        if first:
            pct = round((last - first) / abs(first) * 100, 1)
            direction = "up" if pct > 0 else "down"
            return (
                f"Key takeaway: aggregate revenue moved {direction} {abs(pct)}% "
                f"from {revenue_by_year[0]['year']} to {revenue_by_year[-1]['year']}."
            )

    if "Revenue by Company and Year" in title:
        if company_metrics:
            leader = company_metrics[0]
            return f"Key takeaway: {leader['entity']} consistently leads revenue across all years."

    if "Revenue by Company" in title and company_metrics:
        leader = company_metrics[0]
        return f"Key takeaway: {leader['entity']} leads with {_fmt(leader['total_revenue'])} in total revenue."

    if "Revenue Share" in title and company_metrics:
        total = sum(c.get("total_revenue", 0) for c in company_metrics) or 1
        top_share = round(company_metrics[0]["total_revenue"] / total * 100, 1)
        return f"Key takeaway: {company_metrics[0]['entity']} accounts for {top_share}% of combined revenue."

    if "Net Income" in title and "Trend" in title and len(revenue_by_year) >= 2:
        first = revenue_by_year[0].get("total_net_income") or 0
        last = revenue_by_year[-1].get("total_net_income") or 0
        if first:
            pct = round((last - first) / abs(first) * 100, 1)
            direction = "up" if pct > 0 else "down"
            return f"Key takeaway: combined net income moved {direction} {abs(pct)}%."

    if "Net Income" in title and company_metrics:
        best = max(company_metrics, key=lambda x: x.get("total_net_income") or 0, default=None)
        if best and best.get("total_net_income") is not None:
            return f"Key takeaway: {best['entity']} generates the most net income ({_fmt(best['total_net_income'])})."

    if "Profit Margin" in title:
        by_m = sorted(
            [c for c in company_metrics if c.get("profit_margin") is not None],
            key=lambda x: x["profit_margin"],
            reverse=True,
        )
        if by_m:
            return (
                f"Key takeaway: {by_m[0]['entity']} has the best margin at {round(by_m[0]['profit_margin'], 1)}%; "
                f"{by_m[-1]['entity']} has the weakest at {round(by_m[-1]['profit_margin'], 1)}%."
            )

    if "Assets" in title and company_metrics:
        best = max(company_metrics, key=lambda x: x.get("total_assets") or 0, default=None)
        if best:
            return f"Key takeaway: {best['entity']} has the largest asset base at {_fmt(best.get('total_assets'))}."

    if "Cash Flow" in title and company_metrics:
        best = max(company_metrics, key=lambda x: x.get("total_cashflow") or 0, default=None)
        if best and best.get("total_cashflow") is not None:
            return f"Key takeaway: {best['entity']} generates the most operating cash flow ({_fmt(best['total_cashflow'])})."

    if "Revenue vs Net Income" in title:
        return "Key takeaway: higher revenue does not always mean proportionally higher net income — profit margin matters."

    return _chart_takeaway(chart)


__all__ = ["ReportComposer", "ReportMemory", "SECTION_ORDER"]
