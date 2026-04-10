#!/usr/bin/env bash
set -euo pipefail

TARGET_ENV=""
ENV_FILE=""
WARN_ONLY=false

usage() {
  cat <<'EOF'
UAH env feature check

Usage:
  bash scripts/lib/env-feature-check.sh --env <dev|beta|prod|local> [options]

Options:
  --env <name>          Target environment to validate
  --env-file <path>     Env file path (default: ./.env)
  --warn-only           Never fail; print findings and exit 0
  -h, --help            Show this help
EOF
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

strip_wrapping_quotes() {
  local value="$1"

  if [[ "${#value}" -ge 2 ]]; then
    if [[ "${value:0:1}" == '"' && "${value: -1}" == '"' ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "${value:0:1}" == "'" && "${value: -1}" == "'" ]]; then
      value="${value:1:${#value}-2}"
    fi
  fi

  printf '%s' "$value"
}

get_env_file_value() {
  local key="$1"
  local file_path="$2"
  local value

  if [[ ! -f "$file_path" ]]; then
    return 1
  fi

  value="$(awk -F= -v key="$key" '
    /^[[:space:]]*#/ { next }
    NF >= 2 {
      k=$1
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", k)
      if (k == key) {
        v=substr($0, index($0, "=") + 1)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
        print v
      }
    }
  ' "$file_path" | tail -n1)"

  if [[ -z "$value" ]]; then
    return 1
  fi

  strip_wrapping_quotes "$value"
}

get_env_value() {
  local key="$1"

  if [[ "${!key+x}" == "x" ]]; then
    printf '%s' "${!key}"
    return 0
  fi

  get_env_file_value "$key" "$ENV_FILE" || true
}

bool_is_true() {
  local value
  value="$(to_lower "$(trim "$1")")"
  [[ "$value" == "1" || "$value" == "true" || "$value" == "yes" || "$value" == "on" ]]
}

declare -a ERRORS=()
declare -a WARNINGS=()

add_error() {
  ERRORS+=("$1")
}

add_warning() {
  WARNINGS+=("$1")
}

require_present() {
  local key="$1"
  local value

  value="$(trim "$(get_env_value "$key")")"
  if [[ -z "$value" ]]; then
    add_error "$key is required but missing or empty."
    return 0
  fi

  return 0
}

validate_dev_like() {
  require_present "DEV_AUTH_TEST_ACCOUNT_ENABLED"
  require_present "VITE_AUTH_NAMESPACE"

  local namespace
  namespace="$(to_lower "$(trim "$(get_env_value "VITE_AUTH_NAMESPACE")")")"
  if [[ -n "$namespace" && "$namespace" != "dev" ]]; then
    add_warning "VITE_AUTH_NAMESPACE is '$namespace' (expected 'dev' for dev/local workflows)."
  fi

  local enabled
  enabled="$(trim "$(get_env_value "DEV_AUTH_TEST_ACCOUNT_ENABLED")")"
  if bool_is_true "$enabled"; then
    require_present "DEV_AUTH_TEST_USERNAME"
    require_present "DEV_AUTH_TEST_PASSWORD"
  fi

  local local_mode
  local_mode="$(to_lower "$(trim "$(get_env_value "VITE_LOCAL_MODE")")")"
  if [[ "$local_mode" == "mock" ]]; then
    add_warning "VITE_LOCAL_MODE is 'mock'; use this only for localhost frontend development."
  fi
}

validate_beta() {
  require_present "DEV_AUTH_TEST_ACCOUNT_ENABLED"
  require_present "VITE_AUTH_NAMESPACE"

  local enabled
  enabled="$(trim "$(get_env_value "DEV_AUTH_TEST_ACCOUNT_ENABLED")")"
  if bool_is_true "$enabled"; then
    add_error "DEV_AUTH_TEST_ACCOUNT_ENABLED must be false for beta."
  fi

  local namespace
  namespace="$(to_lower "$(trim "$(get_env_value "VITE_AUTH_NAMESPACE")")")"
  if [[ "$namespace" != "beta" ]]; then
    add_error "VITE_AUTH_NAMESPACE must be 'beta' for beta (current: '${namespace:-<empty>}')."
  fi

  local local_mode
  local_mode="$(to_lower "$(trim "$(get_env_value "VITE_LOCAL_MODE")")")"
  if [[ "$local_mode" == "mock" ]]; then
    add_error "VITE_LOCAL_MODE must not be 'mock' for beta."
  fi
}

validate_prod() {
  require_present "DEV_AUTH_TEST_ACCOUNT_ENABLED"
  require_present "VITE_AUTH_NAMESPACE"

  local enabled
  enabled="$(trim "$(get_env_value "DEV_AUTH_TEST_ACCOUNT_ENABLED")")"
  if bool_is_true "$enabled"; then
    add_error "DEV_AUTH_TEST_ACCOUNT_ENABLED must be false for prod."
  fi

  local namespace
  namespace="$(to_lower "$(trim "$(get_env_value "VITE_AUTH_NAMESPACE")")")"
  if [[ "$namespace" != "prod" ]]; then
    add_warning "VITE_AUTH_NAMESPACE is '$namespace' (expected 'prod' for prod deployments)."
  fi

  local local_mode
  local_mode="$(to_lower "$(trim "$(get_env_value "VITE_LOCAL_MODE")")")"
  if [[ "$local_mode" == "mock" ]]; then
    add_error "VITE_LOCAL_MODE must not be 'mock' for prod."
  fi
}

while (($#)); do
  case "$1" in
    --env)
      TARGET_ENV="${2:-}"
      if [[ -z "$TARGET_ENV" ]]; then
        echo "Missing value for --env" >&2
        exit 2
      fi
      shift 2
      ;;
    --env-file)
      ENV_FILE="${2:-}"
      if [[ -z "$ENV_FILE" ]]; then
        echo "Missing value for --env-file" >&2
        exit 2
      fi
      shift 2
      ;;
    --warn-only)
      WARN_ONLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option '$1'" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$TARGET_ENV" ]]; then
  echo "--env is required." >&2
  usage >&2
  exit 2
fi

if [[ -z "$ENV_FILE" ]]; then
  ENV_FILE="$(pwd)/.env"
fi

TARGET_ENV="$(to_lower "$(trim "$TARGET_ENV")")"

if [[ ! -f "$ENV_FILE" ]]; then
  add_error "Env file not found: $ENV_FILE"
fi

case "$TARGET_ENV" in
  dev|development|local)
    validate_dev_like
    ;;
  beta)
    validate_beta
    ;;
  prod|production)
    validate_prod
    ;;
  *)
    add_warning "No explicit env feature policy for '$TARGET_ENV'; skipping strict checks."
    ;;
esac

echo "[env-check] Environment: $TARGET_ENV"
echo "[env-check] Env file: $ENV_FILE"

if ((${#WARNINGS[@]} > 0)); then
  for warning in "${WARNINGS[@]}"; do
    echo "[env-check] WARN: $warning"
  done
fi

if ((${#ERRORS[@]} > 0)); then
  for err in "${ERRORS[@]}"; do
    echo "[env-check] ERROR: $err"
  done

  if [[ "$WARN_ONLY" == true ]]; then
    echo "[env-check] WARN-ONLY mode active; continuing despite ${#ERRORS[@]} error(s)."
    exit 0
  fi

  echo "[env-check] FAILED with ${#ERRORS[@]} error(s)."
  exit 1
fi

if ((${#WARNINGS[@]} > 0)); then
  echo "[env-check] Completed with ${#WARNINGS[@]} warning(s)."
else
  echo "[env-check] PASS: required env feature variables are present."
fi
