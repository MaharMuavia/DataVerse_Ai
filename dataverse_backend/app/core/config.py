"""Configuration management for DataVerse AI.

Uses environment variables for all configurable parameters to ensure 12-factor principles.
"""
from __future__ import annotations

import os
from typing import Optional
# Support both pydantic v1 and v2 migration where BaseSettings moved to pydantic-settings
try:
    # pydantic v2
    from pydantic_settings import BaseSettings
    from pydantic import Field
except Exception:
    # pydantic v1
    from pydantic import BaseSettings, Field

from pydantic import validator


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DataVerse AI"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    # Logging
    LOG_DIR: str = Field(default="./logs", env="LOG_DIR")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Intent parsing provider
    # Options: "auto" (default), "deepseek", "openai"
    INTENT_LLM_PROVIDER: str = Field(default="auto", env="INTENT_LLM_PROVIDER")
    INTENT_LLM_TIMEOUT: int = Field(default=20, env="INTENT_LLM_TIMEOUT")

    # OpenAI for intent parsing
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_API_BASE: Optional[str] = Field(default=None, env="OPENAI_API_BASE")
    OPENAI_INTENT_MODEL: str = Field(default="gpt-4o-mini", env="OPENAI_INTENT_MODEL")

    # DeepSeek for intent parsing (OpenAI-compatible API)
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    DEEPSEEK_API_BASE: str = Field(default="https://api.deepseek.com/v1", env="DEEPSEEK_API_BASE")
    DEEPSEEK_INTENT_MODEL: str = Field(default="deepseek-chat", env="DEEPSEEK_INTENT_MODEL")

    # DeepAnalyze / Ollama settings
    DEEPANALYZE_BASE_URL: str = Field(default="http://localhost:11434", env="DEEPANALYZE_BASE_URL")
    # Preferred logical role/model used for reasoning. This is the primary model name the system will
    # attempt to use, but the system treats this as a logical role and will fall back to other local
    # models if allowed by configuration. This prevents crashes when a specific model artifact is missing.
    DEEPANALYZE_MODEL: str = Field(default="deepanalyze-8b", env="DEEPANALYZE_MODEL")
    # A reasonable default fallback model installed locally via Ollama (phi3:mini is available offline)
    DEEPANALYZE_FALLBACK_MODEL: str = Field(default="phi3:mini", env="DEEPANALYZE_FALLBACK_MODEL")
    DEEPANALYZE_TIMEOUT: int = Field(default=20, env="DEEPANALYZE_TIMEOUT")
    # Allow falling back to local models when the preferred model isn't available. Safe for dev.
    DEEPANALYZE_ALLOW_FALLBACK: bool = Field(default=True, env="DEEPANALYZE_ALLOW_FALLBACK")

    # Security / Limits
    MAX_UPLOAD_SIZE_MB: int = Field(default=50, env="MAX_UPLOAD_SIZE_MB")
    
    # Authentication
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Database
    # Expect a full async SQLAlchemy-compatible DATABASE_URL, e.g.
    # postgresql+asyncpg://user:password@host:5432/dbname
    DATABASE_URL: str | None = Field(default=None, env="DATABASE_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
