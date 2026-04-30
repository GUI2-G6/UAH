# Environment Example Files

This folder contains sanitized example env files for each environment shape used by the repository.

## Runtime Rule

The application does not run directly from files inside this directory.

- Runtime file location: repo-root `.env`
- Template location: `env-examples/*/.env.example`

Copy the relevant example into a real root `.env`, then replace placeholder values with environment-specific secrets and URLs.

## Available Templates

| Template | Purpose |
| --- | --- |
| `env-examples/dev/.env.example` | Team-oriented dev stack values |
| `env-examples/beta/.env.example` | Beta deployment values, namespacing, and tunnel-related settings |
| `env-examples/local/.env.example` | Frontend-first local development with optional localhost backend |
| `env-examples/prod/.env.example` | Production placeholder/stub for future production hardening |
| `frontend/.env.local.example` | Vite-only variables for the main SPA (not loaded by root `.env` unless you export them) |
| `landing/.env.local.example` | Vite-only variables for the marketing landing app (`VITE_LOCAL_BACKEND_ORIGIN`, `VITE_UAH_LOGIN_URL`) |

## Repository Policy

- Never commit a real `.env`.
- Never replace placeholders in `*.env.example` with live credentials.
- Keep templates aligned with `backend/app/core/config.py`, compose files, and lifecycle/audit expectations.
- When a new environment variable is added, update the relevant example files in the same change.

## Staying current (automation)

- **`backend/app/core/config.py` ↔ templates:** PRs run [`.github/scripts/check_env_sync.py`](../../.github/scripts/check_env_sync.py). Run the same check locally before opening a PR:
  - `npm run check:env` from the repo root, or
  - `python .github/scripts/check_env_sync.py --all-templates`

- **Compose / lifecycle:** Changing defaults in `docker-compose*.yml` or tunnel images should usually be mirrored in the matching `env-examples/*/.env.example` (and compose interpolation checked with a merged `docker compose config` using a populated `--env-file`).

- **`VITE_*` (frontend / landing):** Not covered by `check_env_sync.py`; grep for `import.meta.env` / `process.env` and update `.env.local.example` files in the same change.

## Template Design Notes

- Placeholders are intentionally fake values so secret scanners do not treat them as leaked credentials.
- Beta and local templates keep some disabled-by-default keys present on purpose so audits and setup flows can verify them explicitly.
- A documented key may be required only when a feature is enabled. That still belongs in the example file.

## Related Docs

- Repo entrypoint: [../../README.md](../../README.md)
- Server checklist: [../SERVER_ENV_CHECKLIST.md](../SERVER_ENV_CHECKLIST.md)
- Backend guide: [../backend/README.md](../backend/README.md)
