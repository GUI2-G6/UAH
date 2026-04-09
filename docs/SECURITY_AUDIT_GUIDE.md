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

- Required environment variable presence.
- Queue and local pipeline environment consistency.
- Secret quality and placeholder detection.
- Environment file permission checks.
- Compose render and compose hardening checks.
- Backend dependency vulnerability checks (`pip-audit` when available).
- Frontend dependency vulnerability checks (`npm audit` when available).

Runtime checks:

- Expected container presence by environment.
- Container health state checks.
- Privileged container and capability checks.
- Host port exposure checks for backend/db/frontend/redis.
- HTTP surface probes (`/api/`, `/api/diagnostics`, `/docs`, `/openapi.json`).
- Beta cloudflared runtime check.
- Optional image vulnerability checks (`trivy` when available).

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
- Some checks are skipped or downgraded to warnings when tools are unavailable (`pip-audit`, `npm`, `trivy`, `iptables`, `ufw`) or when privilege is insufficient.
- For beta deployments, treat warnings around docs/diagnostics endpoint exposure as release blockers unless explicitly accepted.
