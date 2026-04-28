# Cloudflare And Tunnel Notes For Beta

This guide documents the current beta ingress posture at a high level.

## Current Repo-Managed Shape

The repository currently models beta ingress through a `cloudflared` tunnel container defined in `docker-compose.beta.yml`.

That means:

- the beta frontend joins the `cloudflared` network namespace
- the repo-managed beta path does not rely on publishing the frontend directly on a public host port
- Cloudflare-side policy still matters, but part of the public-exposure story now lives in tunnel configuration instead of only origin firewall rules

## What The Repo Can Prove

The repository can help prove:

- the beta override includes `cloudflared`
- the tunnel token is expected in env
- beta-specific hostnames and namespaces are configured
- the app itself disables generated docs in `ENVIRONMENT=beta`
- diagnostics stay admin-gated

## What Still Needs Manual Operator Review

The repo cannot fully prove these Cloudflare-side controls:

- Access / Zero Trust policy for who may enter beta
- WAF rules and rate limits
- DNS / hostname wiring in Cloudflare
- tunnel ownership, routing, and service mapping

Those should be reviewed alongside the repo-managed audit before inviting external testers.

## Practical Review Items

- Confirm the hostname used by `PUBLIC_APP_URL` matches the Cloudflare-routed beta hostname.
- Confirm the tunnel publishes the expected service only.
- Confirm beta access control is intentional for the audience you are inviting.
- Confirm Cloudflare-side rate limiting covers auth-sensitive routes.

## Route Buckets For Rollout

Use these buckets when deciding what can be publicly reachable versus still behind Cloudflare Access.

### Public (Internet reachable)

- frontend public pages: `/landing`, `/login`, `/register`, `/signup`, `/status`, `/forgot-password`, `/reset-password`, `/oauth-callback`, `/verify-email`, `/privacy-policy`, `/our-commitment` (legacy redirect to `/privacy-policy`), `/contributors`
- backend public/identity routes needed for user auth and onboarding:
  - `/api/status`
  - `/api/auth/*`
  - `/api/public/*`
- backend account recovery / verification routes that must remain reachable for non-authenticated users:
  - `/api/account/forgot-password`
  - `/api/account/reset-password`
  - `/api/account/verify-email`

### Authenticated App Surface (internet reachable, app auth enforced)

- frontend authenticated pages such as `/home`, `/job-board`, `/resumes`, `/application`, `/settings`, `/notifications`, `/analytics`, `/timeline`
- backend user routes guarded by app auth:
  - `/api/account/*`
  - `/api/resume/*`
  - `/api/applicant-profile/*`
  - `/api/apply-sessions/*`
  - `/api/integrations/*`
  - `/api/integrations/gmail/*`

### Privileged/Internal (keep behind Cloudflare Access)

- `/api/admin/*` (admin only)
- `/api/jobs/debug/*` (admin/developer only)
- `/api/diagnostics` (privileged operational data)
- `/api/geolocation/muse-supported-locations/refresh` (internal refresh endpoint)
- `/docs`, `/redoc`, `/openapi.json`
- `/dev` frontend route

## Cloudflare Access Policy Set

When removing the full "all-site" Access wall, keep these Access applications/policies in place:

1. `uah-beta-privileged-admin`
   - include paths: `/api/admin/*`, `/api/diagnostics`, `/api/geolocation/muse-supported-locations/refresh`, `/docs`, `/redoc`, `/openapi.json`
   - allow: admin identity group only
2. `uah-beta-privileged-devtools`
   - include paths: `/api/jobs/debug/*`, `/dev`
   - allow: admin and developer groups

If your team uses one Access app per hostname, use policy path filters. If your team uses separate Access apps, map each path set into its own app.

In addition to Access, configure a request-header transform on the privileged path set so Cloudflare injects `X-Internal-Api-Key` with the same value configured in the backend environment.

## Edge Protection Requirements

Keep Cloudflare WAF/rate controls active even after relaxing the global Access wall.

- WAF managed ruleset enabled for the beta hostname.
- Bot Management/Super Bot Fight Mode enabled.
- Rate limit rules for auth-sensitive endpoints:
  - `/api/auth/login`
  - `/api/auth/token`
  - `/api/auth/register`
  - `/api/account/forgot-password`
  - `/api/account/reset-password`
  - `/api/account/verify-email`
  - `/api/public/beta-access`
  - `/api/public/landing-feedback`
- Add challenge/managed challenge rule for abusive bursts on the auth endpoints above.

## 72-Hour Observation Window

After rollout, hold for 48-72 hours before further loosening.

Monitor at minimum:

- request spikes and block/challenge events by path
- `401`, `403`, and `429` trends
- probes against privileged paths (`/api/admin/*`, `/api/jobs/debug/*`, docs routes)
- auth failure bursts from a single IP/ASN/country

Rollback triggers:

- repeated privileged-path probes getting through Access
- sustained auth attack traffic not contained by edge controls
- user-facing auth degradation caused by new edge rules

Rollback action:

- re-enable prior broad Access posture for the hostname and investigate before retrying.

## Related Docs

- [BETA_SETUP.md](BETA_SETUP.md)
- [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)
- [ZERO_TRUST_REMOVAL_CHECKLIST.md](ZERO_TRUST_REMOVAL_CHECKLIST.md)
- [../SECURITY_AUDIT_GUIDE.md](../SECURITY_AUDIT_GUIDE.md)
