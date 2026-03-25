"""
Application Configuration
=========================

Centralizes all configuration values.
Reads from environment variables so nothing is hard-coded.

Usage:
  from app.core.config import settings
  print(settings.DATABASE_URL)

To add a new setting:
  1. Add the field with a type hint and default below.
  2. Set the env var in docker-compose.yml or .env file.
"""

import os


def _env_bool(name: str, default: str = "false") -> bool:
  return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Simple settings object — swap for pydantic-settings when needed."""

    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "UAH")
    VERSION: str = os.getenv("VERSION", "0.1.0")

    # Database — constructed from individual env vars for clarity.
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "uah")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "uah_dev_pass")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "uah_dev")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")  # Docker service name
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    # Auth / JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Email (SMTP)
    EMAILS_ENABLED: bool = _env_bool("EMAILS_ENABLED", "false")
    PUBLIC_APP_URL: str = os.getenv("PUBLIC_APP_URL", "http://localhost:5173")

    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")
    SMTP_USE_TLS: bool = _env_bool("SMTP_USE_TLS", "true")
    SMTP_USE_SSL: bool = _env_bool("SMTP_USE_SSL", "false")
    SMTP_TIMEOUT_SECONDS: int = int(os.getenv("SMTP_TIMEOUT_SECONDS", "20"))

    ZAI_API_KEY: str = os.getenv("ZAI_API_KEY", "")
    ZAI_OCR_URL: str = os.getenv("ZAI_OCR_URL", "https://api.z.ai/api/paas/v4/layout_parsing")
    ZAI_LLM_URL: str = os.getenv("ZAI_LLM_URL", "https://api.z.ai/api/paas/v4/chat/completions")
    ZAI_LLM_MODEL: str = os.getenv("ZAI_LLM_MODEL", "GLM-4.7-Flash")

    # Muse jobs API guardrails
    MUSE_PAGE_CHASE_ENABLED: bool = _env_bool("MUSE_PAGE_CHASE_ENABLED", "true")
    MUSE_PAGE_CHASE_MAX_PAGES: int = int(os.getenv("MUSE_PAGE_CHASE_MAX_PAGES", "3"))
    MUSE_PAGE_CHASE_MAX_API_CALLS_PER_REQUEST: int = int(os.getenv("MUSE_PAGE_CHASE_MAX_API_CALLS_PER_REQUEST", "3"))
    MUSE_PAGE_CHASE_TARGET_ACCEPTED_RESULTS: int = int(os.getenv("MUSE_PAGE_CHASE_TARGET_ACCEPTED_RESULTS", "20"))
    MUSE_PAGE_CHASE_MIN_FILTERED_RATIO: float = float(os.getenv("MUSE_PAGE_CHASE_MIN_FILTERED_RATIO", "0.4"))
    MUSE_PAGE_CHASE_TIMEOUT_SECONDS: float = float(os.getenv("MUSE_PAGE_CHASE_TIMEOUT_SECONDS", "8"))

    @property
    def DATABASE_URL(self) -> str:
        """
        SQLAlchemy connection string.
        Uses the 'db' Docker service name so the backend can reach
        Postgres over the shared Docker network without exposing ports.
        """
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
