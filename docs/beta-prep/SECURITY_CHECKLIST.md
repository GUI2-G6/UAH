# Beta Security Checklist

Use this checklist before sharing `beta.uahapp.com` outside the core team.

This file describes the current beta shape. Historical findings and one-time gap analyses belong in the archive, not here.

## Environment

- [ ] Beta host uses a real repo-root `.env` derived from `env-examples/beta/.env.example`
- [ ] `ENV=beta` and `ENVIRONMENT=beta` are set
- [ ] `COMPOSE_PROJECT_NAME=uah-beta` is set
- [ ] `AUTH_NAMESPACE=beta`, `AUTH_COOKIE_NAME=uah_auth_beta`, and `SESSION_COOKIE_NAME=uah_session_beta` are set
- [ ] `PUBLIC_APP_URL=https://beta.uahapp.com` is set
- [ ] `SESSION_COOKIE_HTTPS_ONLY=true` is set
- [ ] Beta secrets differ from dev secrets

## Tunnel / Cloudflare

- [ ] `CLOUDFLARE_BETA_TUNNEL_TOKEN` is set
- [ ] `uah-beta-cloudflared` is running
- [ ] `beta.uahapp.com` resolves through the intended Cloudflare/tunnel setup
- [ ] Public vs privileged route bucket review completed (see `CLOUDFLARE_SECURITY.md`)
- [ ] Access policy keeps `/api/admin/*`, `/api/jobs/debug/*`, `/docs`, `/redoc`, `/openapi.json`, and `/dev` restricted
- [ ] Access identity groups are mapped correctly (admin vs admin/developer)
- [ ] WAF managed rules are enabled on beta hostname
- [ ] Bot mitigation is enabled on beta hostname
- [ ] Cloudflare rate limits exist for auth-sensitive routes (`/api/auth/login`, `/api/auth/register`, `/api/auth/forgot-password`, OAuth paths)
- [ ] 48-72h post-change observation window is planned (or completed) with rollback criteria

## Backend

- [ ] `/api/status` responds as expected
- [ ] `/api/diagnostics` requires an admin session
- [ ] `/docs`, `/redoc`, and `/openapi.json` are not exposed in beta
- [ ] Saved jobs routes require authentication
- [ ] Queue-backed services use beta-specific Redis and queue namespaces
- [ ] The current beta backend bind mount (`./backend:/app`) has been reviewed and explicitly accepted or changed before broader exposure

## Frontend

- [ ] Frontend was built through the compose workflow, not `npm run dev`
- [ ] Public status behavior is acceptable when diagnostics access is limited
- [ ] No dev-only URLs are present in the beta runtime configuration

## Identity / Integrations

- [ ] Google OAuth beta callback URI is registered
- [ ] Gmail callback URI is registered if Gmail integration is enabled
- [ ] Email verification and password reset links point to beta
- [ ] SMTP / relay configuration has been tested

## Data / Services

- [ ] Beta DB is separate from dev
- [ ] Beta Redis is separate from dev
- [ ] Celery worker and beat are healthy when queue-backed features are enabled
- [ ] Required provider API keys are configured for the intended beta feature set

## Validation

- [ ] `bash scripts/uah.sh beta audit --mode full --json` has been run
- [ ] Registration/login/password-reset/manual smoke tests passed
- [ ] Resume upload and parsing smoke tests passed
- [ ] Job search smoke tests passed

## Related Docs

- [BETA_SETUP.md](BETA_SETUP.md)
- [CLOUDFLARE_SECURITY.md](CLOUDFLARE_SECURITY.md)
- [../SECURITY_AUDIT_GUIDE.md](../SECURITY_AUDIT_GUIDE.md)
