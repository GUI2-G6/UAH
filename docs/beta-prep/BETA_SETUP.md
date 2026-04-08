# Beta Environment Setup Guide

**Target domain:** `beta.uahapp.com`  
**Based on:** `dev` branch  
**For:** Team members with legitimate deploy access

---

## Overview

This guide covers everything needed to configure and deploy the UAH application on `beta.uahapp.com`. The beta deployment is Cloudflare-proxied (no VPN required) and targets semi-public access for approved testers and graders.

Before following this guide, ensure you have:

- SSH access to the beta server host
- Access to the team's secret management tool (for `.env` values)
- Google Cloud Console access (for OAuth callback URI updates)
- Cloudflare access for the `uahapp.com` zone

---

## Part 1 — Domain and Routing

### 1.1 Current dev.uahapp.com References That Need Updating

Every occurrence of `dev.uahapp.com` in the codebase is driven by environment variables. **No source code changes are needed** to switch from dev to beta — only `.env` values must change.

The following table maps each occurrence to the env var that controls it:

| File | Variable | Current dev value | Beta value |
|------|----------|------------------|------------|
| `.env` | `DEV_DOMAIN` | `dev.uahapp.com` | `beta.uahapp.com` |
| `.env` | `GOOGLE_REDIRECT_URI` | `https://dev.uahapp.com/api/auth/google/callback` | `https://beta.uahapp.com/api/auth/google/callback` |
| `.env` | `PUBLIC_APP_URL` | `https://dev.uahapp.com` | `https://beta.uahapp.com` |
| `.env` | `COMPOSE_PROJECT_NAME` | `uah-dev` | `uah-beta` |

### 1.2 Where Nginx Uses the Domain

The `docker-compose.yml` passes `DEV_DOMAIN` into the frontend container. The Nginx container startup script (`docker-entrypoint.d/10-select-nginx-config.sh`) uses this variable to substitute the `__DOMAIN__` placeholder in the Nginx config template.

When `DEV_DOMAIN=beta.uahapp.com`, Nginx will serve the `server_name beta.uahapp.com;` block correctly.

### 1.3 OAuth Callback URIs — External Service Updates

When the beta environment is ready, update the following external services before going live:

**Google Cloud Console:**

1. Go to the project in [console.cloud.google.com](https://console.cloud.google.com)
2. Navigate to **APIs & Services → Credentials → OAuth 2.0 Client IDs**
3. Edit the client used by UAH
4. Under **Authorized redirect URIs**, add: `https://beta.uahapp.com/api/auth/google/callback`
5. You may leave `https://dev.uahapp.com/api/auth/google/callback` in place so dev continues to work

**Note:** The `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` values can be the same for dev and beta if they are part of the same Google Cloud project. The redirect URI is what differentiates the environments.

---

## Part 2 — Environment Variables

### 2.1 Creating the Beta .env File

On the beta server, create `/srv/uah/environments/beta/.env` using `env-examples/beta/.env.example` as the template.

Important: runtime expects `.env` in the deployment root (`/srv/uah/environments/beta/.env`), not inside `env-examples/`.

**Variables that differ between dev and beta:**

| Variable | dev value | beta value | Notes |
|----------|----------|-----------|-------|
| `COMPOSE_PROJECT_NAME` | `uah-dev` | `uah-beta` | Prevents container name conflicts |
| `ENV` | `dev` | `beta` | Environment label used in logs |
| `ENVIRONMENT` | `development` | `production` | Controls debug mode in backend |
| `DEV_DOMAIN` | `dev.uahapp.com` | `beta.uahapp.com` | Used by Nginx server_name |
| `POSTGRES_DB` | `uah_dev` | `uah_beta` | Separate database from dev |
| `POSTGRES_PASSWORD` | (dev password) | (beta-specific strong secret) | Must be different from dev |
| `SECRET_KEY` | (dev secret) | (beta-specific strong secret) | Must be different from dev |
| `SESSION_SECRET` | (dev secret) | (beta-specific strong secret) | Must be different from dev |
| `GOOGLE_REDIRECT_URI` | `https://dev.uahapp.com/api/auth/google/callback` | `https://beta.uahapp.com/api/auth/google/callback` | Must be registered in GCP |
| `PUBLIC_APP_URL` | `https://dev.uahapp.com` | `https://beta.uahapp.com` | Used in email links |
| `EMAILS_ENABLED` | `false` | `true` | Enable real email sending |
| `ADMIN_BOOTSTRAP_ENABLED` | `false` | `false` | Keep disabled unless you need to create an admin |
| `DEV_TLS_ENABLED` | `false` | `false` | TLS is handled by Cloudflare, not the container |

**Variables that should be the same or equivalent:**

- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — same GCP project, unless you create a separate beta OAuth client
- `ZAI_API_KEY` — reuse dev key or provision a separate key depending on usage/quota
- `SMTP_*` — same SMTP provider, sender address should be `noreply@uahapp.com`

### 2.2 Variables That Must Never Be Committed

The following variables must **never** appear in any committed file (including example files):

- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `SESSION_SECRET`
- `GOOGLE_CLIENT_SECRET`
- `ZAI_API_KEY`
- `SMTP_PASSWORD`
- `IPSTACK_API_KEY`
- `ADMIN_BOOTSTRAP_PASSWORD`

The `env-examples/beta/.env.example` file uses placeholder values for all of these.

---

## Part 3 — Beta Docker Compose Changes

### 3.1 Overview of Changes Needed

The existing `docker-compose.yml` is designed for the dev VPN deployment. For beta, the following changes are required:

| Change | Reason |
|--------|--------|
| Remove `./backend:/app` volume mount | Hot-reload source mount is a dev-only feature |
| Remove `--reload` from backend Dockerfile CMD (or override in compose) | Hot-reload should not run in production |
| Change `network_mode: "container:uah-dev-vpn"` | Beta uses Cloudflare, not a VPN container |
| Add `ports:` mapping for Nginx | With no VPN container, frontend needs a host port |
| Update container names to `uah-beta-*` | Avoids conflicts with dev containers on same host |
| Add `mem_limit` and `cpus` resource limits | Prevent resource exhaustion |
| Update `COMPOSE_PROJECT_NAME` to `uah-beta` | Consistent naming |

### 3.2 Beta-Specific Compose Behavior

For beta, the frontend container should **not** use `network_mode: "container:uah-dev-vpn"`. Instead, it should expose a port on the host (e.g., `80:80`) so that Cloudflare's reverse proxy can reach it. Cloudflare handles TLS termination, so the Nginx container only needs to serve HTTP on port 80. The origin firewall (iptables/ufw) ensures only Cloudflare IP ranges can reach that port.

See `CODE_CHANGES.md` for the exact compose diff.

### 3.3 Backend Dockerfile for Beta

The backend Dockerfile currently uses `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]`.

For beta, override this in `docker-compose.yml` using the `command:` key to remove `--reload`:

```yaml
backend:
  command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

Do not modify the `dev` Dockerfile directly — use the compose override so the dev environment is not affected.

### 3.4 Ports That Must Not Be Exposed

| Service | Port | Must expose? |
|---------|------|-------------|
| `db` (Postgres) | 5432 | ❌ Never — internal only |
| `backend` (FastAPI) | 8000 | ❌ Never — proxied by Nginx |
| `frontend` (Nginx) | 80 | ✅ Yes — to host, for Cloudflare proxy |
| `frontend` (Nginx) | 443 | ❌ No — TLS handled by Cloudflare |

The host machine's firewall (see `CLOUDFLARE_SECURITY.md`) must ensure that port 80 is only reachable from Cloudflare IP ranges.

---

## Part 4 — Branch Strategy

### 4.1 Beta Branch Rules

The `beta` branch does not exist yet. When the team is ready to create it, follow these steps:

1. Create `beta` from the current `dev` branch:
   ```
   git checkout dev
   git checkout -b beta
   git push origin beta
   ```

2. In GitHub repository settings → **Branches** → **Add branch protection rule**:
   - Branch name pattern: `beta`
   - ✅ **Require a pull request before merging**
   - ✅ **Require approvals** (at least 1)
   - ✅ **Restrict pushes that create matching branches** — allow only UAHTEAM
   - ✅ **Do not allow bypassing the above settings**

3. Only UAHTEAM members may push to `beta`. All changes must come via pull request from `dev`.

4. No direct commits to `beta` are permitted, even from team leads.

### 4.2 Merge Workflow

```
feature/* → dev (via PR)
dev → beta (via PR, reviewed by team lead)
beta → prod (via PR, full review + sign-off)
```

### 4.3 Keeping Beta in Sync with Dev

After each sprint, open a pull request from `dev` into `beta`. Code review should focus on:

- Any new endpoints being added to the unauthenticated list
- Any new environment-specific values being hardcoded
- Any dependency version changes

---

## Part 5 — Beta Deployment Steps (Checklist)

Follow these steps in order when deploying to beta for the first time.

### Pre-deployment

- [ ] Create the `beta` branch in GitHub and set branch protection rules (see §4.1)
- [ ] Provision the beta server host (separate VM or separate directory on the same host as dev)
- [ ] Create DNS record: `beta.uahapp.com → [origin server IP]`, proxied through Cloudflare (orange cloud)
- [ ] Configure Cloudflare Access policy for `beta.uahapp.com` (see `CLOUDFLARE_SECURITY.md`)
- [ ] Configure origin firewall to only accept traffic from Cloudflare IP ranges (see `CLOUDFLARE_SECURITY.md`)

### Environment Configuration

- [ ] Create `/srv/uah/environments/beta/` directory on the server
- [ ] Copy `env-examples/beta/.env.example` to `/srv/uah/environments/beta/.env` and fill in all secrets
- [ ] Verify `.env` file is not world-readable (`chmod 600 .env`)
- [ ] Confirm all required variables are set (none are empty)

### Docker Deployment

- [ ] Clone or copy the repository to the beta deployment directory
- [ ] Ensure the external `uah-infra` Docker network exists on the host (`docker network create uah-infra`)
- [ ] Run `docker compose up -d --build` from the beta deployment directory
- [ ] Verify all containers start without errors (`docker compose logs`)
- [ ] Verify the health check passes (`docker compose ps`)

### Verification

- [ ] Access `https://beta.uahapp.com` via Cloudflare Access (confirm gating works)
- [ ] Log in with a test account and confirm OAuth flow completes
- [ ] Confirm email sending works (trigger a verification or password reset)
- [ ] Confirm `/api/health` returns `{"status": "healthy"}`
- [ ] Confirm `/api/diagnostics` is **not** accessible (returns 404 or 401 depending on the fix applied)
- [ ] Confirm `/docs` and `/redoc` are **not** accessible
- [ ] Complete the full demo flow end-to-end

---

## Appendix: Beta Env Example Template

See the file at `env-examples/beta/.env.example` for the complete annotated environment variable template for the beta deployment.
