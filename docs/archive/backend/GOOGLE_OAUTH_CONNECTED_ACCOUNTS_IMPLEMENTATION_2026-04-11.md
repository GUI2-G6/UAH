# Historical Snapshot: Google OAuth + Connected Accounts Implementation (2026-04-11)

This document is an archival implementation note tied to a specific change window.

Use these active docs for current behavior:

- [../../backend/README.md](../../backend/README.md)
- [../../frontend/README.md](../../frontend/README.md)
- [../../../uah-browser-extension/README.md](../../../uah-browser-extension/README.md)

# Google OAuth + Connected Accounts Implementation (2026-04-11)

## Scope Implemented
- Added Google OAuth browser flow for:
  - Login page
  - Register page
  - Settings page account linking/unlinking
- Added a reusable "Connected Accounts" section in Settings to support additional providers over time.
- Kept current credential-based accounts fully supported and backward-compatible.
- Explicitly did **not** implement Gmail inbox integration in this change.

## Backend Changes

### Updated Endpoints
- `GET /api/auth/google`
  - Starts OAuth for unauthenticated login/register flow.
  - Supports optional query params:
    - `intent=login|register`
    - `next=/some/path`
  - Stores OAuth state + post-login target in server session.

- `GET /api/auth/google/callback`
  - Now completes OAuth and **redirects to frontend** instead of returning raw JSON.
  - Modes:
    - `login`: creates/links user and redirects to `/oauth-callback#access_token=...`.
    - `connect`: links Google to current account and redirects back to `/settings`.

### New Endpoints
- `POST /api/auth/google/connect/start`
  - Auth required.
  - Generates a Google authorization URL for linking a Google account in Settings.

- `GET /api/auth/connected-accounts`
  - Auth required.
  - Returns provider list/status for Settings (currently `google`, plus `linkedin` placeholder for future).

- `DELETE /api/auth/google/disconnect`
  - Auth required.
  - Unlinks Google from the current user.
  - Safety guard: blocks disconnect when Google is the user's only sign-in method (no password set).

### Service Update
- `backend/app/google/service.py`
  - Improved Google user linking/creation logic:
    - Prefer match by `google_id`, fallback to `email` for existing account linking.
    - Generate unique username for newly created OAuth accounts.
    - Update avatar/email verification cleanly without breaking existing users.

## Frontend Changes

### Login + Register
- Added "Continue with Google" CTA on:
  - `frontend/src/views/Login.vue`
  - `frontend/src/views/Register.vue`
- Added OAuth error surface from query params.
- Shared button styles added in:
  - `frontend/src/views/css/Login.css`

### OAuth Callback Page
- Added new view:
  - `frontend/src/views/OAuth-Callback.vue`
- Behavior:
  - Parses `access_token` from URL fragment.
  - Stores token, fetches `/api/auth/me`, stores user, routes to `next` or `/home`.
  - Handles/prints OAuth errors safely.

### Router
- Updated `frontend/src/router/index.js`:
  - Added `/oauth-callback` to public routes so callback can complete before auth guard redirect.

### Settings: Connected Accounts
- Updated `frontend/src/views/Settings.vue`:
  - Added a dedicated "Connected Accounts" card.
  - Loads provider status from `/api/auth/connected-accounts`.
  - Connect flow:
    - `POST /api/auth/google/connect/start`
    - browser redirect to Google
  - Disconnect flow:
    - `DELETE /api/auth/google/disconnect`
  - Handles callback success/error query params and displays toasts.
- Styling added in:
  - `frontend/src/views/css/Settings.css`

## Compatibility + Safety Notes
- Existing password accounts continue to work unchanged.
- Existing accounts are auto-linkable to Google when emails match.
- OAuth-only accounts are protected from accidental lockout:
  - Google disconnect is blocked unless a password sign-in method exists.
- Settings UI is provider-oriented and extensible for future connected accounts.

## Validation Run
- Backend syntax check:
  - `python -m compileall backend/app` ✅
- Frontend production build:
  - `npm --prefix frontend run build` ✅
