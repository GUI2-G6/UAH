# Frontend Development Guide

This is the current source of truth for the Vue frontend.

For repo-wide context, use:

- [../../README.md](../../README.md)
- [../ARCHITECTURE.md](../ARCHITECTURE.md)

## What This App Is

The frontend is a Vue 3 SPA that talks to the FastAPI backend through same-origin `/api` routes in deployed environments. In local development it can run in one of two modes:

- mock-first mode for UI work with no backend dependency
- backend passthrough mode for real API behavior on localhost

## Scripts

Run these from `frontend/`:

```bash
npm install
npm run dev
npm run dev:backend
npm run build
npm run check:cards
```

### What each script does

| Script | Purpose |
| --- | --- |
| `npm run dev` | Mock-first local development. Uses the in-browser mock API layer. |
| `npm run dev:backend` | Proxies `/api`, `/docs`, and `/openapi.json` to the configured backend origin. |
| `npm run build` | Production build of the SPA bundle. |
| `npm run check:cards` | Contract check for the shared card component and its consumers. |

## Auth And Runtime Behavior

### Backend mode

- The app expects backend-issued auth cookies and session-backed API behavior.
- `syncCurrentUser()` is the main frontend-side identity refresh path.
- `/api/status` is the lightweight public connectivity check.
- `/api/diagnostics` is admin-gated, so the status page must handle limited-access states gracefully.

### Mock mode

- The mock API layer emulates auth and common data flows entirely in-browser.
- Mock mode keeps local storage namespaced by `VITE_AUTH_NAMESPACE`.
- Mock mode is for renderability and workflow development, not for proving backend correctness.

## Current Route Surface

### Active, non-placeholder views

- `Home`
- `Job-Board`
- `Resumes`
- `Applicant-Information`
- `Settings`
- `Login`
- `Register`
- `Forgot-Password`
- `Reset-Password`
- `Status`
- `Privacy-Policy` (also reachable via the legacy `/our-commitment` redirect)
- `Contributors`
- `Dev` (debug-tools gated)

### Placeholder or thin-shell views

These routes exist, but they are not full product surfaces yet:

- `Analytics`
- `Timeline`
- `Application`

`Notifications` has a routed surface, but it is currently a simple static shell rather than a fully wired reminders system.

Document those views as partial, not complete.

## Local Development Modes

### Mock-first mode

```bash
npm run dev
```

Default local mock credentials:

- email: `local.admin@uah.local`
- password: `LocalAdmin123!`

Mock mode now auto-logins by default on localhost (set `VITE_LOCAL_AUTO_LOGIN=false` to opt out).

Use this for:

- layout work
- component iteration
- route flow scaffolding
- work that should not depend on backend availability

### Backend passthrough mode

```bash
npm run dev:backend
```

Important behavior:

- defaults to `http://localhost:8000` unless overridden
- refuses non-loopback backend targets unless `VITE_ALLOW_REMOTE_API=true`
- can optionally serve over HTTPS when the local HTTPS env vars are configured

### One command for backend + frontend + landing

From repo root:

```bash
npm run dev:local
```

This starts:

- local backend profile (`db-local` + `backend-local`)
- frontend mock dev server (`5173`)
- landing dev server (`5174`)

## Shared Card Contract

`frontend/src/components/Card.vue` is a shared UI primitive, not a page-specific card.

Public variants:

- `default`
- `job`
- `minimal`

Caller-owned tuning should happen through documented CSS variables rather than global overrides:

- `--ui-card-bg`
- `--ui-card-border`
- `--ui-card-shadow`
- `--ui-card-padding`
- `--ui-card-header-bg`
- `--ui-card-header-padding`

Run `npm run check:cards` if a change touches the card primitive or many card consumers.

## Job Board Notes

- Filter metadata is backend-owned through `GET /api/jobs/filter-metadata`.
- Keyword search and `posted_after` filtering are sent server-side so totals and pagination stay consistent.
- Location canonicalization and cap/truncation diagnostics are surfaced in the UI before search.
- Result totals from provider-backed search are conservative estimates; local DB-backed search can return exact totals.

## Docs And Debug Expectations

- In local/dev-style environments, `/docs` and `/openapi.json` may be available through backend passthrough mode.
- In beta-like environments, generated docs are intentionally disabled by the backend.
- The `Dev` route should be treated as a gated troubleshooting surface, not a public product page.

## Related Docs

- Backend guide: [../backend/README.md](../backend/README.md)
- Extension guide: [../../uah-browser-extension/README.md](../../uah-browser-extension/README.md)
- Architecture: [../ARCHITECTURE.md](../ARCHITECTURE.md)
