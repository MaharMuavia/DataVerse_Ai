from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    automl_time_budget: int = int(os.getenv("AUTOML_TIME_BUDGET", "15"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "50"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
