"""When a dataset has no literal `product` column, product ranking should fall
back to the most product-like categorical column (e.g. subcategory)."""
import pandas as pd

from app.services.business_metrics import calculate_business_metrics
from app.services.semantic_mapper import SemanticMapper


def test_top_products_falls_back_to_subcategory():
    df = pd.DataFrame(
        {
            "region": ["N", "S", "N", "S", "E", "W", "N", "S"],
            "subcategory": ["Soap", "Soap", "Shampoo", "Soap", "Shampoo", "Oil", "Soap", "Oil"],
            "total_sales": [100, 200, 150, 300, 120, 90, 110, 80],
            "quantity": [1, 2, 1, 3, 1, 1, 1, 1],
        }
    )
    sm = SemanticMapper().map_dataframe(df, filename="retail.csv")
    bm = calculate_business_metrics(df, sm)
    assert bm["top_products"], "expected product ranking to fall back to subcategory"
    assert len(bm["top_products"]) >= 1
    # rows must use the normalized "product" key so the answer layer can read them
    assert "product" in bm["top_products"][0], f"got keys {list(bm['top_products'][0])}"


def test_integer_coded_labels_are_prefixed_with_column_name():
    """Datasets with integer-coded categories should read like 'subcategory 3',
    never a bare '3' (which produces narrative like 'merchandising for 3')."""
    df = pd.DataFrame(
        {
            "region": [1, 2, 1, 2, 3, 4, 1, 2],
            "subcategory": [0, 0, 3, 0, 3, 7, 0, 7],
            "total_sales": [100, 200, 150, 300, 120, 90, 110, 80],
            "quantity": [1, 2, 1, 3, 1, 1, 1, 1],
        }
    )
    sm = SemanticMapper().map_dataframe(df, filename="retail.csv")
    bm = calculate_business_metrics(df, sm)
    top = bm["top_products"]
    assert top, "expected a product ranking"
    label = str(top[0]["product"])
    assert not label.strip().isdigit(), f"bare coded label leaked: {label!r}"
    assert "subcategory" in label.lower(), f"expected column-name prefix, got {label!r}"
