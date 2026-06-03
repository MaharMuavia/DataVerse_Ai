from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.analysis import router as analysis_router


app = FastAPI(
    title="DataVerse Analyst",
    version="1.0.0",
    description="AI-powered CSV analysis with EDA, AutoML, XAI, LIME, and GPT narrative reports.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
