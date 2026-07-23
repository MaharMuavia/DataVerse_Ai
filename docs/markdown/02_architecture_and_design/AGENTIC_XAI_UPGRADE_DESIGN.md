# Agentic + XAI Upgrade — Design

Date: 2026-07-03
Branch: feat/verifiable-analyst-chat

## Goal

Make DataVerse AI's "agentic AI + XAI" pitch literal and demo-winning by adding three
features, all preserving the deterministic-first guarantee (every number computed in
pandas/sklearn; the LLM only orchestrates and narrates):

1. **Root-Cause Investigator** — answers "why did X drop/rise?" with a multi-step,
   receipt-backed driver decomposition.
2. **Counterfactual XAI** — per-prediction "smallest change that flips the outcome".
3. **Agent loop for chat** — an LLM plan→act→observe loop over deterministic tools,
   with live progress trace and a deterministic fallback.

User confirmed: all three features; a working LLM API key is guaranteed at the demo.

## Constraints (from CLAUDE.md)

- Keep the two-agent boundary: all new capability lives in `app/services/`, invoked
  from the pipeline / session service — no new files in `app/agents/`.
- Deterministic-first: LLM never originates a number.
- Offline mode must keep working end-to-end (fallbacks everywhere).
- Reports stay 1–2 pages; existing test invariants stay green (141 tests).
- Do not break existing API routes.

## Feature 1 — Root-Cause Investigator

New service `app/services/root_cause.py`.

**Input:** df, semantic_map, a metric (revenue | profit | quantity | transaction count),
an optional focus period parsed from the question ("May", "2024-05", "last month"),
comparison period defaulting to the immediately preceding period.

**Algorithm (deterministic):**
1. Build a period series for the metric (reuse semantic_map date/amount columns).
2. Pick target period B and baseline period A; compute delta and % change.
3. For each candidate dimension present (product, category, region, customer):
   group the metric per period, compute per-group contribution `metric_B - metric_A`,
   rank by |contribution|, and report share of total delta explained.
4. Price-vs-volume split when price & quantity columns exist:
   `Δrevenue ≈ Δprice·qty_A + price_A·Δqty + Δprice·Δqty` (report all three terms).
5. Emit an ordered `steps` list — the investigation trace: each step has
   `{action, finding, receipt}` where receipt reuses `provenance.py` structures.

**Output shape:** `{question, metric, period_a, period_b, delta, pct_change, steps[],
drivers[], price_volume|null, chart, narrative}`. Chart = bar chart of top signed
contributions.

**Wiring:**
- `POST /api/sessions/{sid}/datasets/{did}/investigate` (body: question or
  metric/period) in `session_routes.py` + `SessionService.investigate_dataset`.
- Chat: "why/reason for/what caused/explain the drop|rise|spike" routes to the
  investigator (both in the intent_router fallback and as an agent-loop tool).
- Frontend: investigation trace rendered in chat (steps + drivers table + chart).

**Edge cases:** no date column → fall back to dimension-only comparison across the
whole dataset halves? No — return `status: "unsupported"` with a stated reason (no
fabricated periods). Single period only → same. Metric missing → stated reason.

## Feature 2 — Counterfactual XAI

New service `app/services/counterfactual.py`.

**Input:** `TrainedModelBundle` (existing dataclass), up to 3 rows from `X_test`.

**Algorithm (deterministic, no randomness):**
- Features ordered by model feature importance (existing fallback importance).
- For each candidate numeric feature: scan multipliers in a fixed grid
  (±5%, ±10%, ±15%, ±20%, ±30%, ±50%); for classification, stop at the smallest
  change that flips the predicted class; for regression, the smallest change that
  moves the prediction across the training-median of the target (or ≥15% shift).
- Single-feature counterfactuals only (interpretable); at most 2 per row.
- Categorical features: skipped in v1 (stated in limitations).

**Output:** appended to the existing XAI payload as
`counterfactuals: [{sample_index, target_before, target_after, changes:[{feature,
original, new, pct_change}], sentence}]` plus a `counterfactual_method` field.
`xai.explain_model` gains an optional bundle-based call; pipeline passes the bundle.

**Frontend:** XAI card gets a "What would change this outcome" block listing the
sentences.

## Feature 3 — Agent loop for chat

New service `app/services/agent_loop.py` (NOT under app/agents/).

**Tool registry** (all deterministic, thin wrappers over existing services):
`get_kpis`, `get_top_segments(dimension, limit)`, `get_trend(metric, period)`,
`run_whatif(column, pct_change)`, `investigate_root_cause(question)`,
`get_prediction_and_xai`, `get_counterfactuals`, `scan_quality`, `get_schema`.

**Loop:** system prompt = dataset schema + semantic map + tool catalog + strict JSON
protocol. Each turn the LLM returns `{thought, tool, args}` or `{thought, final_answer}`.
Execute tool → append observation JSON → repeat. Max 5 steps, per-step timeout, total
budget ~30s. Final answer must cite only observed numbers; we also attach the raw
observations to the response for the UI.

**Progress:** each step emits `progress_bus` events (`agent_step` stage with
thought/tool/args summary) so ThinkingTrace renders the loop live.

**Fallback:** if `LLMProvider().is_configured()` is false, or the loop errors/times
out or returns malformed JSON twice → fall back to the existing
`SessionService.analyze` path (intent router). Guarantees offline mode.

**Wiring:** `SessionService.chat_message` tries the agent loop first when a dataset is
attached and the provider is configured; the response keeps the existing ChatEvent
shape (events/kpis/charts/tables/audit) so the frontend contract is unchanged, plus
`agent_trace: [{thought, tool, args, observation_summary}]`.

## Testing

- `tests/test_root_cause.py`: synthetic 2-period sales data with a planted driver
  (one product causes 70% of the drop) → investigator finds it, shares sum to ~100%,
  receipts present, unsupported cases return stated reasons.
- `tests/test_counterfactual.py`: small deterministic classification + regression
  models → counterfactual flips class / crosses threshold; determinism (same input →
  same output); rows below prediction threshold → skipped with reason.
- `tests/test_agent_loop.py`: fake provider that returns scripted JSON tool calls →
  loop executes tools, respects max steps, malformed JSON falls back, unconfigured
  provider falls back to intent-router path.
- Existing suite (141 tests) stays green; frontend `npm run build` stays clean.

## Out of scope

Categorical counterfactuals, multi-feature counterfactual search, drift comparison,
auth changes, report layout changes beyond the XAI counterfactual lines.
