# UAH Codebase Security & Production-Readiness Audit

**Branch audited:** `dev`  
**Date:** 2026-03-31  
**Scope:** Backend (FastAPI/Python), Frontend (Vue 3/Nginx), Infrastructure (Docker Compose)

---

## ⚠️ Flag for Team — Critical Issues Requiring Action Before Beta

Two critical security issues were found and are described in full in **Section 2** below. They must be resolved before beta.uahapp.com accepts any external users.

---

## Table of Contents

1. [Backend Findings](#1-backend-findings)
2. [Frontend Findings](#2-frontend-findings)
3. [Infrastructure Findings](#3-infrastructure-findings)
4. [Dependency Scan](#4-dependency-scan)
5. [Summary Table](#5-summary-table)

---

## 1. Backend Findings

### 1.1 Hardcoded URLs / Environment-Specific Values

| Severity | Location | Value | Notes |
|----------|----------|-------|-------|
| **Medium** | `backend/app/core/config.py` line ~37 | Default `PUBLIC_APP_URL = "http://localhost:5173"` | Used in email links; falls back to localhost if env var not set |
| Low | `backend/app/core/config.py` | `ZAI_OCR_URL` / `ZAI_LLM_URL` default to `https://api.z.ai/…` | External SaaS endpoints; configurable via env vars — acceptable default |
| Low | `backend/app/api/routes.py` | `https://accounts.google.com/o/oauth2/v2/auth` | Google OAuth provider URL — not environment-specific |
| Low | `backend/app/api/routes.py` | `https://oauth2.googleapis.com/token` | Google token exchange — not environment-specific |
| Low | `backend/app/services/geolocation.py` | `http://ip-api.com/json/{ip}` | Free public IP geolocation API; no key required |
| Low | `backend/app/services/geolocation.py` | `http://api.ipstack.com/{ip}` | Optional paid geolocation API; configurable via `IPSTACK_API_KEY` |

**No hardcoded secrets or API keys were found in source code.** All sensitive values are read from environment variables.

---

### 1.2 .env File Status

| Item | Status |
|------|--------|
| `.env` committed to repo | ✅ Not present — `.gitignore` excludes it |
| `.env.example` present | ✅ Present at repo root |
| `.env.example` completeness | ⚠️ See notes below |

**`.env.example` gaps / concerns:**

- `SECRET_KEY` and `SESSION_SECRET` are present but empty — the file should note the generation command (already partially documented in a comment: `python -c "import secrets; print(secrets.token_hex(32))"`).  
- `COMPOSE_PROJECT_NAME=uah-dev` is hardcoded to "dev" — a beta operator must remember to change this. Consider adding a comment.  
- `GOOGLE_REDIRECT_URI=https://dev.uahapp.com/api/auth/google/callback` is domain-specific for `dev` — beta requires updating this value.  
- `PUBLIC_APP_URL=https://dev.uahapp.com` is domain-specific for `dev` — beta requires updating this value.  
- `ADMIN_BOOTSTRAP_PASSWORD` has no description. It is optional but if enabled it grants admin access.  
- `ENVIRONMENT` variable is not present in `.env.example` but is read by `config.py`; defaults to `"development"`. Beta should set this to `"beta"` or `"production"`.

---

### 1.3 CORS Configuration

**Status: No explicit CORS middleware is configured.**

`backend/app/main.py` does not include `fastapi.middleware.cors.CORSMiddleware`. This means:

- Browser cross-origin requests to the backend are **blocked by default** — this is the correct and intended behavior.  
- The frontend uses Nginx's same-origin reverse proxy (`/api/ → backend:8000`), so no CORS headers are required for normal browser use.  
- The backend Swagger UI at `/docs` can still make requests, but this is via the same-origin Nginx proxy.

**Severity: Low** — The absence of CORS middleware is intentional and correct given the proxy architecture. No action required, but this should be documented to prevent a well-meaning developer from "fixing" it by adding a wildcard CORS rule.

---

### 1.4 Endpoints That Skip Authentication

The following endpoints require **no authentication token**. Each is assessed for whether this is intentional.

| Endpoint | Auth Required | Intentional? | Notes |
|----------|--------------|--------------|-------|
| `GET /api/` | None | ✅ Yes | Root/version check |
| `GET /api/health` | None | ✅ Yes | Docker health check |
| `GET /api/status` | None | ✅ Yes | Public status page |
| `POST /api/auth/login` | None | ✅ Yes | Login endpoint |
| `POST /api/auth/register` | None | ✅ Yes | Registration endpoint |
| `GET /api/auth/google` | None | ✅ Yes | OAuth initiation redirect |
| `GET /api/auth/google/callback` | None | ✅ Yes | OAuth callback handler |
| `POST /api/auth/token` | None | ✅ Yes | OAuth2 password flow for Swagger UI |
| `GET /api/jobs/search` | None | ✅ Yes | Public job search |
| `GET /api/geolocation/*` | None | ✅ Yes | Client IP geolocation for search UX |
| `POST /api/account/forgot-password` | None | ✅ Yes | Password reset initiation |
| `POST /api/account/verify-email` | None | ✅ Yes | Email verification token redemption |
| **`POST /api/jobs/save`** | **None** | ❌ **No** | **CRITICAL — see §1.5** |
| **`GET /api/jobs/saved`** | **None** | ❌ **No** | **CRITICAL — see §1.5** |
| **`GET /api/diagnostics`** | **None** | ❌ **No** | **HIGH — see §1.6** |

---

### 1.5 🔴 CRITICAL — Unauthenticated Job Save / Retrieve Endpoints

**File:** `backend/app/api/routes.py` lines ~1402–1453  
**Endpoints:** `POST /api/jobs/save`, `GET /api/jobs/saved`

Both endpoints accept an arbitrary `user_id` value from the **request body or query string** with no authentication check. This means:

- Any unauthenticated caller can save a job attributed to any user's account by supplying that user's numeric ID.  
- Any unauthenticated caller can retrieve the complete list of saved jobs for any account by supplying that account's numeric ID.

**Fix required:** Add `current_user: User = Depends(get_current_user)` to both endpoints and derive `user_id` from the authenticated token rather than from client input. See `CODE_CHANGES.md` for the exact diff.

---

### 1.6 🔴 CRITICAL — `/api/diagnostics` Publicly Accessible

**File:** `backend/app/api/routes.py` line ~1544  
**Endpoint:** `GET /api/diagnostics`

This endpoint is unauthenticated and returns detailed internal system information including:

- Python version and platform string  
- Server hostname and PID  
- PostgreSQL version, database name, DB user, database size, table count, host, and port  
- External API reachability (Z.AI, Muse, SMTP)  
- Application version and environment label  
- Geolocation dataset build state  

This is an information disclosure risk in any environment reachable by untrusted parties. The current deployment is VPN-only, which mitigates exposure, but on beta.uahapp.com (Cloudflare-proxied but accessible to testers) this must be addressed.

**Fix required (choose one):**  
- Require admin authentication on the endpoint (`Depends(require_admin_user)`), or  
- Strip all internal details (DB credentials, host, PID, versions) from the public response, or  
- Remove the Nginx proxy pass for `/diagnostics` so it is only accessible from within the Docker network.

---

### 1.7 Endpoints That Expose Sensitive Internal Data

| Endpoint | Exposed Data | Severity |
|----------|-------------|----------|
| `GET /api/diagnostics` | DB version, user, size, host, PID, Python version, platform | 🔴 Critical (see §1.6) |
| `GET /docs` | Full API schema, all endpoints, all parameter names | 🟡 High |
| `GET /redoc` | Same as `/docs` (alternate renderer) | 🟡 High |
| `GET /openapi.json` | Machine-readable full API schema | 🟡 High |

The FastAPI app enables `/docs`, `/redoc`, and `/openapi.json` by default. These are proxied through Nginx (see `nginx.http.conf` and `nginx.https.conf`). In a VPN-only environment this is acceptable; for beta.uahapp.com they should be disabled or gated behind admin authentication.

---

### 1.8 Rate Limiting

**Status: No global rate limiting middleware is present.**

| Endpoint | Rate Limiting | Notes |
|----------|--------------|-------|
| `POST /api/auth/login` | ❌ None | Brute-force risk |
| `POST /api/auth/register` | ❌ None | Account enumeration / spam risk |
| `POST /api/account/forgot-password` | ❌ None | Email flooding risk |
| `POST /api/account/send-verification` | ❌ None | Email flooding risk |
| `GET /api/jobs/search` | ❌ None | Resource exhaustion risk |
| `POST /api/resume/upload` | ✅ Per-user cooldown (30 s) | Implemented in `resume.py` |
| `POST /api/resume/reparse` | ✅ Per-user cooldown (10 s) | Implemented in `resume.py` |

**Recommendation:** For beta, rate limiting on auth and email endpoints should be implemented at the Cloudflare WAF layer (see `CLOUDFLARE_SECURITY.md`). Application-level rate limiting (e.g., `slowapi`) should be added as a defense-in-depth measure in a future sprint.

---

### 1.9 Session and Token Handling

| Property | Value | Assessment |
|----------|-------|------------|
| JWT algorithm | `HS256` | Acceptable for internal use |
| JWT signing key | `SECRET_KEY` env var (required, crashes if missing) | ✅ Good |
| Access token expiry | 60 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`) | Configurable; acceptable |
| Refresh token | ❌ Not implemented | Users must re-login after expiry |
| Session middleware | `starlette.middleware.sessions.SessionMiddleware` | Used for OAuth state only |
| Session secret | `SESSION_SECRET` env var (required) | ✅ Good |
| Token storage (frontend) | `localStorage` | Acceptable given VPN/Cloudflare gating; XSS risk if gating is removed |

**Note on refresh tokens:** The absence of a refresh token flow means users are logged out after 60 minutes of inactivity. This is a usability concern rather than a security concern. For beta, this is acceptable.

---

## 2. Frontend Findings

### 2.1 API Base URL Configuration

All API calls in the frontend source use **relative paths** (e.g., `/api/auth/login`, `/api/jobs/search`). No API base URL is hardcoded.

These relative paths are resolved by Nginx's reverse proxy rule:

```nginx
location /api/ {
    proxy_pass http://backend:8000;
}
```

**This means the frontend is completely environment-agnostic** — the same built `dist/` bundle works on `dev.uahapp.com`, `beta.uahapp.com`, or any other domain without rebuilding. No frontend code changes are required for beta.

**Severity: None** — No issues found.

---

### 2.2 Secrets or Tokens in Frontend Source

No secrets, API keys, or tokens were found in frontend source code. The only configuration consumed by the frontend at runtime is the relative `/api/*` path, which is not sensitive.

**Severity: None** — No issues found.

---

### 2.3 Routes Requiring Authentication

The Vue Router configuration (`frontend/src/router/index.js`) uses navigation guards to protect authenticated routes. The `lib/auth.js` module checks for a valid, non-expired JWT in `localStorage` before allowing access to protected views.

**Potential concern:** JWT validation on the frontend is purely expiry-based (checking the `exp` claim by decoding the token client-side without verifying the signature). This is standard for SPAs — the server always validates the signature before acting on a token.

**Severity: Low** — No direct issue; matches standard SPA patterns.

---

## 3. Infrastructure Findings

### 3.1 docker-compose.yml

| Item | Assessment | Severity |
|------|-----------|----------|
| `db` — no host ports exposed | ✅ Database is not reachable outside Docker network | None |
| `backend` — no host ports exposed | ✅ Backend is not directly reachable | None |
| `frontend` — `network_mode: "container:uah-dev-vpn"` | ✅ Frontend only accessible via VPN container | None |
| `backend` volume `./backend:/app` | ⚠️ Hot-reload source mount should be removed for beta | Medium |
| `backend` CMD uses `--reload` flag (in Dockerfile) | ⚠️ Should be removed for beta | Medium |
| No resource limits (`mem_limit`, `cpus`) | ⚠️ Container can exhaust host resources | Medium |
| `restart: unless-stopped` | ✅ Appropriate for always-on deployment | None |
| Health check on `db` | ✅ Backend waits for healthy DB | None |
| `uah-infra` network is `external: true` | ✅ Managed by infrastructure, not this compose | None |
| `COMPOSE_PROJECT_NAME=uah-dev` | ⚠️ Should be changed to `uah-beta` for the beta environment | Low |

---

### 3.2 docker-compose.local.yml

| Item | Assessment | Severity |
|------|-----------|----------|
| DB port `5432:5432` exposed to host | ✅ Intentional for local development only | None (dev-only file) |
| `POSTGRES_DB: uah_dev` hardcoded | ⚠️ Not driven by env var — only acceptable for local dev | Low |

This file is only for local developer use and should never be deployed to any server environment.

---

### 3.3 .env.example — Variable Audit

| Variable | Description Present | Insecure Default | Notes |
|----------|-------------------|-----------------|-------|
| `COMPOSE_PROJECT_NAME` | ❌ No description | — | Needs description; must change for beta |
| `ENV` | ❌ No description | — | Undocumented; set to "dev" by default |
| `DEV_DOMAIN` | ❌ No description | — | Must change to `beta.uahapp.com` for beta |
| `POSTGRES_PASSWORD` | ❌ No description | Empty | ⚠️ Must not be empty in any deployment |
| `SECRET_KEY` | ✅ Generation command noted | Empty | ⚠️ Must not be empty in any deployment |
| `SESSION_SECRET` | ❌ No description | Empty | ⚠️ Must not be empty in any deployment |
| `GOOGLE_REDIRECT_URI` | ❌ No description | `dev.uahapp.com` URL | Must update for beta |
| `PUBLIC_APP_URL` | ❌ No description | `dev.uahapp.com` URL | Must update for beta; used in email links |
| `EMAILS_ENABLED` | ❌ No description | `false` | Must set to `true` for beta |
| `ADMIN_BOOTSTRAP_PASSWORD` | ❌ No description | Empty | If used, must be a strong random value |
| `ENVIRONMENT` | ❌ Not in example | Defaults to `"development"` | Should be added to example; set to `"production"` for beta |

---

## 4. Dependency Scan

### 4.1 Backend (requirements.txt)

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
psycopg2-binary==2.9.10
beautifulsoup4==4.12.3
httpx==0.27.2
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.4.0
bcrypt==4.1.2
itsdangerous==2.2.0
python-multipart==0.0.22
python-dotenv==1.0.1
```

| Package | Version | Known CVE | Notes |
|---------|---------|-----------|-------|
| `python-jose` | 3.4.0 | ⚠️ CVE-2024-33663 | Algorithm confusion / key confusion vulnerability in some jose implementations. Verify that `HS256`-only usage mitigates this. Monitor for upstream patches. |
| `passlib` | 1.7.4 | Low | `passlib` is in maintenance mode; bcrypt context is functional. |
| `psycopg2-binary` | 2.9.10 | None known | Binary distribution; check for updates before beta. |
| All others | — | None known at time of audit | Pin all versions if not already pinned. |

**Note:** A full CVE scan using a tool such as `pip-audit` or `safety` should be run as part of the pre-beta checklist. The table above is based on publicly known advisories at the time of this audit.

### 4.2 Frontend (package.json)

```json
"vue": "^3.5.28",
"vue-router": "^4.5.0",
"vite": "^7.3.1",
"@vitejs/plugin-vue": "^6.0.4",
"vite-plugin-vue-devtools": "^8.0.6"
```

| Package | Notes |
|---------|-------|
| `vite-plugin-vue-devtools` | ⚠️ **Development-only** plugin. Must not be included in a production build. Verify it is excluded from the Vite production build or remove it from `package.json` before beta. |
| All others | No known critical CVEs at time of audit. |

---

## 5. Summary Table

| # | Finding | Severity | Area | Status |
|---|---------|----------|------|--------|
| 1 | `POST /api/jobs/save` — no authentication, accepts arbitrary `user_id` | 🔴 Critical | Backend | Must fix |
| 2 | `GET /api/jobs/saved` — no authentication, accepts arbitrary `user_id` | 🔴 Critical | Backend | Must fix |
| 3 | `GET /api/diagnostics` — publicly accessible, leaks internal system details | 🔴 Critical | Backend | Must fix |
| 4 | `/docs`, `/redoc`, `/openapi.json` publicly accessible via Nginx proxy | 🟡 High | Backend/Infra | Fix for beta |
| 5 | No rate limiting on auth/email endpoints | 🟡 High | Backend | Mitigate via Cloudflare WAF for beta; add app-level later |
| 6 | Backend `--reload` flag and source volume mount active in dev compose | 🟠 Medium | Infra | Remove for beta |
| 7 | `PUBLIC_APP_URL` defaults to `http://localhost:5173` if env var not set | 🟠 Medium | Backend | Set correctly in beta .env |
| 8 | No resource limits on containers | 🟠 Medium | Infra | Add for beta |
| 9 | `vite-plugin-vue-devtools` present in frontend deps | 🟠 Medium | Frontend | Verify excluded from prod build |
| 10 | `python-jose` 3.4.0 — potential algorithm confusion CVE | 🟠 Medium | Backend | Review and update |
| 11 | `ENVIRONMENT` env var missing from `.env.example` | 🟡 Low | Config | Add to example |
| 12 | Several `.env.example` variables lack descriptions | 🟡 Low | Config | Document |
| 13 | No refresh token mechanism | 🟡 Low | Backend | Acceptable for beta |
| 14 | JWT stored in `localStorage` | 🟡 Low | Frontend | Acceptable given Cloudflare gating |
| 15 | `docker-compose.local.yml` hardcodes DB name | 🟡 Low | Infra | Dev-only, acceptable |
