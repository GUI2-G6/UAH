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
from contextvars import Token
import os, secrets, httpx
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.models.user import User
from app.db.session import get_db
from app.google.service import GoogleAuthService
from backend.app.schemas.user import TokenResponse, UserResponse


router = APIRouter()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SERCRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

@router.get("/auth/google")
async def google_oauth(request: Request):
    # Generates a random  16 character state string to prevent attacks
    state = secrets.token_urlsafe(16)
    # Stores the state in the session for later verification when the user is redirected back
    request.session["oauth_state"] = state
    
    # Holds all the parameters required for the Google OAuth including client ID, redirect URI, response type, scope, and the generated state
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    
    # Creates a query string from the parameters and redirects the user to Google's OAuth 2.0 authorization endpoint with the query string attached
    query = "&".join([f"{key}={value}" for key, value in params.items()])
    # Then sends the user's browser to the Google OAuth consent screen s they can log in and authorize the application to access their Google account information. 
    # After the user completes the authorization process, Google will redirect them back to the specified redirect URI with an authorization code 
    #                                                                                                   that can be exchanged for an access token.
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")
    
    
    
@router.get("/auth/google/callback", response_model=TokenResponse)
async def google_oauth_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    # Verifies if the parameter "state" matches the one stored in the session to prevent any attacks. 
    # If they don't match, it raises an HTTP 400 error.
    if state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid state parameter")    
    
    # Opens an asynchronous HTTP client session using httpx to exchange the authorization code for an access token 
    # by making a POST request to Google's token endpoint.
    async with httpx.AsyncClient() as client:
        
        # Sends a POST request to Google's token endpoint with the required parameters including the authorization code, client ID, client secret, 
        # redirect URI, and grant type.
        token_response = await client.post("https://oauth2.googleapis.com/token", 
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SERCRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        # Converts the response to JSON and extracts the access token from the response data. 
        # The access token can then be used to make authenticated requests to Google's APIs on behalf of the user.
        token_response_data = token_response.json()
        access_token = token_response_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        
        # Gets the user's profile information by making a GET request to Google's userinfo endpoint with the access token included in the Authorization header.
        profile_response = await client.get("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        profile_data = profile_response.json()
        
        # Extracts the user's Google ID, email, name, and profile picture URL from the profile data returned by Google.
        google_id = profile_data['sub']
        email = profile_data["email"]
        name = profile_data["name"]
        picture = profile_data.get("picture")

        
        user = GoogleAuthService.get_or_create_user(db=db, google_id=google_id, email=email, full_name=name, picture_url=picture)

        from app.core.security import create_access_token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return TokenResponse(access_token=Token, user=UserResponse.model_validate(user),
    )


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
