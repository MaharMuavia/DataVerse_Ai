"""Heuristic query-routing must map free-form questions to the right intent."""
from app.services.query_planner import QueryPlanner


def _plan(q, dataset_type="retail_sales", metrics=None):
    sm = {"dataset_type": dataset_type, "metrics": metrics or {"revenue": {"source_column": "total_sales"}}}
    return QueryPlanner()._heuristic_plan(q, sm)


def test_sales_by_region_routes_to_region():
    assert _plan("show me sales by region").intent == "region_performance"
    assert _plan("revenue by region").intent == "region_performance"
    assert _plan("compare regions").intent == "region_performance"


def test_category_breakdown_and_profitability():
    assert _plan("sales by category").intent == "category_performance"
    assert _plan("which category is most profitable").intent == "category_performance"
    assert _plan("top categories").intent == "category_performance"


def test_hot_selling_product():
    assert _plan("what is the hot selling product").intent == "top_product"
    assert _plan("top selling products").intent == "top_product"
    assert _plan("best products by quantity").intent == "top_product"


def test_total_sales_and_profit_unaffected():
    assert _plan("tell me total sales").intent == "total_sales"
    assert _plan("what is the total profit").intent == "profit_summary"


def test_customer_breakdown():
    assert _plan("top customers by revenue").intent == "customer_analysis"
