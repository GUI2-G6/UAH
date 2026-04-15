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
- Lets users pin the extension into the current tab as a floating side panel. The pinned panel reuses the same popup app in an iframe, remembers its position, and can be dismissed per-tab or fully unpinned.
- Lets users run a manual, profile-driven page scan/fill flow on the current tab. The popup sends a prepared token map to the background worker, which injects the in-page autofill runtime only when you click `Scan page` or `Fill page`.
- Lets users step through multi-page application flows with `Previous page` and `Next page` actions that try visible navigation controls first, then fall back to browser history for back navigation.
- Opens the full UAH app for anything that belongs in the full product experience.

## Legacy Reference Folders

The repo still contains `uah-test-extension/` and `uah-apply-overlay-prototype/` as rough historical references. They are legacy prototypes and are not part of the supported build path for this extension.

## Storage Model

- `chrome.storage.local`
  - Stores only extension auth metadata and pinned UI preferences: the JWT, its expiry, and panel state so the extension can survive browser restarts.
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

## Runtime Flow

### Popup and Background

1. `popup.html` mounts the Vue app and chooses either the normal popup surface or the pinned-panel surface.
2. The Vue UI talks only to the background service worker through runtime messages.
3. The background worker owns auth, API fetches, cache hydration, logout cleanup, tab opening, and content-script injection.
4. Profile, resume, and account API responses are cached in `chrome.storage.session` until logout, expiry, or a forced refresh.

### Manual Autofill

1. The popup loads the selected applicant profile.
2. The extension builds a sanitized token map from `profile.token_map` when present, otherwise from flattened canonical resume data plus a few profile-specific fields such as work authorization and links.
3. Clicking `Scan page` or `Fill page` asks the background worker to inject `autofill-content.js` into the active tab.
4. The injected runtime scans visible standard form controls on the top-level page and either reports matches or fills fields from the prepared token map.
5. The extension does not run continuously in the page; the runtime is injected only when needed.

### Pinned Panel

1. Clicking `Pin` stores the preference in extension storage.
2. The background worker watches supported tabs and injects `pinned-panel.js` when pinning is enabled.
3. The pinned runtime renders a floating iframe that points back to `popup.html?surface=pinned`.
4. Position and size changes are persisted, while a temporary dismiss only hides the panel for the current tab until that tab navigates again.

## Configuration

Copy `.env.example` to `.env` inside `uah-browser-extension/` for shared remote targets, or set up the local harness config as described in the repo-root README. The build requires:

- `VITE_EXTENSION_APP_ORIGIN`
- `VITE_EXTENSION_API_ORIGIN`
- `VITE_EXTENSION_AUTH_COOKIE_NAME` or `VITE_EXTENSION_AUTH_NAMESPACE`

Both origins must be HTTPS-only. The build intentionally fails for non-HTTPS values.

The extension build emits three bundled surfaces into `dist/`:

- `manifest.json`, `popup.html`, and `background.js` from the main Vite build
- `autofill-content.js` from `vite.autofill.config.mjs`
- `pinned-panel.js` from `vite.pinned.config.mjs`

## Local Build

```bash
cd uah-browser-extension
npm install
npm run build
```

This repo also supports a fallback where the extension reuses `frontend/node_modules` for Vite if that toolchain is already installed.

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

- The popup is intentionally read-only for profile and resume editing.
- Resume upload/parse flows stay in the full app.
- The manual autofill runtime is generic and intentionally limited to visible standard controls on the top-level page. It does not currently scan iframes or shadow DOM.
- The navigation helpers only look for common visible button/link labels such as `Back`, `Previous`, `Next`, `Continue`, `Review`, and `Submit`.
- Google sign-in depends on the configured UAH auth cookie name and the browser permitting the extension to read it through the `cookies` permission on the configured API origin.
