# Historical Snapshot: Beta Environment — Required Code Changes

This document is preserved as a point-in-time implementation delta list from an earlier beta planning pass.

It should not be treated as the current beta setup guide. Use these active docs instead:

- [../../beta-prep/BETA_SETUP.md](../../beta-prep/BETA_SETUP.md)
- [../../beta-prep/SECURITY_CHECKLIST.md](../../beta-prep/SECURITY_CHECKLIST.md)

# Beta Environment — Required Code Changes

This document lists every specific file and change needed to support the beta deployment at `beta.uahapp.com`. Items are grouped by category. Changes that apply to a new `docker-compose.beta.yml` file are described as additions, not modifications to the existing dev file.

---

## 1. `.env` (Not Committed — Per-Environment File)

These are not code changes but are the most critical configuration changes. See `env-examples/beta/.env.example` for the full template.

| Variable | Dev Value | Beta Value | Why |
|----------|----------|-----------|-----|
| `COMPOSE_PROJECT_NAME` | `uah-dev` | `uah-beta` | Prevents container name collisions on the same Docker host |
| `ENV` | `dev` | `beta` | Environment label in logs and diagnostics |
| `ENVIRONMENT` | `development` | `production` | Disables debug features in backend |
| `DEV_DOMAIN` | `dev.uahapp.com` | `beta.uahapp.com` | Used by Nginx `server_name` |
| `POSTGRES_DB` | `uah_dev` | `uah_beta` | Separate database per environment |
| `POSTGRES_PASSWORD` | (dev password) | (new strong secret) | Separate credentials per environment |
| `SECRET_KEY` | (dev key) | (new strong secret) | Separate JWT signing key per environment |
| `SESSION_SECRET` | (dev key) | (new strong secret) | Separate session key per environment |
| `GOOGLE_REDIRECT_URI` | `https://dev.uahapp.com/api/auth/google/callback` | `https://beta.uahapp.com/api/auth/google/callback` | OAuth callback must match the active domain |
| `PUBLIC_APP_URL` | `https://dev.uahapp.com` | `https://beta.uahapp.com` | Base URL injected into email links |
| `EMAILS_ENABLED` | `false` | `true` | Enable real email sending for beta |

---

## 2. New File: `docker-compose.beta.yml`

**Do not modify `docker-compose.yml`** — that file serves the dev environment. Instead, create a `docker-compose.beta.yml` that overrides only the parts that differ for beta.

**File path:** `docker-compose.beta.yml` (at repo root, alongside `docker-compose.yml`)

### 2.1 Changes from `docker-compose.yml`

#### Remove source volume mount from backend

```yaml
# In docker-compose.yml (dev) — REMOVE this for beta:
volumes:
  - ./backend:/app   # Hot-reload mount — dev only

# In docker-compose.beta.yml — do NOT include this volume
```

The backend container should only contain the image-baked code. Source mounting the directory enables hot-reload but also exposes the source tree inside the container.

#### Remove --reload from backend startup command

```yaml
# In docker-compose.yml (dev), the Dockerfile CMD is:
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# In docker-compose.beta.yml, override the command:
backend:
  command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

**File:** `docker-compose.beta.yml`  
**Current:** Inherits `--reload` from Dockerfile CMD  
**Should be:** Override with `--workers 2` (no reload)  
**Why:** `--reload` watches the filesystem for changes and restarts the server — inappropriate for a beta/production deployment and a potential information disclosure risk.

#### Change frontend network mode

```yaml
# In docker-compose.yml (dev):
network_mode: "container:uah-dev-vpn"

# In docker-compose.beta.yml:
frontend:
  network_mode: ""          # Remove VPN network sharing
  networks:
    - uah-infra
  ports:
    - "80:80"               # Expose port 80 to host (Cloudflare reaches this)
```

**Why:** The dev frontend shares the VPN container's network namespace. Beta does not have a VPN container — instead, Cloudflare proxies traffic directly to port 80 on the host. The host firewall restricts port 80 to Cloudflare IP ranges only.

#### Add resource limits

```yaml
# In docker-compose.beta.yml, add to each service:
backend:
  deploy:
    resources:
      limits:
        memory: 512m
        cpus: "1.0"

frontend:
  deploy:
    resources:
      limits:
        memory: 128m
        cpus: "0.5"

db:
  deploy:
    resources:
      limits:
        memory: 512m
        cpus: "1.0"
```

**Why:** Without resource limits, a single misbehaving container can exhaust host memory or CPU, taking down other services.

#### Update container names

```yaml
# In docker-compose.beta.yml, override container names:
db:
  container_name: uah-beta-db

backend:
  container_name: uah-beta-backend

frontend:
  container_name: uah-beta-frontend
```

**Why:** Allows dev and beta to coexist on the same Docker host without name conflicts (in addition to `COMPOSE_PROJECT_NAME`).

---

## 3. Backend: `backend/app/api/routes.py`

### 3.1 🔴 Fix `/api/jobs/save` — Add Authentication

**File:** `backend/app/api/routes.py`  
**Lines:** ~1402–1431

**Current code:**
```python
@router.post("/jobs/save", tags=["jobs"])
async def save_job(
    job_data: SaveJobRequest,
    db: Session = Depends(get_db),
):
    existing_job = db.query(SavedJob).filter(
        SavedJob.user_id == job_data.user_id,
        SavedJob.job_id == job_data.job_id
    ).first()
    ...
    new_saved_job = SavedJob(
        user_id=job_data.user_id,
        ...
    )
```

**Should be:**
```python
from app.api.deps import get_current_user
from app.models.user import User

@router.post("/jobs/save", tags=["jobs"])
async def save_job(
    job_data: SaveJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing_job = db.query(SavedJob).filter(
        SavedJob.user_id == current_user.id,
        SavedJob.job_id == job_data.job_id
    ).first()
    ...
    new_saved_job = SavedJob(
        user_id=current_user.id,
        ...
    )
```

**Why:** Without authentication, any unauthenticated caller can save jobs attributed to any user's account by supplying an arbitrary `user_id`. The fix derives `user_id` from the validated JWT token instead.

---

### 3.2 🔴 Fix `/api/jobs/saved` — Add Authentication

**File:** `backend/app/api/routes.py`  
**Lines:** ~1434–1453

**Current code:**
```python
@router.get("/jobs/saved", tags=["jobs"])
async def get_saved_jobs(
    user_id: int,
    db: Session = Depends(get_db),
):
    saved_jobs = db.query(SavedJob).filter(SavedJob.user_id == user_id).all()
```

**Should be:**
```python
@router.get("/jobs/saved", tags=["jobs"])
async def get_saved_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    saved_jobs = db.query(SavedJob).filter(SavedJob.user_id == current_user.id).all()
```

**Why:** Without authentication, any caller can retrieve the saved jobs list for any account by guessing or knowing the numeric user ID. The fix removes the `user_id` query parameter entirely and derives it from the authenticated token.

---

### 3.3 🔴 Gate or Remove `/api/diagnostics`

**File:** `backend/app/api/routes.py`  
**Lines:** ~1544+

**Option A — Require admin authentication (recommended):**
```python
# Add admin check dependency (create this in deps.py if it doesn't exist):
from app.api.deps import require_admin_user

@router.get("/diagnostics", tags=["status"])
async def diagnostics(current_user: User = Depends(require_admin_user)):
    ...
```

**Option B — Remove from Nginx proxy (simpler):**

In `frontend/nginx.http.conf` and `frontend/nginx.https.conf`, remove or comment out:
```nginx
# Remove this block:
location /diagnostics {
    proxy_pass http://backend:8000;
}
```

If there is no explicit `/diagnostics` proxy block (it may be covered by the `/api/` catch-all), add an explicit block that returns 404:
```nginx
location = /api/diagnostics {
    return 404;
}
```

Place this block **before** the `/api/` proxy block so it takes precedence.

**Why:** The diagnostics endpoint returns detailed internal system information (database version, user, size, Python version, PID, hostname). This information is useful for operators but creates an information disclosure risk for any external user who can reach the endpoint.

---

## 4. Backend: `backend/app/main.py`

### 4.1 Disable API Documentation in Production

**File:** `backend/app/main.py`  
**Lines:** ~192–197 (the `FastAPI(...)` instantiation)

**Current code:**
```python
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Unified Application Hub — DEV API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
```

**Should be:**
```python
is_production = settings.ENVIRONMENT == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Unified Application Hub API",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
    lifespan=lifespan,
)
```

**Why:** When `ENVIRONMENT` resolves to a non-dev runtime such as `beta` or `production`, FastAPI will not serve `/docs`, `/redoc`, or `/openapi.json`. This removes the interactive API explorer and the full schema from public access. The dev environment retains these URLs unchanged.

---

## 5. Frontend Nginx Config

### 5.1 Remove `/docs`, `/redoc`, `/openapi.json` Proxy Blocks (If Present)

**Files:** `frontend/nginx.http.conf`, `frontend/nginx.https.conf`

Check whether these files contain explicit proxy blocks for the docs URLs:
```nginx
location /docs { proxy_pass http://backend:8000; }
location /redoc { proxy_pass http://backend:8000; }
location /openapi.json { proxy_pass http://backend:8000; }
```

If the fix in §4.1 above disables these URLs at the FastAPI level (returning 404), the Nginx proxy blocks are harmless but redundant. Removing them makes the intent explicit.

**Should be:** Remove or comment out those three `location` blocks.

---

## 6. `env-examples/dev/.env.example` — Documentation Improvements

These changes improve the developer experience but do not affect beta deployment directly.

**File:** `env-examples/dev/.env.example`  
**Changes:** Add descriptions to undocumented variables.

```bash
# Before (no description):
COMPOSE_PROJECT_NAME=uah-dev

# After:
# Docker project name prefix. Change per environment (uah-dev, uah-beta, uah-prod)
# to avoid container name conflicts when multiple environments share a host.
COMPOSE_PROJECT_NAME=uah-dev
```

Similarly add descriptions for:
- `ENV` — "Short environment tag (dev, beta, prod). Used in log output."
- `ENVIRONMENT` — "Controls backend docs/debug gating. Set to 'beta' for beta or 'production' for prod."
- `DEV_DOMAIN` — "Public hostname for this deployment. Used by Nginx server_name."
- `SESSION_SECRET` — "Signing key for session cookies. Generate same as SECRET_KEY."
- `ADMIN_BOOTSTRAP_PASSWORD` — "Admin password if ADMIN_BOOTSTRAP_ENABLED=true. Must be strong."

Add the missing variable:
```bash
# Runtime environment label consumed by backend config.py.
# Set to "beta" for beta deployments and "production" for prod deployments.
ENVIRONMENT=development
```

---

## Summary of Changes by Priority

| Priority | File | Change |
|----------|------|--------|
| 🔴 Critical | `backend/app/api/routes.py` | Add `get_current_user` dependency to `/api/jobs/save` |
| 🔴 Critical | `backend/app/api/routes.py` | Add `get_current_user` dependency to `/api/jobs/saved` |
| 🔴 Critical | `backend/app/api/routes.py` or `nginx.http.conf` | Gate or block `/api/diagnostics` |
| 🟡 High | `backend/app/main.py` | Disable `/docs`, `/redoc`, `/openapi.json` outside dev/local runtimes |
| 🟠 Medium | `docker-compose.beta.yml` (new) | Remove hot-reload, add ports, remove VPN network mode, add resource limits |
| 🟢 Low | `env-examples/dev/.env.example` | Add descriptions for undocumented variables, add `ENVIRONMENT` variable |
