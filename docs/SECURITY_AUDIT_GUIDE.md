# Security Audit Guide

This guide covers the new comprehensive security audit workflow integrated into the scripts stack.

## Entrypoints

Unified router:

```bash
bash scripts/uah.sh <dev|beta|prod> audit [options]
```

Environment-specific wrappers:

```bash
bash scripts/dev/lifecycle/dev-audit.sh [options]
bash scripts/beta/lifecycle/beta-audit.sh [options]
```

Wrappers are stable aliases; `scripts/uah.sh` remains the canonical audit interface.
Audit options are also listed in `bash scripts/uah.sh --help`.

Direct environment scripts:

```bash
bash scripts/dev/diagnostic/dev-security-audit.sh [options]
bash scripts/beta/diagnostic/beta-security-audit.sh [options]
bash scripts/prod/prod-security-audit.sh [options]
```

## Options

```text
--env-file <path>     Override environment file path
--mode <mode>         full | repo | docker | host
--fix                 Enable limited remediations (default is read-only)
--fail-on-warn        Return non-zero when warnings exist
--json [path]         Write JSON report (optional custom output path)
-h, --help            Show usage help
```

## Modes

- `full`: run repository, dependency, runtime, and host firewall checks.
- `repo`: run repository and dependency checks only.
- `docker`: run repository/dependency checks plus runtime container checks.
- `host`: run repository/dependency checks plus host firewall checks.

## Check Coverage

Repository/build checks:

- Beta-aware environment validation aligned with `config.py`, compose, and env templates.
- Conditional OAuth, Gmail, SMTP, queue, and local pipeline validation.
- Secret quality and placeholder detection.
- Environment file permission checks.
- Env example drift detection via `.github/scripts/check_env_sync.py`.
- Compose render and compose hardening checks.
- Frontend nginx header / HSTS / TLS-entrypoint static checks.
- Frontend production-build safety checks (including Vue devtools gating).
- Secret scanning parity with `gitleaks` when available.
- Backend dependency vulnerability checks (`pip-audit` when available).
- Frontend dependency vulnerability checks (`npm audit` when available).
- Browser extension dependency vulnerability checks (`npm audit` when a lockfile is present).

Runtime checks:

- Expected container presence by environment.
- Container health state checks.
- Privileged container and capability checks.
- Host port exposure checks for backend/db/frontend/redis.
- HTTP surface probes (`/api/`, `/api/diagnostics`, `/docs`, `/redoc`, `/openapi.json`).
- Beta cloudflared runtime check.
- Optional image vulnerability checks (`trivy` when available).
- Beta manual-controls reminders for Cloudflare and other operator-managed hardening that the repo cannot prove automatically.

Host firewall checks:

- iptables rules readability and DOCKER-USER chain presence.
- beta-focused DOCKER-USER rule presence hints.
- UFW status checks and beta-origin exposure warnings.

## Exit Codes

- `0`: pass, or warning-only when `--fail-on-warn` is not set.
- `1`: warning-only with `--fail-on-warn`.
- `2`: one or more failed checks.

## JSON Reports

If `--json` is supplied without a path, output is written to:

```text
logs/security-audit/<env>-audit-<timestamp>.json
```

## Recommended Workflows

Dev full audit:

```bash
bash scripts/uah.sh dev audit --mode full --json
```

Beta full audit with explicit env file:

```bash
bash scripts/uah.sh beta audit --env-file /srv/uah/environments/beta/.env --mode full --json
```

Host firewall only (with sudo where required):

```bash
sudo bash scripts/uah.sh beta audit --mode host --json
```

Read-only baseline plus optional remediation pass:

```bash
bash scripts/uah.sh dev audit --mode full --json
bash scripts/uah.sh dev audit --mode full --fix --json
```

## Notes

- The default behavior is read-only.
- Some checks are skipped or downgraded to warnings when tools are unavailable (`pip-audit`, `npm`, `trivy`, `gitleaks`, `iptables`, `ufw`) or when privilege is insufficient.
- Beta manual-controls findings are warnings by default because they require operator verification outside the repo.
- In this repository, beta is modeled explicitly as `ENVIRONMENT=beta` / `ENV=beta`; the audit no longer assumes beta should masquerade as `production`.
- If you run the audit from a Windows workstation, prefer CI or a real bash-capable environment for final verification when local bash integration is unreliable.
