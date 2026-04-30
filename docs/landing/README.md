# UAH Landing SPA

Source for this app lives under [`landing/`](../../landing/). This page is documentation only — the codebase is unchanged when you edit this file.

This directory (`landing/`) contains the standalone public landing page for `uahapp.com`.

It is intentionally separate from the main UAH frontend codebase:

- its own Vue 3 + Vite app
- no shared components or tooling from `/frontend`
- no backend API calls
- no Node server in production
- built to static files in `dist/`
- served by a lightweight `nginx:alpine` container named `uah-landing`

Operationally, the landing container is now integrated into the beta stack:

- compose service: `landing` in `docker-compose.beta.yml`
- lifecycle start/stop via `bash scripts/uah.sh beta start|stop|restart`

## Files

- `index.html` — Vite entry shell
- `package.json` — standalone landing app dependencies and scripts
- `vite.config.js` — static build config
- `src/` — the landing page Vue app, components, and global styles
- `docker-compose.yml` — optional standalone local compose for landing-only workflows
- `Dockerfile` — production image build used by beta compose
- `nginx.conf` — SPA-safe static serving config

## Local development

From the repo root:

```powershell
cd landing
npm install
npm run dev
```

Standalone `npm run dev` in `landing/` uses Vite’s default dev server (typically `http://localhost:5173`). If you launch the landing app through the repo root helper `npm run dev:local`, the orchestrator assigns **port 5174** for landing so it does not collide with the main frontend (`5173`). See the root [README.md](../../README.md).

For local dev, copy `landing/.env.local.example` to `landing/.env.local` and set:

- `VITE_LOCAL_BACKEND_ORIGIN` — backend base URL for the Vite `/api` proxy (see `landing/vite.config.js`; default `http://localhost:8000`)
- `VITE_UAH_LOGIN_URL` — where marketing CTAs point for Sign in (e.g. `http://localhost:5173/login` when the main app runs on 5173)

You can also set these ad hoc in the shell:

```powershell
$env:VITE_LOCAL_BACKEND_ORIGIN = "http://localhost:8000"
$env:VITE_UAH_LOGIN_URL = "http://localhost:5173/login"
```

Default `VITE_UAH_LOGIN_URL` when unset is `https://beta.uahapp.com/login`.

## Build and deploy

Build the static production files:

```powershell
cd landing
npm run build
```

That writes the deployable site to `landing/dist/`.

If `uah-landing` is already running in standalone mode:

```powershell
docker compose restart uah-landing
```

If the container is not running yet:

```powershell
docker compose up -d
```

For beta-stack-integrated operations, use:

```bash
bash scripts/uah.sh beta start
```

## Cloudflare tunnel routing

The landing site stays on the existing external Docker network `uah-beta-infra`.

Cloudflare should route both hostnames below to the landing container:

- `uahapp.com` → `http://uah-landing:80`
- `www.uahapp.com` → `http://uah-landing:80`

Cloudflare handles TLS termination, so no TLS configuration is needed inside Nginx for this site.

## Operational notes

- Production is still just static files served by Nginx.
- There are no analytics scripts, cookies, local storage writes, or backend integrations on this site by default — keep it that way unless an intentional change lands with updated policy docs.
- The landing app remains operationally independent from the main UAH frontend in `/frontend`.
- The closed beta remains separate at `https://beta.uahapp.com`.
- The public route `/browser-extension` hosts the extension alpha notice, download link (`/downloads/uah-browser-extension-alpha.zip`), and Chrome install guide link (`/docs/BROWSER_EXTENSION_CHROME_INSTALL.md`).
