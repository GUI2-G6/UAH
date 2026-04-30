# Historical Snapshot: Email-First Identity + Autofill Scope Reset (2026-04-11)

This document is an archival implementation note. It explains a specific migration window and should not be treated as the current setup guide.

For current behavior, use:

- [../../backend/README.md](../../backend/README.md)
- [../../architecture/ARCHITECTURE.md](../../architecture/ARCHITECTURE.md)
- [../../../uah-browser-extension/README.md](../../../uah-browser-extension/README.md)

# Email-First Identity + Autofill Scope Reset (2026-04-11)

## What Changed

- Identity is now email-first across active auth/account flows.
- Username is sunset in UI and treated as an internal compatibility mirror of email.
- Non-auth autofill was rolled back on Settings profile/preferences and resume/applicant profile forms.
- Autofill/password-manager metadata remains on auth and account-security forms only.
- Shared validation/normalization was added for email and phone.

## Backend

- Added shared validators:
  - `backend/app/core/validation.py`
  - Email normalization/validation (`trim + lowercase + regex`)
  - Phone normalization (`7-15 digits`, international-friendly, US-format on 10/11-digit US-like numbers)
- Startup identity backfill and guardrails:
  - `backend/app/main.py`
  - Preflights for case-insensitive duplicate emails and fails fast if found
  - Normalizes stored emails and enforces `username=email` for all users
  - Idempotent and rerunnable at startup
- Dev test bootstrap alignment:
  - `DEV_AUTH_TEST_EMAIL` is the primary identifier when enabled.
  - `DEV_AUTH_TEST_USERNAME` is retained as a legacy fallback only and should contain an email value.
- Auth/account changes:
  - `POST /api/auth/register` now email + password (+ names); persists `username=email`
  - `POST /api/auth/login` uses email; still accepts legacy `username` payload key as alias
  - `POST /api/auth/token` still receives OAuth2 `username` form field, treated as email
  - `PUT /api/account/change-email` now updates both `email` and mirrored `username`
  - `PUT /api/account/change-username` now returns `410 Gone` with deprecation message
- Google OAuth account provisioning/linking now enforces email/username mirror:
  - `backend/app/google/service.py`
  - `backend/app/api/routes.py`

## Frontend

- Email-first auth UI:
  - Login now uses email input/payload
  - Register removes username/confirm-username fields
  - Settings removes username-change UI
  - Nav user summary falls back to full name, then email
- Autofill policy:
  - Kept on login/register/forgot/reset and Settings account-security (change email/password)
  - Set to `autocomplete="off"` for non-auth profile/preferences/resume/applicant forms
- Added shared frontend validation helper:
  - `frontend/src/lib/validation.js`
  - Used by login/register/forgot-password/settings-change-email and applicant save in resumes
  - Includes phone normalization on blur/save in resume applicant form
- Local mock API aligned with new contracts:
  - Email-first login/register payload handling
  - `username=email` mirror behavior
  - `/api/account/change-username` returns `410`

## Notes

- `UserResponse.username` is intentionally retained for compatibility and mirrors email.
- Column removal for `users.username` is deferred to a later migration window.
