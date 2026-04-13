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


def _env_slug(value: str) -> str:
  cleaned = "".join(ch if ch.isalnum() else "_" for ch in (value or ""))
  cleaned = cleaned.strip("_").lower()
  return cleaned or "dev"


class Settings:
    """Simple settings object — swap for pydantic-settings when needed."""
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
    AUTH_NAMESPACE: str = _env_slug(os.getenv("AUTH_NAMESPACE", os.getenv("ENVIRONMENT", "development")))
    AUTH_COOKIE_NAME: str = os.getenv("AUTH_COOKIE_NAME", f"uah_auth_{AUTH_NAMESPACE}")
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", f"uah_session_{AUTH_NAMESPACE}")
    SESSION_COOKIE_SAMESITE: str = os.getenv("SESSION_COOKIE_SAMESITE", "lax").strip().lower()
    SESSION_COOKIE_PATH: str = os.getenv("SESSION_COOKIE_PATH", "/")
    SESSION_COOKIE_HTTPS_ONLY: bool = _env_bool(
      "SESSION_COOKIE_HTTPS_ONLY",
      "true" if AUTH_NAMESPACE in {"beta", "staging", "prod", "production"} else "false",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    GMAIL_TOKEN_ENCRYPTION_KEY: str = os.getenv("GMAIL_TOKEN_ENCRYPTION_KEY", "")

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEV_AUTH_TEST_ACCOUNT_ENABLED: bool = _env_bool("DEV_AUTH_TEST_ACCOUNT_ENABLED", "false")
    DEV_AUTH_TEST_USERNAME: str = os.getenv("DEV_AUTH_TEST_USERNAME", "")
    DEV_AUTH_TEST_PASSWORD: str = os.getenv("DEV_AUTH_TEST_PASSWORD", "")
    DEV_AUTH_TEST_EMAIL: str = os.getenv("DEV_AUTH_TEST_EMAIL", "")
    DEV_AUTH_TEST_FIRST_NAME: str = os.getenv("DEV_AUTH_TEST_FIRST_NAME", "Dev")
    DEV_AUTH_TEST_LAST_NAME: str = os.getenv("DEV_AUTH_TEST_LAST_NAME", "Tester")
    DEV_AUTH_TEST_IS_ADMIN: bool = _env_bool("DEV_AUTH_TEST_IS_ADMIN", "false")
    DEV_AUTH_TEST_IS_DEVELOPER: bool = _env_bool("DEV_AUTH_TEST_IS_DEVELOPER", "false")
    DEV_AUTH_TEST_ROTATE_PASSWORD: bool = _env_bool("DEV_AUTH_TEST_ROTATE_PASSWORD", "true")

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

    GMAIL_CLIENT_ID: str = os.getenv("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET: str = os.getenv("GMAIL_CLIENT_SECRET", "")
    GMAIL_REDIRECT_URI: str = os.getenv("GMAIL_REDIRECT_URI", "")

    ZAI_API_KEY: str = os.getenv("ZAI_API_KEY", "")
    ZAI_OCR_URL: str = os.getenv("ZAI_OCR_URL", "https://api.z.ai/api/paas/v4/layout_parsing")
    ZAI_LLM_URL: str = os.getenv("ZAI_LLM_URL", "https://api.z.ai/api/paas/v4/chat/completions")
    ZAI_LLM_MODEL: str = os.getenv("ZAI_LLM_MODEL", "GLM-4.7-Flash")

    # Local Ollama pipeline (replaces ZAI when USE_LOCAL_PIPELINE=true)
    USE_LOCAL_PIPELINE: bool = _env_bool("USE_LOCAL_PIPELINE", "false")
    LOCAL_OCR_URL: str = os.getenv("LOCAL_OCR_URL", "http://10.8.0.8:11434")
    LOCAL_OCR_MODEL: str = os.getenv("LOCAL_OCR_MODEL", "glm-ocr-hires")
    LOCAL_LLM_URL: str = os.getenv("LOCAL_LLM_URL", "http://10.8.0.8:11434")
    LOCAL_LLM_MODEL: str = os.getenv("LOCAL_LLM_MODEL", "qwen2.5:7b")
    LOCAL_OCR_TIMEOUT: float = float(os.getenv("LOCAL_OCR_TIMEOUT", "120"))
    LOCAL_LLM_TIMEOUT: float = float(os.getenv("LOCAL_LLM_TIMEOUT", "120"))
    LOCAL_OCR_DPI: int = int(os.getenv("LOCAL_OCR_DPI", "120"))

    # Redis parse queue
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    REDIS_ENABLED: bool = _env_bool("REDIS_ENABLED", "false")
    PARSE_QUEUE_NAME: str = os.getenv("PARSE_QUEUE_NAME", "uah:parse_jobs")
    PARSE_QUEUE_NAME_CLOUD: str = os.getenv("PARSE_QUEUE_NAME_CLOUD", "uah:parse_jobs:cloud")
    PARSE_QUEUE_NAME_LOCAL: str = os.getenv("PARSE_QUEUE_NAME_LOCAL", "uah:parse_jobs:local")
    PARSE_QUEUE_NAME_RULES: str = os.getenv("PARSE_QUEUE_NAME_RULES", "uah:parse_jobs:rules")
    PARSE_QUEUE_MAX_RETRIES: int = int(os.getenv("PARSE_QUEUE_MAX_RETRIES", "3"))
    PARSE_QUEUE_MAX_RETRIES_CLOUD: int = int(os.getenv("PARSE_QUEUE_MAX_RETRIES_CLOUD", "-1"))
    PARSE_QUEUE_MAX_RETRIES_LOCAL: int = int(os.getenv("PARSE_QUEUE_MAX_RETRIES_LOCAL", "-1"))
    PARSE_QUEUE_MAX_RETRIES_RULES: int = int(os.getenv("PARSE_QUEUE_MAX_RETRIES_RULES", "0"))
    PARSE_QUEUE_CONCURRENCY_CLOUD: int = int(os.getenv("PARSE_QUEUE_CONCURRENCY_CLOUD", "1"))
    PARSE_QUEUE_CONCURRENCY_LOCAL: int = int(os.getenv("PARSE_QUEUE_CONCURRENCY_LOCAL", "2"))
    PARSE_QUEUE_CONCURRENCY_RULES: int = int(os.getenv("PARSE_QUEUE_CONCURRENCY_RULES", "2"))
    PARSE_QUEUE_CLAIM_TTL_SECONDS: int = int(os.getenv("PARSE_QUEUE_CLAIM_TTL_SECONDS", "1800"))
    PARSE_QUEUE_SHUTDOWN_DRAIN_SECONDS: int = int(os.getenv("PARSE_QUEUE_SHUTDOWN_DRAIN_SECONDS", "30"))
    PARSE_QUEUE_STALE_JOB_MINUTES: int = int(os.getenv("PARSE_QUEUE_STALE_JOB_MINUTES", "20"))

    # Muse jobs API guardrails
    MUSE_PAGE_CHASE_ENABLED: bool = _env_bool("MUSE_PAGE_CHASE_ENABLED", "true")
    MUSE_PAGE_CHASE_MAX_PAGES: int = int(os.getenv("MUSE_PAGE_CHASE_MAX_PAGES", "5"))
    MUSE_PAGE_CHASE_MAX_API_CALLS_PER_REQUEST: int = int(os.getenv("MUSE_PAGE_CHASE_MAX_API_CALLS_PER_REQUEST", "5"))
    MUSE_PAGE_CHASE_TARGET_ACCEPTED_RESULTS: int = int(os.getenv("MUSE_PAGE_CHASE_TARGET_ACCEPTED_RESULTS", "20"))
    MUSE_PAGE_CHASE_MIN_FILTERED_RATIO: float = float(os.getenv("MUSE_PAGE_CHASE_MIN_FILTERED_RATIO", "0.25"))
    MUSE_PAGE_CHASE_TIMEOUT_SECONDS: float = float(os.getenv("MUSE_PAGE_CHASE_TIMEOUT_SECONDS", "12"))
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
    JOBS_URL_VALIDATION_ENABLED: bool = _env_bool("JOBS_URL_VALIDATION_ENABLED", "true")
    JOBS_URL_VALIDATION_TIMEOUT_SECONDS: float = float(os.getenv("JOBS_URL_VALIDATION_TIMEOUT_SECONDS", "2.5"))
    JOBS_URL_VALIDATION_MAX_CHECKS_PER_REQUEST: int = int(os.getenv("JOBS_URL_VALIDATION_MAX_CHECKS_PER_REQUEST", "20"))
    JOBS_URL_VALIDATION_CONCURRENCY: int = int(os.getenv("JOBS_URL_VALIDATION_CONCURRENCY", "4"))
    JOBS_URL_VALIDATION_BAD_TTL_SECONDS: int = int(os.getenv("JOBS_URL_VALIDATION_BAD_TTL_SECONDS", "1800"))
    JOBS_URL_VALIDATION_GOOD_TTL_SECONDS: int = int(os.getenv("JOBS_URL_VALIDATION_GOOD_TTL_SECONDS", "300"))
    JOBS_URL_VALIDATION_UNKNOWN_TTL_SECONDS: int = int(os.getenv("JOBS_URL_VALIDATION_UNKNOWN_TTL_SECONDS", "90"))

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

    @property
    def ACCESS_TOKEN_EXPIRE_SECONDS(self) -> int:
        return max(int(self.ACCESS_TOKEN_EXPIRE_MINUTES), 1) * 60

    def missing_resume_ocr_config(self) -> list[str]:
        missing = []
        if not self.ZAI_API_KEY or not self.ZAI_API_KEY.strip():
            missing.append("ZAI_API_KEY")
        if not self.ZAI_OCR_URL or not self.ZAI_OCR_URL.strip():
            missing.append("ZAI_OCR_URL")
        return missing

    def parse_queue_name_for_method(self, method: str | None) -> str:
        normalized = (method or "").strip().lower()
        if normalized == "cloud":
            return self.PARSE_QUEUE_NAME_CLOUD
        if normalized == "rules":
            return self.PARSE_QUEUE_NAME_RULES
        return self.PARSE_QUEUE_NAME_LOCAL

    @property
    def parse_queue_name_by_method(self) -> dict[str, str]:
        return {
            "cloud": self.PARSE_QUEUE_NAME_CLOUD,
            "local": self.PARSE_QUEUE_NAME_LOCAL,
            "rules": self.PARSE_QUEUE_NAME_RULES,
        }

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

      if self.SECRET_KEY.strip() == self.SESSION_SECRET.strip():
        raise RuntimeError("SECRET_KEY and SESSION_SECRET must be different values.")

      if not isinstance(self.SESSION_COOKIE_NAME, str) or not self.SESSION_COOKIE_NAME.strip():
        raise RuntimeError("SESSION_COOKIE_NAME must be configured.")

      if self.SESSION_COOKIE_NAME.strip().lower() == "session":
        raise RuntimeError("SESSION_COOKIE_NAME='session' is not allowed; use an environment-scoped cookie name.")

      if not isinstance(self.AUTH_COOKIE_NAME, str) or not self.AUTH_COOKIE_NAME.strip():
        raise RuntimeError("AUTH_COOKIE_NAME must be configured.")

      if self.AUTH_COOKIE_NAME.strip().lower() in {"session", self.SESSION_COOKIE_NAME.strip().lower()}:
        raise RuntimeError("AUTH_COOKIE_NAME must be distinct from SESSION_COOKIE_NAME and may not use reserved defaults.")

      allowed_samesite = {"lax", "strict", "none"}
      if self.SESSION_COOKIE_SAMESITE not in allowed_samesite:
        raise RuntimeError("SESSION_COOKIE_SAMESITE must be one of: lax, strict, none.")

      if self.SESSION_COOKIE_SAMESITE == "none" and not self.SESSION_COOKIE_HTTPS_ONLY:
        raise RuntimeError("SESSION_COOKIE_SAMESITE=none requires SESSION_COOKIE_HTTPS_ONLY=true.")

      if not isinstance(self.AUTH_NAMESPACE, str) or not self.AUTH_NAMESPACE.strip():
        raise RuntimeError("AUTH_NAMESPACE must be configured.")

      env_slug = _env_slug(self.ENVIRONMENT)
      if env_slug in {"beta", "staging", "prod", "production"}:
        lower_secret = self.SECRET_KEY.lower()
        lower_session_secret = self.SESSION_SECRET.lower()
        if "placeholder" in lower_secret or "placeholder" in lower_session_secret:
          raise RuntimeError("Placeholder auth secrets are not allowed in beta/prod environments.")
        if not self.SESSION_COOKIE_HTTPS_ONLY:
          raise RuntimeError("SESSION_COOKIE_HTTPS_ONLY must be true in beta/staging/prod environments.")

      if self.DEV_AUTH_TEST_ACCOUNT_ENABLED and env_slug not in {"dev", "development", "local"}:
        raise RuntimeError("DEV_AUTH_TEST_ACCOUNT_ENABLED is only allowed in development/local environments.")

      if self.DEV_AUTH_TEST_ACCOUNT_ENABLED:
        if not self.DEV_AUTH_TEST_EMAIL.strip() and not self.DEV_AUTH_TEST_USERNAME.strip():
          raise RuntimeError(
            "DEV_AUTH_TEST_EMAIL is required when DEV_AUTH_TEST_ACCOUNT_ENABLED=true "
            "(legacy fallback: DEV_AUTH_TEST_USERNAME)."
          )
        if not self.DEV_AUTH_TEST_PASSWORD.strip():
          raise RuntimeError("DEV_AUTH_TEST_PASSWORD is required when DEV_AUTH_TEST_ACCOUNT_ENABLED=true.")


settings = Settings()
