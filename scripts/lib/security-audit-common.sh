#!/usr/bin/env bash
# shellcheck shell=bash

# Shared security audit helpers for UAH operations scripts.
# This file is sourced by environment-specific audit entrypoints.

AUDIT_RESULTS=()
AUDIT_SECTION="general"
AUDIT_PASS_COUNT=0
AUDIT_WARN_COUNT=0
AUDIT_FAIL_COUNT=0
AUDIT_SKIP_COUNT=0
AUDIT_INFO_COUNT=0

: "${AUDIT_ENV:=dev}"
: "${AUDIT_ROOT_DIR:=}"
: "${AUDIT_ENV_FILE:=}"
: "${AUDIT_MODE:=full}"
: "${AUDIT_FIX:=false}"
: "${AUDIT_FAIL_ON_WARN:=false}"
: "${AUDIT_JSON_PATH:=}"
: "${AUDIT_COMPOSE_FILES:=}"

AUDIT_START_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
AUDIT_COMPOSE_CMD=()

_audit_usage() {
  cat <<'USAGE'
Usage: <env>-security-audit.sh [options]

Options:
  --env-file <path>     Override environment file path
  --mode <mode>         full | repo | docker | host
  --fix                 Enable limited remediations (default: read-only)
  --fail-on-warn        Return non-zero when warnings exist
  --json [path]         Write JSON report (optional custom output path)
  -h, --help            Show this help
USAGE
}

_audit_has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

_audit_capture() {
  local __outvar="$1"
  shift

  local _out
  local _rc

  set +e
  _out="$("$@" 2>&1)"
  _rc=$?
  set -e

  printf -v "$__outvar" "%s" "$_out"
  return "$_rc"
}

_audit_capture_privileged() {
  local __outvar="$1"
  shift

  local _out
  if _audit_capture _out "$@"; then
    printf -v "$__outvar" "%s" "$_out"
    return 0
  fi

  if _audit_has_cmd sudo; then
    if sudo -n true >/dev/null 2>&1; then
      if _audit_capture _out sudo -n "$@"; then
        printf -v "$__outvar" "%s" "$_out"
        return 0
      fi
    fi
  fi

  return 1
}

_audit_clean_field() {
  local value="$1"
  value="${value//$'\n'/; }"
  value="${value//$'\r'/}"
  value="${value//|//}"
  printf "%s" "$value"
}

_audit_set_section() {
  AUDIT_SECTION="$1"
}

_audit_add_result() {
  local severity="$1"
  local check_id="$2"
  local message="$3"
  local details="${4:-}"
  local remediation="${5:-}"

  case "$severity" in
    pass) AUDIT_PASS_COUNT=$((AUDIT_PASS_COUNT + 1)) ;;
    warn) AUDIT_WARN_COUNT=$((AUDIT_WARN_COUNT + 1)) ;;
    fail) AUDIT_FAIL_COUNT=$((AUDIT_FAIL_COUNT + 1)) ;;
    skip) AUDIT_SKIP_COUNT=$((AUDIT_SKIP_COUNT + 1)) ;;
    info) AUDIT_INFO_COUNT=$((AUDIT_INFO_COUNT + 1)) ;;
    *) severity="info"; AUDIT_INFO_COUNT=$((AUDIT_INFO_COUNT + 1)) ;;
  esac

  AUDIT_RESULTS+=(
    "${AUDIT_SECTION}|${severity}|$(_audit_clean_field "$check_id")|$(_audit_clean_field "$message")|$(_audit_clean_field "$details")|$(_audit_clean_field "$remediation")"
  )
}

_audit_env_value() {
  local key="$1"
  local file="$2"
  local line
  local value

  if [[ ! -f "$file" ]]; then
    return 1
  fi

  line="$(grep -E "^[[:space:]]*${key}=" "$file" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    return 1
  fi

  value="${line#*=}"
  value="${value#${value%%[![:space:]]*}}"
  value="${value%${value##*[![:space:]]}}"

  if [[ "${#value}" -ge 2 ]]; then
    if [[ "${value:0:1}" == '"' && "${value: -1}" == '"' ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "${value:0:1}" == "'" && "${value: -1}" == "'" ]]; then
      value="${value:1:${#value}-2}"
    fi
  fi

  printf "%s" "$value"
}

_audit_env_is_true() {
  local file="$1"
  local key="$2"
  local value

  value="$(_audit_env_value "$key" "$file" 2>/dev/null || true)"
  value="${value,,}"
  [[ "$value" == "1" || "$value" == "true" || "$value" == "yes" || "$value" == "on" ]]
}

_audit_is_placeholder_value() {
  local value="${1,,}"
  [[ "$value" == "" ]] && return 0

  case "$value" in
    *placeholder*|*changeme*|*change-me*|*example*|*your_*|*todo*|*replace_me*|*replace-this*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

_audit_mode_allows_docker() {
  [[ "$AUDIT_MODE" == "full" || "$AUDIT_MODE" == "docker" ]]
}

_audit_mode_allows_host() {
  [[ "$AUDIT_MODE" == "full" || "$AUDIT_MODE" == "host" ]]
}

_audit_mode_valid() {
  case "$AUDIT_MODE" in
    full|repo|docker|host) return 0 ;;
    *) return 1 ;;
  esac
}

_audit_parse_args() {
  while (($#)); do
    case "$1" in
      --env-file)
        AUDIT_ENV_FILE="${2:-}"
        if [[ -z "$AUDIT_ENV_FILE" ]]; then
          echo "Missing value for --env-file" >&2
          exit 1
        fi
        shift 2
        ;;
      --mode)
        AUDIT_MODE="${2:-}"
        if [[ -z "$AUDIT_MODE" ]]; then
          echo "Missing value for --mode" >&2
          exit 1
        fi
        shift 2
        ;;
      --fix)
        AUDIT_FIX=true
        shift
        ;;
      --fail-on-warn)
        AUDIT_FAIL_ON_WARN=true
        shift
        ;;
      --json)
        if (($# > 1)) && [[ "$2" != --* ]]; then
          AUDIT_JSON_PATH="$2"
          shift 2
        else
          AUDIT_JSON_PATH="__AUTO__"
          shift
        fi
        ;;
      -h|--help)
        _audit_usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        _audit_usage
        exit 1
        ;;
    esac
  done
}

_audit_build_compose_cmd() {
  AUDIT_COMPOSE_CMD=(docker compose --env-file "$AUDIT_ENV_FILE")
  local file
  for file in "${AUDIT_COMPOSE_FILES[@]}"; do
    AUDIT_COMPOSE_CMD+=(-f "$file")
  done
}

_audit_init() {
  if [[ -z "$AUDIT_ROOT_DIR" ]]; then
    echo "AUDIT_ROOT_DIR must be set by the environment wrapper script." >&2
    exit 1
  fi

  if [[ -z "$AUDIT_ENV_FILE" ]]; then
    AUDIT_ENV_FILE="$AUDIT_ROOT_DIR/.env"
  fi

  if ! _audit_mode_valid; then
    echo "Invalid mode '$AUDIT_MODE'. Use full, repo, docker, or host." >&2
    exit 1
  fi

  if [[ "$AUDIT_JSON_PATH" == "__AUTO__" ]]; then
    AUDIT_JSON_PATH="$AUDIT_ROOT_DIR/logs/security-audit/${AUDIT_ENV}-audit-$(date -u +%Y%m%d-%H%M%S).json"
  fi

  if [[ -n "$AUDIT_JSON_PATH" ]]; then
    mkdir -p "$(dirname "$AUDIT_JSON_PATH")"
  fi

  _audit_build_compose_cmd
}

_audit_check_env_file() {
  _audit_set_section "environment"

  if [[ -f "$AUDIT_ENV_FILE" ]]; then
    _audit_add_result pass env_file_present "Environment file is present." "$AUDIT_ENV_FILE"
    return
  fi

  _audit_add_result fail env_file_missing "Environment file is missing." "$AUDIT_ENV_FILE" "Create the file or pass --env-file <path>."
}

_audit_check_required_env_vars() {
  _audit_set_section "environment"

  if [[ ! -f "$AUDIT_ENV_FILE" ]]; then
    _audit_add_result skip env_required_skipped "Required variable checks skipped." "Env file missing: $AUDIT_ENV_FILE"
    return
  fi

  local required_vars=(
    POSTGRES_PASSWORD
    SECRET_KEY
    SESSION_SECRET
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GOOGLE_REDIRECT_URI
    MUSE_API_KEY
    GMAIL_CLIENT_ID
    GMAIL_CLIENT_SECRET
    GMAIL_REDIRECT_URI
    ZAI_API_KEY
    ZAI_OCR_URL
    ZAI_LLM_URL
    ZAI_LLM_MODEL
  )

  local missing=()
  local key
  for key in "${required_vars[@]}"; do
    if [[ -z "$(_audit_env_value "$key" "$AUDIT_ENV_FILE" 2>/dev/null || true)" ]]; then
      missing+=("$key")
    fi
  done

  if [[ "$AUDIT_ENV" == "beta" ]]; then
    if [[ -z "$(_audit_env_value "CLOUDFLARE_BETA_TUNNEL_TOKEN" "$AUDIT_ENV_FILE" 2>/dev/null || true)" ]]; then
      missing+=("CLOUDFLARE_BETA_TUNNEL_TOKEN")
    fi
  fi

  if ((${#missing[@]} == 0)); then
    _audit_add_result pass env_required_present "All required environment variables are set."
  else
    _audit_add_result fail env_required_missing "Required environment variables are missing." "${missing[*]}" "Populate missing keys in the environment file."
  fi

  if _audit_env_is_true "$AUDIT_ENV_FILE" "REDIS_ENABLED"; then
    local redis_required=(
      REDIS_URL
      PARSE_QUEUE_NAME
      PARSE_QUEUE_NAME_CLOUD
      PARSE_QUEUE_NAME_LOCAL
      PARSE_QUEUE_NAME_RULES
    )
    local redis_missing=()
    for key in "${redis_required[@]}"; do
      if [[ -z "$(_audit_env_value "$key" "$AUDIT_ENV_FILE" 2>/dev/null || true)" ]]; then
        redis_missing+=("$key")
      fi
    done

    if ((${#redis_missing[@]} == 0)); then
      _audit_add_result pass env_redis_required "Redis queue variables are complete."
    else
      _audit_add_result fail env_redis_missing "Redis queue variables are missing while REDIS_ENABLED=true." "${redis_missing[*]}" "Set missing queue variables."
    fi

    local redis_recommended=(
      PARSE_QUEUE_MAX_RETRIES
      PARSE_QUEUE_MAX_RETRIES_CLOUD
      PARSE_QUEUE_MAX_RETRIES_LOCAL
      PARSE_QUEUE_MAX_RETRIES_RULES
      PARSE_QUEUE_CONCURRENCY_CLOUD
      PARSE_QUEUE_CONCURRENCY_LOCAL
      PARSE_QUEUE_CONCURRENCY_RULES
      PARSE_QUEUE_CLAIM_TTL_SECONDS
      PARSE_QUEUE_SHUTDOWN_DRAIN_SECONDS
      PARSE_QUEUE_STALE_JOB_MINUTES
    )
    local redis_recommended_missing=()
    for key in "${redis_recommended[@]}"; do
      if [[ -z "$(_audit_env_value "$key" "$AUDIT_ENV_FILE" 2>/dev/null || true)" ]]; then
        redis_recommended_missing+=("$key")
      fi
    done

    if ((${#redis_recommended_missing[@]} == 0)); then
      _audit_add_result pass env_redis_recommended "Recommended Redis queue controls are present."
    else
      _audit_add_result warn env_redis_recommended_missing "Some recommended Redis queue controls are missing." "${redis_recommended_missing[*]}"
    fi
  fi

  if _audit_env_is_true "$AUDIT_ENV_FILE" "USE_LOCAL_PIPELINE"; then
    local local_required=(LOCAL_OCR_URL LOCAL_OCR_MODEL LOCAL_LLM_URL LOCAL_LLM_MODEL)
    local local_missing=()
    for key in "${local_required[@]}"; do
      if [[ -z "$(_audit_env_value "$key" "$AUDIT_ENV_FILE" 2>/dev/null || true)" ]]; then
        local_missing+=("$key")
      fi
    done

    if ((${#local_missing[@]} == 0)); then
      _audit_add_result pass env_local_pipeline "Local pipeline variables are complete when USE_LOCAL_PIPELINE=true."
    else
      _audit_add_result fail env_local_pipeline_missing "Local pipeline variables are missing while USE_LOCAL_PIPELINE=true." "${local_missing[*]}"
    fi
  fi

  local deprecated=(API_PORT API_HOST VUE_PORT ADMIN_BYPASS_PASSPHRASE)
  local deprecated_found=()
  for key in "${deprecated[@]}"; do
    if grep -Eq "^[[:space:]]*${key}=" "$AUDIT_ENV_FILE"; then
      deprecated_found+=("$key")
    fi
  done

  if ((${#deprecated_found[@]} == 0)); then
    _audit_add_result pass env_deprecated_absent "Deprecated environment keys are absent."
  else
    _audit_add_result warn env_deprecated_present "Deprecated environment keys are present." "${deprecated_found[*]}" "Remove deprecated keys from env files."
  fi
}

_audit_check_secret_quality() {
  _audit_set_section "secrets"

  if [[ ! -f "$AUDIT_ENV_FILE" ]]; then
    _audit_add_result skip secret_quality_skipped "Secret quality checks skipped." "Env file missing"
    return
  fi

  local secret_key
  local session_secret
  local postgres_password

  secret_key="$(_audit_env_value "SECRET_KEY" "$AUDIT_ENV_FILE" 2>/dev/null || true)"
  session_secret="$(_audit_env_value "SESSION_SECRET" "$AUDIT_ENV_FILE" 2>/dev/null || true)"
  postgres_password="$(_audit_env_value "POSTGRES_PASSWORD" "$AUDIT_ENV_FILE" 2>/dev/null || true)"

  if [[ -z "$secret_key" || ${#secret_key} -lt 32 ]] || _audit_is_placeholder_value "$secret_key"; then
    _audit_add_result fail secret_key_strength "SECRET_KEY is weak, missing, or placeholder-like." "length=${#secret_key}"
  else
    _audit_add_result pass secret_key_strength "SECRET_KEY meets baseline quality checks." "length=${#secret_key}"
  fi

  if [[ -z "$session_secret" || ${#session_secret} -lt 32 ]] || _audit_is_placeholder_value "$session_secret"; then
    _audit_add_result fail session_secret_strength "SESSION_SECRET is weak, missing, or placeholder-like." "length=${#session_secret}"
  else
    _audit_add_result pass session_secret_strength "SESSION_SECRET meets baseline quality checks." "length=${#session_secret}"
  fi

  if [[ -z "$postgres_password" || ${#postgres_password} -lt 16 ]] || _audit_is_placeholder_value "$postgres_password"; then
    _audit_add_result warn postgres_password_strength "POSTGRES_PASSWORD appears weak, missing, or placeholder-like." "length=${#postgres_password}" "Use a longer random value."
  else
    _audit_add_result pass postgres_password_strength "POSTGRES_PASSWORD meets baseline quality checks." "length=${#postgres_password}"
  fi

  if [[ -n "$secret_key" && -n "$session_secret" && "$secret_key" == "$session_secret" ]]; then
    _audit_add_result fail secret_reuse "SECRET_KEY and SESSION_SECRET should not match."
  else
    _audit_add_result pass secret_reuse "SECRET_KEY and SESSION_SECRET are distinct."
  fi

  if [[ "$AUDIT_ENV" == "beta" ]]; then
    local admin_bootstrap
    admin_bootstrap="$(_audit_env_value "ADMIN_BOOTSTRAP_ENABLED" "$AUDIT_ENV_FILE" 2>/dev/null || true)"
    admin_bootstrap="${admin_bootstrap,,}"
    if [[ "$admin_bootstrap" == "true" || "$admin_bootstrap" == "1" || "$admin_bootstrap" == "yes" ]]; then
      _audit_add_result warn admin_bootstrap_beta "ADMIN_BOOTSTRAP_ENABLED is true in beta." "This can be valid temporarily but should be disabled after bootstrap." "Set ADMIN_BOOTSTRAP_ENABLED=false after admin setup."
    else
      _audit_add_result pass admin_bootstrap_beta "ADMIN_BOOTSTRAP_ENABLED is disabled for beta."
    fi
  fi
}

_audit_check_env_permissions() {
  _audit_set_section "permissions"

  if [[ ! -f "$AUDIT_ENV_FILE" ]]; then
    _audit_add_result skip env_permission_skipped "Env file permission check skipped." "Env file missing"
    return
  fi

  if ! _audit_has_cmd stat; then
    _audit_add_result skip env_permission_stat_missing "stat command unavailable; skipping permission check."
    return
  fi

  local mode
  mode="$(stat -c "%a" "$AUDIT_ENV_FILE" 2>/dev/null || true)"

  if [[ -z "$mode" ]]; then
    _audit_add_result warn env_permission_unknown "Could not read env file mode." "$AUDIT_ENV_FILE"
    return
  fi

  if [[ "$mode" == "600" || "$mode" == "640" ]]; then
    _audit_add_result pass env_permission_mode "Env file permission mode is acceptable." "$AUDIT_ENV_FILE mode=$mode"
    return
  fi

  if [[ "$AUDIT_FIX" == "true" ]]; then
    if chmod 600 "$AUDIT_ENV_FILE" 2>/dev/null; then
      _audit_add_result warn env_permission_fixed "Env file permissions were tightened via --fix." "old_mode=$mode new_mode=600"
      return
    fi
  fi

  _audit_add_result warn env_permission_mode "Env file mode is broader than recommended." "$AUDIT_ENV_FILE mode=$mode" "Use chmod 600 on env files."
}

_audit_check_compose_files_and_render() {
  _audit_set_section "compose"

  local file
  local missing_files=()
  for file in "${AUDIT_COMPOSE_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
      missing_files+=("$file")
    fi
  done

  if ((${#missing_files[@]} > 0)); then
    _audit_add_result fail compose_files_missing "One or more compose files are missing." "${missing_files[*]}"
    return
  fi

  _audit_add_result pass compose_files_present "Compose files are present." "${AUDIT_COMPOSE_FILES[*]}"

  if ! _audit_has_cmd docker; then
    _audit_add_result warn compose_render_skipped "Docker CLI unavailable; compose render skipped."
    return
  fi

  local output
  if _audit_capture output "${AUDIT_COMPOSE_CMD[@]}" config; then
    _audit_add_result pass compose_render "Compose render succeeded." "docker compose config"
  else
    _audit_add_result fail compose_render "Compose render failed." "$output" "Run docker compose config and resolve parser/env issues."
  fi
}

_audit_check_compose_hardening() {
  _audit_set_section "compose"

  local latest_images=()
  local file
  for file in "${AUDIT_COMPOSE_FILES[@]}"; do
    while IFS= read -r line; do
      latest_images+=("$line")
    done < <(grep -nE "^[[:space:]]*image:[[:space:]]*[^[:space:]]+:latest[[:space:]]*$" "$file" || true)
  done

  if ((${#latest_images[@]} == 0)); then
    _audit_add_result pass compose_image_tags "No compose image uses :latest."
  else
    _audit_add_result warn compose_image_tags "Compose file contains :latest image tags." "${latest_images[*]}" "Pin versions for reproducible builds."
  fi

  local dev_compose="${AUDIT_COMPOSE_FILES[0]}"
  if grep -Eq "^[[:space:]]*command:[[:space:]].*--reload" "$dev_compose"; then
    _audit_add_result fail compose_reload_flag "Backend appears to use --reload in compose command." "Do not run reload in beta/prod-like environments."
  else
    _audit_add_result pass compose_reload_flag "No explicit --reload flag found in compose files."
  fi

  if [[ "$AUDIT_ENV" == "beta" ]]; then
    local beta_compose="${AUDIT_COMPOSE_FILES[1]:-}"
    if [[ -n "$beta_compose" && -f "$beta_compose" ]]; then
      if grep -Eq "^[[:space:]]*-[[:space:]]*\./backend:/app" "$beta_compose"; then
        _audit_add_result warn beta_source_mount "Beta backend uses source mount ./backend:/app." "This increases mutable runtime surface." "Prefer immutable image-only deployment for beta/prod."
      else
        _audit_add_result pass beta_source_mount "Beta backend source mount override is absent."
      fi

      if grep -Eq "^[[:space:]]*-[[:space:]]*\./volumes/postgres:/var/lib/postgresql/data" "$beta_compose"; then
        _audit_add_result warn beta_db_volume_overlap "Beta DB volume path matches dev pattern (./volumes/postgres)." "Concurrent stacks may share state if run from same checkout." "Use a beta-specific DB volume path."
      else
        _audit_add_result pass beta_db_volume_overlap "Beta DB volume path does not match default dev path."
      fi
    fi
  fi
}

_audit_check_dependency_vulnerabilities() {
  _audit_set_section "dependencies"

  local backend_req="$AUDIT_ROOT_DIR/backend/requirements.txt"
  local frontend_dir="$AUDIT_ROOT_DIR/frontend"

  if [[ -f "$backend_req" ]]; then
    if _audit_has_cmd pip-audit; then
      local pip_json
      local pip_err
      local pip_rc
      local pip_count

      pip_json="$(mktemp)"
      pip_err="$(mktemp)"

      set +e
      pip-audit -r "$backend_req" --format json >"$pip_json" 2>"$pip_err"
      pip_rc=$?
      set -e

      if _audit_has_cmd python3; then
        pip_count="$(python3 - "$pip_json" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    print("parse_error")
    raise SystemExit(0)

deps = []
if isinstance(data, list):
    deps = data
elif isinstance(data, dict):
    deps = data.get("dependencies") or []

count = 0
for dep in deps:
    vulns = dep.get("vulns") or dep.get("vulnerabilities") or []
    count += len(vulns)
print(count)
PY
        )"
      else
        pip_count="parse_error"
      fi

      if [[ "$pip_count" =~ ^[0-9]+$ ]]; then
        if [[ "$pip_count" -gt 0 ]]; then
          _audit_add_result fail backend_dep_vulns "pip-audit found backend vulnerabilities." "count=$pip_count" "Upgrade or pin patched backend dependencies."
        else
          _audit_add_result pass backend_dep_vulns "pip-audit found no backend vulnerabilities."
        fi
      else
        local pip_err_head
        pip_err_head="$(head -n 5 "$pip_err" | tr '\n' '; ')"
        _audit_add_result warn backend_dep_vulns_parse "Could not parse pip-audit JSON output." "rc=$pip_rc err=$pip_err_head"
      fi

      rm -f "$pip_json" "$pip_err"
    else
      if grep -Eq '^python-jose==3\.3\.0$' "$backend_req"; then
        _audit_add_result warn backend_dep_known_cve "python-jose==3.3.0 is present and has known advisories." "Install pip-audit to get complete vulnerability coverage." "Upgrade python-jose to a patched version."
      else
        _audit_add_result warn backend_dep_scan_skipped "pip-audit is not installed; backend vulnerability scan skipped."
      fi
    fi
  else
    _audit_add_result warn backend_req_missing "backend/requirements.txt not found; backend dependency audit skipped."
  fi

  if [[ -f "$frontend_dir/package-lock.json" ]]; then
    if _audit_has_cmd npm; then
      local npm_json
      local npm_err
      local npm_rc
      local npm_counts

      npm_json="$(mktemp)"
      npm_err="$(mktemp)"

      set +e
      npm audit --prefix "$frontend_dir" --json --audit-level=high --package-lock-only >"$npm_json" 2>"$npm_err"
      npm_rc=$?
      set -e

      if _audit_has_cmd python3; then
        npm_counts="$(python3 - "$npm_json" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    print("parse_error")
    raise SystemExit(0)

meta = data.get("metadata", {}).get("vulnerabilities", {})
high = int(meta.get("high", 0) or 0)
critical = int(meta.get("critical", 0) or 0)
print(f"{high}|{critical}")
PY
        )"
      else
        npm_counts="parse_error"
      fi

      if [[ "$npm_counts" =~ ^[0-9]+\|[0-9]+$ ]]; then
        local high_count="${npm_counts%%|*}"
        local critical_count="${npm_counts##*|}"
        if [[ "$high_count" -gt 0 || "$critical_count" -gt 0 ]]; then
          _audit_add_result fail frontend_dep_vulns "npm audit found high or critical vulnerabilities." "high=$high_count critical=$critical_count" "Patch or pin frontend dependencies."
        else
          _audit_add_result pass frontend_dep_vulns "npm audit found no high/critical vulnerabilities."
        fi
      else
        local npm_err_head
        npm_err_head="$(head -n 5 "$npm_err" | tr '\n' '; ')"
        _audit_add_result warn frontend_dep_vulns_parse "Could not parse npm audit JSON output." "rc=$npm_rc err=$npm_err_head"
      fi

      rm -f "$npm_json" "$npm_err"
    else
      _audit_add_result warn frontend_dep_scan_skipped "npm is not installed; frontend vulnerability scan skipped."
    fi
  else
    _audit_add_result warn frontend_lock_missing "frontend/package-lock.json not found; frontend dependency audit skipped."
  fi
}

_audit_check_runtime_containers() {
  _audit_set_section "runtime"

  if ! _audit_mode_allows_docker; then
    _audit_add_result skip runtime_container_skipped "Runtime container checks skipped by mode." "mode=$AUDIT_MODE"
    return
  fi

  if ! _audit_has_cmd docker; then
    _audit_add_result warn runtime_docker_missing "Docker CLI unavailable; runtime checks skipped."
    return
  fi

  local docker_info
  if ! _audit_capture docker_info docker info; then
    _audit_add_result warn runtime_docker_unavailable "Docker daemon unavailable; runtime checks skipped." "$docker_info"
    return
  fi

  local expected=()
  if [[ "$AUDIT_ENV" == "dev" ]]; then
    expected=(uah-dev-db uah-dev-backend uah-dev-frontend uah-redis uah-dev-vpn)
  elif [[ "$AUDIT_ENV" == "beta" ]]; then
    expected=(uah-beta-db uah-beta-backend uah-beta-frontend uah-beta-redis uah-beta-cloudflared)
  else
    expected=(uah-prod-db uah-prod-backend uah-prod-frontend)
  fi

  local running
  running="$(docker ps --format '{{.Names}}')"

  local missing=()
  local name
  for name in "${expected[@]}"; do
    if ! grep -Fxq "$name" <<< "$running"; then
      missing+=("$name")
      continue
    fi

    local health
    health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || true)"
    case "$health" in
      healthy|none)
        ;;
      starting)
        _audit_add_result warn runtime_health_starting "Container health is still starting." "$name"
        ;;
      unhealthy)
        _audit_add_result fail runtime_health_unhealthy "Container health is unhealthy." "$name"
        ;;
      *)
        _audit_add_result info runtime_health_unknown "Container health status unavailable." "$name status=$health"
        ;;
    esac

    local privileged
    privileged="$(docker inspect -f '{{.HostConfig.Privileged}}' "$name" 2>/dev/null || true)"
    if [[ "$privileged" == "true" ]]; then
      _audit_add_result fail runtime_privileged "Container runs in privileged mode." "$name" "Run containers without privileged mode."
    fi

    local cap_add
    cap_add="$(docker inspect -f '{{json .HostConfig.CapAdd}}' "$name" 2>/dev/null || true)"
    if [[ "$cap_add" != "null" && "$cap_add" != "[]" && "$name" != "uah-dev-vpn" ]]; then
      _audit_add_result warn runtime_cap_add "Container has additional Linux capabilities." "$name cap_add=$cap_add"
    fi

    local user_value
    user_value="$(docker inspect -f '{{.Config.User}}' "$name" 2>/dev/null || true)"
    if [[ "$name" == *"backend" || "$name" == *"frontend" ]]; then
      if [[ -z "$user_value" || "$user_value" == "root" || "$user_value" == "0" || "$user_value" == "0:0" ]]; then
        _audit_add_result warn runtime_user_root "Application container appears to run as root." "$name user=$user_value" "Use a non-root user in Dockerfile when possible."
      fi
    fi
  done

  if ((${#missing[@]} == 0)); then
    _audit_add_result pass runtime_expected_containers "Expected containers are running for this environment." "env=$AUDIT_ENV"
  else
    _audit_add_result fail runtime_missing_containers "Expected containers are not running." "${missing[*]}" "Start missing services before production use."
  fi
}

_audit_check_runtime_ports() {
  _audit_set_section "runtime"

  if ! _audit_mode_allows_docker; then
    _audit_add_result skip runtime_ports_skipped "Runtime port checks skipped by mode." "mode=$AUDIT_MODE"
    return
  fi

  if ! _audit_has_cmd docker; then
    _audit_add_result warn runtime_ports_docker_missing "Docker CLI unavailable; runtime port checks skipped."
    return
  fi

  local port_map
  if ! _audit_capture port_map docker ps --format '{{.Names}}|{{.Ports}}'; then
    _audit_add_result warn runtime_ports_unavailable "Unable to enumerate running container ports."
    return
  fi

  local public_exposure=()
  local redis_exposure_warn=()

  local line
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    local name="${line%%|*}"
    local ports="${line#*|}"

    if [[ "$AUDIT_ENV" == "dev" ]]; then
      if [[ "$name" == "uah-dev-backend" || "$name" == "uah-dev-db" || "$name" == "uah-dev-frontend" ]]; then
        if [[ "$ports" == *"0.0.0.0"* || "$ports" == *"[::]"* ]]; then
          public_exposure+=("$name:$ports")
        fi
      fi
      if [[ "$name" == "uah-redis" ]]; then
        if [[ "$ports" == *"0.0.0.0"* || "$ports" == *"[::]"* ]]; then
          redis_exposure_warn+=("$name:$ports")
        fi
      fi
    fi

    if [[ "$AUDIT_ENV" == "beta" ]]; then
      if [[ "$name" == "uah-beta-backend" || "$name" == "uah-beta-db" || "$name" == "uah-beta-frontend" ]]; then
        if [[ "$ports" == *"0.0.0.0"* || "$ports" == *"[::]"* ]]; then
          public_exposure+=("$name:$ports")
        fi
      fi
      if [[ "$name" == "uah-beta-redis" ]]; then
        if [[ "$ports" == *"0.0.0.0"* || "$ports" == *"[::]"* ]]; then
          redis_exposure_warn+=("$name:$ports")
        fi
      fi
    fi
  done <<< "$port_map"

  if ((${#public_exposure[@]} == 0)); then
    _audit_add_result pass runtime_public_ports "No unexpected public host port exposure for core app services."
  else
    _audit_add_result fail runtime_public_ports "Unexpected public host port exposure detected." "${public_exposure[*]}" "Bind services to localhost or internal networks only."
  fi

  if ((${#redis_exposure_warn[@]} == 0)); then
    _audit_add_result pass runtime_redis_bind "Redis host binding is not public."
  else
    _audit_add_result fail runtime_redis_bind "Redis appears publicly exposed on host interfaces." "${redis_exposure_warn[*]}" "Bind Redis to 127.0.0.1 only."
  fi
}

_audit_check_http_surface() {
  _audit_set_section "http-surface"

  if ! _audit_mode_allows_docker; then
    _audit_add_result skip http_surface_skipped "HTTP surface checks skipped by mode." "mode=$AUDIT_MODE"
    return
  fi

  if ! _audit_has_cmd docker; then
    _audit_add_result warn http_surface_docker_missing "Docker CLI unavailable; HTTP surface checks skipped."
    return
  fi

  local backend_container
  if [[ "$AUDIT_ENV" == "dev" ]]; then
    backend_container="uah-dev-backend"
  elif [[ "$AUDIT_ENV" == "beta" ]]; then
    backend_container="uah-beta-backend"
  else
    _audit_add_result skip http_surface_prod_scaffold "Prod runtime HTTP checks are scaffold-only."
    return
  fi

  if ! docker ps --format '{{.Names}}' | grep -Fxq "$backend_container"; then
    _audit_add_result skip http_surface_backend_missing "Backend container not running; HTTP surface checks skipped." "$backend_container"
    return
  fi

  local output
  if ! _audit_capture output docker exec "$backend_container" python3 - <<'PY'
import httpx

targets = {
    "api": "/api/",
    "diagnostics": "/api/diagnostics",
    "docs": "/docs",
    "openapi": "/openapi.json",
}

for name, path in targets.items():
    try:
        status = httpx.get(f"http://localhost:8000{path}", timeout=3.0).status_code
    except Exception:
        status = 0
    print(f"{name}={status}")
PY
  then
    _audit_add_result warn http_surface_probe_failed "Could not probe backend HTTP surface from container." "$output"
    return
  fi

  local api_status diagnostics_status docs_status openapi_status
  api_status="$(grep -E '^api=' <<< "$output" | head -n1 | cut -d= -f2 || true)"
  diagnostics_status="$(grep -E '^diagnostics=' <<< "$output" | head -n1 | cut -d= -f2 || true)"
  docs_status="$(grep -E '^docs=' <<< "$output" | head -n1 | cut -d= -f2 || true)"
  openapi_status="$(grep -E '^openapi=' <<< "$output" | head -n1 | cut -d= -f2 || true)"

  if [[ "$api_status" == "200" ]]; then
    _audit_add_result pass http_surface_api "Backend /api/ probe succeeded."
  else
    _audit_add_result warn http_surface_api "Backend /api/ probe did not return 200." "status=$api_status"
  fi

  if [[ "$AUDIT_ENV" == "beta" ]]; then
    if [[ "$diagnostics_status" == "200" ]]; then
      _audit_add_result fail http_surface_diagnostics "Beta exposes /api/diagnostics with status 200." "status=$diagnostics_status" "Gate or remove diagnostics endpoint in beta."
    else
      _audit_add_result pass http_surface_diagnostics "Beta does not expose /api/diagnostics as 200."
    fi

    if [[ "$docs_status" == "200" || "$openapi_status" == "200" ]]; then
      _audit_add_result warn http_surface_docs "Beta exposes API docs/openapi endpoints." "docs=$docs_status openapi=$openapi_status" "Disable or gate docs endpoints in beta."
    else
      _audit_add_result pass http_surface_docs "Beta docs/openapi endpoints are not exposed as 200."
    fi
  else
    _audit_add_result info http_surface_dev_docs "Dev docs/diagnostics probe values." "diagnostics=$diagnostics_status docs=$docs_status openapi=$openapi_status"
  fi
}

_audit_check_cloudflared_beta() {
  _audit_set_section "beta-cloudflare"

  if [[ "$AUDIT_ENV" != "beta" ]]; then
    _audit_add_result skip beta_cloudflare_not_applicable "Cloudflare runtime checks are beta-only."
    return
  fi

  if ! _audit_mode_allows_docker; then
    _audit_add_result skip beta_cloudflare_skipped "Cloudflare runtime checks skipped by mode." "mode=$AUDIT_MODE"
    return
  fi

  if ! _audit_has_cmd docker; then
    _audit_add_result warn beta_cloudflare_docker_missing "Docker CLI unavailable; cloudflared checks skipped."
    return
  fi

  if docker ps --format '{{.Names}}' | grep -Fxq uah-beta-cloudflared; then
    _audit_add_result pass beta_cloudflare_running "Cloudflared container is running."
  else
    _audit_add_result fail beta_cloudflare_running "Cloudflared container is not running." "Expected uah-beta-cloudflared"
  fi
}

_audit_check_host_firewall_iptables() {
  _audit_set_section "host-firewall"

  if ! _audit_mode_allows_host; then
    _audit_add_result skip host_iptables_skipped "Host iptables checks skipped by mode." "mode=$AUDIT_MODE"
    return
  fi

  if ! _audit_has_cmd iptables; then
    _audit_add_result warn host_iptables_missing "iptables command not available on host."
    return
  fi

  local rules
  if ! _audit_capture_privileged rules iptables -S; then
    _audit_add_result warn host_iptables_privilege "Could not read iptables rules (requires root or passwordless sudo)." "Run with sudo for full host firewall audit."
    return
  fi

  _audit_add_result pass host_iptables_access "iptables rules are readable."

  if grep -Eq '^-N DOCKER-USER$' <<< "$rules"; then
    _audit_add_result pass host_iptables_docker_user "DOCKER-USER chain exists."
  else
    _audit_add_result warn host_iptables_docker_user "DOCKER-USER chain not found." "Docker network enforcement may be unmanaged."
  fi

  if [[ "$AUDIT_ENV" == "beta" ]]; then
    local docker_user_rules
    docker_user_rules="$(grep -E '^-A DOCKER-USER ' <<< "$rules" || true)"
    if [[ -n "$docker_user_rules" ]]; then
      _audit_add_result pass host_iptables_beta_rules "DOCKER-USER rules exist for beta host-level controls." "$(head -n 3 <<< "$docker_user_rules" | tr '\n' '; ')"
    else
      _audit_add_result warn host_iptables_beta_rules "No DOCKER-USER rules found." "Beta hardening may be incomplete."
    fi
  fi
}

_audit_check_host_firewall_ufw() {
  _audit_set_section "host-firewall"

  if ! _audit_mode_allows_host; then
    _audit_add_result skip host_ufw_skipped "Host UFW checks skipped by mode." "mode=$AUDIT_MODE"
    return
  fi

  if ! _audit_has_cmd ufw; then
    _audit_add_result warn host_ufw_missing "UFW command not available on host."
    return
  fi

  local ufw_status
  if ! _audit_capture_privileged ufw_status ufw status verbose; then
    _audit_add_result warn host_ufw_privilege "Could not read UFW status (requires root or passwordless sudo)." "Run with sudo for full host firewall audit."
    return
  fi

  if grep -qi '^Status:[[:space:]]*active' <<< "$ufw_status"; then
    _audit_add_result pass host_ufw_active "UFW is active."
  else
    _audit_add_result warn host_ufw_inactive "UFW is inactive." "Consider host firewall enforcement if this is an internet-facing host."
  fi

  if [[ "$AUDIT_ENV" == "beta" ]]; then
    if grep -Eq '80/tcp[[:space:]]+ALLOW[[:space:]]+Anywhere' <<< "$ufw_status"; then
      _audit_add_result warn host_ufw_beta_open80 "UFW allows 80/tcp from Anywhere." "Restrict origin access where possible (Cloudflare-only policy)."
    fi
  fi
}

_audit_check_image_vulnerabilities() {
  _audit_set_section "image-vulnerabilities"

  if ! _audit_mode_allows_docker; then
    _audit_add_result skip image_vuln_skipped "Image vulnerability checks skipped by mode." "mode=$AUDIT_MODE"
    return
  fi

  if ! _audit_has_cmd trivy; then
    _audit_add_result warn image_vuln_trivy_missing "trivy is not installed; image vulnerability scan skipped."
    return
  fi

  if ! _audit_has_cmd python3; then
    _audit_add_result warn image_vuln_python_missing "python3 is not installed; trivy JSON parsing is unavailable."
    return
  fi

  if ! _audit_has_cmd docker; then
    _audit_add_result warn image_vuln_docker_missing "Docker CLI unavailable; image vulnerability checks skipped."
    return
  fi

  local target_containers=()
  if [[ "$AUDIT_ENV" == "dev" ]]; then
    target_containers=(uah-dev-backend uah-dev-frontend)
  elif [[ "$AUDIT_ENV" == "beta" ]]; then
    target_containers=(uah-beta-backend uah-beta-frontend)
  else
    _audit_add_result skip image_vuln_prod_scaffold "Prod image vulnerability checks are scaffold-only."
    return
  fi

  declare -A images_seen=()
  local container
  for container in "${target_containers[@]}"; do
    if ! docker ps --format '{{.Names}}' | grep -Fxq "$container"; then
      _audit_add_result skip image_vuln_container_missing "Container missing; image scan skipped for container." "$container"
      continue
    fi

    local image
    image="$(docker inspect -f '{{.Config.Image}}' "$container" 2>/dev/null || true)"
    if [[ -z "$image" || -n "${images_seen[$image]:-}" ]]; then
      continue
    fi
    images_seen[$image]=1

    local trivy_json
    local trivy_rc
    local vuln_count

    trivy_json="$(mktemp)"
    set +e
    trivy image --quiet --severity HIGH,CRITICAL --format json "$image" >"$trivy_json" 2>/dev/null
    trivy_rc=$?
    set -e

    if [[ "$trivy_rc" -ne 0 ]]; then
      _audit_add_result warn image_vuln_scan_failed "trivy image scan failed." "$image"
      rm -f "$trivy_json"
      continue
    fi

    vuln_count="$(python3 - "$trivy_json" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    print("parse_error")
    raise SystemExit(0)

count = 0
for result in data.get("Results", []):
    for vuln in result.get("Vulnerabilities") or []:
        sev = (vuln.get("Severity") or "").upper()
        if sev in {"HIGH", "CRITICAL"}:
            count += 1
print(count)
PY
)"

    if [[ "$vuln_count" =~ ^[0-9]+$ ]]; then
      if [[ "$vuln_count" -gt 0 ]]; then
        _audit_add_result fail image_vuln_found "trivy found HIGH/CRITICAL vulnerabilities in image." "$image count=$vuln_count" "Patch base images and rebuild."
      else
        _audit_add_result pass image_vuln_found "trivy found no HIGH/CRITICAL vulnerabilities in image." "$image"
      fi
    else
      _audit_add_result warn image_vuln_parse "Could not parse trivy JSON output." "$image"
    fi

    rm -f "$trivy_json"
  done
}

_audit_print_results() {
  echo ""
  echo "=== UAH Security Audit (${AUDIT_ENV}) ==="
  echo "start: $AUDIT_START_TS"
  echo "mode:  $AUDIT_MODE"
  echo "fix:   $AUDIT_FIX"
  echo "env:   $AUDIT_ENV_FILE"

  local rec
  for rec in "${AUDIT_RESULTS[@]}"; do
    IFS='|' read -r section severity check_id message details remediation <<< "$rec"
    printf "[%s] (%s) %s - %s\n" "${severity^^}" "$section" "$check_id" "$message"
    if [[ -n "$details" ]]; then
      printf "  details: %s\n" "$details"
    fi
    if [[ -n "$remediation" ]]; then
      printf "  remediation: %s\n" "$remediation"
    fi
  done
}

_audit_write_json() {
  if [[ -z "$AUDIT_JSON_PATH" ]]; then
    return
  fi

  if ! _audit_has_cmd python3; then
    echo "[WARN] (reporting) json_output_skipped - python3 not available; JSON report was not written."
    return
  fi

  local temp_file
  temp_file="$(mktemp)"

  local rec
  for rec in "${AUDIT_RESULTS[@]}"; do
    printf "%s\n" "$rec" >> "$temp_file"
  done

  python3 - "$temp_file" "$AUDIT_JSON_PATH" "$AUDIT_ENV" "$AUDIT_ENV_FILE" "$AUDIT_MODE" "$AUDIT_FIX" "$AUDIT_START_TS" <<'PY'
import json
import sys
from datetime import datetime, timezone

input_path = sys.argv[1]
output_path = sys.argv[2]
audit_env = sys.argv[3]
env_file = sys.argv[4]
mode = sys.argv[5]
fix_flag = sys.argv[6].lower() == "true"
start_ts = sys.argv[7]

results = []
pass_count = 0
warn_count = 0
fail_count = 0
skip_count = 0
info_count = 0

with open(input_path, "r", encoding="utf-8") as f:
    for raw in f:
        raw = raw.rstrip("\n")
        if not raw:
            continue
        parts = raw.split("|", 5)
        while len(parts) < 6:
            parts.append("")
        section, severity, check_id, message, details, remediation = parts
        severity = severity.lower()
        if severity == "pass":
            pass_count += 1
        elif severity == "warn":
            warn_count += 1
        elif severity == "fail":
            fail_count += 1
        elif severity == "skip":
            skip_count += 1
        else:
            info_count += 1
        results.append(
            {
                "section": section,
                "severity": severity,
                "check_id": check_id,
                "message": message,
                "details": details,
                "remediation": remediation,
            }
        )

risk_score = min(fail_count * 20 + warn_count * 5, 100)
report = {
    "audit": {
        "environment": audit_env,
        "env_file": env_file,
        "mode": mode,
        "fix_enabled": fix_flag,
        "start_utc": start_ts,
        "end_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "risk_score": risk_score,
        "summary": {
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
            "skip": skip_count,
            "info": info_count,
            "total": len(results),
        },
        "results": results,
    }
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
PY

  rm -f "$temp_file"
  echo "[INFO] (reporting) audit_json_written - $AUDIT_JSON_PATH"
}

_audit_print_summary() {
  local risk_score=$((AUDIT_FAIL_COUNT * 20 + AUDIT_WARN_COUNT * 5))
  if ((risk_score > 100)); then
    risk_score=100
  fi

  echo ""
  echo "=== Security Audit Summary ==="
  echo "pass:  $AUDIT_PASS_COUNT"
  echo "warn:  $AUDIT_WARN_COUNT"
  echo "fail:  $AUDIT_FAIL_COUNT"
  echo "skip:  $AUDIT_SKIP_COUNT"
  echo "info:  $AUDIT_INFO_COUNT"
  echo "risk:  ${risk_score}/100"

  if ((AUDIT_FAIL_COUNT > 0)); then
    echo "result: FAIL"
  elif ((AUDIT_WARN_COUNT > 0)); then
    echo "result: WARN"
  else
    echo "result: PASS"
  fi
}

_audit_exit_code() {
  if ((AUDIT_FAIL_COUNT > 0)); then
    return 2
  fi

  if [[ "$AUDIT_FAIL_ON_WARN" == "true" && AUDIT_WARN_COUNT -gt 0 ]]; then
    return 1
  fi

  return 0
}

audit_run() {
  _audit_init

  _audit_check_env_file
  _audit_check_required_env_vars
  _audit_check_secret_quality
  _audit_check_env_permissions

  _audit_check_compose_files_and_render
  _audit_check_compose_hardening

  _audit_check_dependency_vulnerabilities

  _audit_check_runtime_containers
  _audit_check_runtime_ports
  _audit_check_http_surface
  _audit_check_cloudflared_beta
  _audit_check_image_vulnerabilities

  _audit_check_host_firewall_iptables
  _audit_check_host_firewall_ufw

  _audit_print_results
  _audit_write_json
  _audit_print_summary

  if _audit_exit_code; then
    return 0
  fi

  return $?
}
