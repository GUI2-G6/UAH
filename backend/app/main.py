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
from app.api.account import router as account_router
from app.api.resume import router as resume_router
from app.api.applicant_profile import router as profile_router
from app.api.apply_session import router as apply_session_router
from app.api.gmail import router as gmail_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_engine, init_engine
from app.services.geolocation import ensure_city_dataset
from app.services.muse_location_index import ensure_muse_location_index
from app.services.parse_queue import start_queue_worker, stop_queue_worker, reconcile_stale_parse_jobs
import app.models  # noqa: F401 — ensure all models are registered

logger = logging.getLogger(__name__)

# Fail fast on missing critical secrets when running the backend.
settings.require_secrets()


def _ensure_users_table_columns(engine) -> None:
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
            "email_verified": "BOOLEAN DEFAULT FALSE",
            "is_active": "BOOLEAN DEFAULT TRUE",
            "is_admin": "BOOLEAN DEFAULT FALSE",
            "gmail_refresh_token": "TEXT",
            "gmail_email": "VARCHAR(255)",
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
        logger.exception("User table schema fixup failed: %s", exc)



def _ensure_resumes_table_columns(engine) -> None:
    """Dev safety net: add pdf_data column to existing resumes table if missing."""
    try:
        from sqlalchemy import inspect, text
    except Exception:
        return

    try:
        inspector = inspect(engine)
        if "resumes" not in inspector.get_table_names():
            return

        existing = {col["name"] for col in inspector.get_columns("resumes")}
        if "pdf_data" not in existing:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE resumes ADD COLUMN IF NOT EXISTS pdf_data BYTEA"))
            logger.warning("Added pdf_data column to resumes table")
    except Exception as exc:
        logger.exception("Resumes table schema fixup failed: %s", exc)


def _bootstrap_admin_user_if_enabled() -> None:
    if os.getenv("ADMIN_BOOTSTRAP_ENABLED", "false").lower() != "true":
        return

    try:
        from app.db.session import SessionLocal
        from app.api.auth import _ensure_admin_user
    except Exception as exc:
        logger.exception("Admin bootstrap import failed: %s", exc)
        return

    db = SessionLocal()
    try:
        _ensure_admin_user(db)
        logger.warning("Admin bootstrap ensured for %s", "admincontact@uahapp.com")
    except Exception as exc:
        logger.exception("Admin bootstrap failed: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    engine = get_engine()

    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
    _ensure_users_table_columns(engine)
    _ensure_resumes_table_columns(engine)
    _bootstrap_admin_user_if_enabled()

    geo_dataset_status = ensure_city_dataset()
    status = geo_dataset_status.get("status")
    if status == "built":
        logger.warning(
            "Geolocation city dataset built at startup (%s cities, %.2f MB)",
            geo_dataset_status.get("cities_written", 0),
            float(geo_dataset_status.get("size_bytes", 0)) / (1024 * 1024),
        )
    elif status == "existing":
        logger.info(
            "Geolocation city dataset already present (%.2f MB)",
            float(geo_dataset_status.get("size_bytes", 0)) / (1024 * 1024),
        )
    elif status == "skipped":
        logger.warning("Geolocation city dataset auto-build skipped: %s", geo_dataset_status.get("reason", "unknown"))
    else:
        logger.warning(
            "Geolocation city dataset build failed: %s. Falling back to embedded cities.",
            geo_dataset_status.get("error", "unknown error"),
        )

    muse_index_status = await ensure_muse_location_index()
    logger.info("Muse location index startup status: %s", muse_index_status)

    if settings.REDIS_ENABLED:
        recovery = await reconcile_stale_parse_jobs()
        logger.info("Redis parse queue stale-job recovery: %s", recovery)
        await start_queue_worker()
        logger.info("Redis parse queue worker startup requested")

    yield

    if settings.REDIS_ENABLED:
        await stop_queue_worker()
        logger.info("Redis parse queue worker stopped")

_is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Unified Application Hub — DEV API",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
    session_cookie=settings.SESSION_COOKIE_NAME,
    same_site=settings.SESSION_COOKIE_SAMESITE,
    https_only=settings.SESSION_COOKIE_HTTPS_ONLY,
    path=settings.SESSION_COOKIE_PATH,
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
app.include_router(account_router)
app.include_router(resume_router)
app.include_router(profile_router)
app.include_router(apply_session_router)
app.include_router(gmail_router)


# ---------------------------------------------------------------------------
# Root and health endpoints (prefixed with /api to match Nginx proxy block)
# ---------------------------------------------------------------------------

@app.get("/api/", tags=["root"])
async def root():
    """
    Root discovery endpoint for quick service identification.

    Returns project name and version so clients and operators can verify they
    are connected to the expected backend instance.

    Response codes:
    - 200: Service metadata returned successfully.
    """
    return {"service": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/api/health", tags=["health"])
async def health():
    """
    Basic health probe endpoint.

    Used by Docker HEALTHCHECK, load balancers, and uptime monitors to confirm
    that the process is alive and serving requests.

    Response codes:
    - 200: Process is healthy and accepting requests.
    """
    return {"status": "healthy"}

