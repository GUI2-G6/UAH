# Backend Development Guide

This is the current source of truth for running the FastAPI backend locally.

Use it when you need:

- a host-run backend with a local Postgres container
- a localhost-only Docker backend for frontend integration
- queue-enabled local parsing and job-sync testing

For repo-wide context, start with [../README.md](../README.md) and [../architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md).

## Choose A Local Mode

| Mode | When to use it | Command surface |
| --- | --- | --- |
| Host-run backend | Best for backend iteration, debugging, and normal local API work | Python venv + `uvicorn` |
| Compose backend profile | Best when you want a full localhost-only backend container | `docker-compose.local.yml --profile backend` |
| Full dev stack | Best when you need the deployed dev shape | `docker-compose.yml` and `scripts/uah.sh` |

For `scripts/uah.sh` lifecycle flows (`start`, `restart`, and post-`sync` rebuild), schema reconcile is automatic via `alembic upgrade head` inside the backend container. Failure policy is environment-aware:

- `dev`: logs warnings and continues.
- `beta`: fails fast with non-zero exit.

## Prerequisites

- Docker running locally
- Python 3.10-3.13
- Node.js 20+ if you also want the frontend
- A real repo-root `.env`

Runtime env files always live at the repository root as `.env`. Do not point the application directly at files in `env-examples/`.

## Required Env For Startup

At minimum, the backend must have:

- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `SESSION_SECRET`
- `POSTGRES_HOST=localhost` for host-run backend with the local DB container

Helpful related docs:

- [../SERVER_ENV_CHECKLIST.md](../SERVER_ENV_CHECKLIST.md)
- [../env-examples/README.md](../env-examples/README.md)
- [../../env-examples/local/.env.example](../../env-examples/local/.env.example)

When you add or rename an env var in `backend/app/core/config.py`, update **`env-examples/dev/.env.example`** and **`env-examples/beta/.env.example`** in the same change and run **`npm run check:env`** (or `python .github/scripts/check_env_sync.py --all-templates`) from the repo root. CI enforces template sync on pull requests.

### Identity compatibility notes

The backend is email-first today, but a few compatibility surfaces still exist:

- `username` remains in the schema and database as a compatibility mirror of email.
- `DEV_AUTH_TEST_USERNAME` is legacy fallback only and should contain an email value if used.
- `/api/account/change-username` is retained as a compatibility endpoint and returns `410 Gone`.

## Option 1: Host-Run Backend

### 1. Start the local database

From the repo root:

```bash
docker compose -f docker-compose.local.yml up -d db-local
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\activate
python -V
pip -V
```

macOS / Linux:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Load repo-root `.env` values

Windows PowerShell example:

```powershell
Get-Content ..\.env | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
  $parts = $_.Split('=', 2)
  if ($parts.Count -eq 2) {
    [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
  }
}
$env:POSTGRES_HOST = "localhost"
```

macOS / Linux example:

```bash
export POSTGRES_HOST=localhost
```

Use your real `.env` values. Do not swap in placeholder strings from the example files.

### 5. Apply migrations

```bash
alembic upgrade head
```

### 6. Run the backend

```bash
python -m uvicorn app.main:app --reload
```

### 7. Smoke test the local API

```text
http://localhost:8000/api/
http://localhost:8000/api/health
http://localhost:8000/api/status
http://localhost:8000/docs
```

Notes:

- `/docs`, `/redoc`, and `/openapi.json` are enabled by default only in `development`, `dev`, or `local` environments.
- Beta can opt in by setting `BETA_DOCS_PASSCODE`; when present, docs stay behind HTTP Basic auth using `BETA_DOCS_USERNAME` (default `dev`).
- `/api/diagnostics` is admin-gated even in local/dev-style environments.

## Option 2: Compose Backend Profile

This keeps the backend inside Docker but still binds only to localhost.

From the repo root:

```bash
docker compose -f docker-compose.local.yml --profile backend up -d db-local backend-local
```

Default local bindings:

- DB: `127.0.0.1:5432`
- Backend: `127.0.0.1:8000`

This mode is a good match for `frontend` backend passthrough mode:

```bash
cd frontend
npm install
npm run dev:backend
```

### Standard local dev test admin account

For local/dev workflows, the standard bypass account uses `DEV_AUTH_TEST_*` settings
(not `ADMIN_BOOTSTRAP_*`).

Default local template values in `env-examples/local/.env.example`:

- `DEV_AUTH_TEST_ACCOUNT_ENABLED=true`
- `DEV_AUTH_TEST_EMAIL=local.admin@uah.local`
- `DEV_AUTH_TEST_PASSWORD=LocalAdmin123!`
- `DEV_AUTH_TEST_IS_ADMIN=true`

This account is local/dev-only and should remain disabled in beta/prod.

## Optional: Queue And Job Sync

Resume parsing and local job-sync maintenance can run with Redis and Celery.

### Host-run worker path

Terminal 1, from repo root:

```bash
docker compose -f docker-compose.local.yml --profile jobs up -d redis-local
```

Terminal 2, from `backend/`:

```bash
set REDIS_URL=redis://localhost:6379/0
celery -A app.worker worker --loglevel=info --concurrency=2
```

Terminal 3, from `backend/`:

```bash
set REDIS_URL=redis://localhost:6379/0
celery -A app.worker beat --loglevel=info --scheduler celery.beat.PersistentScheduler
```

### Compose-only jobs path

```bash
docker compose -f docker-compose.local.yml --profile jobs up -d db-local redis-local celery-worker-local celery-beat-local
```

### Common queue-related env knobs

- `REDIS_ENABLED`
- `REDIS_URL`
- `PARSE_QUEUE_NAME*`
- `PARSE_QUEUE_MAX_RETRIES*`
- `PARSE_QUEUE_CONCURRENCY_*`
- `JOB_SYNC_*`
- `JOB_LINK_*`
- `JOB_COUNTRY_BACKFILL_*`

See [../SERVER_ENV_CHECKLIST.md](../SERVER_ENV_CHECKLIST.md) for the categorized checklist.

## Local Frontend Integration

When the backend is up locally:

```bash
cd frontend
npm run dev:backend
```

That Vite mode proxies:

- `/api`
- `/docs`
- `/openapi.json`

to the configured local backend origin. In plain mock mode (`npm run dev`), the frontend does not require the backend.

## Troubleshooting

### Virtualenv activation did not apply on Windows

Symptoms:

- `pip -V` points outside `backend/venv`
- `python` resolves to a global interpreter

Fix:

- reactivate the venv
- verify `python -V`, `python -c "import sys; print(sys.executable)"`, and `pip -V`

### Database auth failures

Check:

- repo-root `.env` contains the expected DB password
- `POSTGRES_HOST=localhost` is set for the host-run path
- the `db-local` container is healthy

### Docs routes missing

Check `ENVIRONMENT`. API docs are intentionally disabled outside `development`, `dev`, or `local`.

### Diagnostics returns 401/403

That is expected for non-admin sessions. `/api/status` is the public health-style route; `/api/diagnostics` is an admin-only troubleshooting surface.

## Related Docs

- Repo entrypoint: [../../README.md](../../README.md)
- Architecture: [../architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
- Frontend guide: [../frontend/README.md](../frontend/README.md)
- Extension guide: [../../uah-browser-extension/README.md](../../uah-browser-extension/README.md)
- Historical backend implementation snapshots: [../archive/README.md](../archive/README.md)
