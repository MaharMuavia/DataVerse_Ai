"""Reject datasets outside the supported retail/mart-sales domain.

DataVerse is scoped to retail-mart analytics: the semantic mapper classifies
every upload, and anything that is not commerce data (a generic table, a
nutrition dataset, ...) is refused at upload time with a message that tells
the user what the system accepts. The gate is controlled by
``settings.RETAIL_ONLY_UPLOADS`` so tests and other deployments can disable it.
"""
from __future__ import annotations

from typing import Any

from ..core.config import settings

# The commerce family of semantic dataset types (see semantic_mapper.DATASET_TYPES).
RETAIL_DATASET_TYPES = {
    "mart_sales",
    "retail_sales",
    "invoice_sales",
    "ecommerce_orders",
    "pos_transactions",
    "transaction_ledger",
    "inventory",
    "customer_sales",
}


class UnsupportedDatasetDomainError(ValueError):
    """Raised when an upload is not a retail/mart-sales dataset."""


def ensure_retail_domain(semantic_map: dict[str, Any] | None) -> None:
    """Raise ``UnsupportedDatasetDomainError`` for non-retail datasets.

    No-op when ``RETAIL_ONLY_UPLOADS`` is disabled.
    """
    if not settings.RETAIL_ONLY_UPLOADS:
        return
    dataset_type = str((semantic_map or {}).get("dataset_type") or "generic_tabular")
    if dataset_type in RETAIL_DATASET_TYPES:
        return
    detected = dataset_type.replace("_", " ")
    raise UnsupportedDatasetDomainError(
        f"This workspace analyzes retail / mart sales data only. The uploaded file "
        f"looks like a '{detected}' dataset, which is outside that scope. Please "
        "upload retail sales data with columns such as product, quantity, "
        "price or revenue, and a sale date (e.g. mart POS transactions, "
        "e-commerce orders, or invoices)."
    )
