# Beta Setup Guide

This guide describes the current repo-managed beta environment shape.

Use it together with:

- [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)
- [CLOUDFLARE_SECURITY.md](CLOUDFLARE_SECURITY.md)
- [../env-examples/README.md](../env-examples/README.md)

Historical beta audit notes live in [../archive/README.md](../archive/README.md).

## Current Beta Shape

- base compose file: `docker-compose.yml`
- beta override: `docker-compose.beta.yml`
- environment template: `env-examples/beta/.env.example`
- ingress pattern: `cloudflared` tunnel container
- backend environment label: `ENVIRONMENT=beta`
- cookie / storage namespace: beta-specific

## 1. Prepare The Beta `.env`

On the beta deployment host, create a real repo-root `.env` from:

```text
env-examples/beta/.env.example
```

Key beta identity settings:

- `ENV=beta`
- `ENVIRONMENT=beta`
- `COMPOSE_PROJECT_NAME=uah-beta`
- `AUTH_NAMESPACE=beta`
- `AUTH_COOKIE_NAME=uah_auth_beta`
- `SESSION_COOKIE_NAME=uah_session_beta`
- `PUBLIC_APP_URL=https://beta.uahapp.com`
- `GOOGLE_REDIRECT_URI=https://beta.uahapp.com/api/auth/google/callback`
- `GMAIL_REDIRECT_URI=https://beta.uahapp.com/api/integrations/gmail/callback`
- `CLOUDFLARE_BETA_TUNNEL_TOKEN=...`

Beta should also use isolated Redis and queue namespaces:

- `BETA_REDIS_URL`
- `BETA_PARSE_QUEUE_NAME*`
- `BETA_REDIS_HOST_PORT`

## 2. Confirm Required External Networks

The current beta override expects these Docker networks to exist:

- `uah-infra`
- `uah-beta-infra`

If they do not exist on the target host yet, create them before startup.

## 3. Start The Stack

From the repo root on the beta host:

```bash
docker compose -f docker-compose.yml -f docker-compose.beta.yml up -d --build
```

This launches the normal app stack plus beta overrides, including `cloudflared` and the public `landing` service.

Important: do not run beta ingress from `docker-compose.local.yml` alone.  
The local compose path does not provide the beta Cloudflared origin shape.

## 4. Verify The Expected Containers

The beta stack should include environment-scoped names such as:

- `uah-beta-db`
- `uah-beta-backend`
- `uah-beta-frontend`
- `uah-beta-redis`
- `uah-beta-celery-worker`
- `uah-beta-celery-beat`
- `uah-beta-cloudflared`
- `uah-landing`

## 5. Current Runtime Expectations

These are current behavior notes, not future aspirations:

- generated API docs should be disabled because `ENVIRONMENT=beta`
- `/api/diagnostics` remains admin-gated
- saved jobs routes are authenticated
- the beta override currently still bind-mounts `./backend:/app`
- the frontend joins the `cloudflared` service network namespace instead of publishing a public host port directly
- Cloudflared ingress (token-managed) expects origin `http://localhost:80` inside the cloudflared namespace; this maps to the beta frontend nginx listener because frontend uses `network_mode: "service:cloudflared"`

That backend bind mount is important to understand before any broader external rollout. It is current behavior and should be reviewed explicitly during beta hardening.

## 6. OAuth And Email Checks

Before inviting testers:

- register the beta Google OAuth callback URI
- register the beta Gmail callback URI if Gmail integration is enabled
- confirm `EMAILS_ENABLED=true` and working SMTP or relay settings
- verify that reset and verification links point at `https://beta.uahapp.com`

## 7. Recommended Validation

```bash
bash scripts/uah.sh beta audit --mode full --json
```

Then verify the ingress path directly with compose:

```bash
docker compose -f docker-compose.yml -f docker-compose.beta.yml ps
docker compose -f docker-compose.yml -f docker-compose.beta.yml logs --tail=60 cloudflared
docker exec uah-beta-frontend wget -q -O - --timeout=8 http://127.0.0.1/api/status
```

Expected outcomes:
- `cloudflared` registers tunnel connections without sustained `dial tcp [::1]:80: connect: connection refused`
- `uah-beta-frontend` returns a successful `/api/status` payload through nginx -> backend proxy

Then manually confirm:

- tunnel connectivity
- login
- register / verify-email flows
- password reset
- job search
- resume upload / parse
- any enabled extension flow against the beta origin

## 8. Cloudflare Access Rollout Sequence

If you are removing a broad "all-users behind Access" wall, do it in stages:

1. Keep privileged paths behind Access:
   - `/api/admin/*`
   - `/api/jobs/debug/*`
   - `/docs`, `/redoc`, `/openapi.json`
   - `/dev`
2. Keep WAF, bot mitigation, and auth endpoint rate limits enabled.
3. Expose only public + normal authenticated app paths to the internet.
4. Observe for 48-72 hours before any additional policy loosening.

See [CLOUDFLARE_SECURITY.md](CLOUDFLARE_SECURITY.md) for the path buckets, policy targets, and rollback criteria.

## Related Docs

- [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)
- [CLOUDFLARE_SECURITY.md](CLOUDFLARE_SECURITY.md)
- [../../docker-compose.beta.yml](../../docker-compose.beta.yml)
- [../../env-examples/beta/.env.example](../../env-examples/beta/.env.example)
