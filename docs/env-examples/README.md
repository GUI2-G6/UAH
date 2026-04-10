# Environment Example Templates

This folder contains sanitized, committed templates for each deployment stage.

## Runtime Rule (Important)

The application expects a real `.env` file in the repository root at runtime.

- Runtime location: `./.env`
- Template location only: `env-examples/*/.env.example`

Do not run the app directly from files inside this folder.
Copy the relevant template values into root `.env` before starting services.

## Folder Intent

- `env-examples/dev/.env.example`
  - Canonical development template.
  - Mirrors current dev variables and defaults.
  - Uses fake placeholders for secret values.

- `env-examples/beta/.env.example`
  - Canonical beta/staging template.
  - Mirrors beta values (domain, compose name, cloudflare token var).
  - Uses fake placeholders for secret values.

- `env-examples/prod/.env.example`
  - Placeholder production stub.
  - Tracks required production fields without storing real credentials.

- `env-examples/local/.env.example`
  - Frontend-first local template with secure defaults.
  - Supports mock-only frontend mode and optional local backend profile.
  - Keeps localhost-only host bindings and admin bootstrap disabled by default.

## Security Notes

- Never commit real `.env` files.
- Never paste real credentials into any `*.env.example` file.
- Placeholders are intentionally non-secret strings so scanners do not treat them as leaked keys.

## Sync Notes

- CI validates that `backend/app/core/config.py` env usage is represented in:
  - `env-examples/dev/.env.example`
  - `env-examples/beta/.env.example`
- Keep variables present even when a feature is disabled in that environment.
  - Example: beta keeps `DEV_AUTH_TEST_*` keys documented with empty values while `DEV_AUTH_TEST_ACCOUNT_ENABLED=false`.
