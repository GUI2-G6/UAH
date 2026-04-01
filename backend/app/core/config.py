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
    #intentional var added
    TEST_MISSING_VAR = os.environ.get("TEST_MISSING_VAR", "")  
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "UAH")
    VERSION: str = os.getenv("VERSION", "0.1.0")

    # Database — constructed from individual env vars for clarity.
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "uah")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "uah_dev")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")  # Docker service name
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    # Auth / JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "")
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
    MUSE_ADAPTIVE_PAGE_CHASE_ENABLED: bool = _env_bool("MUSE_ADAPTIVE_PAGE_CHASE_ENABLED", "true")
    MUSE_ADAPTIVE_PAGE_CHASE_EXTRA_PAGES: int = int(os.getenv("MUSE_ADAPTIVE_PAGE_CHASE_EXTRA_PAGES", "2"))
    MUSE_ADAPTIVE_PAGE_CHASE_BREADTH_THRESHOLD: int = int(os.getenv("MUSE_ADAPTIVE_PAGE_CHASE_BREADTH_THRESHOLD", "45"))
    MUSE_ADAPTIVE_PAGE_CHASE_MIN_FILTERED_RATIO: float = float(os.getenv("MUSE_ADAPTIVE_PAGE_CHASE_MIN_FILTERED_RATIO", "0.2"))
    MUSE_LOCATION_PARAM_CAP: int = int(os.getenv("MUSE_LOCATION_PARAM_CAP", "60"))
    CONSTRAINT_COMPATIBILITY_ENABLED: bool = _env_bool("CONSTRAINT_COMPATIBILITY_ENABLED", "true")
    CONSTRAINT_FILTER_MIN_CONFIDENCE: str = os.getenv("CONSTRAINT_FILTER_MIN_CONFIDENCE", "high")
    JOBS_DEFAULT_PAGE_SIZE: int = int(os.getenv("JOBS_DEFAULT_PAGE_SIZE", "10"))
    JOBS_CACHE_ENABLED: bool = _env_bool("JOBS_CACHE_ENABLED", "true")
    JOBS_CACHE_TTL_SECONDS: int = int(os.getenv("JOBS_CACHE_TTL_SECONDS", "45"))
    JOBS_CACHE_MAX_KEYS: int = int(os.getenv("JOBS_CACHE_MAX_KEYS", "250"))

    # Muse-supported location index refresh settings
    MUSE_LOCATION_INDEX_ENABLED: bool = _env_bool("MUSE_LOCATION_INDEX_ENABLED", "true")
    MUSE_LOCATION_INDEX_REFRESH_HOURS: int = int(os.getenv("MUSE_LOCATION_INDEX_REFRESH_HOURS", "24"))
    MUSE_LOCATION_INDEX_SCAN_MAX_PAGES: int = int(os.getenv("MUSE_LOCATION_INDEX_SCAN_MAX_PAGES", "25"))
    MUSE_LOCATION_INDEX_TIMEOUT_SECONDS: float = float(os.getenv("MUSE_LOCATION_INDEX_TIMEOUT_SECONDS", "10"))
    MUSE_LOCATION_INDEX_RETENTION_DAYS: int = int(os.getenv("MUSE_LOCATION_INDEX_RETENTION_DAYS", "45"))

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

    def missing_resume_ocr_config(self) -> list[str]:
        missing = []
        if not self.ZAI_API_KEY or not self.ZAI_API_KEY.strip():
            missing.append("ZAI_API_KEY")
        if not self.ZAI_OCR_URL or not self.ZAI_OCR_URL.strip():
            missing.append("ZAI_OCR_URL")
        return missing

    def require_secrets(self) -> None:
      missing: list[str] = []
      for name in ("POSTGRES_PASSWORD", "SECRET_KEY", "SESSION_SECRET"):
        value = getattr(self, name, "")
        if not isinstance(value, str) or not value.strip():
          missing.append(name)

      if missing:
        raise RuntimeError(
          "Missing required environment variables: " + ", ".join(missing)
        )


settings = Settings()
