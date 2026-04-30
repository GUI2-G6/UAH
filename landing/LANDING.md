# Landing app

Operational and developer notes for `landing/` are in **[docs/landing/README.md](../docs/landing/README.md)**.

## Local environment

- Copy **`landing/.env.local.example`** to `landing/.env.local`.
- **`VITE_LOCAL_BACKEND_ORIGIN`** — `landing/vite.config.js` proxies `/api` to this origin (default `http://localhost:8000`).
- **`VITE_UAH_LOGIN_URL`** — Sign-in / CTA links to the main app (defaults to beta if unset).

Documentation index: **[docs/README.md](../docs/README.md)**.
