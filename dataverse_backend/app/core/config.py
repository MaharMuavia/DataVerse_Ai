"""Configuration management for DataVerse AI.

Uses environment variables for all configurable parameters to ensure 12-factor principles.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
    )

    # App
    APP_NAME: str = "DataVerse AI"
    ENVIRONMENT: str = "development"
    APP_VERSION: str = "1.0.0"
    ENABLE_OPENAPI_DOCS: bool = True
    REQUEST_TIMEOUT_SECONDS: int = 60

    # Logging
    LOG_DIR: str = "./logs"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    # API and transport security
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    # Optional regex matched against the Origin header in addition to CORS_ORIGINS,
    # e.g. ^https://myapp-[a-z0-9]+-myteam\.vercel\.app$ for preview deployments.
    CORS_ORIGIN_REGEX: Optional[str] = None
    TRUSTED_HOSTS: str = "localhost,127.0.0.1,testserver"
    SECURE_HEADERS_ENABLED: bool = True
    HTTPS_REDIRECT: bool = False

    # API rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_PATH_PREFIX: str = "/api"

    # Intent parsing provider
    # Options: "auto" (default), "deepseek", "openai"
    INTENT_LLM_PROVIDER: str = "auto"
    INTENT_LLM_TIMEOUT: int = 20

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = None
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_INTENT_MODEL: str = "gpt-4o-mini"

    # Gemini for report narration fallback after OpenAI
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_REPORT_MODEL: str = "gemini-1.5-pro"

    # Supabase persistence (optional)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None
    SUPABASE_DATASET_BUCKET: str = "dataverse-datasets"
    SUPABASE_REPORT_BUCKET: str = "dataverse-reports"
    SUPABASE_HEALTH_TIMEOUT_SECONDS: float = 5.0
    BACKEND_BASE_URL: str = "http://localhost:8000"
    FRONTEND_BASE_URL: str = "https://127.0.0.1:3000"

    # DeepSeek for intent parsing (OpenAI-compatible API)
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    DEEPSEEK_INTENT_MODEL: str = "deepseek-chat"

    # DeepAnalyze / Ollama settings
    DEEPANALYZE_API_KEY: Optional[str] = None
    DEEPANALYZE_API_BASE: Optional[str] = None
    DEEPANALYZE_LOCAL_BASE_URL: Optional[str] = None
    DEEPANALYZE_BASE_URL: str = "http://localhost:11434"
    # Preferred logical role/model used for reasoning. This is the primary model name the system will
    # attempt to use, but the system treats this as a logical role and will fall back to other local
    # models if allowed by configuration. This prevents crashes when a specific model artifact is missing.
    DEEPANALYZE_MODEL: str = "deepanalyze-8b"
    # A reasonable default fallback model installed locally via Ollama (phi3:mini is available offline)
    DEEPANALYZE_FALLBACK_MODEL: str = "phi3:mini"
    DEEPANALYZE_TIMEOUT: int = 20
    # Allow falling back to local models when the preferred model isn't available. Safe for dev.
    DEEPANALYZE_ALLOW_FALLBACK: bool = True

    MAX_UPLOAD_SIZE_MB: int = 50
    # Refuse uploads whose semantic dataset type is outside the retail/mart
    # commerce family (see services/domain_guard.py). Tests disable this.
    RETAIL_ONLY_UPLOADS: bool = True
    USE_LLM_NARRATION: bool = True
    LLM_PROVIDER: str = "auto"
    REPORT_NARRATOR_TIMEOUT_SECONDS: int = 20
    AUTO_TRAIN_TARGET_CONFIDENCE: float = 0.65
    MIN_ROWS_FOR_PREDICTION: int = 30
    # Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RATE_LIMIT_PER_MINUTE: int = 120
    
    # Database
    # Expect a full async SQLAlchemy-compatible DATABASE_URL, e.g.
    # postgresql+asyncpg://user:password@host:5432/dbname
    DATABASE_URL: str | None = None
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # File Storage
    STORAGE_TYPE: str = "local"  # local, minio, s3
    
    # MinIO Configuration
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "dataverse"
    MINIO_SECURE: bool = False
    
    # AWS S3 Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: str = "dataverse"
    
    # Claude AI
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # Sentry
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.0

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def trusted_hosts_list(self) -> List[str]:
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",") if host.strip()]


settings = Settings()
