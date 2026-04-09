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

### Compile and Minify for Production

```sh
npm run build
```
