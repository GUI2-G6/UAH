"""
API Routes
==========

All /api/* endpoints live here.

How routing works:
  - This file defines an APIRouter that gets mounted in main.py.
  - Each endpoint is a decorated async function.
  - FastAPI automatically generates OpenAPI/Swagger docs from the
    type hints and docstrings you provide.

Where to add new routes:
  - Simple CRUD routes can be added directly here.
  - As the app grows, split into sub-routers:
      app/api/v1/users.py
      app/api/v1/jobs.py
    and include them in main.py with version prefixes.

Where business logic should go:
  - Keep route handlers thin — they should validate input, call a
    service function, and return the result.
  - Business logic belongs in a services/ directory:
      app/services/scraper.py    — web scraping with BeautifulSoup
      app/services/jobs.py       — job application logic
  - Import and call those services from route handlers.

Where scraping services will live:
  - app/services/scraper.py (create when needed)
  - Use BeautifulSoup + httpx/requests for scraping.
  - Keep scraping logic fully decoupled from route handlers.

How DB session will be injected later:
  - Import `get_db` from app.db.session
  - Add it as a FastAPI dependency:
      from fastapi import Depends
      from app.db.session import get_db
      from sqlalchemy.orm import Session

      @router.get("/items")
      async def list_items(db: Session = Depends(get_db)):
          return db.query(Item).all()
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/status", tags=["status"])
async def api_status():
    """
    Status endpoint used by the frontend to verify backend connectivity.

    Returns a simple JSON payload. The frontend Vue app calls this
    on mount to confirm the /api proxy is working through Nginx.
    """
    return {
        "status": "ok",
        "environment": "dev",
        "message": "UAH API is running",
    }


@router.get("/api/diagnostics", tags=["status"])
async def diagnostics():
    """
    Comprehensive diagnostics endpoint for the status page.

    Probes every service and returns detailed information about
    the health, configuration, and connectivity of the entire stack.
    """
    import time
    import platform
    import sys
    import os
    from datetime import datetime, timezone

    from app.core.config import settings

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": os.getenv("ENV", "dev"),
        "services": {},
    }

    # --- Backend info ---
    result["services"]["backend"] = {
        "status": "healthy",
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "python_version": sys.version,
        "platform": platform.platform(),
        "pid": os.getpid(),
        "framework": f"FastAPI (uvicorn)",
        "host": os.getenv("HOSTNAME", "unknown"),
    }

    # --- Database probe ---
    db_start = time.monotonic()
    try:
        from sqlalchemy import text
        from app.db.session import engine

        with engine.connect() as conn:
            row = conn.execute(text("SELECT version()")).fetchone()
            pg_version = row[0] if row else "unknown"

            row = conn.execute(text("SELECT current_database()")).fetchone()
            db_name = row[0] if row else "unknown"

            row = conn.execute(text("SELECT current_user")).fetchone()
            db_user = row[0] if row else "unknown"

            row = conn.execute(text(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )).fetchone()
            db_size = row[0] if row else "unknown"

            row = conn.execute(text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )).fetchone()
            table_count = row[0] if row else 0

        db_latency = round((time.monotonic() - db_start) * 1000, 2)

        result["services"]["database"] = {
            "status": "healthy",
            "latency_ms": db_latency,
            "postgres_version": pg_version,
            "database_name": db_name,
            "user": db_user,
            "size": db_size,
            "public_tables": table_count,
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
        }
    except Exception as e:
        db_latency = round((time.monotonic() - db_start) * 1000, 2)
        result["services"]["database"] = {
            "status": "unhealthy",
            "latency_ms": db_latency,
            "error": str(e),
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
        }

    # --- Network / DNS probe (can backend resolve service names?) ---
    import socket

    # On the live dev server, "backend" resolves to the Docker container IP.
    # Locally (running on host), "backend" won't resolve, which is expected.
    # To prevent local tests from showing "degraded", we conditionally check
    # the hostname if we're not inside Docker or if POSTGRES_HOST is localhost.
    dns_checks = {"db": settings.POSTGRES_HOST}
    if settings.POSTGRES_HOST != "localhost":
        dns_checks["backend"] = "backend"

    network_results = {}
    for name, host in dns_checks.items():
        try:
            ip = socket.gethostbyname(host)
            network_results[name] = {"resolved": True, "ip": ip}
        except socket.gaierror:
            network_results[name] = {"resolved": False, "ip": None}

    result["services"]["network"] = {
        "status": "healthy" if all(r["resolved"] for r in network_results.values()) else "degraded",
        "dns_resolution": network_results,
    }

    # --- Overall status ---
    statuses = [s.get("status") for s in result["services"].values()]
    if all(s == "healthy" for s in statuses):
        result["overall"] = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        result["overall"] = "unhealthy"
    else:
        result["overall"] = "degraded"

    return result
