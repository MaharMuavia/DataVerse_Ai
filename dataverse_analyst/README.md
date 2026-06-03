# DataVerse Analyst

Unified AI-powered CSV analyst app that replaces the disconnected retail/static-dashboard/PostgreSQL paths with one FastAPI backend and one Streamlit UI.

## Schema

- `app/main.py`: FastAPI app, permissive CORS, health endpoint, analysis router.
- `app/routers/analysis.py`: `POST /upload`, `POST /analyze`, `GET /report/{session_id}`.
- `app/models/session.py`: module-level in-memory `SessionStore` with UUID4 session IDs.
- `app/agents/analysis_agent.py`: the only non-XAI analysis agent; owns CSV profiling, trends, target detection, FLAML/sklearn modeling, LIME output, and GPT narrative fallback.
- `app/agents/xai_agent.py`: `XAIAgent` with SHAP TreeExplainer, KernelExplainer fallback, and structured errors.
- `ui/streamlit_app.py`: Streamlit tabs for EDA, Trends, Model, XAI, and AI Report.

## Run

```powershell
cd dataverse_analyst
pip install -r requirements.txt
uvicorn app.main:app --port 8001
streamlit run ui/streamlit_app.py
```

Open `http://localhost:8501`, upload any CSV, and run full analysis.
