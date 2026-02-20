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
