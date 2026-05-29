# Teacher Explanation / Presentation Script (DataVerse AI)

Use this as a speaking script + checklist when explaining the project.

## 1) One‑sentence summary (what the project is)

**DataVerse AI is an AI‑powered Business Intelligence platform that lets a user upload a CSV dataset and ask natural‑language questions, then returns insights, charts, and explanations through a web UI.**

## 2) Problem statement (why we built it)

In many real business scenarios, decision‑makers have data in spreadsheets/CSVs but:
- they don’t know SQL / Python
- generating charts and insights takes time
- results are not explainable or reproducible

We built DataVerse AI to convert “CSV + question” into “analysis + visualization + narrative”, while keeping a clean full‑stack architecture.

## 3) What we built (high level)

### Frontend (Next.js)
- Chat‑style interface for asking questions.
- Dataset upload workflow.
- Real‑time updates while the backend is processing.
- Rendering of interactive charts (Plotly).

### Backend (FastAPI)
- REST API for upload + query.
- Orchestration layer that routes a user question to the right analysis steps.
- A toolbox of analysis utilities (EDA/statistics/visualization/modeling/explainability helpers).
- Session management so a user can upload once and run multiple queries.

### Persistence / Infra
- PostgreSQL for persistent metadata and long‑running sessions.
- Redis + Celery workers for background/async jobs (where applicable).
- Docker Compose to run the complete platform with one command.

## 4) Tech stack (what tools we used)

- **Backend**: Python, FastAPI, Uvicorn
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS (and supporting UI libs)
- **Database**: PostgreSQL
- **Async / queues**: Redis + Celery
- **Visualization**: Plotly
- **AI/LLM integration**: API keys via `.env` (OpenAI + optional fallback keys)

## 5) Key features to highlight (what makes it strong)

- **Natural language analytics**: user asks questions like a conversation.
- **Interactive charts**: results can include chart specs rendered in the UI.
- **Streaming / real‑time feedback**: user sees progress while analysis runs.
- **Session persistence**: uploaded datasets and query history survive restarts.
- **Production‑ready structure**: Docker Compose, health checks, logging, and clean separation of concerns.

## 6) How to demo in front of the teacher (step‑by‑step)

### Option A: Docker demo (recommended)

1. From the repo root (folder containing `docker-compose.yml`):
   - `docker-compose up -d --build`
2. Open:
   - Frontend: `http://localhost:3000`
   - Backend docs: `http://localhost:8001/docs`
3. Upload a dataset (pick one from `data/`):
   - `data/sample_products.csv` (small, quick demo)
4. Ask a few questions (examples):
   - “Show sales by category”
   - “Which products have the highest profit?”
   - “Create a chart of top 10 items”

### Option B: Windows local dev demo

From the repo root:
- `powershell -ExecutionPolicy Bypass -File scripts/start-all.ps1`

Then open the frontend at `http://localhost:3000` and repeat the same upload + query demo.

## 7) What we delivered (deliverables)

- Working full‑stack app:
  - `dataverse_backend/` (FastAPI service)
  - `dataverse_frontend/` (Next.js service)
- Sample datasets in `data/`
- Start/deploy/demo utilities in `scripts/`
- Complete documentation set inside `docs/` (setup guides, reference, status reports, evaluation reports, etc.)

## 8) Repository restructure (what we changed to make it easy to understand)

To make the project readable for reviewers:
- All Markdown documentation moved into **`docs/`**
- All runnable helper scripts moved into **`scripts/`**
- All sample CSV datasets moved into **`data/`**
- Static dashboard moved into **`docs/assets/`**
- Updated docs + scripts so they reference the new paths correctly
- Removed hard‑coded absolute machine paths from startup/deploy scripts (now repo‑relative and portable)

If the teacher wants to navigate quickly:
- Start here: `START_HERE.txt`
- Docs index: `docs/INDEX.md`
- Structure map: `docs/STRUCTURE_GUIDE.md`

## 9) How to run the project reliably

### Correct commands
From the repository root, use:
```powershell
cd .\dataverse_frontend
npm install
npm run dev
```

Then start the backend in another terminal:
```powershell
cd .\dataverse_backend
python -m uvicorn app.main:app --app-dir dataverse_backend --host 127.0.0.1 --port 8000 --reload
```

> Note: the command `cddataverse_frontend` is incorrect. The correct command is `cd .\dataverse_frontend`.

## 10) Closing (30‑second wrap‑up)

“In summary, DataVerse AI turns datasets into insights using a clean full‑stack architecture: a Next.js UI, a FastAPI analytics backend, and PostgreSQL persistence. The main value is that non‑technical users can upload a CSV and ask questions naturally, and the platform produces charts and explanations. We also organized the repo so a reviewer can instantly find docs, scripts, data, and source code.”

