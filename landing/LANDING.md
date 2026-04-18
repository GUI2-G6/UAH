# UAH Landing SPA

This directory contains the standalone public landing page for `uahapp.com`.

It is intentionally separate from the main UAH app stack:

- its own Vue 3 + Vite app
- no shared components or tooling from `/frontend`
- no backend API calls
- no Node server in production
- built to static files in `dist/`
- served by a lightweight `nginx:alpine` container named `uah-landing`

## Files

- `index.html` - Vite entry shell
- `package.json` - standalone landing app dependencies and scripts
- `vite.config.js` - static build config
- `src/` - the landing page Vue app, components, and global styles
- `docker-compose.yml` - isolated Nginx container definition for the landing site

## Local Development

From the repo root:

```powershell
cd landing
npm install
npm run dev
```

Vite serves the landing SPA locally at `http://localhost:5173`.

## Build And Deploy

Build the static production files:

```powershell
cd landing
npm run build
```

That writes the deployable site to `landing/dist/`.

If `uah-landing` is already running:

```powershell
docker compose restart uah-landing
```

If the container is not running yet:

```powershell
docker compose up -d
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
