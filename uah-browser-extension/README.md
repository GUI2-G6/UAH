# UAH Browser Extension

Vue 3 + Vite browser extension that gives UAH users quick access to their saved applicant profiles and parsed resume data without leaving the current job board tab.

## What It Does

- Signs in against the existing UAH backend. There is no separate extension auth system.
- Supports email/password login and Google sign-in through the existing UAH OAuth endpoints.
- Shows compact read-only views for:
  - applicant profiles
  - parsed resumes
  - account and connected sign-in status
- Lets users copy individual fields like email, phone, summary, skills, and quick resume snapshots.
- Opens the full UAH app for anything that belongs in the full product experience.

## Legacy Reference Folders

The repo still contains `uah-test-extension/` and `uah-apply-overlay-prototype/` as rough historical references. They are legacy prototypes and are not part of the supported build path for this extension.

## Storage Model

- `chrome.storage.local`
  - Stores only extension auth metadata: the JWT, its expiry, and basic auth bookkeeping so the extension can survive browser restarts.
- `chrome.storage.session`
  - Stores non-sensitive view caches such as the current user snapshot, profile and resume summaries, and detail responses for the current browser session. These session caches are cleared on logout and whenever auth expires.
- The extension does not use `localStorage` or `sessionStorage`.

## Auth Flow

### Email / Password

1. The popup sends the credentials to the background service worker.
2. The background posts to `/api/auth/login` with `X-UAH-Client: extension`.
3. The backend returns the normal token payload and also sets the same HttpOnly auth cookie it uses for the web app.
4. The extension stores the JWT and expiry metadata in `chrome.storage.local`.
5. Each popup open validates the stored expiry first, then calls `/api/auth/me`; any `401` clears auth and returns to the sign-in screen.

### Google OAuth

1. The popup asks the background worker to start Google sign-in.
2. The background opens `/api/auth/google?intent=login&client=extension` in a new tab.
3. The backend completes the normal OAuth flow and redirects back to the configured UAH app origin.
4. The background watches that auth tab, then reads the env-scoped UAH auth cookie from the configured API origin with `chrome.cookies`.
5. The cookie JWT becomes the extension bearer token stored in `chrome.storage.local`.

## Configuration

Copy `.env.example` to `.env` inside `uah-browser-extension/` and set:

- `VITE_EXTENSION_APP_ORIGIN`
- `VITE_EXTENSION_API_ORIGIN`
- `VITE_EXTENSION_AUTH_COOKIE_NAME` or `VITE_EXTENSION_AUTH_NAMESPACE`

Both origins must be HTTPS-only. The build intentionally fails for non-HTTPS values.

For the reusable localhost harness, copy `.env.local.example` to `.env.local` instead. That local config points the extension at `https://localhost:5173`.

## Local Build

```bash
cd uah-browser-extension
npm install
npm run build
```

This repo also supports a fallback where the extension reuses `frontend/node_modules` for Vite if that toolchain is already installed.

## Local HTTPS Test Harness

This is the supported local integration path for the extension.

Quick helper:

```powershell
pwsh -File .\scripts\local\lifecycle\local-extension-test.ps1
```

Tiny wrappers:

```powershell
pwsh -File .\scripts\local\lifecycle\extension-local.ps1
pwsh -File .\scripts\local\lifecycle\extension-beta.ps1
```

Use `extension-beta.ps1` when you want the unpacked extension built against beta with Google OAuth enabled.

Build the unpacked extension for beta endpoints without starting the local harness:

```powershell
pwsh -File .\scripts\local\lifecycle\local-extension-test.ps1 -ExtensionTarget beta
```

1. Generate trusted localhost certs with `mkcert`:

```bash
mkdir -p volumes/certs/local
mkcert -install
mkcert -cert-file volumes/certs/local/tls.crt -key-file volumes/certs/local/tls.key localhost 127.0.0.1 ::1
```

2. Create the root local `.env` from `env-examples/local/.env.example`.
3. If you want a seeded login, set:
   - `DEV_AUTH_TEST_ACCOUNT_ENABLED=true`
   - `DEV_AUTH_TEST_PASSWORD=<your local password>`
4. Create `frontend/.env.local` from `frontend/.env.local.example`.
5. Start the local backend:

```bash
docker compose -f docker-compose.local.yml --profile backend up -d db-local backend-local
```

6. Start the HTTPS frontend:

```bash
cd frontend
npm install
npm run dev:backend
```

7. Open `https://localhost:5173` once in the browser and confirm the cert is trusted.
8. Create `uah-browser-extension/.env.local` from `uah-browser-extension/.env.local.example`.
9. Build the extension:

```bash
cd uah-browser-extension
npm run build
```

10. Load `uah-browser-extension/dist` unpacked in Chrome.
11. Sign in with email/password using either your normal local account or the seeded test account.

The local harness keeps the extension HTTPS-only and routes all app and API traffic through the same `https://localhost:5173` origin.
The helper script validates the required local env files, starts backend-local, launches the HTTPS frontend in a new PowerShell window, builds the extension, and prints the manual smoke-test checklist.
Pass `-ExtensionTarget beta` to reuse the same helper for a beta-targeted extension build that reads `uah-browser-extension/.env` and skips local backend/frontend startup.

## Load Unpacked In Chrome

1. Build the extension with `npm run build`.
2. Open `chrome://extensions`.
3. Enable `Developer mode`.
4. Click `Load unpacked`.
5. Select `uah-browser-extension/dist`.

## Load Temporarily In Firefox

1. Build the extension with `npm run build`.
2. Open `about:debugging`.
3. Choose `This Firefox`.
4. Click `Load Temporary Add-on...`.
5. Select the generated `uah-browser-extension/dist/manifest.json`.

## Firefox Note

The code isolates browser APIs behind a small wrapper to keep Firefox compatibility feasible later, but this version is Chrome-first and has only been planned and wired for MV3 behavior.

## Known Limitations

- The popup is intentionally read-only for profiles and resume data.
- Resume upload/parse flows stay in the full app.
- The old overlay autofill prototype is not part of this extension build.
- Google sign-in depends on the configured UAH auth cookie name and the browser permitting the extension to read it through the `cookies` permission on the configured API origin.
- Google sign-in is intentionally disabled when the extension is pointed at the localhost HTTPS harness; use email/password there and verify OAuth against dev or beta.
