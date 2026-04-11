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

## Job Board Notes

- Filter metadata is backend-owned via `GET /api/jobs/filter-metadata` and includes:
  - Canonical category groups/aliases
  - Supported level labels
  - `location_param_cap`
- Job search sends keyword/date server-side (`q`, `posted_after`) so totals and pagination match backend filtering.
- Before search, the UI preflights location trimming and shows `Using X of Y resolved locations`.
- Compatibility transparency:
  - With Remote off, constraint-overlap roles can still appear (policy: `allow-if-overlap`).
  - The Job Board shows a diagnostics hint when this happens.
- Local mock mode emulates:
  - Category expansion behavior
  - Location cap/truncation diagnostics
  - Search diagnostics fields used by Job Board transparency UI

## Settings And Autofill Notes (April 11, 2026)

- Settings layout now keeps `Notifications & Preferences` inside the `Profile Settings` card for a single consolidated profile area.
- `Connected Accounts` remains a dedicated card for long-term provider support (`Google` now, additional providers later).
- Browser autofill compatibility pass applied to core forms:
  - Auth (`Login`, `Register`, `Forgot-Password`, `Reset-Password`)
  - Settings account/security inputs
  - Resume applicant profile forms
  - Applicant Information page
- Standards used:
  - Personal/contact fields use semantic `name` + `autocomplete` tokens (`given-name`, `family-name`, `email`, `tel`, `street-address`, `address-level2`, `address-level1`, `postal-code`).
  - Password/token fields use `current-password`, `new-password`, `one-time-code`.
  - Search/filter/custom query controls use `autocomplete="off"` plus neutral names to prevent account autofill bleed into non-account forms.
