# Admin Bypass (Alpha Only)

This repo includes an **alpha-only** login override that lets an operator access the app without creating a normal account.

## How it works

- Frontend login page includes an **"Alpha override"** passphrase input.
- If the passphrase is valid, the frontend calls:
  - `POST /api/auth/bypass`
- The backend validates the passphrase (server-side) and returns a normal JWT `TokenResponse`.

## Required environment variables (backend)

Set these in the **dev environment .env** (the file used by `docker compose`):

- `ADMIN_BYPASS_PASSPHRASE` — passphrase required to bypass login
- `ADMIN_BOOTSTRAP_ENABLED` — set to `true` to auto-create/ensure the admin user on backend startup
- `ADMIN_BOOTSTRAP_USERNAME` — username for the admin user
- `ADMIN_BOOTSTRAP_PASSWORD` — password for the admin user (hashed and stored in DB)
- `ADMIN_BOOTSTRAP_FIRST_NAME`
- `ADMIN_BOOTSTRAP_LAST_NAME`

Admin email is **fixed in code** to:

- `admincontact@uahapp.com`

## Notes / security

- This is intended for **alpha/dev only**. Treat the bypass passphrase as a secret.
- Do **not** commit real secrets into git.
- Prefer a passphrase without spaces; if you must use special characters, ensure your `.env` parser preserves them.
- When disabling the bypass, unset `ADMIN_BYPASS_PASSPHRASE` (or remove it) and set `ADMIN_BOOTSTRAP_ENABLED=false`.

## API

### `POST /api/auth/bypass`

Request body:

```json
{ "passphrase": "<your-passphrase>" }
```

Responses:
- `200` → `{ access_token, token_type, user }`
- `401` → invalid passphrase
- `500` → required env vars not configured
