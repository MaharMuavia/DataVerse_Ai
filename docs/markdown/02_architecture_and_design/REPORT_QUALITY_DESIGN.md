# Report Quality Improvements — Design

Date: 2026-07-12. Approved by owner ("make it better according to your own choice").

## Goal

Make the generated HTML/PDF analysis report read and look like a professional
analyst deliverable, while preserving every existing concision invariant
(1–2 pages, ≤2 charts, ≤3 recommendations, XAI last, deterministic-first).

## Changes

### 1. Prose & jargon (report_composer.py)
- Volatility: never print raw floats; use a qualitative phrase
  ("with low/moderate/high variability") derived from the coefficient of
  variation of the series when available, else drop it.
- Delete the "Method used: <internal_name>" sentence from the XAI section;
  keep only plain-language driver statements.
- Internal skip-notes (e.g. "Category column missing; skipped category
  ranking.") are filtered out of report sections.
- Executive summary: no modeling jargon ("Ridge", "(regression)"); phrase as
  forward-looking capability. Model naming stays in the XAI section.
- XAI dummy grouping: one-hot features (Col_value) are grouped by source
  column; grouped drivers render as one line with combined importance
  ("Timing (Date) is the dominant driver, ~53% of the prediction").

### 2. Repetition & contradiction (ReportMemory)
- Semantic trend fingerprint (metric, direction, rounded pct) so paraphrases
  of the same trend fact dedupe across sections; first mention wins.
- Chart takeaways state their scope when their direction differs from the
  headline trend ("Within the monthly top-products view, ...").

### 3. Visuals (report_generator.py)
- HTML: KPI cards (label + large value) instead of plain lines; insights as
  bulleted lists; light theme only.
- SVG line charts: x-axis first/middle/last period labels, y-axis min/max,
  value label at the final point.
- Chart titles adapt to actual counts ("Top 3 ..." when 3 items).
- Remove generic per-chart-type boilerplate captions; keep "Key takeaway".
- PDF mirrors the same content decisions (KPI table row, bullet glyphs).

## Non-goals

- No templating-engine rewrite; no LLM dependency for quality (must look
  right in Mock mode); no dark theme.

## Testing

Extend tests/test_report_generator.py and tests/test_compact_report.py:
- report text contains no internal method names (feature_importance_fallback)
- no float with >2 decimals in narrative text
- a trend fact (metric+direction+pct) appears at most once
- SVG line charts contain axis label elements
- adaptive chart titles match item counts
- all existing invariants stay green (188-test suite passes).
