# Verifiable Analyst Chat — Design Spec

- **Date:** 2026-06-24
- **Status:** Approved (depth A)
- **Project context:** Real product
- **Owner:** DataVerse AI

## 1. Problem & Opportunity

DataVerse AI already computes every metric deterministically in Pandas/scikit-learn;
the LLM only polishes narration. But the chat UI shows a *final number* and discards the
provenance — the user still has to trust it, exactly like they'd trust ChatGPT Advanced
Data Analysis or Julius AI, both of which can let an LLM fabricate numbers.

The opportunity: make the deterministic guarantee **visible and interactive**. Under every
number the analyst reports, the user can click **"Show the math"** and see the exact
operation, the source column(s), the row count, and a sample of the real rows that produced
it. This is something LLM-first tools structurally cannot promise. It is the product's
differentiator: **the analyst that shows its receipts.**

A secondary goal (real-product context): turn the workspace into a genuinely fluid,
Claude-style interactive chat, and fix two core issues encountered along the way (a 72KB
monolith component and a CI pipeline that never runs the tests).

## 2. Goals / Non-Goals

### Goals
1. **Verifiable numbers (the differentiator):** every business-metric KPI surfaced in chat
   carries a "receipt" — operation, plain-English formula, source columns, row count, and a
   sample of contributing rows — revealed by a click-to-expand control. The displayed value
   is unchanged; we attach metadata beside it.
2. **Claude-style interactive chat:** streaming markdown answers, copy-on-message,
   regenerate, suggested follow-up chips, smooth autoscroll, keyboard send, and the receipt
   expanders as the signature interaction.
3. **Maintainability fix:** decompose `frontend/components/dashboard/DashboardApp.tsx`
   (~1,100 lines / 72KB) into focused, independently-understandable components.
4. **CI fix:** CI runs the pytest suite, not only `python -m compileall`.

### Non-Goals (YAGNI for this spec)
- Provenance for EDA stats, correlations, or model metrics (that is depth B).
- Live recompute / interactive filtering with fresh receipts (depth C).
- A full dead-code purge across all of `app/services/` and `app/agents/`. We only touch
  modules on the live path; broad cleanup is a separate spec.
- Auth, marketing-site, or dark-theme changes.

## 3. The Differentiator in One Sentence

> Every number in a DataVerse answer comes with a one-click receipt proving how it was
> computed from your actual rows — a guarantee LLM-first analysts cannot make.

## 4. Architecture & Data Flow

```
Upload → DatasetAgent → AnalystAgent → AnalysisPipeline
  AnalysisPipeline._compute:
    calculate_business_metrics(df, semantic_map)
      └── ALSO emits provenance records (NEW)   ← provenance.py
    → facts["business_metrics"], facts["provenance"]  (NEW key)
  session_service.chat_message / analyze:
    builds kpis[] from facts → attaches kpi.provenance from facts["provenance"]  (NEW)
  → /api/sessions/{id}/messages response: kpis[] each optionally carry `provenance`
Frontend:
  ChatThread → MessageBubble → KpiCard
    KpiCard renders value + "Show the math" expander (NEW) reading kpi.provenance
```

The deterministic value path is untouched. Provenance is an **additive** parallel channel.

## 5. Backend Design

### 5.1 New module: `app/services/provenance.py`
A small, dependency-light helper. No scikit-learn, no LLM.

```python
@dataclass
class Provenance:
    metric_key: str            # "total_revenue"
    label: str                 # "Total revenue"
    operation: str             # "SUM" | "MEAN" | "COUNT" | "DIVIDE" | "SUBTRACT" ...
    formula_plain: str         # "Sum of `revenue` across 40 rows"
    source_columns: list[str]  # ["revenue"]
    value: float | int | None  # the SAME value the metric reports
    row_count: int             # rows that contributed (non-null)
    sample_rows: list[dict]    # up to N (default 5) contributing rows, json-safe

def build_series_provenance(metric_key, label, operation, series, df,
                            source_columns, sample_n=5) -> Provenance: ...
def build_derived_provenance(metric_key, label, operation, formula_plain,
                             value, source_columns, components) -> Provenance: ...
def provenance_to_dict(p: Provenance) -> dict: ...
```

- `sample_rows` is drawn from the rows that actually contribute (e.g. for `SUM(revenue)`,
  the top-N by `revenue`; for derived metrics, the components are listed instead).
- All values pass through the existing `json_safe` helper from `data_quality.py`.

### 5.2 Instrument `calculate_business_metrics`
Add a `collect_provenance: bool = True` path that, alongside each computed metric, appends a
`Provenance`. Covered metrics (the ones surfaced as KPIs): `total_revenue`, `total_profit`,
`total_quantity`, `total_cost`/`total_expenses`, `gross_margin`, `average_order_value`,
`transaction_count`. Return shape gains one key:

```python
return { ...existing..., "provenance": { metric_key: provenance_dict, ... } }
```

Existing keys and values are unchanged so current tests stay green.

### 5.3 Pipeline & response wiring
- `AnalysisPipeline._compute` lifts `business_metrics["provenance"]` to `facts["provenance"]`.
- `session_service`'s KPI builder attaches `provenance` to each KPI dict whose key has a
  receipt: `{ "label", "value", "provenance"? }`.
- `/api/sessions/{id}/messages` and `/analyze` responses carry it through unchanged plumbing.

### 5.4 The trust test
New `tests/test_provenance.py`: for a fixture dataset, assert for every receipt
`provenance.value == business_metrics[metric_key]` (after equal rounding), `row_count` matches
non-null count, and `sample_rows` are a subset of the dataframe. This makes the core guarantee
a regression test.

## 6. Frontend Design

### 6.1 Decompose the monolith
`DashboardApp.tsx` becomes a thin container (session state, layout, data fetching). Extract
into `frontend/components/dashboard/`:

| Component | Responsibility |
|---|---|
| `ChatThread.tsx` | Renders the ordered message list + autoscroll |
| `MessageBubble.tsx` | One message: role styling, markdown, copy, regenerate |
| `KpiCard.tsx` | A KPI value **+ "Show the math" receipt expander** (signature) |
| `ChartCard.tsx` | Wraps existing `SimpleChart` SVG rendering |
| `ResultTable.tsx` | Existing `ResultTable` extracted |
| `Composer.tsx` | Input box, keyboard send, suggested follow-up chips |

`ThinkingTrace` and `DropZone` already exist and are reused. Each extracted component has a
single clear purpose, typed props, and no hidden coupling to `DashboardApp` internals.

### 6.2 The "Show the math" receipt (signature interaction)
`KpiCard` shows the value and a subtle "Show the math" affordance. Expanding reveals:
- the plain-English formula (e.g. *"Sum of `revenue` across 40 rows = 21,630"*),
- operation + source column chips,
- a compact table of the sample contributing rows,
- a small "verified deterministically" badge.

Collapsed by default; animated expand (motion/react, already a dependency). If a KPI has no
`provenance`, the card renders exactly as today (graceful, additive).

### 6.3 Claude-style interactivity
- Streaming markdown rendering of assistant answers (reuse existing stream plumbing).
- Copy button per assistant message; regenerate last answer.
- Suggested follow-up chips from `suggestions`/`next_questions` (already returned).
- Smooth autoscroll that pauses when the user scrolls up; Enter to send, Shift+Enter newline.

### 6.4 API client
`lib/dataverse-api.ts`: extend the KPI type with optional `provenance` matching the backend
schema. Purely additive; no breaking change to the contract.

## 7. Data Contract (provenance)

```ts
type KpiProvenance = {
  operation: string;          // "SUM" | "MEAN" | ...
  formula_plain: string;
  source_columns: string[];
  value: number | null;
  row_count: number;
  sample_rows: Record<string, unknown>[];
};
type Kpi = { label: string; value: string | number | null; provenance?: KpiProvenance };
```

## 8. Core-Issue Fixes (in-path)
1. **Monolith split** — §6.1, the central maintainability win.
2. **CI runs pytest** — `.github/workflows/ci.yml` adds a step that installs
   `requirements-mvp.txt` and runs `pytest` from `dataverse_backend`, keeping the existing
   `compileall` step.

## 9. Testing Strategy
- `tests/test_provenance.py` — the trust test (§5.4) + sample-row correctness.
- Existing `tests/test_report_generator.py`, `test_mvp_e2e.py`, `test_analyze_endpoints.py`
  must stay green (additive backend changes).
- Frontend: `npm run lint` and `npm run build` pass; component extraction is behavior-
  preserving (same rendered output for messages with no provenance).

## 10. Risks & Mitigations
- **Risk:** sample rows leak unintended columns / large payloads. **Mitigation:** cap at 5
  rows, only include columns relevant to the metric + a few identifiers; json-safe coercion.
- **Risk:** monolith split introduces visual regressions. **Mitigation:** extract
  incrementally, behavior-preserving; verify `npm run build` + manual smoke after each.
- **Risk:** provenance value drifts from metric value. **Mitigation:** computed from the same
  series; asserted equal in the trust test.

## 11. Acceptance Criteria
1. Uploading the sample sales dataset and asking for an overview shows KPIs, each with a
   working "Show the math" expander whose value equals the KPI value and whose sample rows
   come from the dataset.
2. `DashboardApp.tsx` no longer contains the inlined `KpiCard`/`ResultTable`/`Composer`
   logic; those live in their own files; `npm run build` passes.
3. Streaming, copy, regenerate, and follow-up chips work in the chat.
4. `pytest` runs in CI and passes; `test_provenance.py` exists and passes.
