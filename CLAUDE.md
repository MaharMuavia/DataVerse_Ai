# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

DataVerse AI is a **two-agent dataset analyst**. A user uploads a CSV/XLSX file; the
backend profiles it, computes business metrics / EDA / optional ML prediction + XAI
**deterministically** with Pandas/scikit-learn, and renders a compact HTML/PDF report.
An LLM is **optional** and only polishes narration text — it must never invent numbers.
With no LLM keys configured, everything still runs in offline/"Mock mode".

Monorepo layout: `frontend/` (Next.js) + `dataverse_backend/` (FastAPI). Root
`package.json` is a thin delegator to `frontend/`.

## Commands

The Python venv lives at the repo-root `.venv` (the dev launcher and docs assume this).

```powershell
# Run BOTH backend + frontend with one command (recommended).
# scripts/dev.mjs auto-starts uvicorn from .venv and `next dev`, waits for /health/live.
npm run dev                 # from repo root (delegates to frontend) OR `cd frontend; npm run dev`

# Backend only
cd dataverse_backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# ...or from repo root: python -m uvicorn app.main:app --reload --app-dir dataverse_backend ...

# Frontend lint / build / dev-script tests
npm run lint                # eslint (flat config, eslint-config-next)
npm run build               # next build
npm run test:dev            # node --test on scripts/*.test.mjs (dev launcher + api client)
```

### Backend tests (pytest)

There is **no pytest config file**; `tests/conftest.py` sets test env vars and imports
`app.main`, so tests must run with `dataverse_backend` as the working directory.

```powershell
cd dataverse_backend
..\.venv\Scripts\python -m pytest -v                        # all tests
..\.venv\Scripts\python -m pytest -v tests/test_mvp_e2e.py  # one file
..\.venv\Scripts\python -m pytest tests/test_report_generator.py::test_name  # one test
```

Dependencies: `requirements-mvp.txt` is the lightweight set used in the README setup;
`requirements.txt` / `requirements-full.txt` are heavier supersets. CI
(`.github/workflows/ci.yml`) only runs `compileall` — it does not run the test suite.

## Architecture

### Request flow (the "two agents")

```
Upload → DatasetAgent (validate, parse, normalize headers, profile, quality, persist)
       → AnalystAgent  (thin wrapper around AnalysisPipeline)
       → AnalysisPipeline (semantic map → query plan → metrics/EDA/trends/prediction/XAI → narration)
       → ReportGenerator + ReportComposer (compact HTML/PDF, dedup'd sections)
       → Frontend (KPIs, 1–2 charts, report download, XAI)
```

- `app/agents/dataset_agent.py` and `app/agents/analyst_agent.py` are the only two
  agents by design. **Do not add more agents.** `AnalystAgent.__init__` just constructs
  an `AnalysisPipeline`; the real work lives in services. (Note: extra `*_agent.py` files
  exist under `app/agents/` and many extra `app/services/*.py` modules exist from earlier
  iterations — the live path is DatasetAgent → AnalystAgent → AnalysisPipeline.)

- `app/services/analysis_pipeline.py` is the deterministic orchestrator
  (`run_full_analysis` / `run_full_analysis_async`). It wires together `semantic_mapper`,
  `query_planner`, `data_profiler`, `data_quality` (EDA/trends/correlations/outliers/charts),
  `business_metrics`, `modeling` (Ridge/RandomForest), `xai`, and `report_narrator`. All
  numbers are computed here; narration is layered on top.

- Prediction + XAI are gated on `settings.MIN_ROWS_FOR_PREDICTION` (default 30). Below the
  threshold, prediction is **skipped with a stated reason** rather than failing — preserve
  this behavior, and keep `run_xai=True` for report generation.

- Differentiator services (all deterministic-first, wired via `session_service.py`):
  `root_cause.py` (multi-step "why did X change?" driver decomposition with receipts;
  chat "why" questions and `POST .../investigate` both use it), `counterfactual.py`
  (smallest single-feature change that flips a prediction; attached to the XAI payload
  by `xai.explain_model`), and `agent_loop.py` (LLM plan→act→observe loop over
  deterministic tools; used for chat answers when a provider is configured, returns
  None to fall back to the deterministic path — never let it originate numbers).

### Reports (concision is a hard requirement)

- `app/services/report_composer.py` builds the section list and owns a `ReportMemory`
  that fingerprints insights/metrics/tables/charts to **prevent repeated content** (no
  repeated revenue/sales/trend explanations). When changing report content, route through
  the composer's dedup rather than emitting duplicate sections.
- `app/services/report_generator.py` renders HTML and PDF (ReportLab, with a manual-PDF
  fallback) from the composed sections, including hand-rolled SVG charts. Light theme only.
- Reports must stay 1–2 pages: max ~2 charts, ≤3 recommendations, XAI is **always the
  final section**, no "Appendix: Column Profile" dumps. `tests/test_report_generator.py`
  enforces these invariants — keep them green.

### Persistence

`app/services/session_service.py` + `supabase_client.py`: Supabase is **required outside
tests** — `SessionService.__init__` raises at import time when `SUPABASE_URL` /
`SUPABASE_SERVICE_ROLE_KEY` are unset and `ENVIRONMENT != "test"` (auth also needs
`SUPABASE_ANON_KEY`; schema lives in `dataverse_backend/supabase_schema.sql`). Dataframes
are additionally cached on the local filesystem (`session_storage/` under the backend cwd;
pickled — see `session_store.py` `_read_pickle_compat` / numpy alias shims for
cross-version pickle loading). DB (`DATABASE_URL`, SQLAlchemy) is not required.

Deployment: Vercel hosts only `frontend/` (project Root Directory = `frontend`); the
FastAPI backend deploys to a Hugging Face Docker Space via
`.github/workflows/deploy-hf-space.yml` (mirrors `dataverse_backend/` on main pushes;
needs `HF_TOKEN` secret + `HF_SPACE_ID` repo variable; backend env vars live in the
Space's settings). The frontend finds the backend through
`NEXT_PUBLIC_DATAVERSE_API_URL` (build-time, set in Vercel).

### API surface

Routers mounted in `app/main.py`, all under `/api`. The frontend uses the session flow:
`POST /api/sessions`, `POST /api/sessions/{id}/datasets/upload?auto_analyze=true`,
`POST /api/sessions/{id}/analyze`, `POST /api/sessions/{id}/messages`,
`POST /api/sessions/{id}/reports/generate`, `GET /api/reports/{id}/download`. There is
also a stateless `/api/analyze/*` flow and a legacy `/api/upload` + `/api/session/{id}`
core router. **Do not break these routes** — `tests/test_analyze_endpoints.py` and
`tests/test_mvp_e2e.py` cover them.

A global exception handler in `main.py` returns rich, suggestion-bearing errors in
`ENVIRONMENT=development` and generic messages otherwise.

### Frontend

Next.js 15 / React 19 / Tailwind v4, App Router. The app is currently driven by a single
large `frontend/app/page.tsx` client component. The backend base URL comes from
`NEXT_PUBLIC_DATAVERSE_API_URL` (or `NEXT_PUBLIC_API_URL`), normalized in
`lib/apiConfig.ts` to always end in `/api`; the typed API client is `lib/dataverse-api.ts`
with its contract in `lib/dataverse-api.contract.ts`. Keep the UI light/minimal — dark
theme is not the main UI.

## Conventions specific to this repo

- Deterministic-first: any metric shown to the user must be computed in Pandas/scikit-learn,
  not produced by the LLM. LLM output is narration polish only.
- Keep the two-agent boundary; new analysis capability belongs in `app/services/` and is
  invoked from the pipeline, not in a new agent.
- `AGENTS.md` is a long general engineering-conduct guide for this repo (root-cause fixes,
  verify before claiming done, don't edit `.env`, report changed files + verification).
  Its operative rules still apply.
