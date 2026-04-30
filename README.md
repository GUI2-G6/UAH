# UAH

Unified Application Hub is a full-stack job-search and application-assistance project with three main surfaces:

- a FastAPI backend
- a Vue 3 frontend
- a browser extension for in-tab profile and autofill workflows

This README is the repo entrypoint. For subsystem-specific details, use the docs map in [docs/README.md](docs/README.md).

## Source Of Truth

| Need | Doc |
| --- | --- |
| Documentation map | [docs/README.md](docs/README.md) |
| Architecture overview | [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) |
| Backend local development | [docs/backend/README.md](docs/backend/README.md) |
| Frontend local development | [docs/frontend/README.md](docs/frontend/README.md) |
| Browser extension build/runtime | [uah-browser-extension/README.md](uah-browser-extension/README.md) |
| Environment template rules | [docs/env-examples/README.md](docs/env-examples/README.md) |
| Server env checklist | [docs/SERVER_ENV_CHECKLIST.md](docs/SERVER_ENV_CHECKLIST.md) |
| Contribution policy | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Branch and PR workflow | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
| Security policy | [SECURITY.md](SECURITY.md) |
| Historical snapshots | [docs/archive/README.md](docs/archive/README.md) |

## Current Stack

| Layer | Primary tech | Notes |
| --- | --- | --- |
| Backend | FastAPI, SQLAlchemy, Alembic, Celery, Redis | Auth, jobs, resumes, profiles, integrations, diagnostics |
| Frontend | Vue 3, Vue Router, Vite | Mock-first local dev plus backend passthrough mode |
| Extension | Vue 3, Vite, MV3 service worker | Reuses backend auth and injects manual autofill tools |
| Infra | Docker Compose, Nginx, Postgres, Cloudflare tunnel for beta | Dev and beta are separate environment shapes |

## Quick Start

### Frontend-only local UI work

```bash
cd frontend
npm install
npm run dev
```

This is the fastest path for UI work. It uses the in-browser mock API layer and does not require backend services.

### One-command local stack (backend + frontend mock + landing)

From repo root:

```bash
npm run dev:local
```

What this does:

- starts `db-local` and `backend-local` using `docker-compose.local.yml`
- starts `frontend` in mock mode on `http://localhost:5173`
- starts `landing` on `http://localhost:5174` (avoids Vite port collision)

Standard local dev credentials:

- email: `local.admin@uah.local`
- password: `LocalAdmin123!`

Useful helpers:

```bash
npm run dev:local:logs
npm run dev:local:down
```

### Local backend + frontend

```bash
docker compose -f docker-compose.local.yml --profile backend up -d db-local backend-local
cd frontend
npm install
npm run dev:backend
```

Use this path when the UI needs live backend behavior on localhost. The frontend dev server proxies `/api`, `/docs`, and `/openapi.json` to the backend origin.

### Browser extension local harness

Use the extension README for the full flow, but the usual local helper is:

```powershell
pwsh -File .\scripts\local\lifecycle\local-extension-test.ps1
```

That helper expects a real repo-root `.env`, `frontend/.env.local`, and a localhost-focused extension env file.

## Runtime Environments

### Local

- `docker-compose.local.yml` provides localhost-only DB/backend support.
- `frontend` runs through Vite outside Docker.
- `uah-browser-extension` can target localhost HTTPS for real auth/cookie flows.

### Dev

- `docker-compose.yml` is the primary dev stack.
- Nginx serves the frontend and proxies `/api` to the backend.
- Dev is the most permissive environment for diagnostics and generated API docs.

### Beta

- `docker-compose.beta.yml` is an override layered onto `docker-compose.yml`.
- Beta is isolated by compose project name, cookie namespace, Redis namespace, and DB.
- The current beta shape uses a `cloudflared` tunnel container rather than exposing the frontend directly on a public host port.

## Canonical Commands

### Frontend

```bash
cd frontend
npm run dev
npm run dev:backend
npm run build
```

### Browser extension

```bash
cd uah-browser-extension
npm install
npm run build
npm test
```

### Backend host-run workflow

Use [docs/backend/README.md](docs/backend/README.md) for the full setup, including venv activation and `.env` loading. The typical local run command from `backend/` is:

```bash
alembic upgrade head
python -m uvicorn app.main:app --reload
```

### Server lifecycle helper

`scripts/uah.sh` is the canonical lifecycle entrypoint for repo-managed server environments.

```bash
bash scripts/uah.sh --help
bash scripts/uah.sh dev start
bash scripts/uah.sh dev sync
bash scripts/uah.sh beta restart --build-all
```

Run `bash scripts/uah.sh <dev|beta>` with no action to open the **Control Center** (grouped lifecycle, deploy, governance, observability, data access, and advanced ops). Non-interactive `bash scripts/uah.sh <env> debug …` subcommands are unchanged. The legacy `tools` / `tooling` / `ui` action names are deprecated in favor of the Control Center; they print a short hint and exit non-zero.

Wrapper scripts under `scripts/dev/lifecycle/` and `scripts/beta/lifecycle/` remain supported aliases, but they pass through to `scripts/uah.sh`.

`start`, `restart`, and post-`sync` rebuild paths in `scripts/uah.sh` run a live Alembic reconcile (`alembic upgrade head`) against the running backend container:

- `dev`: migration/reconcile failures are logged as warnings and lifecycle flow continues.
- `beta`: migration/reconcile failures are treated as fatal and the lifecycle command exits non-zero.

## Repository Layout

```text
backend/                 FastAPI app, models, services, migrations, tests
frontend/                Vue SPA, local mock API, shared UI primitives
uah-browser-extension/   MV3 extension, adapters, autofill runtime, tests
docs/                    Active guides (architecture, extension, landing notes) plus archive
scripts/                 Lifecycle, sync, audit, debug, and env helpers
shared/                  Shared theme assets
env-examples/            Sanitized example env files for each environment
```

## Documentation Rules

- Active docs should describe current behavior, not aspirational behavior.
- If a behavior is temporary, say that explicitly.
- Dated audits and migration notes belong in `docs/archive/`.
- When changing a user-visible or operator-visible behavior, update the corresponding source-of-truth doc in the same change.

## License

UAH is licensed under AGPL-3.0 with Commons Clause.
