"""Retail Dataset Detector Agent.

Validates that uploaded datasets are retail-mart related by checking for required
product, sales, and date columns.
"""
from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd

from .base_agent import BaseAgent
from ..state.session_state import SessionState
from ..data.data_manager import DataManager
from ..core.logger import logger
from ..core.exceptions import DataNotFoundError


class RetailDetectorAgent(BaseAgent):
    """Detects and validates retail-mart datasets.
    
    Checks for presence of:
    - Product columns (product_name, product_id, item, sku, etc.)
    - Sales columns (units_sold, quantity, revenue, sales, etc.)
    - Date columns (order_date, sale_date, date, timestamp, etc.)
    """
    
    PRODUCT_INDICATORS = {
        'product_name', 'product_id', 'item', 'sku', 'product', 
        'name', 'title', 'description', 'model_name',
        'itemname', 'product_title', 'item_name'
    }
    SALES_INDICATORS = {
        'units_sold', 'quantity', 'revenue', 'sales', 'amount', 
        'price', 'total', 'qty', 'quantity_sold', 'unit_price',
        'unitprice', 'sales_amount', 'sales_value'
    }
    DATE_INDICATORS = {
        'order_date', 'sale_date', 'date', 'timestamp', 
        'created_at', 'purchase_date', 'sale_timestamp', 'orderdate',
        'saledate', 'transactiondate', 'ordertime'
    }

    def __init__(self, session_id: str) -> None:
        """Initialize the RetailDetectorAgent."""
        super().__init__(
            name="retail_detector",
            description="Validates datasets are retail-mart related",
            session_id=session_id
        )

    def _find_matching_columns(self, df: pd.DataFrame, indicators: set) -> List[str]:
        """Find columns matching given indicators (case-insensitive)."""
        matches = []
        col_norm = {col.lower().replace('_', '').replace(' ', ''): col for col in df.columns}
        indicators_norm = {ind.lower().replace('_', '').replace(' ', '') for ind in indicators}
        
        for norm_name, original_name in col_norm.items():
            if norm_name in indicators_norm:
                matches.append(original_name)
        return matches

    def run(self) -> Dict[str, Any]:
        """Execute retail dataset detection."""
        try:
            self.log_action("starting_retail_detection")
            dm = DataManager(session_id=self.session_id)
            df = dm.get_raw()
            
            product_cols = self._find_matching_columns(df, self.PRODUCT_INDICATORS)
            sales_cols = self._find_matching_columns(df, self.SALES_INDICATORS)
            date_cols = self._find_matching_columns(df, self.DATE_INDICATORS)
            
            is_valid = len(product_cols) > 0 and len(sales_cols) > 0 and len(date_cols) > 0
            
            result = {
                "is_retail": is_valid,
                "is_valid": is_valid,
                "product_column": product_cols[0] if product_cols else None,
                "sales_column": sales_cols[0] if sales_cols else None,
                "date_column": date_cols[0] if date_cols else None,
                "found_product_columns": product_cols,
                "found_sales_columns": sales_cols,
                "found_date_columns": date_cols,
                "missing_types": [],
                "message": "",
                "error": None
            }
            
            if not is_valid:
                missing = []
                if not product_cols:
                    missing.append("product/item")
                if not sales_cols:
                    missing.append("sales/quantity")
                if not date_cols:
                    missing.append("date")
                result["missing_types"] = missing
                result["message"] = f"Dataset NOT retail-compatible. Missing: {', '.join(missing)}"
            else:
                result["message"] = f"✓ Retail dataset detected. Product: {product_cols[0]}, Sales: {sales_cols[0]}, Date: {date_cols[0]}"
            
            state = SessionState.get(self.session_id)
            state.set("retail_validation", result)
            state.set("dataset_is_retail", is_valid)
            
            self.log_action("retail_detection_completed", {"is_valid": is_valid})
            return result
            
        except Exception as e:
            self.logger.exception(f"Retail detection failed: {e}")
            return {
                "is_retail": False,
                "is_valid": False,
                "product_column": None,
                "sales_column": None,
                "date_column": None,
                "found_product_columns": [],
                "found_sales_columns": [],
                "found_date_columns": [],
                "missing_types": [],
                "message": "",
                "error": str(e)
            }