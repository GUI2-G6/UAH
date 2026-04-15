# UAH Browser Extension Security Model

## Scope

This extension is a compact companion to the UAH web app. It reads existing UAH account data and opens the full app for any broader workflow.

## Network Boundaries

- The extension build requires a configured HTTPS UAH app origin and HTTPS UAH API origin.
- `manifest.json` grants host permissions only for the configured API origin.
- No wildcard origins are used.
- All backend requests are sent with `X-UAH-Client: extension`.

## Permissions

- `storage`
  - Required to persist extension auth metadata across browser restarts and hold session-scoped caches.
- `cookies`
  - Required to read and clear the existing UAH auth cookie on the configured API origin for Google sign-in bridging and explicit logout cleanup.
- `tabs`
  - Required to open the full UAH app and watch the Google OAuth tab until it lands back on the configured UAH origin.
- `activeTab`
  - Required so manual autofill actions can run only on the currently active page after the user clicks Scan or Fill.
- `scripting`
  - Required to inject the on-demand autofill runtime into the active tab. The extension does not use a persistent content script.

## Stored Data

### `chrome.storage.local`

Stored:

- extension JWT
- token expiry timestamp
- token issued-at timestamp
- client marker (`extension`)

Not stored:

- passwords
- Google OAuth codes
- full applicant profile payloads
- full resume payloads

Reason:

- This is the minimum persistent state needed to keep the user signed in between browser restarts.

### `chrome.storage.session`

Stored:

- current user snapshot
- connected-account status payload
- profile list and profile detail responses
- resume list and resume detail responses

Reason:

- This is non-sensitive display data that helps the popup stay responsive during the current browser session without persisting those payloads long-term.
- All session cache entries are cleared on logout and on auth expiry so stale profile or resume data does not linger between signed-in states.

## Logging

- Tokens and cookie values must never be written to `console.log`.
- Errors are surfaced to the UI using generic user-safe messages.
- The background worker avoids serializing raw auth headers or cookies into thrown errors.

## Session Expiry

- The extension checks the stored JWT expiry before using it.
- It then confirms the session against `/api/auth/me`.
- Any `401` clears local auth state and returns the popup to the sign-in flow.

## CSP

- The extension uses Manifest V3 with a strict `extension_pages` CSP.
- No inline scripts are used.
- No `eval` usage is allowed.
