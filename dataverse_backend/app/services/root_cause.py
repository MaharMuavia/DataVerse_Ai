"""Agentic Root-Cause Investigator: deterministic "why did X change?" analysis.

Given a question like "Why did revenue drop in May?", the investigator runs a
multi-step, fully deterministic investigation:

1. resolve the metric (revenue / profit / quantity) from the question,
2. build the period-over-period series and locate the change being asked about,
3. decompose the change across every available dimension (product, category,
   region, customer) and rank drivers by their contribution to the delta,
4. split the change into price vs volume effects when possible,
5. emit an ordered investigation trace where each step carries a provenance
   receipt, so every claim is verifiable ("show the math").

No LLM is involved: the same question on the same data always produces the same
answer. Narration layers on top; it never originates a number.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .business_metrics import _first_role, _metric_col, _metric_series
from .provenance import build_derived_provenance, provenance_to_dict

# Dimensions in priority order: the most actionable explanation leads.
DIMENSION_PRIORITY: tuple[tuple[str, str], ...] = (
    ("product", "product"),
    ("category", "category"),
    ("region", "region"),
    ("customer", "customer"),
)

METRIC_WORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("profit", ("profit", "margin", "earnings")),
    ("quantity", ("quantity", "units", "qty")),
    ("revenue", ("revenue", "sales", "income", "turnover", "amount")),
)

DROP_WORDS = ("drop", "decline", "fall", "fell", "decrease", "down", "lower", "shrink", "dip")
RISE_WORDS = ("rise", "rose", "increase", "spike", "grow", "grew", "jump", "up", "higher", "improve")

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

WHY_PATTERNS = (
    "why", "reason", "what caused", "what drove", "cause of", "explain the",
    "root cause", "what happened to",
)


def is_why_question(question: str | None) -> bool:
    query = (question or "").lower()
    return any(pattern in query for pattern in WHY_PATTERNS) and (
        any(word in query for word in DROP_WORDS + RISE_WORDS)
        or any(word in query for words in (w for _, w in METRIC_WORDS) for word in words)
    )


def _round(value: Any) -> float:
    return round(float(value), 2)


def _metric_from_question(question: str) -> str:
    query = question.lower()
    for metric, words in METRIC_WORDS:
        if any(word in query for word in words):
            return metric
    return "revenue"


def _direction_from_question(question: str) -> str | None:
    query = question.lower()
    if any(word in query for word in DROP_WORDS):
        return "drop"
    if any(word in query for word in RISE_WORDS):
        return "rise"
    return None


def _named_period(question: str, periods: list[str]) -> str | None:
    query = question.lower()
    explicit = re.search(r"\b(20\d{2})-(\d{2})\b", query)
    if explicit and explicit.group(0) in periods:
        return explicit.group(0)
    year_match = re.search(r"\b(20\d{2})\b", query)
    for name, number in sorted(MONTH_NAMES.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{name}\b", query):
            candidates = [p for p in periods if p.endswith(f"-{number:02d}")]
            if year_match:
                candidates = [p for p in candidates if p.startswith(year_match.group(1))]
            if candidates:
                return sorted(candidates)[-1]
    return None


def _metric_series_for(df: pd.DataFrame, semantic_map: dict[str, Any], metric: str) -> pd.Series | None:
    metrics = semantic_map.get("metrics") or {}
    roles = semantic_map.get("column_roles") or {}
    warnings: list[str] = []
    series = _metric_series(df, metrics.get(metric), roles, warnings, metric_name=metric)
    if series is None and metric == "profit":
        revenue = _metric_series(df, metrics.get("revenue"), roles, warnings, metric_name="revenue")
        cost = _metric_series(df, metrics.get("cost"), roles, warnings, metric_name="cost")
        if revenue is not None and cost is not None:
            series = revenue - cost
    return series


def _unsupported(question: str | None, metric: str, reason: str) -> dict[str, Any]:
    return {
        "status": "unsupported",
        "question": question,
        "metric": metric,
        "reason": reason,
        "steps": [],
        "drivers": [],
        "breakdowns": {},
        "price_volume": None,
        "chart": None,
        "narrative": reason,
    }


def _rank_contributions(
    df_a: pd.DataFrame, df_b: pd.DataFrame, column: str, values_a: pd.Series, values_b: pd.Series,
    delta: float, limit: int = 7,
) -> list[dict[str, Any]]:
    group_a = values_a.groupby(df_a[column].fillna("Unknown").astype(str)).sum()
    group_b = values_b.groupby(df_b[column].fillna("Unknown").astype(str)).sum()
    labels = sorted(set(group_a.index) | set(group_b.index))
    rows = []
    for label in labels:
        before = float(group_a.get(label, 0.0))
        after = float(group_b.get(label, 0.0))
        contribution = after - before
        rows.append(
            {
                "value": str(label),
                "before": _round(before),
                "after": _round(after),
                "contribution": _round(contribution),
                "share_of_delta": round(contribution / delta, 4) if delta else None,
            }
        )
    rows.sort(key=lambda row: (-abs(row["contribution"]), row["value"]))
    return rows[:limit]


def _price_volume_split(
    df_a: pd.DataFrame, df_b: pd.DataFrame,
    revenue_a: pd.Series, revenue_b: pd.Series,
    quantity_a: pd.Series | None, quantity_b: pd.Series | None,
) -> dict[str, Any] | None:
    if quantity_a is None or quantity_b is None:
        return None
    rev_a, rev_b = float(revenue_a.sum()), float(revenue_b.sum())
    qty_a, qty_b = float(quantity_a.sum()), float(quantity_b.sum())
    if qty_a <= 0 or qty_b <= 0:
        return None
    price_a, price_b = rev_a / qty_a, rev_b / qty_b
    d_price, d_qty = price_b - price_a, qty_b - qty_a
    return {
        "price_effect": d_price * qty_a,
        "volume_effect": price_a * d_qty,
        "mix_effect": d_price * d_qty,
        "avg_price_before": _round(price_a),
        "avg_price_after": _round(price_b),
        "quantity_before": _round(qty_a),
        "quantity_after": _round(qty_b),
    }


def investigate(
    df: pd.DataFrame,
    semantic_map: dict[str, Any],
    question: str | None = None,
    metric: str | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    """Run the deterministic root-cause investigation. See module docstring."""
    question = question or ""
    metric = metric or _metric_from_question(question)
    metrics_spec = semantic_map.get("metrics") or {}

    values = _metric_series_for(df, semantic_map, metric)
    if values is None:
        return _unsupported(question, metric, f"No {metric} metric could be resolved from the dataset, so the change cannot be investigated.")

    date_col = _metric_col(metrics_spec.get("date")) or _first_role(semantic_map.get("column_roles") or {}, "date")
    if not date_col or date_col not in df.columns:
        return _unsupported(question, metric, "No date column was found, so period-over-period change cannot be investigated.")

    dates = pd.to_datetime(df[date_col], errors="coerce")
    mask = dates.notna()
    if not bool(mask.any()):
        return _unsupported(question, metric, "The date column could not be parsed, so period-over-period change cannot be investigated.")
    work = df.loc[mask].copy()
    values = values.loc[mask]
    periods_index = dates.loc[mask].dt.to_period("M")
    by_period = values.groupby(periods_index).sum().sort_index()
    period_labels = [str(p) for p in by_period.index]
    if len(period_labels) < 2:
        return _unsupported(question, metric, "Only one time period is available; at least two periods are needed to explain a change.")

    direction = _direction_from_question(question)
    target = period or _named_period(question, period_labels)
    if target and target in period_labels and period_labels.index(target) > 0:
        period_b = target
    else:
        changes = by_period.diff().dropna()
        if direction == "drop":
            pick = changes.idxmin()
        elif direction == "rise":
            pick = changes.idxmax()
        else:
            pick = changes.abs().idxmax()
        period_b = str(pick)
    idx_b = period_labels.index(period_b)
    period_a = period_labels[idx_b - 1]

    value_a = float(by_period.iloc[idx_b - 1])
    value_b = float(by_period.iloc[idx_b])
    delta = value_b - value_a
    pct_change = (delta / abs(value_a) * 100) if value_a else None

    labels = periods_index.astype(str)
    rows_a = labels == period_a
    rows_b = labels == period_b
    df_a, df_b = work.loc[rows_a.values], work.loc[rows_b.values]
    values_a, values_b = values.loc[rows_a.values], values.loc[rows_b.values]

    steps: list[dict[str, Any]] = []
    steps.append(
        {
            "action": f"Resolved metric '{metric}' and monthly series",
            "finding": f"{metric.title()} spans {len(period_labels)} periods ({period_labels[0]} to {period_labels[-1]}).",
            "receipt": None,
        }
    )
    delta_receipt = provenance_to_dict(
        build_derived_provenance(
            metric_key=f"{metric}_delta_{period_b}",
            label=f"{metric.title()} change {period_a} to {period_b}",
            operation="SUBTRACT",
            formula_plain=f"{metric} in {period_b} - {metric} in {period_a} = {_round(value_b)} - {_round(value_a)} = {_round(delta)}",
            value=_round(delta),
            source_columns=[date_col],
            components=[(period_a, _round(value_a)), (period_b, _round(value_b))],
        )
    )
    steps.append(
        {
            "action": f"Compared {period_b} against {period_a}",
            "finding": (
                f"{metric.title()} went from {_round(value_a)} to {_round(value_b)} "
                f"({'+' if delta >= 0 else ''}{_round(delta)}"
                + (f", {round(pct_change, 1)}%" if pct_change is not None else "")
                + ")."
            ),
            "receipt": delta_receipt,
        }
    )

    roles = semantic_map.get("column_roles") or {}
    breakdowns: dict[str, list[dict[str, Any]]] = {}
    primary_dimension: str | None = None
    for dimension, metric_key in DIMENSION_PRIORITY:
        column = _metric_col(metrics_spec.get(metric_key)) or _first_role(roles, dimension)
        if not column or column not in work.columns:
            continue
        if work[column].nunique(dropna=True) < 2:
            continue
        ranked = _rank_contributions(df_a, df_b, column, values_a, values_b, delta)
        if not ranked:
            continue
        breakdowns[dimension] = ranked
        if primary_dimension is None:
            primary_dimension = dimension
        top = ranked[0]
        share = top.get("share_of_delta")
        receipt = provenance_to_dict(
            build_derived_provenance(
                metric_key=f"{metric}_driver_{dimension}_{period_b}",
                label=f"Top {dimension} driver of the {period_b} change",
                operation="GROUP_DELTA",
                formula_plain=(
                    f"SUM({metric}) for {dimension}='{top['value']}' in {period_b} - same in {period_a} "
                    f"= {top['after']} - {top['before']} = {top['contribution']}"
                ),
                value=top["contribution"],
                source_columns=[column, date_col],
                components=[(row["value"], row["contribution"]) for row in ranked[:5]],
            )
        )
        steps.append(
            {
                "action": f"Decomposed the change by {dimension} ('{column}')",
                "finding": (
                    f"'{top['value']}' moved {metric} by {top['contribution']}"
                    + (f", explaining {round(share * 100, 1)}% of the change." if share is not None else ".")
                ),
                "receipt": receipt,
            }
        )

    if not breakdowns:
        return _unsupported(
            question, metric,
            "No categorical dimension (product/category/region/customer) was found to decompose the change.",
        )

    quantity_a = quantity_b = None
    if metric == "revenue":
        quantity = _metric_series_for(df, semantic_map, "quantity")
        if quantity is not None:
            quantity = quantity.loc[mask]
            quantity_a, quantity_b = quantity.loc[rows_a.values], quantity.loc[rows_b.values]
    price_volume = (
        _price_volume_split(df_a, df_b, values_a, values_b, quantity_a, quantity_b)
        if metric == "revenue"
        else None
    )
    if price_volume:
        steps.append(
            {
                "action": "Split the revenue change into price vs volume effects",
                "finding": (
                    f"Price effect {_round(price_volume['price_effect'])}, volume effect "
                    f"{_round(price_volume['volume_effect'])}, mix effect {_round(price_volume['mix_effect'])} "
                    f"(they sum exactly to the {_round(delta)} change)."
                ),
                "receipt": provenance_to_dict(
                    build_derived_provenance(
                        metric_key=f"revenue_price_volume_{period_b}",
                        label="Price vs volume decomposition",
                        operation="DECOMPOSE",
                        formula_plain=(
                            "delta_revenue = delta_price*qty_before + price_before*delta_qty + delta_price*delta_qty = "
                            f"{_round(price_volume['price_effect'])} + {_round(price_volume['volume_effect'])} "
                            f"+ {_round(price_volume['mix_effect'])} = {_round(delta)}"
                        ),
                        value=_round(delta),
                        source_columns=[date_col],
                        components=[
                            ("price_effect", _round(price_volume["price_effect"])),
                            ("volume_effect", _round(price_volume["volume_effect"])),
                            ("mix_effect", _round(price_volume["mix_effect"])),
                        ],
                    )
                ),
            }
        )

    drivers = breakdowns[primary_dimension]
    top = drivers[0]
    moved = "dropped" if delta < 0 else "rose"
    share_text = (
        f" '{top['value']}' alone explains {round(top['share_of_delta'] * 100, 1)}% of the change."
        if top.get("share_of_delta") is not None
        else ""
    )
    narrative = (
        f"{metric.title()} {moved} by {abs(_round(delta))} from {period_a} to {period_b} "
        f"({_round(value_a)} to {_round(value_b)}). The main {primary_dimension} driver is '{top['value']}' "
        f"({top['before']} to {top['after']}, contribution {top['contribution']}).{share_text}"
    )
    steps.append({"action": "Concluded the investigation", "finding": narrative, "receipt": None})

    chart = {
        "type": "bar",
        "title": f"What drove the {metric} change in {period_b} (by {primary_dimension})",
        "x_key": "segment",
        "y_key": "contribution",
        "data": [{"segment": row["value"], "contribution": row["contribution"]} for row in drivers],
    }

    return {
        "status": "complete",
        "question": question,
        "metric": metric,
        "direction": "drop" if delta < 0 else "rise",
        "period_a": period_a,
        "period_b": period_b,
        "value_a": _round(value_a),
        "value_b": _round(value_b),
        "delta": _round(delta),
        "pct_change": None if pct_change is None else round(pct_change, 2),
        "primary_dimension": primary_dimension,
        "drivers": drivers,
        "breakdowns": breakdowns,
        "price_volume": price_volume,
        "steps": steps,
        "chart": chart,
        "narrative": narrative,
    }
