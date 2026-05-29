"""Safe predefined dataframe analytics tools for business questions."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .data_profiler import coerce_analysis_dataframe, detect_semantic_columns, profile_dataframe


def _round(value: Any, digits: int = 2) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return round(float(value), digits)
    return value


class AnalyticsTools:
    """Business analytics implemented with pandas, never generated code."""

    def __init__(self, df: pd.DataFrame):
        self.df = coerce_analysis_dataframe(df)
        self.profile = profile_dataframe(self.df)
        self.semantic = self.profile["semantic_columns"]

    def _metric_column(self, preferred: str | None = None) -> str | None:
        if preferred and preferred in self.df.columns:
            return preferred
        for role in ("revenue", "profit", "quantity", "price"):
            column = self.semantic.get(role)
            if column and column in self.df.columns and pd.api.types.is_numeric_dtype(self.df[column]):
                return column
        numeric_columns = self.df.select_dtypes(include=["number"]).columns.tolist()
        return str(numeric_columns[0]) if numeric_columns else None

    def _dimension_column(self, role: str, fallback: bool = True) -> str | None:
        column = self.semantic.get(role)
        if column and column in self.df.columns:
            return column
        if not fallback:
            return None
        candidates = self.df.select_dtypes(include=["object", "category"]).columns.tolist()
        return str(candidates[0]) if candidates else None

    def _base_result(self, intent: str, method: str) -> dict[str, Any]:
        return {
            "intent": intent,
            "answer": "",
            "method": method,
            "tables": [],
            "charts": [],
            "warnings": [],
            "recommendations": [],
        }

    def _table(self, columns: list[str], rows: list[dict[str, Any]], title: str) -> dict[str, Any]:
        return {"title": title, "columns": columns, "rows": rows}

    def _chart(self, chart_type: str, title: str, data: list[dict[str, Any]], x_key: str, y_key: str | None = None) -> dict[str, Any]:
        chart: dict[str, Any] = {"type": chart_type, "title": title, "data": data, "x_key": x_key}
        if y_key:
            chart["y_key"] = y_key
        return chart

    def _finish(self, result: dict[str, Any]) -> dict[str, Any]:
        if result.get("tables"):
            result["table"] = result["tables"][0]
        if result.get("charts"):
            result["chart"] = result["charts"][0]
        if result.get("warnings"):
            result["warning"] = result["warnings"][0]
        return result

    def top_products(self, limit: int = 10, metric: str | None = None, ascending: bool = False) -> dict[str, Any]:
        result = self._base_result("top_products", "Calculated total metric by product using pandas groupby and sorting.")
        product_col = self._dimension_column("product", fallback=True)
        metric_col = self._metric_column(metric)
        if not product_col or not metric_col:
            result["answer"] = "I need a product column and a numeric sales, revenue, quantity, or price column to rank products."
            result["warnings"].append("Missing required product or metric column.")
            return self._finish(result)

        grouped = (
            self.df.dropna(subset=[product_col])
            .groupby(product_col, dropna=False)[metric_col]
            .sum()
            .sort_values(ascending=ascending)
            .head(limit)
        )
        total = float(pd.to_numeric(self.df[metric_col], errors="coerce").sum())
        rows = [
            {
                product_col: str(name),
                f"total_{metric_col}": _round(value),
                "share_pct": _round((float(value) / total * 100) if total else 0, 1),
            }
            for name, value in grouped.items()
        ]
        leader = rows[0] if rows else None
        direction = "lowest" if ascending else "highest"
        if leader:
            result["answer"] = (
                f"{leader[product_col]} has the {direction} {metric_col} at "
                f"{leader[f'total_{metric_col}']:,.2f}, representing {leader['share_pct']}% of the dataset total."
            )
        else:
            result["answer"] = "No product rows were available after cleaning the dataset."
        result["tables"].append(self._table([product_col, f"total_{metric_col}", "share_pct"], rows, f"Products by {metric_col}"))
        result["charts"].append(self._chart("bar", f"Products by {metric_col}", rows, product_col, f"total_{metric_col}"))
        result["recommendations"].append("Use this ranking with trend analysis before making stock decisions.")
        return self._finish(result)

    def trending_products(self, limit: int = 10) -> dict[str, Any]:
        result = self._base_result(
            "trending_products",
            "Detected date, product, revenue and quantity columns, then compared recent period totals against previous period totals.",
        )
        product_col = self._dimension_column("product", fallback=False)
        date_col = self.semantic.get("date")
        revenue_col = self._metric_column(self.semantic.get("revenue"))
        quantity_col = self.semantic.get("quantity")

        if not product_col or not revenue_col:
            result["warnings"].append("Missing product or revenue/sales column. Falling back to product ranking.")
            fallback = self.top_products(limit=limit)
            fallback["intent"] = "top_products"
            fallback["warnings"].extend(result["warnings"])
            return self._finish(fallback)
        if not date_col or date_col not in self.df.columns:
            result["warnings"].append("No date column found, so true trend cannot be calculated. Falling back to top-selling products.")
            fallback = self.top_products(limit=limit)
            fallback["intent"] = "top_products"
            fallback["warning"] = result["warnings"][0]
            fallback["warnings"].extend(result["warnings"])
            return self._finish(fallback)

        working = self.df[[date_col, product_col, revenue_col] + ([quantity_col] if quantity_col in self.df.columns else [])].copy()
        working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
        working[revenue_col] = pd.to_numeric(working[revenue_col], errors="coerce")
        if quantity_col in working.columns:
            working[quantity_col] = pd.to_numeric(working[quantity_col], errors="coerce")
        working = working.dropna(subset=[date_col, product_col, revenue_col])
        if working.empty:
            result["answer"] = "The detected trend columns did not contain enough valid rows for time-series analysis."
            result["warnings"].append("Date/product/revenue rows are empty after parsing.")
            return self._finish(result)

        working["_period"] = working[date_col].dt.to_period("M")
        periods = sorted(working["_period"].dropna().unique())
        if len(periods) < 2:
            result["warnings"].append("Only one time period is present, so growth cannot be compared. Falling back to top-selling products.")
            fallback = self.top_products(limit=limit)
            fallback["intent"] = "top_products"
            fallback["warnings"].extend(result["warnings"])
            return self._finish(fallback)

        recent_period = periods[-1]
        previous_period = periods[-2]
        recent = working[working["_period"] == recent_period].groupby(product_col)[revenue_col].sum()
        previous = working[working["_period"] == previous_period].groupby(product_col)[revenue_col].sum()
        all_products = sorted(set(recent.index) | set(previous.index))

        rows = []
        for product in all_products:
            recent_value = float(recent.get(product, 0.0))
            previous_value = float(previous.get(product, 0.0))
            growth_pct = ((recent_value - previous_value) / previous_value * 100) if previous_value else (100.0 if recent_value > 0 else 0.0)
            row = {
                product_col: str(product),
                "previous_period": str(previous_period),
                "recent_period": str(recent_period),
                "previous_revenue": _round(previous_value),
                "recent_revenue": _round(recent_value),
                "growth_pct": _round(growth_pct, 1),
                "total_revenue": _round(working.loc[working[product_col] == product, revenue_col].sum()),
            }
            if quantity_col in working.columns:
                recent_qty = float(working[(working["_period"] == recent_period) & (working[product_col] == product)][quantity_col].sum())
                previous_qty = float(working[(working["_period"] == previous_period) & (working[product_col] == product)][quantity_col].sum())
                row["previous_quantity"] = _round(previous_qty)
                row["recent_quantity"] = _round(recent_qty)
            rows.append(row)

        rows.sort(key=lambda item: (item["growth_pct"], item["recent_revenue"]), reverse=True)
        rows = rows[:limit]
        columns = list(rows[0].keys()) if rows else [product_col, "previous_revenue", "recent_revenue", "growth_pct"]
        leader = rows[0] if rows else None
        if leader:
            result["answer"] = (
                f"{leader[product_col]} is the strongest trending product. Revenue increased from "
                f"{leader['previous_revenue']:,.2f} in {leader['previous_period']} to "
                f"{leader['recent_revenue']:,.2f} in {leader['recent_period']}, a {leader['growth_pct']}% change."
            )
        else:
            result["answer"] = "I could not compute product trends from the available rows."
        result["tables"].append(self._table(columns, rows, "Trending products"))
        result["charts"].append(self._chart("bar", "Revenue growth by product", rows, product_col, "growth_pct"))
        result["recommendations"].append("Prioritize products with both high growth and meaningful recent revenue.")
        return self._finish(result)

    def declining_products(self, limit: int = 10) -> dict[str, Any]:
        result = self.trending_products(limit=100)
        result["intent"] = "declining_products"
        rows = [row for row in result.get("tables", [{}])[0].get("rows", []) if row.get("growth_pct", 0) < 0]
        rows = sorted(rows, key=lambda row: row["growth_pct"])[:limit]
        if not rows:
            result["answer"] = "No declining products were detected in the most recent comparable period."
            result["tables"] = []
            result["charts"] = []
            return result
        columns = list(rows[0].keys())
        product_col = self._dimension_column("product", fallback=True) or columns[0]
        result["answer"] = f"{rows[0][product_col]} is declining fastest, with {rows[0]['growth_pct']}% revenue change."
        result["tables"] = [self._table(columns, rows, "Declining products")]
        result["charts"] = [self._chart("bar", "Declining products by growth rate", rows, product_col, "growth_pct")]
        return result

    def revenue_trend(self, period: str = "M") -> dict[str, Any]:
        result = self._base_result("revenue_trend", "Grouped the detected revenue metric by parsed date period.")
        date_col = self.semantic.get("date")
        metric_col = self._metric_column(self.semantic.get("revenue"))
        if not date_col or not metric_col:
            result["answer"] = "I need a date column and a revenue/sales column to calculate a revenue trend."
            result["warnings"].append("Missing date or revenue column.")
            return result

        working = self.df[[date_col, metric_col]].copy()
        working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
        working[metric_col] = pd.to_numeric(working[metric_col], errors="coerce")
        working = working.dropna(subset=[date_col, metric_col])
        working["_period"] = working[date_col].dt.to_period(period)
        grouped = working.groupby("_period")[metric_col].sum().sort_index()
        rows = [{"period": str(period_key), metric_col: _round(value)} for period_key, value in grouped.items()]
        if len(rows) >= 2:
            first = rows[0][metric_col]
            last = rows[-1][metric_col]
            change_pct = ((last - first) / first * 100) if first else 0
            result["answer"] = f"{metric_col} moved from {first:,.2f} to {last:,.2f}, a {change_pct:.1f}% change over the observed periods."
        elif rows:
            result["answer"] = f"{metric_col} totals {rows[0][metric_col]:,.2f} in the only detected period."
        else:
            result["answer"] = "No valid dated revenue rows were available."
        result["tables"].append(self._table(["period", metric_col], rows, f"{metric_col} trend"))
        result["charts"].append(self._chart("line", f"{metric_col} over time", rows, "period", metric_col))
        return result

    def dimension_performance(self, role: str, limit: int = 10) -> dict[str, Any]:
        result = self._base_result(f"{role}_performance", f"Grouped the metric by detected {role} column.")
        dimension_col = self._dimension_column(role, fallback=False)
        metric_col = self._metric_column(self.semantic.get("revenue"))
        if not dimension_col or not metric_col:
            result["answer"] = f"I need a {role} column and a numeric sales/revenue metric for this analysis."
            result["warnings"].append(f"Missing {role} or metric column.")
            return result

        grouped = self.df.groupby(dimension_col)[metric_col].agg(["sum", "mean", "count"]).sort_values("sum", ascending=False).head(limit)
        rows = [
            {
                dimension_col: str(name),
                f"total_{metric_col}": _round(row["sum"]),
                f"avg_{metric_col}": _round(row["mean"]),
                "records": int(row["count"]),
            }
            for name, row in grouped.iterrows()
        ]
        if rows:
            result["answer"] = f"{rows[0][dimension_col]} is the best-performing {role} by total {metric_col}."
        else:
            result["answer"] = f"No {role} performance rows could be computed."
        result["tables"].append(self._table(list(rows[0].keys()) if rows else [dimension_col], rows, f"{role.title()} performance"))
        result["charts"].append(self._chart("bar", f"{role.title()} performance", rows, dimension_col, f"total_{metric_col}"))
        return result

    def missing_value_report(self) -> dict[str, Any]:
        result = self._base_result("missing_values", "Counted missing cells and missing percentages per column.")
        rows = [
            {"column": column, "missing": info["count"], "missing_pct": info["pct"]}
            for column, info in self.profile["missing_values"].items()
            if info["count"] > 0
        ]
        rows.sort(key=lambda row: row["missing"], reverse=True)
        total_missing = self.profile["quality"]["total_missing"]
        result["answer"] = (
            f"The dataset has {total_missing:,} missing cells."
            if total_missing
            else "No missing values were detected in the uploaded dataset."
        )
        result["tables"].append(self._table(["column", "missing", "missing_pct"], rows, "Missing value report"))
        if rows:
            result["charts"].append(self._chart("bar", "Missing values by column", rows, "column", "missing"))
        return result

    def data_quality_report(self) -> dict[str, Any]:
        result = self._base_result("data_quality", "Profiled missing values, duplicates, data types and semantic columns.")
        quality = self.profile["quality"]
        result["answer"] = (
            f"Data quality score is {quality['score']}/100 with {quality['duplicate_rows']} duplicate rows "
            f"and {quality['total_missing']} missing cells."
        )
        rows = self.profile["column_profiles"]
        result["tables"].append(self._table(["name", "dtype", "role", "missing", "missing_pct", "unique"], rows, "Column quality profile"))
        if quality["duplicate_rows"]:
            result["recommendations"].append("Review duplicate rows before making operational decisions.")
        if quality["total_missing"]:
            result["recommendations"].append("Handle missing values in columns with high business importance.")
        return result

    def correlation_analysis(self) -> dict[str, Any]:
        result = self._base_result("correlation", "Computed Pearson correlations across numeric columns.")
        numeric = self.df.select_dtypes(include=["number"]).columns.tolist()
        if len(numeric) < 2:
            result["answer"] = "At least two numeric columns are required for correlation analysis."
            result["warnings"].append("Not enough numeric columns.")
            return result
        corr = self.df[numeric].corr()
        rows = []
        for i, col_a in enumerate(numeric):
            for col_b in numeric[i + 1:]:
                rows.append({"metric_a": col_a, "metric_b": col_b, "correlation": _round(corr.loc[col_a, col_b], 3)})
        rows.sort(key=lambda row: abs(row["correlation"] or 0), reverse=True)
        result["answer"] = (
            f"The strongest relationship is {rows[0]['metric_a']} vs {rows[0]['metric_b']} "
            f"with correlation {rows[0]['correlation']}."
            if rows else "No numeric correlation pairs were available."
        )
        result["tables"].append(self._table(["metric_a", "metric_b", "correlation"], rows[:10], "Top correlations"))
        return result

    def outlier_detection(self) -> dict[str, Any]:
        result = self._base_result("outliers", "Applied the IQR rule to every numeric column.")
        rows = []
        for column in self.df.select_dtypes(include=["number"]).columns:
            series = pd.to_numeric(self.df[column], errors="coerce").dropna()
            if series.empty:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            low = q1 - 1.5 * iqr
            high = q3 + 1.5 * iqr
            count = int(((series < low) | (series > high)).sum())
            rows.append({"column": str(column), "outliers": count, "low_bound": _round(low), "high_bound": _round(high)})
        rows.sort(key=lambda row: row["outliers"], reverse=True)
        total = sum(row["outliers"] for row in rows)
        result["answer"] = f"I detected {total} potential outlier values using the IQR rule."
        result["tables"].append(self._table(["column", "outliers", "low_bound", "high_bound"], rows, "Outlier report"))
        return result

    def recommendations(self) -> dict[str, Any]:
        result = self._base_result("recommendations", "Combined product ranking, trend, quality and semantic profile signals.")
        trend = self.trending_products(limit=5)
        top = self.top_products(limit=5)
        recommendations = []
        if trend.get("intent") == "trending_products" and trend["tables"]:
            row = trend["tables"][0]["rows"][0]
            product_col = self._dimension_column("product", fallback=True)
            recommendations.append(f"Stock more {row[product_col]} if supply allows; it has the strongest recent growth.")
        if top["tables"]:
            row = top["tables"][0]["rows"][0]
            product_col = self._dimension_column("product", fallback=True)
            recommendations.append(f"Protect availability for {row[product_col]} because it leads total sales.")
        if self.profile["quality"]["total_missing"]:
            recommendations.append("Clean missing values before relying on fine-grained forecasts.")
        if not recommendations:
            recommendations.append("Upload date, product, revenue and quantity columns for stronger business recommendations.")

        result["answer"] = " ".join(recommendations)
        result["recommendations"] = recommendations
        if top["tables"]:
            result["tables"].append(top["tables"][0])
        if trend.get("charts"):
            result["charts"].append(trend["charts"][0])
        return result

    def forecast(self) -> dict[str, Any]:
        result = self.revenue_trend(period="M")
        result["intent"] = "forecast"
        rows = result["tables"][0]["rows"] if result["tables"] else []
        metric_col = self._metric_column(self.semantic.get("revenue"))
        if len(rows) < 3 or not metric_col:
            result["answer"] = "At least three dated revenue periods are required for a simple forecast."
            result["warnings"].append("Insufficient history for forecast.")
            return result
        values = [row[metric_col] for row in rows]
        average_change = float(np.diff(values).mean())
        next_value = max(0.0, values[-1] + average_change)
        result["answer"] = f"Using a simple average-change baseline, the next period is forecast at {next_value:,.2f} {metric_col}."
        result["method"] = "Used monthly revenue totals and projected the next period with the average period-over-period change."
        result["tables"][0]["rows"].append({"period": "next", metric_col: _round(next_value)})
        result["charts"][0]["data"] = result["tables"][0]["rows"]
        return result
