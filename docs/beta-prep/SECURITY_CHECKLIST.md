# Beta Pre-Launch Security Checklist

Track this checklist as a GitHub issue before sharing `beta.uahapp.com` with any external testers or graders.
All items must be checked before the beta URL is shared outside the core team.

---

## Environment Configuration

- [ ] All `.env` values confirmed set correctly for the beta environment (no dev URLs, no empty secrets)
- [ ] No `.env` file committed to the `beta` branch — confirmed via `git status` and `.gitignore` check
- [ ] `ENVIRONMENT=beta` and `ENV=beta` set in beta `.env`
- [ ] `AUTH_NAMESPACE=beta` and `VITE_AUTH_NAMESPACE=beta` set for cookie/storage isolation
- [ ] `VITE_LOCAL_MODE=backend` set for beta builds (not `mock`)
- [ ] `SESSION_COOKIE_HTTPS_ONLY=true` set in beta `.env`
- [ ] `COMPOSE_PROJECT_NAME=uah-beta` set to avoid container name conflicts with dev
- [ ] `PUBLIC_APP_URL=https://beta.uahapp.com` set correctly (used in email links)
- [ ] `GOOGLE_REDIRECT_URI=https://beta.uahapp.com/api/auth/google/callback` set correctly
- [ ] `EMAILS_ENABLED=true` and all SMTP values configured and tested
- [ ] `ADMIN_BOOTSTRAP_ENABLED=false` unless a one-time admin account creation is needed

## Secrets Quality

- [ ] `SECRET_KEY` is a strong random value (minimum 32 hex characters, not a default or placeholder)
- [ ] `SESSION_SECRET` is a strong random value (minimum 32 hex characters, not a default or placeholder)
- [ ] `POSTGRES_PASSWORD` is a strong random value, different from the dev environment password
- [ ] `SECRET_KEY`, `SESSION_SECRET`, and `POSTGRES_PASSWORD` are different from their dev counterparts

## Backend Security

- [ ] Beta runtime confirmed in backend logs/startup output (`ENVIRONMENT=beta`)
- [ ] Hot-reload (`--reload`) flag removed from the backend process (use `command:` override in compose)
- [ ] Source code volume mount (`./backend:/app`) removed from compose for beta
- [ ] `/api/jobs/save` endpoint requires authentication (fix from `AUDIT.md` §1.5 applied)
- [ ] `/api/jobs/saved` endpoint requires authentication (fix from `AUDIT.md` §1.5 applied)
- [ ] `/api/diagnostics` is either removed, auth-gated (admin only), or not proxied by Nginx
- [ ] `/docs`, `/redoc`, `/openapi.json` are either disabled in FastAPI or not proxied by Nginx
- [ ] Beta celery worker and beat services are running and isolated from dev

## Frontend

- [ ] Frontend built in production mode (Vite `npm run build`, not `npm run dev`)
- [ ] `vite-plugin-vue-devtools` confirmed excluded from production build output
- [ ] No hardcoded dev URLs present in the built frontend (verify `dist/` assets)

## CORS

- [ ] CORS policy confirmed — no `CORSMiddleware` with wildcard origins is present in `backend/app/main.py`
- [ ] All API calls route through the Nginx same-origin proxy — no cross-origin requests needed

## OAuth

- [ ] `https://beta.uahapp.com/api/auth/google/callback` added to Google Cloud Console authorized redirect URIs
- [ ] Google OAuth login flow tested end-to-end on `beta.uahapp.com`

## Cloudflare — Proxy

- [ ] `beta.uahapp.com` DNS record confirmed as **Proxied** (orange cloud) in Cloudflare dashboard
- [ ] Origin server firewall configured — only Cloudflare IP ranges can reach port 80 on the host
- [ ] Direct-to-origin IP access confirmed blocked (test from a non-Cloudflare IP)
- [ ] No other ports (5432, 8000, WireGuard) accessible from the public internet on the beta host

## Cloudflare — Zero Trust Access

- [ ] Cloudflare Access application created for `beta.uahapp.com`
- [ ] Access policy configured with approved tester/grader email list
- [ ] One-time PIN email authentication enabled
- [ ] Access policy tested with at least one approved tester email — confirmed gating works
- [ ] Access policy tested with an unapproved email — confirmed access is denied

## Cloudflare — WAF and Rate Limiting

- [ ] Cloudflare WAF managed ruleset enabled on `beta.uahapp.com`
- [ ] Rate limiting rule active on `/api/auth/*` (brute-force prevention)
- [ ] Rate limiting rule active on `/api/account/forgot-password` (email flood prevention)
- [ ] Rate limiting rule active on `/api/account/send-verification` (email flood prevention)
- [ ] Bot Fight Mode enabled

## Cloudflare — SSL/TLS

- [ ] SSL/TLS mode set to **Full (strict)**
- [ ] HSTS enabled with minimum 6-month max-age
- [ ] Minimum TLS version set to **TLS 1.2**
- [ ] HTTPS redirect confirmed (HTTP → HTTPS for all traffic)

## Database

- [ ] Database (port 5432) confirmed not exposed on any public port
- [ ] Beta database is separate from the dev database (`POSTGRES_DB=uah_beta`)
- [ ] Database volume stored on the beta host — not shared with dev

## Dependencies

- [ ] `pip-audit` or `safety` run against `backend/requirements.txt` — no critical CVEs unaddressed
- [ ] `npm audit` run against `frontend/package.json` — no critical CVEs unaddressed
- [ ] `npm audit` run against `uah-browser-extension/package.json` when the extension lockfile is present
- [ ] `gitleaks` scan run against tracked repo files — no unapproved secret findings
- [ ] Dependabot alerts reviewed in GitHub — no critical vulnerabilities outstanding

## Final Verification

- [ ] Full demo flow completed on `beta.uahapp.com` before sharing access with testers:
  - [ ] Registration with email/password
  - [ ] Email verification flow
  - [ ] Google OAuth login
  - [ ] Job search and save
  - [ ] Resume upload and parse
  - [ ] Password reset flow
  - [ ] Profile update
- [ ] At least one team member has tested the complete flow in a fresh private browser window via Cloudflare Access authentication
- [ ] Beta URL and tester instructions shared only with the approved list — not posted publicly

---

*This checklist was generated as part of the beta prep audit. See `docs/beta-prep/AUDIT.md` for full findings and `docs/beta-prep/BETA_SETUP.md` for setup instructions.*
