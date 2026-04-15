# Security Audit Guide

This guide covers the repository's script-based security audit workflow.

## Canonical Entrypoints

Primary router:

```bash
bash scripts/uah.sh <dev|beta|prod> audit [options]
```

Environment wrapper aliases:

```bash
bash scripts/dev/lifecycle/dev-audit.sh [options]
bash scripts/beta/lifecycle/beta-audit.sh [options]
```

Direct diagnostic scripts:

```bash
bash scripts/dev/diagnostic/dev-security-audit.sh [options]
bash scripts/beta/diagnostic/beta-security-audit.sh [options]
bash scripts/prod/prod-security-audit.sh [options]
```

`scripts/uah.sh` remains the source-of-truth interface.

## Options

```text
--env-file <path>     Override environment file path
--mode <mode>         full | repo | docker | host
--fix                 Enable limited remediations (default is read-only)
--fail-on-warn        Return non-zero when warnings exist
--json [path]         Write JSON report (optional custom output path)
-h, --help            Show usage help
```

## What The Audit Checks

### Repository / configuration checks

- env template coverage and drift
- placeholder / weak-secret detection
- compose rendering and compose hardening checks
- frontend build-safety checks
- backend dependency checks when `pip-audit` is available
- frontend and extension dependency checks when `npm audit` is available
- secret-scanning parity with `gitleaks` when available

### Runtime checks

- expected container presence and health
- exposed host ports
- privileged container / capability checks
- HTTP surface probes such as `/api/`, `/api/status`, `/api/diagnostics`, `/docs`, `/redoc`, and `/openapi.json`
- beta tunnel/container expectations

### Host checks

- firewall readability
- Docker user-chain hints
- environment-specific exposure warnings

## Interpreting Current Behavior

These expectations matter when reading audit results:

- `/api/status` is the lightweight public connectivity route.
- `/api/diagnostics` is admin-gated.
- generated docs routes are expected in local/dev-style environments but should be absent in beta-like environments where `ENVIRONMENT=beta`.
- beta currently uses a `cloudflared` tunnel container in the repo-managed compose override.

## Recommended Usage

Dev full audit:

```bash
bash scripts/uah.sh dev audit --mode full --json
```

Beta full audit with explicit env file:

```bash
bash scripts/uah.sh beta audit --env-file /srv/uah/environments/beta/.env --mode full --json
```

Host-layer checks where privilege is needed:

```bash
sudo bash scripts/uah.sh beta audit --mode host --json
```

## Exit Codes

- `0`: pass, or warning-only when `--fail-on-warn` is not set
- `1`: warning-only with `--fail-on-warn`
- `2`: one or more failed checks

## Notes

- The default audit mode is read-only.
- Some checks degrade to warnings when required tools are not installed.
- The audit can confirm a large amount of repo-managed posture, but operator-managed Cloudflare Access/WAF configuration still requires manual review.
