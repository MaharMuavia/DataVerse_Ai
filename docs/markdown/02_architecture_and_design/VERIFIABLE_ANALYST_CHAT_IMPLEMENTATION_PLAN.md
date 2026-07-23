# Verifiable Analyst Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every KPI in the analyst chat carry a one-click "Show the math" receipt (deterministic provenance), delivered through a decomposed, Claude-style interactive dashboard, with CI running the test suite.

**Architecture:** The backend already computes metrics deterministically; we attach a parallel `provenance` channel (operation, formula, source columns, row count, contributing-row sample) inside `calculate_business_metrics`, flow it through the existing `kpis` array (no new plumbing), and render it in a new `KpiCard` expander. The 72KB `DashboardApp.tsx` monolith is split into focused components along the way.

**Tech Stack:** Python 3.12 / FastAPI / Pandas / pytest (backend); Next.js 15 / React 19 / Tailwind v4 / motion/react (frontend).

---

## Conventions

- **Backend working dir for tests:** `dataverse_backend`. Run pytest as `..\.venv\Scripts\python -m pytest` from there (per CLAUDE.md). On Git Bash use `../.venv/Scripts/python -m pytest`.
- **Backend changes are additive.** Existing keys/values in `business_metrics`/`facts`/responses are never removed or altered — only a new `provenance` key and a new `kpi.provenance` field are added, so `test_report_generator.py`, `test_mvp_e2e.py`, `test_analyze_endpoints.py` stay green.
- **Frontend has no component test runner** (only `node --test` on `scripts/*.test.mjs`). Frontend tasks are verified by `npm run lint`, `npm run build`, and a manual smoke check. Backend tasks use strict TDD with pytest.
- **Commit after every task.** Branch is `feat/verifiable-analyst-chat` (already created).

---

## File Structure

**Backend**
- Create `dataverse_backend/app/services/provenance.py` — provenance dataclass + builders (self-contained, pandas-only).
- Modify `dataverse_backend/app/services/business_metrics.py` — emit `provenance` dict in `calculate_business_metrics`; attach to `build_kpi_cards`.
- Modify `dataverse_backend/app/services/analysis_pipeline.py` — make `_default_kpis` delegate to `build_kpi_cards` (DRY + provenance).
- Create `dataverse_backend/tests/test_provenance.py` — the trust test.
- Modify `.github/workflows/ci.yml` — run pytest.

**Frontend**
- Modify `frontend/lib/dataverse-api.ts` — add `KpiProvenance` + `Kpi` types.
- Create `frontend/lib/dashboard-format.ts` — `formatCell`, `formatNumber` (moved out of the monolith).
- Create `frontend/components/dashboard/GlassCard.tsx` — extracted primitive.
- Create `frontend/components/dashboard/KpiCard.tsx` — **the signature "Show the math" component (new).**
- Create `frontend/components/dashboard/Composer.tsx` — query input + suggestion chips (extracted).
- Modify `frontend/components/dashboard/DashboardApp.tsx` — import the extracted pieces; render `KpiCard`; add per-message copy + markdown answer.

---

## PHASE 1 — Backend: provenance (the differentiator)

### Task 1: Provenance module

**Files:**
- Create: `dataverse_backend/app/services/provenance.py`
- Test: `dataverse_backend/tests/test_provenance.py`

- [ ] **Step 1: Write the failing test**

Create `dataverse_backend/tests/test_provenance.py`:

```python
import pandas as pd

from app.services.provenance import (
    build_series_provenance,
    build_derived_provenance,
    provenance_to_dict,
)


def test_series_provenance_records_sum_and_samples():
    df = pd.DataFrame({"product": ["A", "B", "C"], "revenue": [100, 300, 200]})
    series = df["revenue"]
    prov = build_series_provenance(
        metric_key="total_revenue",
        label="Total revenue",
        operation="SUM",
        series=series,
        df=df,
        source_columns=["revenue"],
        value=600,
    )
    data = provenance_to_dict(prov)
    assert data["value"] == 600
    assert data["operation"] == "SUM"
    assert data["row_count"] == 3
    assert data["source_columns"] == ["revenue"]
    # sample rows are the largest contributors, json-safe
    assert len(data["sample_rows"]) == 3
    assert data["sample_rows"][0]["revenue"] == 300


def test_derived_provenance_lists_components():
    prov = build_derived_provenance(
        metric_key="gross_margin",
        label="Gross margin",
        operation="DIVIDE",
        formula_plain="Total profit / total revenue * 100 = 25.0%",
        value=25.0,
        source_columns=["revenue", "cost"],
        components=[("total_profit", 150), ("total_revenue", 600)],
    )
    data = provenance_to_dict(prov)
    assert data["value"] == 25.0
    assert data["row_count"] == 2
    assert data["sample_rows"] == [
        {"component": "total_profit", "value": 150},
        {"component": "total_revenue", "value": 600},
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `dataverse_backend`): `../.venv/Scripts/python -m pytest tests/test_provenance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.provenance'`.

- [ ] **Step 3: Write minimal implementation**

Create `dataverse_backend/app/services/provenance.py`:

```python
"""Deterministic provenance ("receipts") for business metrics.

Self-contained: pandas + stdlib only, so it can be imported by
business_metrics without circular-import risk. Every receipt records HOW a
number was computed; the value itself is always the same value the metric
reports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class Provenance:
    metric_key: str
    label: str
    operation: str
    formula_plain: str
    source_columns: list[str]
    value: Any
    row_count: int
    sample_rows: list[dict[str, Any]] = field(default_factory=list)


def _coerce(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        return value
    try:
        import numpy as np

        if isinstance(value, np.generic):
            return value.item()
    except Exception:
        pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def _sample_rows(
    df: pd.DataFrame | None,
    series: pd.Series | None,
    source_columns: list[str],
    sample_n: int = 5,
) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    cols = [c for c in source_columns if c in df.columns]
    try:
        if series is not None:
            order = series.abs().sort_values(ascending=False)
            idx = list(order.index[:sample_n])
        else:
            idx = list(df.index[:sample_n])
        subset = df.loc[idx, cols] if cols else df.loc[idx]
    except Exception:
        subset = df.head(sample_n)[cols] if cols else df.head(sample_n)
    rows: list[dict[str, Any]] = []
    for record in subset.to_dict(orient="records"):
        rows.append({key: _coerce(val) for key, val in record.items()})
    return rows


def build_series_provenance(
    *,
    metric_key: str,
    label: str,
    operation: str,
    series: pd.Series | None,
    df: pd.DataFrame | None,
    source_columns: list[str],
    value: Any,
    sample_n: int = 5,
) -> Provenance:
    row_count = int(series.notna().sum()) if series is not None else 0
    cols = list(source_columns or [])
    col_text = ", ".join(f"`{c}`" for c in cols) if cols else "values"
    formula = f"{operation} of {col_text} across {row_count} rows = {value}"
    return Provenance(
        metric_key=metric_key,
        label=label,
        operation=operation,
        formula_plain=formula,
        source_columns=cols,
        value=_coerce(value),
        row_count=row_count,
        sample_rows=_sample_rows(df, series, cols, sample_n),
    )


def build_derived_provenance(
    *,
    metric_key: str,
    label: str,
    operation: str,
    formula_plain: str,
    value: Any,
    source_columns: list[str],
    components: list[tuple[str, Any]],
) -> Provenance:
    sample = [{"component": name, "value": _coerce(val)} for name, val in components]
    return Provenance(
        metric_key=metric_key,
        label=label,
        operation=operation,
        formula_plain=formula_plain,
        source_columns=list(source_columns or []),
        value=_coerce(value),
        row_count=len(components),
        sample_rows=sample,
    )


def provenance_to_dict(provenance: Provenance) -> dict[str, Any]:
    return {
        "metric_key": provenance.metric_key,
        "label": provenance.label,
        "operation": provenance.operation,
        "formula_plain": provenance.formula_plain,
        "source_columns": provenance.source_columns,
        "value": provenance.value,
        "row_count": provenance.row_count,
        "sample_rows": provenance.sample_rows,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `../.venv/Scripts/python -m pytest tests/test_provenance.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add dataverse_backend/app/services/provenance.py dataverse_backend/tests/test_provenance.py
git commit -m "feat(backend): deterministic provenance receipts module"
```

---

### Task 2: Emit provenance from `calculate_business_metrics`

**Files:**
- Modify: `dataverse_backend/app/services/business_metrics.py` (imports near line 8; computations ~line 23-90; return dict ~line 80-105)
- Test: `dataverse_backend/tests/test_provenance.py` (append)

- [ ] **Step 1: Write the failing test** (append to `tests/test_provenance.py`)

```python
def test_calculate_business_metrics_emits_matching_provenance():
    from app.services.business_metrics import calculate_business_metrics
    from app.services.semantic_mapper import SemanticMapper

    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "product": ["A", "B", "C"],
            "revenue": [100, 300, 200],
            "cost": [50, 150, 100],
        }
    )
    sm = SemanticMapper().map_dataframe(df, filename="sales.csv")
    bm = calculate_business_metrics(df, sm)

    prov = bm.get("provenance")
    assert isinstance(prov, dict)
    assert "total_revenue" in prov
    # the receipt value equals the reported metric value (the trust guarantee)
    assert prov["total_revenue"]["value"] == bm["total_revenue"]
    assert prov["total_revenue"]["operation"] == "SUM"
    assert prov["total_revenue"]["row_count"] == 3
    assert prov["transaction_count"]["value"] == bm["transaction_count"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../.venv/Scripts/python -m pytest tests/test_provenance.py::test_calculate_business_metrics_emits_matching_provenance -v`
Expected: FAIL with `KeyError`/`AssertionError` (no `provenance` key).

- [ ] **Step 3: Write minimal implementation**

In `business_metrics.py`, add the import after the existing import block (after line 8 `from .semantic_mapper import ...`):

```python
from .provenance import build_series_provenance, build_derived_provenance, provenance_to_dict
```

Then, immediately before the `return {` statement of `calculate_business_metrics` (currently ~line 80), insert the provenance assembly:

```python
    revenue_col = _metric_col(metrics.get("revenue"))
    quantity_col = _metric_col(metrics.get("quantity"))
    cost_col = _metric_col(metrics.get("cost"))
    expense_col = _metric_col(metrics.get("expense"))
    profit_col = _metric_col(metrics.get("profit"))

    provenance: dict[str, Any] = {}
    if revenue_series is not None:
        provenance["total_revenue"] = provenance_to_dict(build_series_provenance(
            metric_key="total_revenue", label="Total Sales", operation="SUM",
            series=revenue_series, df=df,
            source_columns=[c for c in [revenue_col] if c], value=_money(total_revenue)))
    if quantity_series is not None:
        provenance["total_quantity"] = provenance_to_dict(build_series_provenance(
            metric_key="total_quantity", label="Total Quantity", operation="SUM",
            series=quantity_series, df=df,
            source_columns=[c for c in [quantity_col] if c], value=_money(total_quantity)))
    if cost_series is not None:
        provenance["total_cost"] = provenance_to_dict(build_series_provenance(
            metric_key="total_cost", label="Total Cost", operation="SUM",
            series=cost_series, df=df,
            source_columns=[c for c in [cost_col] if c], value=_money(total_cost)))
    if expense_series is not None:
        provenance["total_expenses"] = provenance_to_dict(build_series_provenance(
            metric_key="total_expenses", label="Total Expenses", operation="SUM",
            series=expense_series, df=df,
            source_columns=[c for c in [expense_col] if c], value=_money(total_expense)))
    if total_profit is not None:
        if profit_series is not None:
            provenance["total_profit"] = provenance_to_dict(build_series_provenance(
                metric_key="total_profit", label="Total Profit", operation="SUM",
                series=profit_series, df=df,
                source_columns=[c for c in [profit_col] if c], value=_money(total_profit)))
        else:
            base = total_cost if total_cost is not None else total_expense
            provenance["total_profit"] = provenance_to_dict(build_derived_provenance(
                metric_key="total_profit", label="Total Profit", operation="SUBTRACT",
                formula_plain=f"Total revenue - total cost = {_money(total_revenue)} - {_money(base)} = {_money(total_profit)}",
                value=_money(total_profit),
                source_columns=[c for c in [revenue_col, cost_col, expense_col] if c],
                components=[("total_revenue", _money(total_revenue)), ("total_cost_or_expense", _money(base))]))
    if gross_margin is not None:
        provenance["gross_margin"] = provenance_to_dict(build_derived_provenance(
            metric_key="gross_margin", label="Gross Margin", operation="DIVIDE",
            formula_plain=f"Total profit / total revenue * 100 = {round(float(gross_margin), 2)}%",
            value=round(float(gross_margin), 2),
            source_columns=[c for c in [revenue_col, cost_col, expense_col] if c],
            components=[("total_profit", _money(total_profit)), ("total_revenue", _money(total_revenue))]))
    if average_order_value is not None:
        provenance["average_order_value"] = provenance_to_dict(build_derived_provenance(
            metric_key="average_order_value", label="Average Order Value", operation="DIVIDE",
            formula_plain=f"Total revenue / sales transactions = {_money(total_revenue)} / {int(sales_transaction_count)} = {_money(average_order_value)}",
            value=_money(average_order_value),
            source_columns=[c for c in [revenue_col] if c],
            components=[("total_revenue", _money(total_revenue)), ("sales_transaction_count", int(sales_transaction_count))]))
    provenance["transaction_count"] = provenance_to_dict(build_series_provenance(
        metric_key="transaction_count", label="Transactions", operation="COUNT",
        series=None, df=df, source_columns=[], value=transaction_count))
```

Then add one line inside the returned dict (e.g. right after `"trend_warning": trend_warning,`):

```python
        "provenance": provenance,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `../.venv/Scripts/python -m pytest tests/test_provenance.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the existing suite to confirm no regressions**

Run: `../.venv/Scripts/python -m pytest -v`
Expected: all previously-passing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add dataverse_backend/app/services/business_metrics.py dataverse_backend/tests/test_provenance.py
git commit -m "feat(backend): emit provenance receipts from business metrics"
```

---

### Task 3: Attach provenance to KPI cards (DRY both builders)

**Files:**
- Modify: `dataverse_backend/app/services/business_metrics.py` (`build_kpi_cards` ~line 396)
- Modify: `dataverse_backend/app/services/analysis_pipeline.py` (import ~line 10; `_default_kpis` ~line 523)
- Test: `dataverse_backend/tests/test_provenance.py` (append)

- [ ] **Step 1: Write the failing test** (append)

```python
def test_kpi_cards_carry_provenance():
    from app.services.business_metrics import build_kpi_cards, calculate_business_metrics
    from app.services.semantic_mapper import SemanticMapper

    df = pd.DataFrame(
        {"product": ["A", "B"], "revenue": [100, 300], "cost": [40, 110]}
    )
    sm = SemanticMapper().map_dataframe(df, filename="sales.csv")
    bm = calculate_business_metrics(df, sm)
    cards = build_kpi_cards(bm)

    sales = next(c for c in cards if c["label"] == "Total Sales")
    assert "provenance" in sales
    assert sales["provenance"]["value"] == bm["total_revenue"]
    # cards without a receipt simply omit the field (graceful)
    assert all("label" in c and "value" in c for c in cards)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../.venv/Scripts/python -m pytest tests/test_provenance.py::test_kpi_cards_carry_provenance -v`
Expected: FAIL (no `provenance` key on the card).

- [ ] **Step 3: Write minimal implementation**

In `business_metrics.py`, replace the body of `build_kpi_cards` (lines 396-403) with:

```python
_KPI_METRIC_KEYS = {
    "Total Sales": "total_revenue",
    "Total Quantity": "total_quantity",
    "Total Profit": "total_profit",
    "Gross Margin": "gross_margin",
    "Transactions": "transaction_count",
}


def build_kpi_cards(business_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    cards = [
        {"label": "Total Sales", "value": business_metrics.get("total_revenue")},
        {"label": "Total Quantity", "value": business_metrics.get("total_quantity")},
        {"label": "Total Profit", "value": business_metrics.get("total_profit")},
        {"label": "Gross Margin", "value": None if business_metrics.get("gross_margin") is None else f"{business_metrics.get('gross_margin')}%"},
        {"label": "Transactions", "value": business_metrics.get("transaction_count")},
    ]
    provenance = business_metrics.get("provenance") or {}
    for card in cards:
        key = _KPI_METRIC_KEYS.get(card["label"])
        if key and key in provenance:
            card["provenance"] = provenance[key]
    return cards
```

In `analysis_pipeline.py`, update the import (line 10) to include `build_kpi_cards`:

```python
from .business_metrics import answer_business_query, build_kpi_cards, calculate_business_metrics, compute_product_trends
```

Then replace `_default_kpis` (lines 523-531) with a delegating version:

```python
def _default_kpis(business_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return build_kpi_cards(business_metrics)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `../.venv/Scripts/python -m pytest tests/test_provenance.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Run full suite**

Run: `../.venv/Scripts/python -m pytest -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add dataverse_backend/app/services/business_metrics.py dataverse_backend/app/services/analysis_pipeline.py dataverse_backend/tests/test_provenance.py
git commit -m "feat(backend): attach provenance to KPI cards (DRY builders)"
```

---

### Task 4: End-to-end — chat response carries KPI provenance

**Files:**
- Test: `dataverse_backend/tests/test_provenance.py` (append)

- [ ] **Step 1: Write the failing/affirming test** (append)

```python
def test_pipeline_facts_kpis_include_provenance():
    from app.services.analysis_pipeline import AnalysisPipeline

    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "product": ["A", "B", "C"],
            "revenue": [100, 300, 200],
            "cost": [50, 150, 100],
        }
    )
    facts = AnalysisPipeline().run_full_analysis(
        df, query="dataset overview", run_predictions=False, run_xai=False, use_llm=False
    )
    kpis = facts.get("kpis") or []
    assert kpis, "expected KPI cards"
    sales = next((c for c in kpis if c.get("label") == "Total Sales"), None)
    assert sales is not None
    assert sales.get("provenance") is not None
    assert sales["provenance"]["value"] == facts["business_metrics"]["total_revenue"]
    # provenance survived the json_safe pass (sample rows are plain dicts)
    assert isinstance(sales["provenance"]["sample_rows"], list)
```

- [ ] **Step 2: Run test**

Run: `../.venv/Scripts/python -m pytest tests/test_provenance.py::test_pipeline_facts_kpis_include_provenance -v`
Expected: PASS (provenance flows through `facts["kpis"]` and `json_safe`). If it fails because the overview intent returns `query_answer.kpis` without provenance, confirm Task 3 attached provenance inside `build_kpi_cards` (which `answer_business_query` calls) — it should now carry through.

- [ ] **Step 3: Commit**

```bash
git add dataverse_backend/tests/test_provenance.py
git commit -m "test(backend): assert KPI provenance flows through pipeline facts"
```

---

## PHASE 2 — Backend: CI runs the tests

### Task 5: CI runs pytest

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add a pytest step**

Replace the file contents of `.github/workflows/ci.yml` with:

```yaml
name: CI

on:
  push:
    branches: ["main", "master"]
  pull_request:
    branches: ["*"]

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: dataverse_backend
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install MVP dependencies
        run: python -m pip install -r requirements-mvp.txt

      - name: Compile Python files
        run: python -m compileall app graph agents config tools tests

      - name: Run tests
        run: python -m pytest -q
```

- [ ] **Step 2: Verify the test command locally (proxy for CI)**

Run (from `dataverse_backend`): `../.venv/Scripts/python -m pytest -q`
Expected: suite passes (the same command CI will run).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: install deps and run pytest, not just compileall"
```

---

## PHASE 3 — Frontend: receipts UI + monolith split

### Task 6: Add provenance types to the API client

**Files:**
- Modify: `frontend/lib/dataverse-api.ts` (line 99; type exports near line 93)

- [ ] **Step 1: Add the types**

In `frontend/lib/dataverse-api.ts`, immediately before `export type AnalysisResponse = {` (line 93), add:

```ts
export type KpiProvenance = {
  metric_key?: string;
  label?: string;
  operation: string;
  formula_plain: string;
  source_columns: string[];
  value: number | string | null;
  row_count: number;
  sample_rows: Record<string, unknown>[];
};

export type Kpi = {
  label: string;
  value: string | number | null;
  provenance?: KpiProvenance;
};
```

Then change line 99 from:

```ts
  kpis?: Array<{ label: string; value: string | number | null }>;
```

to:

```ts
  kpis?: Kpi[];
```

- [ ] **Step 2: Verify types compile**

Run (from `frontend`): `npm run lint`
Expected: no new errors from `dataverse-api.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/dataverse-api.ts
git commit -m "feat(frontend): Kpi + KpiProvenance types"
```

---

### Task 7: Extract format helpers and GlassCard from the monolith

**Files:**
- Create: `frontend/lib/dashboard-format.ts`
- Create: `frontend/components/dashboard/GlassCard.tsx`
- Modify: `frontend/components/dashboard/DashboardApp.tsx` (remove inline defs at lines 102-116 and 190-197; add imports)

- [ ] **Step 1: Create `frontend/lib/dashboard-format.ts`**

```ts
export const formatNumber = (value?: number) => {
  if (typeof value !== 'number') return '0';
  return new Intl.NumberFormat('en-US', { notation: value > 9999 ? 'compact' : 'standard' }).format(value);
};

export const formatCell = (value: unknown) => {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'number') return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
  return String(value);
};
```

- [ ] **Step 2: Create `frontend/components/dashboard/GlassCard.tsx`**

```tsx
import React from 'react';

export const GlassCard = ({ children, className = '', onClick }: { children: React.ReactNode; className?: string; onClick?: () => void }) => (
  <div
    onClick={onClick}
    className={`bg-[#FFFFFF]/60 backdrop-blur-xl border border-[#E2E8F0]/30 rounded-xl overflow-hidden ${onClick ? 'cursor-pointer hover:border-violet-500/50 hover:shadow-[0_0_20px_rgba(139,92,246,0.15)] transition-all duration-300' : ''} ${className}`}
  >
    {children}
  </div>
);
```

- [ ] **Step 3: Update `DashboardApp.tsx`**

Delete the inline `formatNumber` (lines 102-105), inline `formatCell` (lines 112-116), and inline `GlassCard` (lines 190-197). Add to the import block (after the `DropZone` import, ~line 38):

```tsx
import { GlassCard } from './GlassCard';
import { formatCell, formatNumber } from '@/lib/dashboard-format';
```

- [ ] **Step 4: Verify build**

Run (from `frontend`): `npm run lint && npm run build`
Expected: builds clean; no "formatCell is not defined" / duplicate-identifier errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/dashboard-format.ts frontend/components/dashboard/GlassCard.tsx frontend/components/dashboard/DashboardApp.tsx
git commit -m "refactor(frontend): extract GlassCard + format helpers from monolith"
```

---

### Task 8: The signature KpiCard with "Show the math"

**Files:**
- Create: `frontend/components/dashboard/KpiCard.tsx`
- Modify: `frontend/components/dashboard/DashboardApp.tsx` (KPI block lines 648-660; ChatMessage.kpis type line 51; import)

- [ ] **Step 1: Create `frontend/components/dashboard/KpiCard.tsx`**

```tsx
'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronDown, ShieldCheck } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { formatCell } from '@/lib/dashboard-format';
import type { Kpi } from '@/lib/dataverse-api';

export function KpiCard({ kpi }: { kpi: Kpi }) {
  const [open, setOpen] = useState(false);
  const prov = kpi.provenance;
  const columns = prov?.sample_rows?.length ? Object.keys(prov.sample_rows[0]) : [];

  return (
    <GlassCard className="p-4 bg-white border-[#E2E8F0]">
      <div className="text-[10px] text-[#64748B] uppercase font-semibold tracking-wider truncate">{kpi.label}</div>
      <div className="text-xl font-extrabold text-[#0F172A] mt-2 tracking-tight">{formatCell(kpi.value)}</div>

      {prov && (
        <>
          <button
            onClick={() => setOpen((v) => !v)}
            className="mt-2 flex items-center gap-1 text-[11px] font-semibold text-violet-600 hover:text-violet-700"
          >
            <ShieldCheck size={12} /> Show the math
            <ChevronDown size={12} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
          </button>

          <AnimatePresence initial={false}>
            {open && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.18 }}
                className="overflow-hidden"
              >
                <div className="mt-2 rounded-lg border border-violet-100 bg-violet-50/40 p-2.5 text-[11px] text-[#475569]">
                  <p className="font-medium text-[#334155]">{prov.formula_plain}</p>
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    <span className="rounded bg-white px-1.5 py-0.5 font-mono text-[10px] text-violet-700 border border-violet-100">{prov.operation}</span>
                    {prov.source_columns.map((c) => (
                      <span key={c} className="rounded bg-white px-1.5 py-0.5 font-mono text-[10px] text-[#64748B] border border-[#E2E8F0]">{c}</span>
                    ))}
                  </div>
                  {columns.length > 0 && (
                    <div className="mt-2 overflow-x-auto">
                      <table className="w-full text-left text-[10px]">
                        <thead>
                          <tr>
                            {columns.map((k) => (
                              <th key={k} className="pr-3 pb-1 font-semibold text-[#94A3B8]">{k}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {prov.sample_rows.map((row, i) => (
                            <tr key={i} className="border-t border-violet-100/60">
                              {columns.map((k) => (
                                <td key={k} className="pr-3 py-0.5 text-[#475569]">{formatCell(row[k])}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <p className="mt-2 flex items-center gap-1 text-[10px] text-emerald-600">
                    <ShieldCheck size={11} /> Verified deterministically from your rows
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </GlassCard>
  );
}
```

- [ ] **Step 2: Wire it into `DashboardApp.tsx`**

Add the import (near the other dashboard imports):

```tsx
import { KpiCard } from './KpiCard';
import type { Kpi } from '@/lib/dataverse-api';
```

Change the `ChatMessage` type's `kpis` field (line 51) from
`kpis?: Array<{ label: string; value: string | number | null }>;`
to
`kpis?: Kpi[];`

Replace the KPI render block (lines 652-657) — the `kpis.slice(0, 4).map(...)` returning inline `GlassCard`s — with:

```tsx
                  {kpis.slice(0, 4).map((kpi, idx) => (
                    <KpiCard key={idx} kpi={kpi} />
                  ))}
```

- [ ] **Step 3: Verify build**

Run (from `frontend`): `npm run lint && npm run build`
Expected: clean build.

- [ ] **Step 4: Manual smoke test**

Run `npm run dev` from the repo root, open the dashboard, upload `sample_sales.csv` (or any CSV with a `revenue` column), and confirm each KPI shows a "Show the math" link that expands to the formula, operation/column chips, a sample-rows table, and the "Verified deterministically" badge. KPIs without provenance render normally with no link.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/dashboard/KpiCard.tsx frontend/components/dashboard/DashboardApp.tsx
git commit -m "feat(frontend): KpiCard with Show-the-math provenance receipts"
```

---

### Task 9: Extract Composer + Claude-style copy/markdown on answers

**Files:**
- Create: `frontend/components/dashboard/Composer.tsx`
- Modify: `frontend/components/dashboard/DashboardApp.tsx` (query block lines 774-822; assistant answer rendering)
- Add dependency: `react-markdown`

- [ ] **Step 1: Install markdown renderer**

Run (from `frontend`): `npm install react-markdown`
Expected: adds `react-markdown` to `package.json` dependencies.

- [ ] **Step 2: Create `frontend/components/dashboard/Composer.tsx`**

```tsx
'use client';

import { useState } from 'react';
import { ArrowUp } from 'lucide-react';
import { GlassCard } from './GlassCard';

export function Composer({
  onSubmit,
  isQuerying,
  suggestedQuestions,
}: {
  onSubmit: (query: string) => void;
  isQuerying: boolean;
  suggestedQuestions: string[];
}) {
  const [value, setValue] = useState('');

  const send = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isQuerying) return;
    onSubmit(trimmed);
    setValue('');
  };

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Ask AnalystAgent</h4>
      <GlassCard className="p-4 bg-white border-[#E2E8F0] flex items-center gap-3">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask a question about this dataset (e.g. 'What are the top categories by sales?')..."
          className="flex-1 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-4 py-2.5 text-sm text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-violet-500/20 placeholder-[#94A3B8]"
          disabled={isQuerying}
          onKeyDown={(e) => {
            if (e.key === 'Enter') send(value);
          }}
        />
        <button
          onClick={() => send(value)}
          disabled={isQuerying}
          className="bg-violet-500 hover:bg-violet-600 text-white p-2.5 rounded-xl transition-all disabled:opacity-50"
        >
          <ArrowUp size={16} />
        </button>
      </GlassCard>
      {suggestedQuestions.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {suggestedQuestions.map((q, idx) => (
            <button
              key={idx}
              onClick={() => send(q)}
              disabled={isQuerying}
              className="text-xs bg-white hover:bg-violet-50 hover:text-violet-600 text-[#64748B] hover:border-violet-200 px-3 py-1.5 rounded-lg border border-[#E2E8F0] transition-all"
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Wire Composer into `DashboardApp.tsx`**

Add import: `import { Composer } from './Composer';`

Replace the entire query `<div className="space-y-3">…</div>` block (lines 774-822) with:

```tsx
            <Composer onSubmit={onSubmit} isQuerying={isQuerying} suggestedQuestions={suggestedQuestions} />
```

- [ ] **Step 4: Render the assistant answer as markdown with a copy button**

Locate where the assistant answer text is rendered in the message area (search `latestAssistant` / the answer string). Wrap the answer text with:

```tsx
import ReactMarkdown from 'react-markdown';
// ...
<div className="group relative">
  <div className="prose prose-sm max-w-none text-[#334155]">
    <ReactMarkdown>{answerText}</ReactMarkdown>
  </div>
  <button
    onClick={() => navigator.clipboard.writeText(answerText)}
    className="absolute right-0 top-0 opacity-0 group-hover:opacity-100 text-[11px] text-[#94A3B8] hover:text-violet-600 transition"
  >
    Copy
  </button>
</div>
```

(Replace `answerText` with the actual variable holding the assistant message string in that scope.)

- [ ] **Step 5: Verify build**

Run (from `frontend`): `npm run lint && npm run build`
Expected: clean build.

- [ ] **Step 6: Manual smoke test**

Run `npm run dev`, ask a follow-up question, confirm: input clears on send, suggestion chips submit, the answer renders with markdown formatting, and the Copy button appears on hover and copies the text.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/dashboard/Composer.tsx frontend/components/dashboard/DashboardApp.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): extract Composer; markdown + copy on answers"
```

---

### Task 10: Final verification

- [ ] **Step 1: Backend suite**

Run (from `dataverse_backend`): `../.venv/Scripts/python -m pytest -q`
Expected: all pass, including `test_provenance.py`.

- [ ] **Step 2: Frontend gates**

Run (from `frontend`): `npm run lint && npm run build && npm run test:dev`
Expected: all pass.

- [ ] **Step 3: Acceptance walkthrough** (matches spec §11)

Upload the sample sales dataset, ask for an overview. Confirm:
1. KPIs show working "Show the math" expanders whose value equals the KPI value and whose sample rows come from the dataset.
2. `DashboardApp.tsx` no longer defines `GlassCard`/`formatCell`/the inline composer; those live in their own files.
3. Copy + follow-up chips work; answers render as markdown.
4. `pytest` is wired in CI and `test_provenance.py` passes.

- [ ] **Step 4: Final commit (if any cleanup)**

```bash
git add -A
git commit -m "chore: verify verifiable-analyst-chat feature end to end"
```

---

## Out of Scope (explicit — follow-up specs)
- Converting the latest-result workspace into a full scrolling message thread.
- Provenance for EDA stats, correlations, and model metrics (depth B) + downloadable audit log.
- Live recompute with filters (depth C).
- Broad dead-code purge across `app/services/` and `app/agents/`.

## Self-Review Notes
- **Spec coverage:** differentiator (Tasks 1-4, 8), Claude-style interactivity (Tasks 8-9), monolith split (Tasks 7-9), CI fix (Task 5), data contract (Task 6) — all mapped.
- **Type consistency:** `Kpi`/`KpiProvenance` defined in Task 6 are the exact types consumed in Tasks 8-9; backend `provenance_to_dict` keys (`operation`, `formula_plain`, `source_columns`, `value`, `row_count`, `sample_rows`) match the `KpiProvenance` TS fields.
- **No placeholders:** every code step contains complete code; the only `answerText` substitution is explicitly flagged because the variable name is local to a region of the monolith the implementer will confirm on sight.
