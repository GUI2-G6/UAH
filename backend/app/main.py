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

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router as api_router
from app.api.auth import router as auth_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401 — ensure all models are registered


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
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

# ---------------------------------------------------------------------------
# Mount the API router
# ---------------------------------------------------------------------------
# All routes defined in app/api/routes.py are prefixed under /api.
# To add new route groups in the future, create additional routers and
# include them here with appropriate prefixes and tags.
# ---------------------------------------------------------------------------
app.include_router(api_router)
app.include_router(auth_router)


# ---------------------------------------------------------------------------
# Root and health endpoints (outside /api prefix)
# ---------------------------------------------------------------------------

@app.get("/", tags=["root"])
async def root():
    """Root endpoint — quick sanity check that the service is running."""
    return {"service": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/health", tags=["health"])
async def health():
    """
    Health check endpoint.

    Used by Docker HEALTHCHECK, load balancers, and monitoring.
    Future improvement: verify DB connectivity here.
    """
    return {"status": "healthy"}

