# UAH — Unified Application Hub

> **DEV Environment Documentation**
> All commands assume you are SSH'd into the server at  `/srv/uah/environments/dev` on proxmox

---

## Connecting to the Server

The app runs on an Ubuntu 24.04 VM behind a Proxmox host. To access it:

### 1. SSH into the VM

```bash
ssh uahdeploy@192.168.1.230
```

You'll be prompted for the `uahdeploy` user's password. After login you'll land in the home directory (`/home/uahdeploy`).

### 2. Navigate to the project

```bash
cd /srv/uah
```

The `/srv/uah` directory is the root of the deployment and contains:

```
/srv/uah/
├── environments/
│   ├── dev/          # Dev environment (docker-compose, app code, volumes)
│   └── prod/         # Production environment
├── infrastructure/   # VPN, tunnel, and network configs
└── shared/           # Shared resources
```

To get to the dev environment specifically:

```bash
cd /srv/uah/environments/dev
```

From here you can run `docker compose` commands, view logs, sync code, etc.

### 3. Verify services are running

```bash
docker ps
```

You should see containers for the frontend, backend, database, and VPN.

---

## Architecture

```
                    VPN Clients
                        │
                   ┌────▼────┐
                   │ WireGuard│  (10.8.0.1)
                   │ wg-easy  │
                   └────┬────┘
                        │ network_mode: container
                   ┌────▼────────┐
                   │  Frontend   │  Nginx :80
                   │  (Vue 3)    │
                   └────┬────────┘
                        │ proxy_pass /api/
                   ┌────▼────────┐
                   │  Backend    │  Uvicorn :8000
                   │  (FastAPI)  │
                   └────┬────────┘
                        │ service name "db"
                   ┌────▼────────┐
                   │  Database   │  Postgres :5432
                   │  (Postgres) │
                   └─────────────┘
```

| Service | Container | Exposed Ports | Network |
|---------|-----------|---------------|---------|
| db | uah-dev-db | None | uah-infra |
| backend | uah-dev-backend | None | uah-infra |
| frontend | uah-dev-frontend | 80/443 (via VPN only) | Shares VPN container |
| vpn | uah-dev-vpn | 51820/udp | uah-infra |

**Access:** `http://dev.uahapp.com` (or `https://dev.uahapp.com` when TLS enabled) — requires VPN connection.

### VPN-only HTTPS for Dev

To enable HTTPS in dev without exposing your app publicly, place cert/key files on the server and keep DNS pointing to your VPN/private address.

1. Put cert files in `./volumes/certs/dev/` as:
     - `tls.crt`
     - `tls.key`
2. Set env vars in `.env`:
     - `DEV_TLS_ENABLED=true`
     - `DEV_TLS_CERT_PATH=/etc/nginx/certs/tls.crt`
     - `DEV_TLS_KEY_PATH=/etc/nginx/certs/tls.key`
3. Rebuild frontend container:
     - `docker compose up -d --build frontend`

If TLS is enabled but cert files are missing, frontend falls back to HTTP automatically.

---

## Local Development

The local path is now frontend-first and mock-first so you can render all modules without starting backend services.

### Fast path (frontend mock mode)

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

- `npm run dev` defaults to mock mode.
- API calls are handled by an in-browser mock API layer.
- This path is isolated from dev/beta/prod infrastructure.
- Non-local frontend builds default to backend mode.
- Mock mode still uses browser storage for its fake JWT; deployed stacks now use a backend-issued `HttpOnly` auth cookie instead.

### Optional local backend passthrough mode

```bash
# from repo root
docker compose -f docker-compose.local.yml --profile backend up -d db-local backend-local

# in a second terminal
cd frontend
npm run dev:backend
```

Notes:

- Local compose binds backend and db to localhost only (`127.0.0.1`).
- Backend mode refuses non-local API targets by default.
- To intentionally target a non-local API in backend mode, set `VITE_ALLOW_REMOTE_API=true`.

### Environment template

- Use `env-examples/local/.env.example` as the starting point for local root `.env` values.

For host-run backend workflows (`uvicorn` outside Docker), continue using the **[Backend Local Development Guide](./docs/backend/README.md)**.

---

## File Structure

```
/srv/uah/environments/dev/
├── .env                          # Environment variables (secrets, DB creds)
├── docker-compose.yml            # Service definitions
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # FastAPI entry point
│       ├── api/routes.py         # API route handlers
│       ├── core/config.py        # Centralized settings from env vars
│       ├── db/session.py         # SQLAlchemy engine + session factory
│       ├── db/base.py            # Declarative Base for models
│       └── models/__init__.py    # Import all models here
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf                # Nginx config (proxy + SPA fallback)
│   ├── package.json
│   └── src/
│       ├── App.vue               # Root component (backend status check)
│       └── main.js               # Vue app mount
├── volumes/postgres/             # Persistent DB data (DO NOT DELETE)
└── logs/
```

---

## Quick Start

```bash
# Start dev stack (default: no rebuild)
bash scripts/uah.sh dev start

# Rebuild only frontend and start stack
bash scripts/uah.sh dev start --build-frontend

# Restart beta stack with full rebuild
bash scripts/uah.sh beta restart --build-all
```

---

## Syncing Dev from GitHub

Use `scripts/uah.sh` as the canonical lifecycle entrypoint. Legacy-style sync wrappers are supported as pass-through aliases.

### Usage

```bash
# Dev sync (fast-forward only)
bash scripts/uah.sh dev sync

# Dev hard sync (discard local changes)
bash scripts/uah.sh dev sync hard

# Dev sync + full rebuild after sync
bash scripts/uah.sh dev sync --build-all

# Beta sync (default mode is safe) + optional rebuild
bash scripts/uah.sh beta sync --build-frontend
bash scripts/uah.sh beta sync safe --build-frontend
bash scripts/uah.sh beta sync hard --build-all
```

### What it does

1. Fetches latest refs from `origin`
2. Checks out `dev` and syncs branch state
3. Supports `safe` (`pull --ff-only`) and `hard` (`reset --hard origin/dev`) sync modes
4. If the environment backend is already running, automatically runs `alembic upgrade head` in the backend container and refreshes `backend`, `celery_worker`, and `celery_beat`
5. Optionally runs post-sync compose startup with rebuild flags when provided, then applies the same Alembic + runtime refresh flow
6. Runs environment feature validation after sync in warn-only mode so missing keys are surfaced early

If safe sync detects blockers (local file changes, local commits, or non-fast-forward state):

1. It prints the detected issues
2. In interactive shells, it prompts to abort or force hard sync
3. In non-interactive mode, safe sync exits with an error and does not modify the working tree

> **Note:** Default sync behavior is still git-only for stopped stacks. If the backend container is already running, sync now also performs a live Alembic reconcile and refreshes the schema-sensitive runtime services.

---

## Lifecycle Script Commands

`scripts/uah.sh` is the canonical command entrypoint for dev/beta lifecycle operations.

```bash
# Show full CLI help and flag reference
bash scripts/uah.sh --help
```

If you omit the environment argument, `scripts/uah.sh` auto-detects context from:

1. Current path segments like `/environments/dev`, `/environments/beta`, `/environments/prod`
2. Root `.env` values (`ENVIRONMENT`, `ENV`, `COMPOSE_PROJECT_NAME`)

If detection fails, pass `dev`, `beta`, or `prod` explicitly.

Wrapper scripts under `scripts/dev/lifecycle/` and `scripts/beta/lifecycle/` pass all arguments through to `scripts/uah.sh`, so rebuild flags work there too.
Wrappers remain stable aliases; `scripts/uah.sh` is the canonical interface.

### Command reference

| Scope | Command |
|-------|---------|
| Dev start | `bash scripts/uah.sh dev start` |
| Dev restart | `bash scripts/uah.sh dev restart` |
| Dev stop | `bash scripts/uah.sh dev stop` |
| Dev sync (safe/hard) | `bash scripts/uah.sh dev sync` / `bash scripts/uah.sh dev sync hard` |
| Beta start | `bash scripts/uah.sh beta start` |
| Beta restart | `bash scripts/uah.sh beta restart` |
| Beta stop | `bash scripts/uah.sh beta stop` |
| Beta sync (safe/hard) | `bash scripts/uah.sh beta sync safe` / `bash scripts/uah.sh beta sync hard` |
| Dev wrapper examples | `bash scripts/dev/lifecycle/dev-start.sh` / `bash scripts/dev/lifecycle/dev-restart.sh` / `bash scripts/dev/lifecycle/sync-dev.sh` |
| Beta wrapper examples | `bash scripts/beta/lifecycle/beta-start.sh` / `bash scripts/beta/lifecycle/beta-restart.sh` / `bash scripts/beta/lifecycle/sync-beta.sh` |

### Debug option interface

The interactive debug consoles still work as before:

- `bash scripts/uah.sh dev debug`
- `bash scripts/uah.sh beta debug`

You can now run targeted debug operations directly through `uah.sh`:

- `bash scripts/uah.sh <env> debug status`
- `bash scripts/uah.sh <env> debug connectivity <check>`
- `bash scripts/uah.sh <env> debug logs <service> [--tail N] [--follow] [--raw|--errors|--filtered]`
- `bash scripts/uah.sh <env> debug queue <action>`
- `bash scripts/uah.sh <env> debug database <action>`
- `bash scripts/uah.sh dev debug users <action>`
- `bash scripts/uah.sh <env> debug network <action>`

Run `bash scripts/uah.sh <env> debug help` for the full matrix.

### Rebuild flags

Use these flags with `start`, `restart`, or `sync`:

- `--no-build` (default behavior)
- `--build` or `--build-all`
- `--build-frontend`
- `--build-backend`
- `--build-db`
- `--build-redis`
- `--build-cloudflared`
- `--build-service <name>` or `--build-service=<name>`

When service-specific build flags are used, scripts rebuild selected services first and then bring the full stack up.

### Sync blocker prompts

When safe sync is blocked in an interactive shell, the script shows detected issues and prompts for:

- `abort` to stop safely with no git reset
- `force` to run hard sync (`reset --hard origin/dev`) after confirmation
- `status` to inspect full git status
- `diff` to inspect diff summary

### Shell script permissions

Shell scripts in this repository are tracked as executable by default.

- `.sh` files are normalized with `.gitattributes` to keep LF line endings.
- You should not need recurring `chmod +x` sweeps after pulling the normalization commit.
- If sync still reports blockers, use the `status` and `diff` prompt options to confirm whether blockers are real content edits.

### Examples

```bash
# Default start (no rebuild)
bash scripts/uah.sh dev start

# Rebuild backend only, then start full stack
bash scripts/uah.sh dev start --build-backend

# Rebuild frontend + backend on restart
bash scripts/uah.sh dev restart --build-frontend --build-backend

# Full rebuild on beta restart
bash scripts/uah.sh beta restart --build-all

# Beta wrapper usage (same options)
bash scripts/beta/lifecycle/beta-restart.sh --build-all
```

### Startup preflight checks

On `start`, `restart`, and `sync` with rebuild flags, scripts validate:

1. Docker CLI and Docker Compose plugin are available
2. Required external networks exist (`uah-infra`, and `uah-beta-infra` for beta)
3. Required infrastructure container `uah-dev-vpn` is running
4. Redis host ports are available before startup (`REDIS_HOST_PORT` for dev, `BETA_REDIS_HOST_PORT` for beta)
5. Environment feature requirements in root `.env` via `scripts/lib/env-feature-check.sh`

After containers are brought up for `dev` or `beta`, lifecycle scripts now automatically run `alembic upgrade head` inside the backend container and restart `backend`, `celery_worker`, and `celery_beat` so schema-dependent services stay aligned.

### Concurrent Dev + Beta OCR Routing

When both environments run on the same host, route ownership is now managed explicitly:

- `dev start` applies dev-owned WireGuard route and VPN forwarding rules for desktop Ollama.
- `dev stop` removes only dev-owned rules.
- `beta start` applies beta-owned route/rules.
- `beta stop` removes only beta-owned rules and preserves the shared host route when a sibling backend is still running.

Route scripts:

- `scripts/dev/network/apply_desktop_ollama_temp_route.sh`
- `scripts/dev/network/rollback_desktop_ollama_temp_route.sh`
- `scripts/beta/network/apply_desktop_ollama_temp_route.sh`
- `scripts/beta/network/rollback_desktop_ollama_temp_route.sh`

### Debug Console Scope

Dev debug console is now near-parity with beta for operational checks:

- Ollama reachability status in the header.
- Queue management menu in dev debug.
- Networking diagnostics in dev debug.
- Frontend/Nginx logs sourced from compose logs (not in-container log files).

Entry points:

- `bash scripts/uah.sh dev debug`
- `bash scripts/uah.sh beta debug`

### Queue Scope Interpretation

Queue execution remains isolated by environment (separate Redis containers and queue namespaces).

- Dev queue position is scoped to dev.
- Beta queue position is scoped to beta.
- UI now labels queue scope/environment to avoid cross-environment ambiguity when both show position `1`.

---

## Direct Docker Compose Commands

### Rebuild a single service (does NOT affect others)

```bash
# Backend only — use after changing Python code or requirements.txt
docker compose up -d --build backend

# Frontend only — use after changing Vue code, nginx.conf, or package.json
docker compose up -d --build frontend

# Database — rarely needed, only if changing Postgres version
docker compose up -d --build db
```

### Restart without rebuilding

```bash
# Restart one service (keeps existing image)
docker compose restart backend
docker compose restart frontend
docker compose restart db
```

### Stop a single service

```bash
# Stop one service without removing it
docker compose stop backend

# Start it back
docker compose start backend
```

### Stop everything (preserves data)

```bash
docker compose down
```

> **Warning:** `docker compose down -v` will **delete the Postgres volume**. Never use `-v` unless you intend to wipe the database.

---

## Checking Status

```bash
# See all running containers and their health
docker compose ps

# View last 50 lines of logs for a service
docker compose logs backend --tail 50
docker compose logs frontend --tail 50
docker compose logs db --tail 50

# Follow logs in real-time (Ctrl+C to stop)
docker compose logs -f backend
```

---

## Testing Endpoints

The backend container uses `python:3.12-slim` (no curl). Use these methods:

```bash
# Test backend health
docker exec uah-dev-backend python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"

# Test API status
docker exec uah-dev-backend python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/status').read().decode())"

# Test frontend + proxy (curl is available in the nginx container)
docker exec uah-dev-frontend curl -s http://localhost/
docker exec uah-dev-frontend curl -s http://localhost/api/status
docker exec uah-dev-frontend curl -s http://localhost/docs | head -20
```

---

## Accessing Dev Tools (VPN Required)

| URL | Description |
|-----|-------------|
| `https://dev.uahapp.com` | Frontend app (preferred, when TLS enabled) |
| `http://dev.uahapp.com` | Frontend app (fallback when TLS disabled) |
| `http://dev.uahapp.com/status` | System status page (full diagnostics) |
| `http://dev.uahapp.com/api/status` | API status check (JSON) |
| `http://dev.uahapp.com/api/diagnostics` | Full diagnostics payload (JSON) |
| `http://dev.uahapp.com/docs` | Swagger UI (auto-generated) |
| `http://dev.uahapp.com/redoc` | ReDoc (alternative API docs) |
| `http://dev.uahapp.com/openapi.json` | Raw OpenAPI spec |

---

## Database Access

```bash
# Open a psql shell inside the DB container
docker exec -it uah-dev-db psql -U uah -d uah_dev

# Run a quick query
docker exec uah-dev-db psql -U uah -d uah_dev -c "\dt"

# Check if DB is accepting connections
docker exec uah-dev-db pg_isready -U uah -d uah_dev
```

---

## Common Workflows

### I changed backend Python code

```bash
# Uvicorn has --reload enabled and the backend/ directory is volume-mounted.
# Changes to .py files are picked up automatically — no rebuild needed.
# Just check the logs:
docker compose logs -f backend
```

### I changed requirements.txt

```bash
# Must rebuild to install new packages
docker compose up -d --build backend
```

### I changed frontend Vue/JS code

```bash
# Frontend must be rebuilt (Vite builds static assets into the Nginx image)
docker compose up -d --build frontend
```

### I changed nginx.conf

```bash
# Must rebuild frontend since nginx.conf is baked into the image
docker compose up -d --build frontend
```

### I need to wipe the database and start fresh

```bash
docker compose down
sudo rm -rf ./volumes/postgres/*
docker compose up -d --build
```

---

## What NOT to Touch

| Item | Reason |
|------|--------|
| `/srv/uah/infrastructure/` | VPN and tunnel configs — managed separately |
| `uah-dev-vpn` container | Frontend depends on its network namespace |
| `uah-infra` Docker network | Shared across infrastructure and app services |
| Cloudflare tunnel config | Managed outside this repo |
| Port `51820/udp` | WireGuard VPN — do not change |

---

## Environment Variables

All secrets live in `.env` at the project root. Docker Compose reads it automatically.

Canonical templates live in:
- `env-examples/dev/.env.example`
- `env-examples/beta/.env.example`
- `env-examples/prod/.env.example`

The application does **not** read files directly from `env-examples/` at runtime.
Copy the appropriate template values into a real root `.env` before running services.

| Variable | Used By | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | db, backend | Database username |
| `POSTGRES_PASSWORD` | db, backend | Database password |
| `POSTGRES_DB` | db, backend | Database name |
| `POSTGRES_PORT` | backend | Database port (default: 5432) |
| `COMPOSE_PROJECT_NAME` | docker compose | Project namespace |
| `ENV` | reference | Current environment |
| `AUTH_NAMESPACE` | backend, frontend build | Environment auth namespace (`dev`, `beta`, `prod`) |
| `AUTH_COOKIE_NAME` | backend | `HttpOnly` browser auth cookie name for API sessions |
| `SESSION_COOKIE_NAME` | backend | Environment-scoped session cookie name (must not be `session`) |
| `SESSION_COOKIE_SAMESITE` | backend | Session cookie SameSite policy (`lax`, `strict`, `none`) |
| `SESSION_COOKIE_PATH` | backend | Session cookie path (usually `/`) |
| `SESSION_COOKIE_HTTPS_ONLY` | backend | Use secure-only session cookie flag |
| `GMAIL_TOKEN_ENCRYPTION_KEY` | backend | Dedicated encryption key for persisted Gmail refresh tokens |
| `VITE_AUTH_NAMESPACE` | frontend build | Frontend auth storage namespace key suffix |
| `VITE_LOCAL_MODE` | frontend build/runtime | Frontend API mode (`backend` for deployed stacks, `mock` for local-only UI runs) |
| `DEV_DOMAIN` | reference | Domain for dev access |

Compose now requires environment-scoped auth naming for backend startup.
Use environment-scoped values such as:

- Dev: `AUTH_NAMESPACE=dev`, `AUTH_COOKIE_NAME=uah_auth_dev`, `SESSION_COOKIE_NAME=uah_session_dev`
- Beta: `AUTH_NAMESPACE=beta`, `AUTH_COOKIE_NAME=uah_auth_beta`, `SESSION_COOKIE_NAME=uah_session_beta`
- Prod: `AUTH_NAMESPACE=prod`, `AUTH_COOKIE_NAME=uah_auth_prod`, `SESSION_COOKIE_NAME=uah_session_prod`

For remote environments, keep `SESSION_COOKIE_HTTPS_ONLY=true` and set a dedicated `GMAIL_TOKEN_ENCRYPTION_KEY` if Gmail integration is enabled.

> **Never commit `.env` to git.** It contains credentials.

## License

UAH is licensed under AGPL-3.0 with Commons Clause.

- ✅ Free for personal, educational, and non-commercial use
- ✅ Modifications must be open sourced under the same license  
- ✅ Self-hosting for non-commercial purposes is permitted
- ❌ Commercial use, resale, or monetization requires explicit written 
     permission from the project maintainers

Contact: admincontact@uahapp.com for commercial licensing inquiries.
