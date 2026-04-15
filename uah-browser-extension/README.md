# UAH Browser Extension

The browser extension gives users quick access to UAH profile and resume data without leaving the current job board tab.

It is Chrome-first, MV3-based, and intentionally built around explicit user actions rather than a continuously running page agent.

## What It Does Today

- signs in against the existing UAH backend
- supports email/password login and Google sign-in
- shows cached read-only profile, resume, and account snapshots
- injects a pinned side panel into supported tabs
- runs a manual `Scan page` / `Fill page` flow on the active tab
- provides simple application-step navigation helpers such as previous/next-page actions

## Source Of Truth

Use these docs together:

- repo entrypoint: [../README.md](../README.md)
- docs map: [../docs/README.md](../docs/README.md)
- extension adapter system: [src/adapters/ADAPTERS.md](src/adapters/ADAPTERS.md)

## Architecture

### Popup app

- `popup.html` mounts the Vue app
- the same UI can render as the standard popup or the pinned panel surface
- the popup does not talk to the backend directly

### Background worker

- owns auth, API fetches, storage, and cache invalidation
- opens OAuth tabs
- reads the environment-scoped backend auth cookie for the extension Google login bridge
- injects the autofill and pinned-panel runtimes when needed

### Injected runtimes

- `src/autofill/` discovers visible fields, builds a fill plan, and writes values only when the user requests it
- `src/pinned-panel/` renders the floating iframe surface inside the active page

## Storage Model

- `chrome.storage.local`
  - long-lived auth metadata
  - pinned UI preferences
- `chrome.storage.session`
  - non-sensitive cached API payloads for the current browser session

The extension does not use `localStorage` or `sessionStorage`.

## Auth Model

### Email / password

1. The popup sends credentials to the background worker.
2. The background posts to `/api/auth/login` with `X-UAH-Client: extension`.
3. The backend returns the normal token payload and sets the same environment-scoped auth cookie used by the web app.
4. The extension persists JWT expiry metadata locally and validates it on future popup opens.

### Google sign-in

1. The background opens `/api/auth/google?intent=login&client=extension`.
2. After the backend completes OAuth, the background reads the configured backend auth cookie from the API origin.
3. That cookie value becomes the extension bearer token for subsequent API calls.

This is why the build requires either `VITE_EXTENSION_AUTH_COOKIE_NAME` or `VITE_EXTENSION_AUTH_NAMESPACE`.

## Manual Autofill Flow

1. The popup loads the selected applicant profile.
2. The extension builds a sanitized token map from `profile.token_map` when present.
3. If there is no explicit token map, the extension falls back to flattened canonical resume/profile data.
4. Clicking `Scan page` or `Fill page` injects the content runtime into the active tab.
5. The runtime inspects visible standard controls on the top-level page only.

Current limitations:

- no always-on monitoring
- no iframe traversal
- no shadow DOM support
- no automatic final submission

## Pinned Panel

- pinning is a user preference stored in extension storage
- the background injects the pinned runtime on supported tabs when pinning is enabled
- the pinned panel is an iframe that points back to `popup.html?surface=pinned`
- panel position and size persist, but temporary dismissals stay tab-scoped

## Build Configuration

Required env values:

- `VITE_EXTENSION_APP_ORIGIN`
- `VITE_EXTENSION_API_ORIGIN`
- `VITE_EXTENSION_AUTH_COOKIE_NAME` or `VITE_EXTENSION_AUTH_NAMESPACE`

Both origins must be HTTPS origins. The build intentionally fails for non-HTTPS origins.

The build emits:

- main extension bundle and `manifest.json`
- `autofill-content.js`
- `pinned-panel.js`

## Commands

Run from `uah-browser-extension/`:

```bash
npm install
npm run build
npm test
```

### Tests

- `npm run test:autofill`
- `npm run test:adapters`

## Local Harness

For the localhost HTTPS flow that pairs the extension with a real local backend/frontend, use the repo-root guidance in [../README.md](../README.md). The PowerShell helper remains:

```powershell
pwsh -File .\scripts\local\lifecycle\local-extension-test.ps1
```

## Known Boundaries

- profile and resume editing stay in the main web app
- the extension is a productivity surface, not a second full product shell
- adapter coverage varies by ATS and company override depth

## Historical Note

Legacy prototype folders may still exist in the repo as references, but they are not part of the supported build path for this extension.
