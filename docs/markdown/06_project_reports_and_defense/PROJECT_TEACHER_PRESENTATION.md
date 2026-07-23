# DataVerse AI — Teacher Presentation Document

## 1) Project Summary

**DataVerse AI is an AI-powered Business Intelligence platform that lets users upload CSV datasets, ask natural language questions, and receive insights, charts, and narrative reports in a web UI.**

## 2) Problem statement

Business users often have CSV files but cannot write SQL or Python. Creating charts and meaningful analysis is slow, error-prone, and not easily repeatable. DataVerse AI solves this by turning a dataset + question into automated analysis, visuals, and explanations.

## 3) System architecture

### Frontend
- Built with **Next.js 14** and **TypeScript**.
- Provides a **chat-style interface** for dataset upload and query entry.
- Supports **interactive Plotly visualizations**.
- Connects to the backend via `NEXT_PUBLIC_API_URL`.
- Stores UI state using **Zustand**.

### Backend
- Built with **Python** and **FastAPI**.
- Uses **Uvicorn** as the application server.
- Routes user requests to analysis workflows.
- Supports **session persistence** and **streaming responses**.
- Includes background worker support via **Celery** and **Redis**.

### Database & persistence
- Primary persistent store: **PostgreSQL**.
- Redis is used for queueing and temporary task coordination.
- The system preserves:
  - session metadata,
  - uploaded dataset info,
  - query history,
  - analysis artifacts.

### Deployment orchestration
- Full stack defined in `docker-compose.yml`.
- Services include:
  - `redis`
  - `postgres`
  - `backend`
  - `frontend`
  - `worker_fast`
  - `worker_slow`

## 4) AI and model components

### Intent parsing
- The backend uses `dataverse_backend/app/llm/intent_parser.py`.
- It selects provider automatically:
  - `DeepSeek` if configured,
  - `OpenAI` if configured,
  - otherwise a deterministic keyword fallback.
- The default OpenAI model is **`gpt-4o-mini`** for intent parsing.
- This component extracts query structure, operations, and metadata from user input.

### Reasoning and narrative generation
- The main reasoning engine is **DeepAnalyze**.
- Backend client: `dataverse_backend/app/llm/deepanalyze_client.py`.
- Preferred model: **`deepanalyze-8b`**.
- Fallback model: **`phi3:mini`**.
- DeepAnalyze receives structured facts and returns business-level narrative, report text, and insight summaries.

### Traditional analytics and explainability
- Uses Python libraries for data processing and modeling:
  - `pandas`, `numpy`, `scikit-learn`
  - `plotly`, `matplotlib`, `seaborn`
  - `shap`, `lime`, `sweetviz`
- The backend can produce:
  - summary statistics,
  - charts,
  - feature importance explanations,
  - model-based recommendations.

## 5) Core workflow

### 1. Upload dataset
- User uploads a CSV file using the frontend.
- Backend receives it at `POST /api/upload`.
- Dataset metadata is extracted and a session is created.

### 2. Ask a question
- User types a natural language prompt such as:
  - “Find me the top businesses”
  - “Show the best products”
  - “Generate a report for product sales”

### 3. Intent classification
- The backend calls the intent parser.
- It converts the query into structured operations and selects the analysis path.

### 4. Analysis and generation
- The backend runs the appropriate analysis modules:
  - EDA / profiling
  - chart generation
  - model-based scoring
  - explainability (SHAP, LIME)
- DeepAnalyze or the configured LLM synthesizes the results into narrative text.

### 5. Response returned
- The API responds with:
  - text answer,
  - chart data,
  - report summary,
  - optional follow-up insights.
- The frontend renders the answer and charts in the chat UI.

## 6) Key files and components

- `docker-compose.yml` — full stack deployment
- `dataverse_frontend/package.json` — frontend scripts and dependencies
- `dataverse_frontend/.env.local` — frontend API URL configuration
- `dataverse_backend/requirements.txt` — backend dependencies
- `dataverse_backend/app/main.py` — FastAPI application entrypoint
- `dataverse_backend/app/llm/intent_parser.py` — query intent parser
- `dataverse_backend/app/llm/deepanalyze_client.py` — local reasoning client
- `dataverse_backend/app/api/routes.py` — application API endpoints
- `data/` — sample datasets for demo
- `scripts/` — demo and startup utilities

## 7) What is already working

- The root `.env` contains a valid `OPENAI_API_KEY` for intent parsing.
- The frontend can connect to a backend running on `http://localhost:8000`.
- Docker Compose is configured to run the complete platform.
- The project supports natural language queries, chart rendering, and report generation.

## 8) How to run the project correctly

### Correct PowerShell command to enter the frontend folder
Use:
```powershell
cd .\dataverse_frontend
```
Not:
```powershell
cddataverse_frontend
```

### Option A: Local development (recommended for quick demo)
From the repo root:
```powershell
cd .\dataverse_frontend
npm install
npm run dev
```

Open the frontend in the browser:
- `http://localhost:3000`

Then start the backend from the repo root:
```powershell
cd .\dataverse_backend
python -m uvicorn app.main:app --app-dir dataverse_backend --host 127.0.0.1 --port 8000 --reload
```

The frontend is configured to call the backend at:
- `http://localhost:8000`

### Option B: Docker Compose (full stack)
From the repo root:
```powershell
docker-compose up -d --build
```

After startup, open:
- Frontend: `http://localhost:3000`
- Backend API docs: `http://localhost:8001/docs`

> Note: if the frontend runs locally and the backend runs in Docker on port `8001`, update `dataverse_frontend/.env.local` to `NEXT_PUBLIC_API_URL=http://localhost:8001`.

## 9) Troubleshooting

- If the frontend does not start, make sure you are in `dataverse_frontend` and that `npm install` was run there.
- If the backend is not reachable, verify the backend is running on the same port configured in `dataverse_frontend/.env.local`.
- The frontend command error you saw was caused by a typo: `cddataverse_frontend` should be `cd .\dataverse_frontend`.
- The root `.env` only stores backend keys; the frontend uses `dataverse_frontend/.env.local` for its API URL.

## 10) Answers for teacher questions

### Is the OpenAI API key needed?
- Yes, for the best natural language intent handling.
- The project can still fall back to keyword parsing if `OPENAI_API_KEY` is missing, but accuracy is lower.
- Since the `.env` already contains `OPENAI_API_KEY`, the system is configured to use it.

### Does the workflow start automatically?
- Yes. When the user uploads a dataset and enters a prompt, the backend receives the request and executes the workflow automatically.
- For a prompt like “find me top businesses or products according to given dataset”, the system will run intent parsing, choose the correct analysis path, and return a report + charts.

### How does the system generate graphs?
- The backend computes chart data from the dataset and returns it as structured results.
- The frontend renders those results using **Plotly**.

## 11) Demo script for the teacher

1. Explain the problem and platform value.
2. Show the repo structure (`docs/`, `dataverse_frontend/`, `dataverse_backend/`, `data/`).
3. Start the frontend and backend.
4. Upload `data/sample_products.csv`.
5. Ask a question such as:
   - “Show top products by sales.”
   - “Generate a product report.”
6. Point out the chart, narrative, and how the system uses AI behind the scenes.
7. Close with the architecture summary: UI, API, database, and AI models.

---

## 12) Summary

DataVerse AI demonstrates a complete full-stack solution: a modern Next.js UI, a Python FastAPI analytics backend, PostgreSQL persistence, Redis/Celery orchestration, and AI-powered query analysis. It is designed for non-technical users to get insights and visualizations from CSV data quickly.
