# UAH Architecture

This document explains how the current codebase is split, how requests move through it, and where to look when a feature crosses multiple layers.

For a paste-friendly ASCII version of the same architecture, use [ARCHITECTURE_TEXT_DIAGRAM.md](ARCHITECTURE_TEXT_DIAGRAM.md).

For setup instructions, use the linked source-of-truth guides instead:

- Repo entrypoint: [../../README.md](../../README.md)
- Backend local development: [../backend/README.md](../backend/README.md)
- Frontend development: [../frontend/README.md](../frontend/README.md)
- Browser extension: [../../uah-browser-extension/README.md](../../uah-browser-extension/README.md)

## Top-Level Shape

| Area | Purpose |
| --- | --- |
| `backend/` | FastAPI app, SQLAlchemy models, Alembic migrations, Celery tasks, provider ingestion, resume parsing, and auth/account APIs. |
| `frontend/` | Vue 3 SPA for the main UAH product surface. Supports mock-first local development and backend passthrough mode. |
| `uah-browser-extension/` | MV3 browser extension that reuses backend auth and exposes profile/resume/autofill tools inside job board tabs. |
| `shared/` | Cross-surface styling assets such as the shared theme CSS. |
| `scripts/` | Lifecycle, audit, sync, debug, and environment-specific operational helpers. |
| `docs/` | Current source-of-truth docs plus an archive for dated snapshots. |

## Request Flow

### Main web app

1. The Vue frontend serves the SPA shell.
2. Browser requests go through Nginx to `/api/*`.
3. FastAPI handles auth, account, job search, resume, profile, integration, and diagnostics endpoints.
4. SQLAlchemy persists application data in Postgres.
5. Optional queue-backed parsing and job sync flows use Redis plus Celery worker/beat processes.

### Browser extension

1. The popup UI talks to the background service worker through runtime messages only.
2. The background worker owns auth, API fetches, cache hydration, tab opening, and content-script injection.
3. The extension reuses the backend's auth flows and environment-scoped auth cookie names.
4. Manual autofill injects runtime code into the active tab only when the user explicitly scans or fills a page.

## Backend Boundaries

The backend is split by responsibility rather than by one giant route file.

| Layer | Location | Responsibility |
| --- | --- | --- |
| Application entrypoint | `backend/app/main.py` | FastAPI setup, startup/shutdown work, docs gating, router registration, and session middleware. |
| Route modules | `backend/app/api/` | Thin HTTP layer for auth, account, resume, jobs, applicant profiles, integrations, Gmail, and apply sessions. |
| Services | `backend/app/services/` | Business logic such as resume parsing, job search shaping, provider requests, canonicalization, and queue orchestration. |
| Data models | `backend/app/models/` | SQLAlchemy tables for users, resumes, jobs, applicant profiles, parse jobs, and related state. |
| Schemas | `backend/app/schemas/` | Pydantic request/response shapes and compatibility fields. |
| Background work | `backend/app/tasks/`, `backend/app/worker.py` | Celery tasks for job sync and maintenance. |
| Migrations | `backend/alembic/` | Schema changes for durable database evolution. |

### Current backend behavior that matters for docs

- Swagger/OpenAPI routes are enabled only when `ENVIRONMENT` is `development`, `dev`, or `local`.
- `/api/status` is the lightweight public connectivity probe.
- `/api/diagnostics` is admin-gated.
- The identity model is email-first, but `username` still exists as a compatibility mirror in parts of the schema and DB.
- Saved jobs routes are authenticated and derive ownership from the current session, not from caller-supplied user IDs.

## Frontend Boundaries

The frontend is a Vue 3 SPA with two local-development modes.

| Mode | Entry | Behavior |
| --- | --- | --- |
| Mock-first | `npm run dev` | Uses the in-browser mock API layer and local storage state so the UI can render without backend services. |
| Backend passthrough | `npm run dev:backend` | Proxies `/api`, `/docs`, and `/openapi.json` to a local backend origin. |

### Current frontend surface

- Auth/account, resume/profile management, job board, settings, status, and contributor/commitment pages are active.
- Some routes still exist as placeholders or partial shells, especially `Analytics`, `Timeline`, and `Application`.
- The `Dev` page is gated by the debug-tools helper instead of being globally public.
- Auth is cookie-first in deployed/backend mode, while mock mode still persists a local token for isolated UI development.

## Browser Extension Boundaries

The extension intentionally keeps responsibility split across three layers:

| Layer | Location | Responsibility |
| --- | --- | --- |
| Popup app | `uah-browser-extension/src/App.vue` and related UI code | User-facing views, actions, and pinned-surface rendering. |
| Background worker | `uah-browser-extension/src/background/index.js` | Auth, API fetches, storage, caching, tab management, and script injection. |
| Injected runtimes | `uah-browser-extension/src/autofill/`, `src/pinned-panel/` | Page scanning/filling and the floating pinned panel injected into supported tabs. |

### Adapter system

- Base ATS adapters cover platform-wide conventions such as Workday, Greenhouse, Lever, and iCIMS.
- Company overrides layer on top of base adapters when one employer diverges from the platform defaults.
- Resolution always tries company overrides before generic ATS matches.

## Deployment Shapes

### Local

- `docker-compose.local.yml` is for localhost-only DB/backend support.
- Frontend local development stays outside Docker via Vite (see root README for `npm run dev:local` port layout).
- The extension local harness can target HTTPS on the dev server origin; see [../../uah-browser-extension/README.md](../../uah-browser-extension/README.md).

### Dev

- `docker-compose.yml` defines the core dev stack.
- Nginx fronts the SPA and `/api` proxy.
- Dev is team-oriented and can keep docs routes enabled.

### Beta

- `docker-compose.beta.yml` is an override layered on top of the main compose file.
- Beta currently uses a `cloudflared` tunnel container rather than exposing the frontend directly on a public host port.
- Beta should be documented as its own environment with isolated cookie names, Redis namespace, compose project name, and DB.

## Where To Document Changes

Use this table when a change crosses multiple parts of the repo:

| Change type | Docs to update |
| --- | --- |
| New backend env var or behavior change | [../backend/README.md](../backend/README.md), [../SERVER_ENV_CHECKLIST.md](../SERVER_ENV_CHECKLIST.md), and the relevant `env-examples/*/.env.example` file |
| Frontend route, auth, or local-dev behavior change | [../frontend/README.md](../frontend/README.md) and sometimes [../../README.md](../../README.md) |
| Extension build/runtime/autofill change | [../../uah-browser-extension/README.md](../../uah-browser-extension/README.md) and adapter docs if relevant |
| Deployment/lifecycle change | [../../README.md](../../README.md), [../WORKFLOW.md](../WORKFLOW.md) if team process changed, and beta docs if deployment-specific |
| Migration plan or one-time incident analysis | [../archive/README.md](../archive/README.md), not the active docs set |
