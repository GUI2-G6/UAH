# UAH Browser Extension Security Model

## Scope

The extension is a compact companion to the UAH web app. It reads existing UAH account data and opens the full app for broader workflows.

## Network boundaries

- Build requires configured HTTPS UAH app origin and HTTPS UAH API origin
- `manifest.json` host permissions are limited to configured API origin
- No wildcard origins
- Backend requests include `X-UAH-Client: extension`

## Permissions

- `storage`: persist extension auth metadata and session-scoped caches
- `cookies`: read/clear UAH auth cookie on configured API origin for Google sign-in bridge and explicit logout cleanup
- `tabs`: open full UAH app and monitor Google OAuth tab until it returns to UAH origin
- `activeTab`: manual autofill actions run only on current tab after explicit user action
- `scripting`: inject on-demand autofill runtime into active tab; no persistent content script

## Stored data

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

### `chrome.storage.session`

Stored:

- current user snapshot
- connected-account status payload
- profile list/detail responses
- resume list/detail responses

Session cache entries are cleared on logout and auth expiry.

## Logging

- Tokens and cookie values must never be logged
- UI surfaces generic user-safe error messages
- Background worker avoids serializing raw auth headers/cookies into thrown errors

## Session expiry

- JWT expiry is checked before token use
- Session is confirmed against `/api/auth/me`
- `401` responses clear auth state and return popup to sign-in flow

## CSP

- Manifest V3 with strict `extension_pages` CSP
- No inline scripts
- No `eval`
