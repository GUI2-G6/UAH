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
from starlette.responses import PlainTextResponse
import os
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from app.api.routes import router as api_router
from app.api.jobs import router as jobs_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.account import router as account_router
from app.api.resume import router as resume_router
from app.api.applicant_profile import router as profile_router
from app.api.apply_session import router as apply_session_router
from app.api.integrations import router as integrations_router
from app.api.gmail import router as gmail_router
from app.core.config import settings
from app.core.runtime_environment import (
    generated_docs_auth_required,
    generated_docs_authenticate_header,
    generated_docs_enabled,
    internal_surface_auth_required,
)
from app.core.validation import normalize_email, require_valid_email
from app.db.base import Base
from app.db.session import get_engine, init_engine
from app.services.geolocation import ensure_city_dataset
from app.services.muse_location_index import ensure_muse_location_index
from app.services.parse_queue import start_queue_worker, stop_queue_worker, reconcile_stale_parse_jobs
import app.models  # noqa: F401 — ensure all models are registered
from app.models.user import User, SavedJob
from app.models.resume import Resume
from app.models.parse_job import ParseJob
from app.models.applicant_profile import ApplicantProfile
from app.models.muse_location import MuseSupportedLocation
from app.models.apply_session import ApplySession, ApplySessionEvent
from app.models.invite import Invite

logger = logging.getLogger(__name__)

# These tables still rely on startup-time `create_all()` support for local/dev
# compatibility. The newer jobs catalog schema is tracked through Alembic.
LEGACY_STARTUP_TABLES = [
    User.__table__,
    SavedJob.__table__,
    Resume.__table__,
    ParseJob.__table__,
    ApplicantProfile.__table__,
    MuseSupportedLocation.__table__,
    ApplySession.__table__,
    ApplySessionEvent.__table__,
    Invite.__table__,
]

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
            "is_developer": "BOOLEAN DEFAULT FALSE",
            "gmail_refresh_token": "TEXT",
            "gmail_email": "VARCHAR(255)",
            "password_reset_token_id": "VARCHAR(255)",
            "password_reset_expires_at": "TIMESTAMPTZ",
            "email_verify_token_id": "VARCHAR(255)",
            "email_verify_target_email": "VARCHAR(255)",
            "email_verify_expires_at": "TIMESTAMPTZ",
            "invite_code_used": "VARCHAR(64)",
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
    """Dev safety net: add newer resume columns to existing resumes table if missing."""
    try:
        from sqlalchemy import inspect, text
    except Exception:
        return

    try:
        inspector = inspect(engine)
        if "resumes" not in inspector.get_table_names():
            return

        existing = {col["name"] for col in inspector.get_columns("resumes")}

        ddl_statements: list[str] = []
        required_columns: dict[str, str] = {
            "pdf_data": "BYTEA",
            "review_status": "VARCHAR(50)",
            "review_draft": "JSONB",
            "review_updated_at": "TIMESTAMPTZ",
        }
        for column_name, column_ddl in required_columns.items():
            if column_name in existing:
                continue
            ddl_statements.append(
                f"ALTER TABLE resumes ADD COLUMN IF NOT EXISTS {column_name} {column_ddl}"
            )

        if ddl_statements:
            with engine.begin() as conn:
                for ddl in ddl_statements:
                    conn.execute(text(ddl))
            logger.warning("Applied dev schema fixups to resumes table")
    except Exception as exc:
        logger.exception("Resumes table schema fixup failed: %s", exc)


def _ensure_saved_jobs_table_columns(engine) -> None:
    """Dev safety net: add newer saved_jobs columns when DB schema lags."""
    try:
        from sqlalchemy import inspect, text
    except Exception:
        return

    try:
        inspector = inspect(engine)
        if "saved_jobs" not in inspector.get_table_names():
            return

        columns = inspector.get_columns("saved_jobs")
        existing = {col["name"] for col in columns}
        column_by_name = {col["name"]: col for col in columns}

        ddl_statements: list[str] = []
        required_columns: dict[str, str] = {
            "provider": "VARCHAR(50)",
            "provider_job_id": "VARCHAR(255)",
            "url": "TEXT DEFAULT ''",
            "created_at": "TIMESTAMPTZ DEFAULT now()",
        }

        for column_name, column_ddl in required_columns.items():
            if column_name in existing:
                continue
            ddl_statements.append(
                f"ALTER TABLE saved_jobs ADD COLUMN IF NOT EXISTS {column_name} {column_ddl}"
            )

        job_id_column = column_by_name.get("job_id")
        if job_id_column and not bool(job_id_column.get("nullable", True)):
            ddl_statements.append("ALTER TABLE saved_jobs ALTER COLUMN job_id DROP NOT NULL")

        url_column = column_by_name.get("url")
        if url_column and "text" not in str(url_column.get("type") or "").lower():
            ddl_statements.append("ALTER TABLE saved_jobs ALTER COLUMN url TYPE TEXT")

        if ddl_statements:
            with engine.begin() as conn:
                for ddl in ddl_statements:
                    conn.execute(text(ddl))
            logger.warning("Applied dev schema fixups to saved_jobs table")
    except Exception as exc:
        logger.exception("Saved jobs table schema fixup failed: %s", exc)


def _ensure_applicant_profiles_table_columns(engine) -> None:
    """Dev safety net: add newer applicant profile columns when DB schema lags."""
    try:
        from sqlalchemy import inspect, text
    except Exception:
        return

    try:
        inspector = inspect(engine)
        if "applicant_profiles" not in inspector.get_table_names():
            return

        existing = {col["name"] for col in inspector.get_columns("applicant_profiles")}
        ddl_statements: list[str] = []
        required_columns: dict[str, str] = {
            "canonical_data": "JSONB",
            "token_map": "JSONB",
        }
        for column_name, column_ddl in required_columns.items():
            if column_name in existing:
                continue
            ddl_statements.append(
                f"ALTER TABLE applicant_profiles ADD COLUMN IF NOT EXISTS {column_name} {column_ddl}"
            )

        if ddl_statements:
            with engine.begin() as conn:
                for ddl in ddl_statements:
                    conn.execute(text(ddl))
            logger.warning("Applied dev schema fixups to applicant_profiles table")
    except Exception as exc:
        logger.exception("Applicant profiles table schema fixup failed: %s", exc)


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


def _enforce_email_first_identity_mirror() -> None:
    """Normalize stored emails and mirror username=email for all users.

    This runs at startup as an idempotent guard while username sunset is in
    progress. It fails fast on case-insensitive duplicate emails so we never
    violate uniqueness assumptions when normalizing.
    """

    try:
        from sqlalchemy import func
        from app.db.session import SessionLocal
        from app.models.user import User
    except Exception as exc:
        logger.exception("Email-first identity bootstrap import failed: %s", exc)
        raise

    db = SessionLocal()
    try:
        duplicate_rows = (
            db.query(
                func.lower(User.email).label("normalized_email"),
                func.count(User.id).label("row_count"),
            )
            .group_by(func.lower(User.email))
            .having(func.count(User.id) > 1)
            .all()
        )

        if duplicate_rows:
            sample = ", ".join(
                [f"{row.normalized_email} ({row.row_count})" for row in duplicate_rows[:5]]
            )
            raise RuntimeError(
                "Case-insensitive duplicate emails detected; cannot enforce email-first identity mirror. "
                f"Examples: {sample}"
            )

        users = db.query(User).all()
        updated_count = 0
        for user in users:
            normalized = normalize_email(user.email)
            if not normalized:
                raise RuntimeError(f"User id={user.id} has an empty email; cannot enforce email-first identity.")
            if user.email != normalized or user.username != normalized:
                user.email = normalized
                user.username = normalized
                updated_count += 1

        if updated_count:
            db.commit()
            logger.warning("Email-first identity mirror enforced for %s user(s).", updated_count)
        else:
            db.rollback()
            logger.info("Email-first identity mirror already in sync.")
    except Exception:
        db.rollback()
        logger.exception("Email-first identity mirror bootstrap failed.")
        raise
    finally:
        db.close()


def _ensure_dev_test_user_if_enabled() -> None:
    if not settings.DEV_AUTH_TEST_ACCOUNT_ENABLED:
        return

    env_slug = (settings.ENVIRONMENT or "").strip().lower()
    if env_slug not in {"development", "dev", "local"}:
        logger.warning(
            "[DEV-AUTH] Skipping dev test user setup outside development/local env: %s",
            settings.ENVIRONMENT,
        )
        return

    legacy_username = settings.DEV_AUTH_TEST_USERNAME.strip()
    password = settings.DEV_AUTH_TEST_PASSWORD.strip()
    identifier = settings.DEV_AUTH_TEST_EMAIL.strip() or legacy_username
    if not identifier or not password:
        logger.error("[DEV-AUTH] DEV_AUTH_TEST_ACCOUNT_ENABLED=true but email/password are missing")
        return

    try:
        email = require_valid_email(identifier, field_name="DEV_AUTH_TEST_EMAIL")
    except ValueError as exc:
        logger.error("[DEV-AUTH] Invalid dev test email identifier: %s", exc)
        return

    try:
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        from app.models.user import User
    except Exception as exc:
        logger.exception("[DEV-AUTH] Import failure while ensuring test user: %s", exc)
        return

    db = SessionLocal()
    try:
        from sqlalchemy import func

        user = db.query(User).filter(func.lower(User.email) == email).first()
        if not user:
            user = db.query(User).filter(User.username == email).first()

        if user:
            user.username = email
            user.email = email
            user.first_name = settings.DEV_AUTH_TEST_FIRST_NAME or "Dev"
            user.last_name = settings.DEV_AUTH_TEST_LAST_NAME or "Tester"
            user.is_active = True
            user.is_admin = settings.DEV_AUTH_TEST_IS_ADMIN
            user.is_developer = settings.DEV_AUTH_TEST_IS_DEVELOPER

            if settings.DEV_AUTH_TEST_ROTATE_PASSWORD or not user.hashed_password:
                user.hashed_password = hash_password(password)

            db.add(user)
            db.commit()
            db.refresh(user)
            logger.warning("[DEV-AUTH] Ensured dev test user '%s'", email)
            return

        user = User(
            email=email,
            username=email,
            hashed_password=hash_password(password),
            first_name=settings.DEV_AUTH_TEST_FIRST_NAME or "Dev",
            last_name=settings.DEV_AUTH_TEST_LAST_NAME or "Tester",
            is_active=True,
            is_admin=settings.DEV_AUTH_TEST_IS_ADMIN,
            is_developer=settings.DEV_AUTH_TEST_IS_DEVELOPER,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.warning("[DEV-AUTH] Created dev test user '%s'", email)
    except Exception as exc:
        logger.exception("[DEV-AUTH] Failed to ensure dev test user: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    engine = get_engine()

    # Local/dev startup still carries a small compatibility layer for older
    # volumes so contributors can keep moving even when their schema lags.
    Base.metadata.create_all(bind=engine, tables=LEGACY_STARTUP_TABLES)
    _ensure_users_table_columns(engine)
    _ensure_resumes_table_columns(engine)
    _ensure_saved_jobs_table_columns(engine)
    _ensure_applicant_profiles_table_columns(engine)
    # First normalize whatever already exists in the database.
    _enforce_email_first_identity_mirror()
    _bootstrap_admin_user_if_enabled()
    _ensure_dev_test_user_if_enabled()
    # Then normalize any bootstrap-created rows using the same invariant.
    _enforce_email_first_identity_mirror()

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

# Generated API docs are a local/dev convenience. Beta-style environments
# should expose the product surface, not a public OpenAPI explorer. Beta can
# opt into docs only when they are auth-gated by a dedicated passcode. Fail
# closed when ENVIRONMENT is missing or unknown.
_docs_enabled = generated_docs_enabled(
    os.getenv("ENVIRONMENT"),
    settings.BETA_DOCS_PASSCODE,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Unified Application Hub — DEV API",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
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


@app.middleware("http")
async def beta_docs_basic_auth_gate(request: Request, call_next):
    requires_auth = generated_docs_auth_required(
        path=request.url.path,
        raw_environment=os.getenv("ENVIRONMENT"),
        authorization_header=request.headers.get("Authorization"),
        expected_username=settings.BETA_DOCS_USERNAME,
        expected_passcode=settings.BETA_DOCS_PASSCODE,
    )
    if requires_auth:
        return PlainTextResponse(
            "Authentication required.",
            status_code=401,
            headers={
                "WWW-Authenticate": generated_docs_authenticate_header(),
                "Cache-Control": "no-store",
            },
        )
    return await call_next(request)


@app.middleware("http")
async def internal_surface_api_key_gate(request: Request, call_next):
    requires_internal_key = internal_surface_auth_required(
        path=request.url.path,
        raw_environment=os.getenv("ENVIRONMENT"),
        provided_key=request.headers.get("X-Internal-Api-Key"),
        expected_key=settings.INTERNAL_API_KEY,
    )
    if requires_internal_key:
        return PlainTextResponse(
            "Not found.",
            status_code=404,
            headers={"Cache-Control": "no-store"},
        )
    return await call_next(request)

# ---------------------------------------------------------------------------
# Mount the API router
# ---------------------------------------------------------------------------
# All routes defined in app/api/routes.py are prefixed under /api.
# To add new route groups in the future, create additional routers and
# include them here with appropriate prefixes and tags.
# ---------------------------------------------------------------------------
app.include_router(api_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(auth_router)
app.include_router(admin_router, prefix="/api/admin")
app.include_router(account_router)
app.include_router(resume_router)
app.include_router(profile_router)
app.include_router(apply_session_router)
app.include_router(integrations_router)
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

