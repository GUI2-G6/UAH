"""
UAH Backend — FastAPI Application Entry Point
================================================

This is the main entry point for the FastAPI application.
Uvicorn loads this module (app.main:app) to start the server.

Key concepts:
  - Swagger/OpenAPI docs are auto-generated at /docs
  - ReDoc alternative docs are at /redoc
  - All /api/* routes are defined in app/api/routes.py
  - Database session dependency is prepared in app/db/session.py
  - Configuration is centralized in app/core/config.py

To run locally (outside Docker):
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""
from starlette.middleware.sessions import SessionMiddleware
import os
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from app.api.routes import router as api_router
from app.api.auth import router as auth_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401 — ensure all models are registered

logger = logging.getLogger(__name__)


def _ensure_users_table_columns() -> None:
    """Dev safety net: add missing columns when DB schema lags behind models.

    This project currently uses `Base.metadata.create_all()`, which does not
    apply schema migrations to existing tables. If the `users` table already
    exists (e.g. persisted Docker volume) but the model gained new columns,
    SQLAlchemy will raise runtime errors like:
      psycopg2.errors.UndefinedColumn: column users.<col> does not exist

    Long-term fix: introduce Alembic migrations.
    """

    try:
        from sqlalchemy import inspect, text
    except Exception:
        return

    try:
        inspector = inspect(engine)
        if "users" not in inspector.get_table_names():
            return

        existing = {col["name"] for col in inspector.get_columns("users")}

        # Only add columns that may be absent in older DB volumes.
        required_columns: dict[str, str] = {
            "hashed_password": "VARCHAR(255)",
            "first_name": "VARCHAR(100)",
            "last_name": "VARCHAR(100)",
            "linkedIn_id": "VARCHAR(255)",
            "google_id": "VARCHAR(255)",
            "full_name": "VARCHAR(255)",
            "picture_url": "VARCHAR(255)",
            "is_active": "BOOLEAN DEFAULT TRUE",
            "created_at": "TIMESTAMPTZ DEFAULT now()",
            "updated_at": "TIMESTAMPTZ DEFAULT now()",
        }

        ddl_statements: list[str] = []
        for column_name, column_ddl in required_columns.items():
            if column_name in existing:
                continue

            needs_quotes = any(ch.isupper() for ch in column_name)
            rendered_name = f'"{column_name}"' if needs_quotes else column_name
            ddl_statements.append(
                f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {rendered_name} {column_ddl}"
            )

        if not ddl_statements:
            return

        with engine.begin() as conn:
            for ddl in ddl_statements:
                conn.execute(text(ddl))
        logger.warning("Applied dev schema fixups to users table: %s", ", ".join([s.split()[5] for s in ddl_statements]))
    except Exception as exc:
        # Don't crash the app if the DB user lacks ALTER privileges.
        logger.exception("User table schema fixup failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
    _ensure_users_table_columns()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Unified Application Hub — DEV API",
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc alternative
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("SESSION_SECRET", "a-very-secret-random-key")
)

# ---------------------------------------------------------------------------
# Mount the API router
# ---------------------------------------------------------------------------
# All routes defined in app/api/routes.py are prefixed under /api.
# To add new route groups in the future, create additional routers and
# include them here with appropriate prefixes and tags.
# ---------------------------------------------------------------------------
app.include_router(api_router, prefix="/api")
app.include_router(auth_router)


# ---------------------------------------------------------------------------
# Root and health endpoints (prefixed with /api to match Nginx proxy block)
# ---------------------------------------------------------------------------

@app.get("/api/", tags=["root"])
async def root():
    """Root endpoint — quick sanity check that the service is running."""
    return {"service": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/api/health", tags=["health"])
async def health():
    """
    Health check endpoint.

    Used by Docker HEALTHCHECK, load balancers, and monitoring.
    Future improvement: verify DB connectivity here.
    """
    return {"status": "healthy"}

