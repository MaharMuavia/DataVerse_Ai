# DataVerse AI Backend

Production-grade FastAPI backend for the DataVerse AI project. This repository is structured for a final-year project and real-world extension.

## Source Location

- Backend source code lives in `dataverse_backend/`.
- This documentation lives in `docs/services/backend/README.md` (so all Markdown stays under `docs/`).

## Run (local dev)

From the repo root:

```bash
python -m uvicorn app.main:app --app-dir dataverse_backend --host 127.0.0.1 --port 8000 --reload
```

The API routes are under the `/api` prefix (example: `http://localhost:8000/api/health`).

> Note: `dataverse_backend/` is a Python backend, not a Node frontend. Do not run `npm install` in `dataverse_backend/`. Use Python dependency installation from `requirements.txt` and start the backend with Uvicorn or Docker Compose.
