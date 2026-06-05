from __future__ import annotations

import pandas as pd

from app.services.business_metrics import answer_business_query, calculate_business_metrics
from app.services.analysis_pipeline import AnalysisPipeline
from app.services.query_planner import QueryPlanner
from app.services.semantic_mapper import SemanticMapper


def _mapped_metrics(df: pd.DataFrame, filename: str = "data.csv", query: str = "show revenue by month"):
    semantic_map = SemanticMapper().map_dataframe(df, filename=filename, query=query)
    business_metrics = calculate_business_metrics(df, semantic_map)
    query_plan = QueryPlanner().plan(query, semantic_map, {"row_count": len(df), "columns": list(df.columns)})
    query_answer = answer_business_query(query_plan, business_metrics)
    return semantic_map, business_metrics, query_plan, query_answer


def test_ai_khata_transaction_report_revenue_uses_sales_filter_only():
    df = pd.DataFrame(
        {
            "Date": ["2026-05-01", "2026-05-01", "2026-05-01", "2026-05-01"],
            "Time": ["11:43:40", "11:43:23", "11:43:10", "11:43:05"],
            "Category": ["UDHAAR", "EXPENSE", "SALES", "SALES"],
            "Item/Customer": ["Ali", "Rent", "General Entry", "burger"],
            "Amount (Rs)": [500, 500, 5000, 2000],
        }
    )

    semantic_map, metrics, query_plan, query_answer = _mapped_metrics(df, "ai_khata.csv")

    assert semantic_map["dataset_type"] == "transaction_ledger"
    assert semantic_map["column_roles"]["Category"] == "transaction_type"
    assert semantic_map["column_roles"]["Amount (Rs)"] == "amount"
    assert semantic_map["metrics"]["revenue"]["filter"]["column"] == "Category"
    assert metrics["total_revenue"] == 7000
    assert metrics["total_expenses"] == 500
    assert metrics["sales_transaction_count"] == 2
    assert metrics["revenue_by_month"] == [{"period": "2026-05", "revenue": 7000}]
    assert query_plan["intent"] == "revenue_trend"
    assert query_answer["tables"][0]["rows"] == [{"period": "2026-05", "revenue": 7000}]
    assert any("trend cannot be reliably detected" in item for item in metrics["data_limitations"])


def test_standard_mart_sales_uses_sales_column_for_revenue():
    df = pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-15", "2026-02-01"],
            "Product": ["Rice", "Oil", "Rice"],
            "Category": ["Grocery", "Grocery", "Grocery"],
            "Quantity": [2, 1, 3],
            "UnitPrice": [100, 500, 100],
            "Sales": [200, 500, 300],
        }
    )

    semantic_map, metrics, _query_plan, _query_answer = _mapped_metrics(df, "mart_sales.csv")

    assert semantic_map["dataset_type"] == "mart_sales"
    assert semantic_map["column_roles"]["Sales"] == "sales_revenue"
    assert metrics["total_revenue"] == 1000
    assert metrics["revenue_by_month"] == [{"period": "2026-01", "revenue": 700}, {"period": "2026-02", "revenue": 300}]
    assert {"product": "Rice", "revenue": 500} in metrics["top_products"]


def test_trending_product_report_uses_computed_product_charts():
    df = pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-15", "2026-02-01", "2026-02-12", "2026-03-01"],
            "Product": ["Rice", "Oil", "Rice", "Oil", "Rice"],
            "Category": ["Grocery", "Grocery", "Grocery", "Grocery", "Grocery"],
            "Quantity": [2, 1, 3, 4, 5],
            "Sales": [200, 500, 300, 800, 500],
            "Profit": [30, 75, 45, 120, 80],
        }
    )

    report = AnalysisPipeline().run_full_analysis(df, query="make a report of trending products in the form charts", run_predictions=False, run_xai=False)

    titles = [chart["title"] for chart in report["charts"]]
    assert "Top 10 Products by Revenue" in titles
    assert "Top 10 Products by Quantity" in titles
    assert "Monthly Revenue Trend for Top Products" in titles
    assert "Revenue Share" in titles
    assert report["product_analysis"]["top_products_by_revenue"][0] == {"product": "Oil", "revenue": 1300}
    assert report["business_summary"] == {}
    assert "sales Rs 0" not in report["executive_summary"]


def test_invoice_dataset_derives_revenue_from_quantity_times_price():
    df = pd.DataFrame(
        {
            "InvoiceDate": ["2026-03-01", "2026-03-02"],
            "InvoiceNo": ["INV-1", "INV-2"],
            "Item": ["Pen", "Notebook"],
            "Qty": [10, 3],
            "Price": [5, 50],
        }
    )

    semantic_map, metrics, _query_plan, _query_answer = _mapped_metrics(df, "invoices.csv")

    assert semantic_map["dataset_type"] == "invoice_sales"
    assert semantic_map["column_roles"]["InvoiceDate"] == "invoice_date"
    assert semantic_map["metrics"]["revenue"]["expression"] == "quantity * unit_price"
    assert metrics["total_revenue"] == 200
    assert metrics["revenue_by_month"] == [{"period": "2026-03", "revenue": 200}]


def test_ecommerce_dataset_uses_net_amount_for_revenue():
    df = pd.DataFrame(
        {
            "order_date": ["2026-04-01", "2026-04-02"],
            "sku": ["SKU-1", "SKU-2"],
            "customer_id": ["C1", "C2"],
            "net_amount": [1200, 800],
            "discount": [100, 50],
            "region": ["North", "South"],
        }
    )

    semantic_map, metrics, _query_plan, _query_answer = _mapped_metrics(df, "ecommerce_orders.csv")

    assert semantic_map["dataset_type"] == "ecommerce_orders"
    assert semantic_map["column_roles"]["net_amount"] == "net_sales"
    assert metrics["total_revenue"] == 2000
    assert metrics["revenue_by_month"] == [{"period": "2026-04", "revenue": 2000}]


def test_generic_dataset_does_not_hallucinate_sales_metrics():
    df = pd.DataFrame(
        {
            "Name": ["Alpha", "Beta", "Gamma"],
            "Score": [10, 20, 30],
            "Notes": ["ok", "review", "ok"],
        }
    )

    semantic_map, metrics, query_plan, query_answer = _mapped_metrics(df, "generic.csv")

    assert semantic_map["dataset_type"] == "generic_tabular"
    assert "revenue" not in semantic_map["metrics"]
    assert metrics["total_revenue"] is None
    assert query_plan["intent"] == "revenue_trend"
    assert query_answer["tables"][0]["rows"] == []
    assert any("No revenue metric" in item or "Revenue metric unavailable" in item for item in metrics["data_limitations"])


def test_food_dataset_is_not_labeled_generic():
    df = pd.DataFrame(
        {
            "food_name": ["Pizza", "Burger", "Biryani"],
            "food_description": ["cheesy flatbread", "grilled sandwich", "rice dish"],
            "main_ingredient": ["Cheese", "Beef", "Rice"],
            "cuisine": ["Italian", "American", "Pakistani"],
            "spice_level": ["Low", "Medium", "High"],
            "calories": [570, 650, 720],
            "category": ["Fast Food", "Fast Food", "Rice"],
        }
    )

    semantic_map = SemanticMapper().map_dataframe(df, filename="food_dataset_extended.csv")
    profile = AnalysisPipeline().profile_dataset(df)

    assert semantic_map["dataset_type"] == "food_dataset"
    assert profile["dataset_type"] == "food_dataset"
    assert profile["column_roles"]["food_name"] == "product"
