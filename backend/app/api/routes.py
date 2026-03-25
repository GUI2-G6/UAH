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
import ipaddress
import os, secrets, httpx
import httpx
import re
from fastapi import APIRouter, HTTPException, Request, Query, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.models.user import User, SavedJob
from app.db.session import get_db
from app.google.service import GoogleAuthService
from app.schemas.user import TokenResponse, UserResponse, SaveJobRequest
from typing import Optional, List
from app.services.geolocation import (
    geocode_query,
    km_to_miles,
    list_country_cities,
    miles_to_km,
    find_cities_in_radius,
    resolve_ip_location,
    reverse_geocode,
)


router = APIRouter()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
MUSE_API_KEY = os.getenv("MUSE_API_KEY")

REMOTE_TEXT_PATTERN = re.compile(
    r"\b(remote|work\s*from\s*home|telecommute|telecommuting|distributed|anywhere)\b",
    flags=re.IGNORECASE,
)
HYBRID_TEXT_PATTERN = re.compile(r"\bhybrid\b", flags=re.IGNORECASE)


def _normalize_text(value: Optional[str]) -> str:
    return " ".join((value or "").strip().lower().split())


def _is_remote_location_name(name: Optional[str]) -> bool:
    normalized = _normalize_text(name)
    if not normalized:
        return False

    return (
        "remote" in normalized
        or "work from home" in normalized
        or "telecommute" in normalized
        or normalized == "anywhere"
    )


def _classify_job_work_mode(job: dict) -> tuple[bool, bool]:
    raw_locations = job.get("locations", []) or []
    location_names = [loc.get("name", "") for loc in raw_locations if isinstance(loc, dict)]
    has_remote_location = any(_is_remote_location_name(name) for name in location_names)

    searchable_text = " ".join(
        [
            job.get("name", "") or "",
            job.get("short_name", "") or "",
            job.get("contents", "") or "",
        ]
    )

    has_hybrid_text = bool(HYBRID_TEXT_PATTERN.search(searchable_text))
    has_remote_text = bool(REMOTE_TEXT_PATTERN.search(searchable_text))

    has_hybrid = has_hybrid_text
    has_remote = has_remote_location or has_remote_text

    return has_remote, has_hybrid


def _extract_client_ip(request: Request) -> Optional[str]:
    candidates: List[str] = []

    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        candidates.extend([part.strip() for part in forwarded.split(",") if part.strip()])

    real_ip = (request.headers.get("x-real-ip", "") or "").strip()
    if real_ip:
        candidates.append(real_ip)

    if request.client and request.client.host:
        candidates.append((request.client.host or "").strip())

    for candidate in candidates:
        try:
            ip_obj = ipaddress.ip_address(candidate)
            if ip_obj.is_global:
                return str(ip_obj)
        except ValueError:
            continue

    # Returning None tells providers to resolve by server egress IP.
    return None


@router.get("/geolocation/ip", tags=["geolocation"])
async def geolocation_by_ip(request: Request):
    client_ip = _extract_client_ip(request)
    try:
        payload = await resolve_ip_location(client_ip)
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "GEO_IP_FAILED",
                "message": "Could not determine location from IP.",
                "debug": str(exc),
            },
        )


@router.get("/geolocation/geocode", tags=["geolocation"])
async def geocode_location(
    q: str = Query(..., min_length=2, description="Zip code, city, or full location text"),
    country_code: Optional[str] = Query(None, description="Optional ISO country code"),
):
    try:
        return await geocode_query(q, country_code=country_code)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "GEO_GEOCODE_FAILED",
                "message": "Could not find that location. Try a city name or ZIP code.",
                "debug": str(exc),
            },
        )


@router.get("/geolocation/reverse", tags=["geolocation"])
async def reverse_geocode_location(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
):
    try:
        return await reverse_geocode(latitude, longitude)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "GEO_REVERSE_FAILED",
                "message": "Could not resolve this coordinate into a place name.",
                "debug": str(exc),
            },
        )


@router.get("/geolocation/cities-in-radius", tags=["geolocation"])
async def cities_in_radius(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: float = Query(25, gt=0, description="Radius value, interpreted by the selected unit"),
    unit: str = Query("mi", description="mi or km"),
    country_code: Optional[str] = Query(None, description="Optional ISO country code to constrain matches"),
    limit: int = Query(200, ge=1, le=500),
):
    normalized_unit = (unit or "mi").strip().lower()
    radius_miles = km_to_miles(radius) if normalized_unit == "km" else radius
    radius_miles = min(radius_miles, 100.0)

    cities = find_cities_in_radius(
        latitude=latitude,
        longitude=longitude,
        radius_miles=radius_miles,
        country_code=country_code,
        limit=limit,
    )

    if not cities:
        return {
            "code": "GEO_RADIUS_EMPTY",
            "message": "No cities were found within this radius.",
            "debug": {
                "latitude": latitude,
                "longitude": longitude,
                "radius_miles": round(radius_miles, 2),
                "country_code": (country_code or "").upper(),
            },
            "cities": [],
            "total_count": 0,
            "radius_miles": round(radius_miles, 2),
            "radius_km": round(miles_to_km(radius_miles), 2),
        }

    return {
        "cities": cities,
        "total_count": len(cities),
        "radius_miles": round(radius_miles, 2),
        "radius_km": round(miles_to_km(radius_miles), 2),
    }


@router.get("/geolocation/country-cities", tags=["geolocation"])
async def country_cities(
    country_code: str = Query(..., min_length=2, max_length=2, description="ISO country code"),
    limit: int = Query(120, ge=1, le=400),
):
    cities = list_country_cities(country_code=country_code, limit=limit)
    if not cities:
        return {
            "code": "GEO_COUNTRY_EMPTY",
            "message": "No known city data for that country yet.",
            "cities": [],
            "total_count": 0,
        }

    return {
        "cities": cities,
        "total_count": len(cities),
        "country_code": country_code.upper(),
    }

@router.get("/jobs/search", tags=["jobs"])
async def search_jobs(
    # Creates an endpoint for each job search query with optional parameters 
    page: int = Query(1, ge=1, description="Page number for pagination"),
    category: Optional[List[str]] = Query(None, description="e.g., 'Software Engineer', 'Data Science'"),
    catogory: Optional[List[str]] = Query(None, description="e.g., 'Software Engineer', 'Data Science'"),
    level: Optional[List[str]] = Query(None, description="e.g., 'Internship', 'Entry', 'Senior'"),
    location: Optional[List[str]] = Query(None, description="e.g., 'New York', 'Remote'"),
    company: Optional[List[str]] = Query(None, description="e.g., 'Google', 'Microsoft'"),
):
    # Gets the list of jobs from The Muse API based on the provided query parameters 
    url = "https://www.themuse.com/api/public/jobs"    
    # Builds the parameters for the API request based on the query parameters provided by the user.
    params = [("page", page)]
    
    if MUSE_API_KEY:
        params.append(("api_key", MUSE_API_KEY))
    
    # If the user provided any of the optional parameters (category, level, location, company), 
    # It adds them to the params dictionary in the format expected by The Muse API.
    categories = []
    for cat in (category or []):
        value = (cat or "").strip()
        if value:
            categories.append(value)
    for cat in (catogory or []):
        value = (cat or "").strip()
        if value:
            categories.append(value)

    # Preserve first-seen order while removing duplicates.
    categories = list(dict.fromkeys(categories))

    if categories:
        for cat in categories:
            params.append(("category", cat))
    if level:
        for lvl in level:
            params.append(("level", lvl))
    if location:
        for loc in location:
            params.append(("location", loc))
    if company:
        for comp in company:
            params.append(("company", comp))
    
    # Makes an GET request to The Muse API using httpx with the constructed parameters. 
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        # If the response status code is not 200, it raises an HTTP 500 error indicating that the job search failed. 
        # If the request is successful, it processes the response data to extract relevant job information and returns it in a structured format.
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch jobs from The Muse API")
    
    # Turns the raw data from The Muse API into a json format that the frontend can easily use.
    data = response.json()
    
    # Exracts the list of jobs from the response data
    # If the "results" key is not present, it defaults to an empty list.
    jobs = data.get("results", [])
    
    # Iterates over all the list of jobs and constructs a new list of job data with only the relevant information needed by the frontend.
    job_data = []
    for job in jobs:
        has_remote, has_hybrid = _classify_job_work_mode(job)
        location_mode_flags = []
        if has_remote:
            location_mode_flags.append("remote")
        if has_hybrid:
            location_mode_flags.append("hybrid")

        job_data.append({
            "id": job.get("id"),
            "name": job.get("name"),
            "company": job.get("company", {}).get("name"),
            "locations": [loc.get("name") for loc in job.get("locations", []) if loc.get("name")],
            "levels": [lvl.get("name") for lvl in job.get("levels", [])],
            "categories": [cat.get("name") for cat in job.get("categories", [])],
            "has_remote": has_remote,
            "has_hybrid": has_hybrid,
            "location_mode_flags": location_mode_flags,
            "publication_date": job.get("publication_date"),
            "job_url": job.get("refs", {}).get("landing_page"),
        })
    # Returns the structured JSON response containing the current page number, total pages, total jobs, and the list of job data extracted from The Muse API.
    return {
        "page": data.get("page"),
        "total_pages": data.get("page_count"),
        "total_jobs": data.get("total"),
        "jobs": job_data,
    }

@router.post("/jobs/save", tags=["jobs"])
async def save_job(
    # Creates an endpoint for saving a job to the user's profile with the required job data and a database session dependency.
    job_data: SaveJobRequest,
    db: Session = Depends(get_db),
):
    # Checks if the job is already saved for the user by querying the SavedJob table in the database with the user ID and job ID.
    existing_job = db.query(SavedJob).filter(
        SavedJob.user_id == job_data.user_id,
        SavedJob.job_id == job_data.job_id
    ).first()
    
    # If the job is already saved, it raises an HTTP 400 error indicating that the job has already been saved by the user.
    if existing_job:
        raise HTTPException(status_code=400, detail="Job already saved")
    
    # If the job isnt saved, it creates a new SavedJob instance with the provided job data and adds it to the database session.
    new_saved_job = SavedJob(
        user_id=job_data.user_id,
        job_id=job_data.job_id,
        title=job_data.name,
        company=job_data.company,
        url=job_data.url
    )
    # Commits the transaction to save the new job to the database and refreshes the instance to get the updated data.
    db.add(new_saved_job)
    db.commit()
    db.refresh(new_saved_job)
    # Tells the frontend that the job has been successfully saved to the user's profile with a success message.
    return {"message": f"Successfully saved  {job_data.name} at {job_data.company}!"}


@router.get("/jobs/saved", tags=["jobs"])
async def get_saved_jobs(
    # Creates an endpoint for retrieving all saved jobs for a user with a database session dependency.
    user_id: int,
    db: Session = Depends(get_db),
):
    # Queries the SavedJob table in the database to get all saved jobs for the specified user ID.
    saved_jobs = db.query(SavedJob).filter(SavedJob.user_id == user_id).all()
    
    # Constructs a list of saved job data with relevant information such as job ID, title, company, and job URL.
    saved_job_data = []
    for job in saved_jobs:
        saved_job_data.append({
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "job_url": job.url,
        })
    # Returns the structured JSON response containing the list of saved jobs for the user.
    return {"saved_jobs": saved_job_data}

@router.get("/auth/google", tags=["google auth"])
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
    
    
    
@router.get("/auth/google/callback", response_model=TokenResponse, tags=["google auth"])
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
                "client_secret": GOOGLE_CLIENT_SECRET,
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
        user_access_token = create_access_token(data={"sub": str(user.id)})
        
        return TokenResponse(access_token=Token, user=UserResponse.model_validate(user),
    )


@router.get("/status", tags=["status"])
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


@router.get("/diagnostics", tags=["status"])
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
