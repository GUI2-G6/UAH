# frontend

This template should help get you started developing with Vue 3 in Vite.

For end-to-end local setup (database + backend + frontend), follow the authoritative flow in [../backend/README.md](../backend/README.md). This file only covers frontend commands.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

Run commands from the `frontend/` directory:

```sh
npm install
```

### Compile and Hot-Reload for Development

Mock-first mode (default) renders the app without requiring backend services:

```sh
npm run dev
```

Backend passthrough mode proxies `/api`, `/docs`, and `/openapi.json` to local backend:

```sh
npm run dev:backend
```

Security notes:

- Local dev server binds to `127.0.0.1` by default.
- Backend mode only allows loopback targets unless you explicitly set `VITE_ALLOW_REMOTE_API=true`.
- Keep `VITE_AUTH_NAMESPACE=dev` for local workflows to avoid auth storage collisions with other environments.

### Compile and Minify for Production

```sh
npm run build
```

## Shared Card Contract

- `frontend/src/components/Card.vue` is the shared structural card primitive.
- Its internal class contract is namespaced as `ui-card*`; do not target bare `.card` or `.big-card`.
- Public variants are limited to:
  - `default` for dashboard and form cards
  - `job` for job listing cards
  - `minimal` for inset or nested cards
- Page-level tuning must happen through caller-owned classes and these documented CSS variables:
  - `--ui-card-bg`
  - `--ui-card-border`
  - `--ui-card-shadow`
  - `--ui-card-padding`
  - `--ui-card-header-bg`
  - `--ui-card-header-padding`
- Do not restyle shared internals globally.
- Run `npm run check:cards` before opening a PR that changes shared card consumers or the card primitive.

## Job Board Notes

- Filter metadata is backend-owned via `GET /api/jobs/filter-metadata` and includes:
  - Canonical category groups/aliases
  - Supported level labels
  - `location_param_cap`
- Default discovery is intentionally broad:
  - `Remote` and `Hybrid` start enabled.
  - Backend may run a one-time relaxed-location fallback when strict location matching returns no jobs.
- Job search sends keyword/date server-side (`q`, `posted_after`) so totals and pagination match backend filtering.
- Before search, the UI preflights location trimming and shows `Using X of Y resolved locations`.
- Compatibility transparency:
  - With Remote off, constraint-overlap roles can still appear (policy: `allow-if-overlap`).
  - The Job Board shows a diagnostics hint when this happens.
- Local mock mode emulates:
  - Category expansion behavior
  - Location cap/truncation diagnostics
  - Search diagnostics fields used by Job Board transparency UI

## Identity And Autofill Notes (April 11, 2026)

- Identity is now email-first in UI flows.
  - Login uses email as the sign-in identifier.
  - Register no longer asks for username.
  - Settings no longer shows username management.
- Autofill policy is intentionally narrow:
  - Keep browser/password-manager metadata only on auth + account-security forms:
    - `Login`, `Register`, `Forgot-Password`, `Reset-Password`
    - Settings `Change Email` + `Change Password`
  - All profile/resume/settings-preference data-entry fields are `autocomplete="off"` to avoid noisy autofill interference.
- Password manager compatibility is preserved for credential updates:
  - Account-security forms provide username/email context and keep `current-password` / `new-password` semantics for password updates.
