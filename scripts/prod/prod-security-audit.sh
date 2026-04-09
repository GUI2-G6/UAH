#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

AUDIT_ENV="prod"
AUDIT_ROOT_DIR="$ROOT_DIR"
AUDIT_ENV_FILE="${UAH_ENV_FILE:-$ROOT_DIR/.env}"
AUDIT_MODE="repo"
AUDIT_FIX=false
AUDIT_FAIL_ON_WARN=false
AUDIT_JSON_PATH=""
AUDIT_COMPOSE_FILES=(
  "$ROOT_DIR/docker-compose.yml"
)

source "$ROOT_DIR/scripts/lib/security-audit-common.sh"

_audit_parse_args "$@"

if [[ "$AUDIT_MODE" != "repo" ]]; then
  echo "[INFO] prod scaffold audit runs in repo mode only; overriding requested mode '$AUDIT_MODE'."
  AUDIT_MODE="repo"
fi

if [[ "$AUDIT_FIX" == "true" ]]; then
  echo "[INFO] prod scaffold audit is read-only; ignoring --fix."
  AUDIT_FIX=false
fi

audit_run
