# UAH Landing SPA

This directory contains the standalone public landing page for `uahapp.com`.

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

- `index.html` - Vite entry shell
- `package.json` - standalone landing app dependencies and scripts
- `vite.config.js` - static build config
- `src/` - the landing page Vue app, components, and global styles
- `docker-compose.yml` - optional standalone local compose for landing-only workflows
- `Dockerfile` - production image build used by beta compose
- `nginx.conf` - SPA-safe static serving config

## Local Development

From the repo root:

```powershell
cd landing
npm install
npm run dev
```

Vite serves the landing SPA locally at `http://localhost:5173`.

To override the Sign in button target during local testing, set:

```powershell
$env:VITE_UAH_LOGIN_URL = "http://localhost:5173/login"
```

Default target is `https://beta.uahapp.com/login`.

## Build And Deploy

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

## Cloudflare Tunnel Routing

The landing site stays on the existing external Docker network `uah-beta-infra`.

Cloudflare should route both hostnames below to the landing container:

- `uahapp.com` -> `http://uah-landing:80`
- `www.uahapp.com` -> `http://uah-landing:80`

Cloudflare handles TLS termination, so no TLS configuration is needed inside Nginx for this site.

## Operational Notes

- Production is still just static files served by Nginx.
- There are no analytics scripts, cookies, local storage writes, or backend integrations on this site.
- The landing app remains operationally independent from the main UAH frontend in `/frontend`.
- The closed beta remains separate at `https://beta.uahapp.com`.
