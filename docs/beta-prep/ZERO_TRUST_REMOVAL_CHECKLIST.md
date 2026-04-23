# Zero Trust Removal Checklist

Use this checklist before removing the site-wide Cloudflare Zero Trust wall from the beta or production hostname.

This is a go/no-go checklist. Do not remove the broad Access wall until every blocker in the first section is complete.

## Stop/Go Blockers

- [ ] Fix trusted client IP handling before public launch.
  Backend rate limits currently trust the first `X-Forwarded-For` value. Before opening the site, change the proxy/backend chain so the app trusts only a sanitized client IP from Cloudflare or Nginx real-IP handling, not a user-supplied `X-Forwarded-For` value.
- [ ] Remove mutable beta runtime behavior.
  Beta should not run with `./backend:/app` bind mounts or `uvicorn --reload`. Build immutable images for beta/prod and run them without source mounts.
- [ ] Patch backend dependency advisories.
  Update the currently flagged packages before launch: `pypdf`, `python-dotenv`, `pyasn1`, and the `fastapi`/`starlette` chain.
- [ ] Reduce public backend detail.
  Trim `/api/status` so it does not expose detailed runtime or database version information, and stop returning raw exception/debug text from public geolocation responses.
- [ ] Make privileged backend header protection mandatory.
  Set a strong `INTERNAL_API_KEY` in beta/prod and verify that privileged routes reject requests when the expected header is missing.
- [ ] Re-run security validation after the changes above.
  Run the repo audit, dependency audit, and targeted smoke tests again after the launch blockers are fixed.

## Public Route Buckets

Keep these route buckets explicit when removing the broad wall.

### Internet Reachable

- Frontend public routes required for onboarding and account recovery:
  `/landing`, `/login`, `/register`, `/signup`, `/status`, `/forgot-password`, `/reset-password`, `/oauth-callback`, `/verify-email`, `/our-commitment`, `/contributors`
- Backend public and identity routes:
  `/api/status`, `/api/auth/*`, `/api/public/*`
- Backend account-recovery routes that must stay reachable for non-authenticated users:
  `/api/account/forgot-password`, `/api/account/reset-password`, `/api/account/verify-email`

### Internet Reachable, App Auth Required

- Frontend authenticated app routes such as `/home`, `/job-board`, `/resumes`, `/application`, `/settings`, `/notifications`, `/analytics`, `/timeline`
- Backend authenticated user routes:
  `/api/account/*` except the three recovery/verification routes above
  `/api/resume/*`
  `/api/applicant-profile/*`
  `/api/apply-sessions/*`
  `/api/integrations/*`
  `/api/integrations/gmail/*`

### Keep Behind Cloudflare Access

- `/api/admin/*`
- `/api/jobs/debug/*`
- `/api/diagnostics`
- `/api/geolocation/muse-supported-locations/refresh`
- `/docs`
- `/redoc`
- `/openapi.json`
- `/dev`

## Cloudflare Configuration To Keep

- [ ] Keep the `cloudflared` tunnel in front of the origin.
- [ ] Keep Cloudflare WAF managed rules enabled on the hostname.
- [ ] Keep bot mitigation enabled on the hostname.
- [ ] Keep Cloudflare Access in place for every privileged path listed above.
- [ ] Add a Cloudflare request-header transform on privileged paths to inject `X-Internal-Api-Key: <same value as backend env>`.
- [ ] Confirm the origin is not directly reachable outside Cloudflare/Tunnel, or is otherwise restricted to Cloudflare-only traffic.

## Cloudflare Rate Limits To Keep

- [ ] `POST /api/auth/login`
- [ ] `POST /api/auth/token`
- [ ] `POST /api/auth/register`
- [ ] `POST /api/account/forgot-password`
- [ ] `POST /api/account/reset-password`
- [ ] `POST /api/account/verify-email`
- [ ] `POST /api/public/beta-access`
- [ ] `POST /api/public/landing-feedback`

For these rules, keep logging and challenge/block actions configured so auth abuse and intake spam are visible during rollout.

## Validation Commands

- [ ] Run the repo audit:
  `bash scripts/uah.sh beta audit --mode full --json`
- [ ] Run backend dependency audit:
  `python -m pip_audit -r backend/requirements.txt`
- [ ] Run frontend dependency audit where applicable:
  `npm audit --omit=dev`
- [ ] Run targeted backend smoke/security tests:
  `pytest backend/tests/test_auth_security.py backend/tests/test_main_docs_gating.py backend/tests/test_status_routes.py backend/tests/test_beta_access_intake.py backend/tests/test_landing_feedback_intake.py backend/tests/test_admin_invites.py -q`

## Operator Validation

- [ ] From a non-privileged identity, confirm Access blocks `/api/admin/*`, `/api/jobs/debug/*`, `/api/diagnostics`, `/docs`, `/redoc`, `/openapi.json`, and `/dev`.
- [ ] Confirm the Cloudflare header transform is only applied to the privileged route set.
- [ ] Confirm login, registration, password reset, email verification, resume upload, and job search work from a normal external client.
- [ ] Confirm the tunnel publishes only the intended service and hostname.
- [ ] Confirm beta secrets, DB, Redis, cookie names, and queue namespaces remain separate from dev.

## Rollout Guardrail

- [ ] Hold a 48-72 hour observation window after removing the site-wide wall.
- [ ] Monitor `401`, `403`, and `429` trends, auth failure bursts, privileged-path probes, and WAF/rate-limit events.
- [ ] Be ready to restore the prior broad Access wall immediately if privileged paths become reachable, auth traffic spikes are not contained, or legitimate users are blocked by new edge rules.

## Related Docs

- [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)
- [CLOUDFLARE_SECURITY.md](CLOUDFLARE_SECURITY.md)
- [../SECURITY_AUDIT_GUIDE.md](../SECURITY_AUDIT_GUIDE.md)
