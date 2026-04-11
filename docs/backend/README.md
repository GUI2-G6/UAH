# UAH Backend - Local Development Guide

This guide explains how to run the FastAPI backend locally for testing purposes on your own machine. We use `docker-compose.local.yml` for a localhost-only database and optional localhost-only backend profile, then run either host `uvicorn` or backend passthrough mode for frontend integration.

**Note:** This setup will run the database on your local machine and will not touch or break the dev server infrastructure.

## Choose Your Local Mode

Use one of these paths depending on what you are testing:

- Host Development (recommended): database in `docker-compose.local.yml`, backend via `uvicorn`, frontend via `npm run dev:backend`.
- Backend Compose Profile (optional): database + backend via `docker-compose.local.yml --profile backend`, frontend via `npm run dev:backend`.
- Full Docker Dev Stack: all services via `docker-compose.yml` for VPN-networked dev environment behavior.

This document is the source of truth for Host Development and is intentionally isolated from the remote dev and beta deployment workflows.

## Prerequisites
- [Docker](https://www.docker.com/) installed and running.
- [Python 3.10-3.13](https://www.python.org/downloads/) installed.
- Optional for full local UI flow: [Node.js 20+](https://nodejs.org/).

## Required Environment Variables for Local Backend

The backend validates required secrets on startup. Set these before launching `uvicorn`:

- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `SESSION_SECRET`
- `POSTGRES_HOST=localhost` (required for host-run backend with local DB container)

Recommended: load these from the repository root `.env` file instead of typing placeholder values manually.

### Optional: Dev Test Account Bootstrap

The backend supports a dev/local-only seeded test account via env flags:

- `DEV_AUTH_TEST_ACCOUNT_ENABLED`
- `DEV_AUTH_TEST_PASSWORD`
- `DEV_AUTH_TEST_EMAIL`
- `DEV_AUTH_TEST_USERNAME` (legacy fallback only)
- `DEV_AUTH_TEST_FIRST_NAME`
- `DEV_AUTH_TEST_LAST_NAME`
- `DEV_AUTH_TEST_IS_ADMIN`
- `DEV_AUTH_TEST_ROTATE_PASSWORD`

Behavior:

- If `DEV_AUTH_TEST_ACCOUNT_ENABLED=true`, email and password must be set.
- `DEV_AUTH_TEST_USERNAME` remains accepted as a temporary compatibility fallback identifier but should be treated as an email value.
- This feature is blocked in beta/prod and should remain disabled there.

You can generate secrets with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Step 1: Start the Local Database

From the **root of the repository** (where the `docker-compose.local.yml` file is located), start the PostgreSQL container:

```bash
docker compose -f docker-compose.local.yml up -d db-local
```

This will automatically create a database container running on `localhost:5432` with the correct default user, password, and database variables.

Optional: run local backend in Docker as well (still localhost-only):

```bash
docker compose -f docker-compose.local.yml --profile backend up -d db-local backend-local
```

## Step 2: Set Up Python Virtual Environment

Navigate into the `backend/` directory from a terminal and create a virtual environment:

### On Windows (PowerShell/CMD):
```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\activate
python -V
python -c "import sys; print(sys.executable)"
pip -V
```

If Python 3.12 is not installed, use Python 3.13 instead:

```powershell
py -3.13 -m venv venv
```

Important checks on Windows:

- `pip -V` must point inside `...\\UAH\\backend\\venv\\...`
- If `pip -V` points to a global Python path (for example Python 3.14 under AppData), venv activation did not apply correctly

### On Mac/Linux:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

## Step 3: Install Dependencies

With the virtual environment activated, install the backend libraries:
```bash
python -m pip install -r requirements.txt
```

## Step 4: Run the Backend

Before running the FastAPI server, you need to map PostgreSQL's host to `localhost` so Python knows where to find the database container you started in Step 1.

Important: `POSTGRES_HOST=db` is for backend running inside Docker compose. For this host-run guide, use `POSTGRES_HOST=localhost`.

Recommended on Windows (loads real values from repository root `.env`):

```powershell
# Run from backend/
Get-Content ..\.env | ForEach-Object {
	if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
	$parts = $_.Split('=',2)
	if ($parts.Count -eq 2) {
		[Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
	}
}
$env:POSTGRES_HOST="localhost"
python -m uvicorn app.main:app --reload
```

Do not use placeholder values like `"your-db-password"` or `"your-generated-secret"` for local startup. Use your actual `.env` values.

### On Windows (PowerShell):
```powershell
$env:POSTGRES_HOST="localhost"
python -m uvicorn app.main:app --reload
```

### On Mac/Linux:
```bash
POSTGRES_PASSWORD="<actual-password>" \
SECRET_KEY="<actual-secret-key>" \
SESSION_SECRET="<actual-session-secret>" \
POSTGRES_HOST=localhost \
python -m uvicorn app.main:app --reload
```

## Step 5: Test the API

Open your browser and navigate to the Swagger UI:
- **API Sandbox:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health:** [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **API Root:** [http://localhost:8000/api/](http://localhost:8000/api/)

Optional frontend dev flow (separate terminal from repository `frontend/` directory):

```bash
npm install
npm run dev:backend
```

Then open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api`, `/docs`, and `/openapi.json` to `http://localhost:8000`.

If you want frontend-only renderability without backend dependency, use `npm run dev` instead (mock mode).

## Teardown

To shut down the backend, press `Ctrl + C` in the terminal where `uvicorn` is running.

To shut down the local database:
```bash
# From the root of the repository
docker compose -f docker-compose.local.yml down
```

## Full Docker Dev Stack (non-host mode)

If you need to mirror the shared dev infrastructure behavior instead of host-run debugging, use `docker-compose.yml` from the repository root:

```bash
docker compose up -d --build
```

This mode expects the existing shared dev networking assumptions (including external infrastructure such as the VPN container). It is separate from the host-run local flow above.

## Email Verification / Password Reset (Google Workspace)

Right now, the API endpoints for email verification and password reset generate JWT tokens.

- If `EMAILS_ENABLED=false`, the backend returns the token in the API response ("dev only") so you can test locally.
- If `EMAILS_ENABLED=true`, the backend will email the token using SMTP.

Dev token endpoints:

- Password reset token: `POST /api/account/forgot-password`
- Email verification token (authenticated): `POST /api/account/send-verification`

### Option A (simplest): Gmail SMTP with an App Password

1. Pick a real mailbox like `noreply@uahapp.com` (or `security@uahapp.com`).
2. Enable 2‑Step Verification on that mailbox.
3. Create an App Password (Google Account → Security → App passwords).
4. Set these env vars for the backend:

```powershell
$env:EMAILS_ENABLED="true"
$env:PUBLIC_APP_URL="https://uahapp.com"

$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USE_TLS="true"
$env:SMTP_USERNAME="noreply@uahapp.com"
$env:SMTP_PASSWORD="<APP_PASSWORD>"
$env:SMTP_FROM="UAH <noreply@uahapp.com>"
```

### Option B (production-friendly): Google Workspace SMTP relay

If you don’t want to store a mailbox password on the server, set up an SMTP relay in Google Admin:

- Admin console → Apps → Google Workspace → Gmail → Routing → SMTP relay service
- Allow your backend server IP(s) to relay
- Require TLS
- Restrict sender domain to `uahapp.com`

Then configure the backend with `SMTP_HOST="smtp-relay.gmail.com"` (port 587) and either:
- no auth (IP allowlist), or
- SMTP auth (depending on your relay configuration)

### Deliverability (recommended)

For best results, ensure your DNS has:
- SPF including Google (`include:_spf.google.com`)
- DKIM enabled in Google Admin and published to DNS
- A basic DMARC record

## Troubleshooting

### Error: `[Errno 13] Permission denied: ...\\venv\\Scripts\\python.exe` or `[WinError 5] Access is denied`

This means files in `backend/venv` are locked by a running Python/Uvicorn process (or another tool scanning loaded `.pyd` files).

Fix (fastest on Windows):

1. Stop running backend processes (`Ctrl+C` in backend terminals).
2. Create a fresh virtual environment in a new folder and use that instead of the locked one:

```powershell
cd backend
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Then run backend with the same environment-loading flow shown above.

Optional cleanup later (when no process holds locks): remove old `venv`.

### Error: `sqlalchemy.exc.OperationalError` / `password authentication failed for user "uah"`

This means your running local Postgres volume has a different password than the one your backend is using.

Fix (keeps current local volume data):

1. Confirm your intended password in repository root `.env` (`POSTGRES_PASSWORD`).
2. Update the DB role password inside the local container:

```powershell
docker exec uah-local-db psql -U uah -d uah_dev -c "ALTER USER uah WITH PASSWORD '<POSTGRES_PASSWORD from .env>';"
```

Alternative (fresh local DB):

```powershell
docker compose -f docker-compose.local.yml down
docker compose -f docker-compose.local.yml up -d
```

### Error: `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`

This usually means the local venv is using an unsupported Python interpreter version for pinned dependency wheels (commonly Python 3.14).

Fix:

1. Stop `uvicorn`.
2. Remove the local venv.
3. Recreate it with Python 3.13 (or 3.12) and reinstall dependencies.

Windows example:

```powershell
deactivate
Remove-Item -Recurse -Force .\venv
py -3.12 -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
```
