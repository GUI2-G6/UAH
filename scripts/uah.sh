#!/usr/bin/env bash
set -euo pipefail

# Ensure the script is executable
chmod +x "$0"

# Ignore file permission changes in Git to avoid sync conflicts
git config core.fileMode false


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

BUILD_MODE="none"
FLAG_NO_BUILD=false
FLAG_BUILD_ALL=false
BUILD_SERVICES=()

SYNC_BLOCKER_STATUS=""
SYNC_BLOCKER_AHEAD=0
SYNC_BLOCKER_BEHIND=0
SYNC_CAN_FAST_FORWARD=true
DETECTED_ENV_SOURCE="unknown"
ENV_CONFIRMATION_APPROVED=false
ENV_CONFIRMATION_ENV=""
SCHEMA_RECONCILE_LAST_STATUS="not-run"
SCHEMA_RECONCILE_LAST_MESSAGE="Schema reconcile has not run yet."

ENV_POLICY_ERROR_COUNT=0
ENV_POLICY_WARN_COUNT=0
ENV_POLICY_INFO_COUNT=0
ENV_POLICY_KEYS=(
  "VITE_LOCAL_MODE"
  "DEV_AUTH_TEST_ACCOUNT_ENABLED"
  "DEV_AUTH_TEST_IS_DEVELOPER"
  "VITE_AUTH_NAMESPACE"
  "USE_LOCAL_PIPELINE"
  "LOCAL_OCR_URL"
  "LOCAL_LLM_URL"
  "REDIS_ENABLED"
  "REDIS_URL"
  "ENVIRONMENT"
  "ENV"
  "COMPOSE_PROJECT_NAME"
)
declare -A ENV_POLICY_CURRENT_VALUES=()
declare -A ENV_POLICY_RECOMMENDED_VALUES=()
declare -A ENV_POLICY_FINDING_LEVEL=()
declare -A ENV_POLICY_PENDING_VALUES=()
declare -a ENV_POLICY_MESSAGES=()
declare -a ENV_POLICY_MISMATCHED_KEYS=()

if [[ -t 1 ]]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BLUE='\033[0;34m'
  CYAN='\033[0;36m'
  BOLD='\033[1m'
  NC='\033[0m'
else
  RED=''
  GREEN=''
  YELLOW=''
  BLUE=''
  CYAN=''
  BOLD=''
  NC=''
fi

# ---- Discord notification helper ----
notify_discord() {
  local webhook_url="${DISCORD_WEBHOOK_URL:-}"

  # Fall back to .env value when not exported in current shell
  if [[ -z "$webhook_url" ]]; then
    webhook_url="$(get_env_value_or_default DISCORD_WEBHOOK_URL "")"
  fi

  # Return early if webhook URL is still not set
  if [[ -z "$webhook_url" ]]; then
    return
  fi

  local message="$1"
  local color="${2:-3066993}"   # green default
  curl -s -X POST "$webhook_url" \
    -H "Content-Type: application/json" \
    -d "{
      \"embeds\": [{
        \"title\": \"UAH Lifecycle Event\",
        \"description\": \"$message\",
        \"color\": $color,
        \"footer\": { \"text\": \"$(hostname) · $(date '+%Y-%m-%d %H:%M')\" }
      }]
    }" > /dev/null
}

# Colors: green=3066993, yellow=16776960, red=15158332



DEBUG_BACKEND_CONTAINER=""
DEBUG_DB_CONTAINER=""
DEBUG_REDIS_CONTAINER=""
DEBUG_DB_NAME=""
DEBUG_MAIN_NETWORK=""
DEBUG_LOG_ALT_SERVICE=""
PROVIDER_CONFIG_MUTATED=false

PROVIDER_NAMES=(
  "the_muse"
  "arbeitnow"
  "findwork"
  "jooble"
  "adzuna"
  "careerjet"
)
PROVIDER_DEFAULT_CATEGORIES=(
  "tech"
  "product"
  "finance"
  "business and operations"
  "sales and marketing"
  "people"
  "customer and support"
)
declare -A PROVIDER_LABELS=(
  ["the_muse"]="The Muse"
  ["arbeitnow"]="Arbeitnow"
  ["findwork"]="Findwork"
  ["jooble"]="Jooble"
  ["adzuna"]="Jobs by Adzuna"
  ["careerjet"]="Careerjet"
)
declare -A PROVIDER_SWEEP_MODES=(
  ["the_muse"]="category"
  ["arbeitnow"]="global"
  ["findwork"]="global"
  ["jooble"]="matrix"
  ["adzuna"]="category"
  ["careerjet"]="disabled"
)
declare -A PROVIDER_DEFAULT_STATES=(
  ["the_muse"]="active"
  ["arbeitnow"]="active"
  ["findwork"]="dormant"
  ["jooble"]="dormant"
  ["adzuna"]="dormant"
  ["careerjet"]="dormant"
)
declare -A PROVIDER_MUTATION_ALLOWED=(
  ["the_muse"]="true"
  ["arbeitnow"]="true"
  ["findwork"]="true"
  ["jooble"]="true"
  ["adzuna"]="true"
  ["careerjet"]="false"
)
declare -A PROVIDER_EDITABLE_FIELDS=(
  ["the_muse"]="api_key rate_limit_per_hour"
  ["arbeitnow"]="inter_request_delay"
  ["findwork"]="api_key inter_request_delay"
  ["jooble"]="api_key inter_request_delay page_size"
  ["adzuna"]="app_id app_key daily_request_budget"
  ["careerjet"]=""
)
declare -A PROVIDER_SECRET_FIELDS=(
  ["the_muse"]="api_key"
  ["arbeitnow"]=""
  ["findwork"]="api_key"
  ["jooble"]="api_key"
  ["adzuna"]="app_key"
  ["careerjet"]=""
)
declare -A PROVIDER_REQUIRED_FIELDS=(
  ["the_muse"]="api_key"
  ["arbeitnow"]=""
  ["findwork"]=""
  ["jooble"]="api_key"
  ["adzuna"]="app_id app_key"
  ["careerjet"]=""
)
declare -A PROVIDER_OPTIONAL_FIELDS=(
  ["the_muse"]=""
  ["arbeitnow"]=""
  ["findwork"]="api_key"
  ["jooble"]=""
  ["adzuna"]=""
  ["careerjet"]=""
)
declare -A PROVIDER_STATUS_SOURCE=()
declare -A PROVIDER_STATUS_INGEST=()
declare -A PROVIDER_STATUS_DISPLAY=()
declare -A PROVIDER_STATUS_SCHEDULED=()
declare -A PROVIDER_STATUS_STATE=()
declare -A PROVIDER_STATUS_CREDENTIALS=()
declare -A PROVIDER_STATUS_CREDENTIAL_STATE=()
declare -A PROVIDER_CONTROL_OVERRIDES=()
declare -A PROVIDER_LEGACY_SCHEDULED=()

append_unique_build_service() {
  local service_name="$1"
  local existing

  for existing in "${BUILD_SERVICES[@]}"; do
    if [[ "$existing" == "$service_name" ]]; then
      return
    fi
  done

  BUILD_SERVICES+=("$service_name")
}

validate_and_add_build_service() {
  local service_name="$1"

  if [[ -z "$service_name" ]]; then
    echo "Build service cannot be empty." >&2
    exit 1
  fi

  if [[ ! "$service_name" =~ ^[a-zA-Z0-9_.-]+$ ]]; then
    echo "Invalid service name for build option: '$service_name'." >&2
    exit 1
  fi

  append_unique_build_service "$service_name"
}

resolve_build_mode() {
  if [[ "$FLAG_NO_BUILD" == true ]] && ([[ "$FLAG_BUILD_ALL" == true ]] || [[ ${#BUILD_SERVICES[@]} -gt 0 ]]); then
    echo "Cannot combine --no-build with build flags." >&2
    exit 1
  fi

  if [[ "$FLAG_BUILD_ALL" == true ]] && [[ ${#BUILD_SERVICES[@]} -gt 0 ]]; then
    echo "Cannot combine --build-all with service-specific build flags." >&2
    exit 1
  fi

  if [[ "$FLAG_BUILD_ALL" == true ]]; then
    BUILD_MODE="all"
    return
  fi

  if [[ ${#BUILD_SERVICES[@]} -gt 0 ]]; then
    BUILD_MODE="services"
    return
  fi

  BUILD_MODE="none"
}

build_mode_label() {
  case "$BUILD_MODE" in
    none)
      echo "no rebuild"
      ;;
    all)
      echo "rebuild all services"
      ;;
    services)
      echo "rebuild services: ${BUILD_SERVICES[*]}"
      ;;
    *)
      echo "unknown build mode"
      ;;
  esac
}

validate_build_mode_for_action() {
  local action="$1"

  if [[ "$BUILD_MODE" == "none" ]]; then
    return
  fi

  case "$action" in
    start|restart|sync)
      ;;
    *)
      echo "Build flags are only supported with start, restart, or sync actions." >&2
      exit 1
      ;;
  esac
}

build_mode_refresh_from_flags_relaxed() {
  if [[ "$FLAG_BUILD_ALL" == true ]]; then
    BUILD_MODE="all"
    return
  fi

  if [[ ${#BUILD_SERVICES[@]} -gt 0 ]]; then
    BUILD_MODE="services"
    return
  fi

  BUILD_MODE="none"
}

build_mode_reset_selection() {
  FLAG_NO_BUILD=false
  FLAG_BUILD_ALL=false
  BUILD_SERVICES=()
  BUILD_MODE="none"
}

build_mode_set_all_selection() {
  FLAG_NO_BUILD=false
  FLAG_BUILD_ALL=true
  BUILD_SERVICES=()
  BUILD_MODE="all"
}

build_mode_set_services_selection() {
  FLAG_NO_BUILD=false
  FLAG_BUILD_ALL=false
  if [[ ${#BUILD_SERVICES[@]} -gt 0 ]]; then
    BUILD_MODE="services"
  else
    BUILD_MODE="none"
  fi
}

build_mode_is_service_selected() {
  local service_name="$1"
  local existing

  for existing in "${BUILD_SERVICES[@]}"; do
    if [[ "$existing" == "$service_name" ]]; then
      return 0
    fi
  done

  return 1
}

build_mode_remove_service() {
  local service_name="$1"
  local existing
  local -a updated_services=()

  for existing in "${BUILD_SERVICES[@]}"; do
    if [[ "$existing" == "$service_name" ]]; then
      continue
    fi
    updated_services+=("$existing")
  done

  BUILD_SERVICES=("${updated_services[@]}")
}

build_mode_default_service_list() {
  local env_name="$1"

  case "$env_name" in
    beta)
      echo "backend frontend db redis cloudflared landing"
      ;;
    *)
      echo "backend frontend db redis"
      ;;
  esac
}

build_mode_service_supported_for_env() {
  local env_name="$1"
  local service_name="$2"

  case "$env_name" in
    dev)
      case "$service_name" in
        backend|frontend|db|redis)
          return 0
          ;;
      esac
      ;;
    beta)
      case "$service_name" in
        backend|frontend|db|redis|cloudflared|landing)
          return 0
          ;;
      esac
      ;;
  esac

  return 1
}

build_mode_supported_services_label() {
  local env_name="$1"

  case "$env_name" in
    dev)
      echo "backend frontend db redis"
      ;;
    beta)
      echo "backend frontend db redis cloudflared landing"
      ;;
    *)
      echo "<none>"
      ;;
  esac
}

validate_build_services_for_env() {
  local env_name="$1"
  local service_name

  if [[ "$BUILD_MODE" != "services" ]]; then
    return
  fi

  for service_name in "${BUILD_SERVICES[@]}"; do
    if ! build_mode_service_supported_for_env "$env_name" "$service_name"; then
      echo "Build service '$service_name' is not available for '$env_name'." >&2
      echo "Supported services: $(build_mode_supported_services_label "$env_name")" >&2
      exit 1
    fi
  done
}

build_mode_print_selected_services() {
  local service

  if [[ ${#BUILD_SERVICES[@]} -eq 0 ]]; then
    echo "<none>"
    return
  fi

  for service in "${BUILD_SERVICES[@]}"; do
    printf "%s " "$service"
  done
  echo ""
}

build_mode_select_services_interactive() {
  local env_name="$1"
  local action_name="$2"
  local choice
  local custom_service
  local marker
  local service
  local index
  local -a default_services=()
  local -a original_services=("${BUILD_SERVICES[@]}")
  local original_mode="$BUILD_MODE"
  local original_flag_no_build="$FLAG_NO_BUILD"
  local original_flag_build_all="$FLAG_BUILD_ALL"

  read -r -a default_services <<< "$(build_mode_default_service_list "$env_name")"

  while true; do
    debug_header "$env_name" "Rebuild :: $action_name :: Services"
    debug_print_section "Toggle services by number"

    for index in "${!default_services[@]}"; do
      service="${default_services[$index]}"
      if build_mode_is_service_selected "$service"; then
        marker="x"
      else
        marker=" "
      fi
      printf "  %2d) [%s] %s\n" "$((index + 1))" "$marker" "$service"
    done

    echo ""
    echo "  Selected services: $(build_mode_print_selected_services)"
    echo ""
    echo "  Actions"
    echo "    c) add custom service"
    echo "    r) reset selected services"
    echo "    a) apply service selection"
    echo "    b) back"
    read -rp "  Choice: " choice

    case "${choice,,}" in
      a|apply)
        if [[ ${#BUILD_SERVICES[@]} -eq 0 ]]; then
          debug_print_warn "Select at least one service before applying services mode."
          debug_press_enter
          continue
        fi
        build_mode_set_services_selection
        return 0
        ;;
      b|back)
        BUILD_SERVICES=("${original_services[@]}")
        BUILD_MODE="$original_mode"
        FLAG_NO_BUILD="$original_flag_no_build"
        FLAG_BUILD_ALL="$original_flag_build_all"
        return 1
        ;;
      c|custom)
        read -rp "  Custom service name: " custom_service
        if [[ -z "$custom_service" ]]; then
          debug_print_warn "Service name cannot be empty."
          debug_press_enter
          continue
        fi
        if [[ ! "$custom_service" =~ ^[a-zA-Z0-9_.-]+$ ]]; then
          debug_print_warn "Invalid service name '$custom_service'."
          debug_press_enter
          continue
        fi
        if build_mode_is_service_selected "$custom_service"; then
          build_mode_remove_service "$custom_service"
        else
          append_unique_build_service "$custom_service"
        fi
        ;;
      r|reset)
        BUILD_SERVICES=()
        ;;
      *)
        if [[ "$choice" =~ ^[0-9]+$ ]]; then
          index=$((choice - 1))
          if (( index < 0 || index >= ${#default_services[@]} )); then
            debug_print_warn "Invalid service number."
            debug_press_enter
            continue
          fi

          service="${default_services[$index]}"
          if build_mode_is_service_selected "$service"; then
            build_mode_remove_service "$service"
          else
            append_unique_build_service "$service"
          fi
          continue
        fi

        debug_print_warn "Invalid selection."
        debug_press_enter
        ;;
    esac
  done
}

configure_rebuild_ui_for_action() {
  local env_name="$1"
  local action_name="$2"
  local choice

  build_mode_refresh_from_flags_relaxed

  while true; do
    debug_header "$env_name" "Rebuild :: ${action_name^^}"
    debug_print_section "Current rebuild selection"
    startup_status_chip "ok" "Mode: $(build_mode_label)"

    if [[ "$BUILD_MODE" == "services" ]]; then
      startup_status_chip "ok" "Services: $(build_mode_print_selected_services)"
    fi

    echo ""
    echo "  Choose rebuild behavior:"
    echo "    1) Keep current selection"
    echo "    2) No rebuild"
    echo "    3) Rebuild all services"
    echo "    4) Select services to rebuild"
    echo "    0) Back"
    read -rp "  Choice [1-4/0]: " choice

    case "$choice" in
      1)
        return 0
        ;;
      2)
        build_mode_reset_selection
        return 0
        ;;
      3)
        build_mode_set_all_selection
        return 0
        ;;
      4)
        if build_mode_select_services_interactive "$env_name" "$action_name"; then
          return 0
        fi
        ;;
      0)
        return 1
        ;;
      *)
        debug_print_warn "Invalid selection."
        debug_press_enter
        ;;
    esac
  done
}

get_env_value_or_default() {
  local key="$1"
  local default_value="$2"
  local value="${!key:-}"

  if [[ -z "$value" && -f "$ROOT_DIR/.env" ]]; then
    value=$(awk -F= -v key="$key" '
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
    ' "$ROOT_DIR/.env" | tail -n1)
  fi

  if [[ -z "$value" ]]; then
    value="$default_value"
  fi

  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"

  echo "$value"
}

normalize_environment_label() {
  local raw_value="${1:-}"
  local value

  value="${raw_value,,}"
  case "$value" in
    dev|development|local)
      echo "dev"
      ;;
    beta|staging)
      echo "beta"
      ;;
    prod|production)
      echo "prod"
      ;;
    *)
      echo ""
      ;;
  esac
}

detect_environment_context() {
  local pwd_env=""
  local root_env=""
  local env_var=""
  local compose_project=""

  if [[ "$PWD" =~ /environments/(dev|beta|prod)(/|$) ]]; then
    pwd_env="${BASH_REMATCH[1]}"
    DETECTED_ENV_SOURCE="cwd-path"
    echo "$pwd_env"
    return
  fi

  if [[ "$ROOT_DIR" =~ /environments/(dev|beta|prod)(/|$) ]]; then
    root_env="${BASH_REMATCH[1]}"
    DETECTED_ENV_SOURCE="repo-path"
    echo "$root_env"
    return
  fi

  env_var="$(normalize_environment_label "$(get_env_value_or_default ENVIRONMENT "")")"
  if [[ -n "$env_var" ]]; then
    DETECTED_ENV_SOURCE="ENVIRONMENT"
    echo "$env_var"
    return
  fi

  env_var="$(normalize_environment_label "$(get_env_value_or_default ENV "")")"
  if [[ -n "$env_var" ]]; then
    DETECTED_ENV_SOURCE="ENV"
    echo "$env_var"
    return
  fi

  compose_project="$(get_env_value_or_default COMPOSE_PROJECT_NAME "")"
  compose_project="${compose_project,,}"
  if [[ "$compose_project" == *"beta"* ]]; then
    DETECTED_ENV_SOURCE="COMPOSE_PROJECT_NAME"
    echo "beta"
    return
  fi
  if [[ "$compose_project" == *"prod"* ]]; then
    DETECTED_ENV_SOURCE="COMPOSE_PROJECT_NAME"
    echo "prod"
    return
  fi
  if [[ "$compose_project" == *"dev"* || "$compose_project" == *"local"* ]]; then
    DETECTED_ENV_SOURCE="COMPOSE_PROJECT_NAME"
    echo "dev"
    return
  fi

  DETECTED_ENV_SOURCE="unknown"
  echo ""
}

debug_header() {
  local env_name="$1"
  local title="$2"

  if [[ -t 1 ]]; then
    clear
  fi

  echo -e "${BOLD}${CYAN}"
  echo "  ██╗   ██╗ █████╗ ██╗  ██╗"
  echo "  ██║   ██║██╔══██╗██║  ██║"
  echo "  ██║   ██║███████║███████║"
  echo "  ██║   ██║██╔══██║██╔══██║"
  echo "  ╚██████╔╝██║  ██║██║  ██║"
  echo "   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝"
  echo -e "${NC}${BOLD}  Debug :: ${env_name^^} :: ${title}${NC}"
  echo -e "${CYAN}  ─────────────────────────────────────────────────────────────${NC}"
  echo ""
}

debug_print_section() {
  echo -e "${CYAN}  $1${NC}"
}

debug_print_ok() {
  echo -e "  ${GREEN}✓${NC} $1"
}

debug_print_warn() {
  echo -e "  ${YELLOW}!${NC} $1"
}

debug_print_error() {
  echo -e "  ${RED}✗${NC} $1"
}

debug_press_enter() {
  if [[ -t 0 ]]; then
    echo ""
    read -rp "  Press Enter to continue... " _unused
  fi
}

debug_profile_init() {
  local env_name="$1"

  case "$env_name" in
    dev)
      DEBUG_BACKEND_CONTAINER="uah-dev-backend"
      DEBUG_DB_CONTAINER="uah-dev-db"
      DEBUG_REDIS_CONTAINER="uah-redis"
      DEBUG_DB_NAME="uah_dev"
      DEBUG_MAIN_NETWORK="uah-infra"
      DEBUG_LOG_ALT_SERVICE="frontend"
      ;;
    beta)
      DEBUG_BACKEND_CONTAINER="uah-beta-backend"
      DEBUG_DB_CONTAINER="uah-beta-db"
      DEBUG_REDIS_CONTAINER="uah-beta-redis"
      DEBUG_DB_NAME="uah_beta"
      DEBUG_MAIN_NETWORK="uah-beta-infra"
      DEBUG_LOG_ALT_SERVICE="cloudflared"
      ;;
    *)
      echo "Unsupported debug environment '$env_name'." >&2
      exit 1
      ;;
  esac
}

is_container_running() {
  local container_name="$1"
  local state

  state=$(docker inspect -f '{{.State.Running}}' "$container_name" 2>/dev/null || true)
  [[ "$state" == "true" ]]
}

require_external_network() {
  local network_name="$1"

  if ! docker network inspect "$network_name" >/dev/null 2>&1; then
    echo "Required Docker network '$network_name' was not found." >&2
    echo "Create it with: docker network create $network_name" >&2
    exit 1
  fi
}

require_running_container() {
  local container_name="$1"

  if ! is_container_running "$container_name"; then
    echo "Required container '$container_name' is not running." >&2
    echo "Start the infrastructure stack first, then retry." >&2
    exit 1
  fi
}

is_tcp_port_in_use() {
  local port="$1"

  if command -v ss >/dev/null 2>&1; then
    ss -H -ltn "sport = :$port" 2>/dev/null | grep -q .
    return
  fi

  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return
  fi

  if command -v netstat >/dev/null 2>&1; then
    netstat -tln 2>/dev/null | awk '{print $4}' | grep -Eq "(^|:)$port$"
    return
  fi

  return 2
}

require_available_host_port() {
  local port="$1"
  local expected_container="$2"
  local label="$3"
  local port_check_status

  if ! [[ "$port" =~ ^[0-9]+$ ]] || ((port < 1 || port > 65535)); then
    echo "Invalid port '$port' for $label." >&2
    exit 1
  fi

  if is_container_running "$expected_container"; then
    return
  fi

  if is_tcp_port_in_use "$port"; then
    port_check_status=0
  else
    port_check_status=$?
  fi

  if [[ $port_check_status -eq 0 ]]; then
    echo "$label requires host port $port, but it is already in use." >&2
    echo "Free the port or change the environment variable in .env." >&2
    exit 1
  fi

  if [[ $port_check_status -eq 2 ]]; then
    echo "Could not verify whether port $port is in use (ss/lsof/netstat unavailable). Continuing." >&2
  fi
}

preflight_startup() {
  local env_name="$1"
  local redis_port

  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker CLI is required but was not found in PATH." >&2
    exit 1
  fi

  if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose plugin is required but not available." >&2
    exit 1
  fi

  case "$env_name" in
    dev)
      require_external_network "uah-infra"
      require_running_container "uah-dev-vpn"
      redis_port="$(get_env_value_or_default REDIS_HOST_PORT 6379)"
      require_available_host_port "$redis_port" "uah-redis" "Dev Redis"
      ;;
    beta)
      require_external_network "uah-infra"
      require_external_network "uah-beta-infra"
      require_running_container "uah-dev-vpn"
      redis_port="$(get_env_value_or_default BETA_REDIS_HOST_PORT 6380)"
      require_available_host_port "$redis_port" "uah-beta-redis" "Beta Redis"
      ;;
    *)
      ;;
  esac
}

run_compose_up_with_build_mode() {
  local env_name="$1"

  case "$BUILD_MODE" in
    none)
      run_compose "$env_name" up -d
      ;;
    all)
      run_compose "$env_name" up -d --build
      ;;
    services)
      run_compose "$env_name" up -d --build "${BUILD_SERVICES[@]}"
      # Ensure all services are up after targeted rebuilds.
      run_compose "$env_name" up -d
      ;;
    *)
      echo "Unknown build mode '$BUILD_MODE'." >&2
      exit 1
      ;;
  esac
}

verify_frontend_asset_integrity() {
  local env_name="$1"
  local frontend_url="${2:-}"
  local index_url
  local index_html
  local max_missing=0

  if [[ -z "$frontend_url" ]]; then
    case "$env_name" in
      beta)
        frontend_url="https://beta.uahapp.com"
        ;;
      dev)
        frontend_url="http://localhost:8080"
        ;;
      *)
        echo "Unsupported environment '$env_name' for frontend integrity check." >&2
        return 1
        ;;
    esac
  fi

  index_url="${frontend_url%/}/index.html"
  echo "  Checking frontend index/chunk integrity: $index_url"

  if ! index_html="$(curl -fsSL --max-time 15 "$index_url")"; then
    echo "  Failed to fetch $index_url" >&2
    return 1
  fi

  local urls
  if ! urls="$(INDEX_HTML="$index_html" FRONTEND_URL="$frontend_url" python3 - <<'PY'
import os
import re
from urllib.parse import urljoin, urlparse

html = os.environ.get("INDEX_HTML", "")
base = os.environ.get("FRONTEND_URL", "").strip()
seen = set()
for value in re.findall(r'(?:src|href)=["\']([^"\']+)["\']', html):
    item = value.strip()
    if not item:
        continue
    if item.startswith("data:"):
        continue
    if not (item.endswith(".js") or item.endswith(".css")):
        continue
    if item.startswith("http://") or item.startswith("https://"):
        parsed = urlparse(item)
        base_host = urlparse(base).netloc
        if parsed.netloc != base_host:
            continue
        seen.add(item)
        continue
    seen.add(urljoin(base.rstrip("/") + "/", item.lstrip("/")))

for url in sorted(seen):
    print(url)
PY
)"; then
    echo "  Failed to parse asset URLs from live index document." >&2
    return 1
  fi

  if [[ -z "$urls" ]]; then
    echo "  No JS/CSS assets discovered in live index document." >&2
    return 1
  fi

  while IFS= read -r asset_url; do
    [[ -z "$asset_url" ]] && continue
    if ! curl -fsSI --max-time 15 "$asset_url" >/dev/null; then
      echo "  Missing asset referenced by index: $asset_url" >&2
      max_missing=1
    fi
  done <<< "$urls"

  if [[ "$max_missing" -ne 0 ]]; then
    echo "  Frontend integrity check failed: index references missing assets." >&2
    return 1
  fi

  echo "  Frontend integrity check passed."
}

backend_container_name_for_env() {
  local env_name="$1"

  case "$env_name" in
    dev)
      echo "uah-dev-backend"
      ;;
    beta)
      echo "uah-beta-backend"
      ;;
    *)
      echo "Unsupported environment '$env_name' for backend container lookup." >&2
      return 1
      ;;
  esac
}

wait_for_backend_exec_ready() {
  local env_name="$1"
  local backend_container="${2:-}"
  local max_attempts="${3:-10}"
  local attempt=1
  local delay=2

  if [[ -z "$backend_container" ]]; then
    backend_container="$(backend_container_name_for_env "$env_name")" || return 1
  fi

  while ((attempt <= max_attempts)); do
    if is_container_running "$backend_container" && docker exec "$backend_container" sh -lc 'cd /app && pwd >/dev/null' >/dev/null 2>&1; then
      return 0
    fi

    if ((attempt < max_attempts)); then
      echo "  Backend container '$backend_container' not ready for docker exec yet. Retrying in ${delay}s..."
      sleep "$delay"
    fi

    attempt=$((attempt + 1))
  done

  echo "Backend container '$backend_container' was not ready for docker exec after $max_attempts attempts." >&2
  return 1
}

run_alembic_upgrade_for_env() {
  local env_name="$1"
  local backend_container="${2:-}"

  if [[ -z "$backend_container" ]]; then
    backend_container="$(backend_container_name_for_env "$env_name")" || return 1
  fi

  echo "Running Alembic migrations in $backend_container..."
  docker exec "$backend_container" sh -lc 'cd /app && alembic upgrade head'
}

record_schema_reconcile_status() {
  local status="${1:-unknown}"
  local message="${2:-}"
  SCHEMA_RECONCILE_LAST_STATUS="$status"
  SCHEMA_RECONCILE_LAST_MESSAGE="$message"
}

print_schema_reconcile_summary() {
  local env_name="$1"
  local context="${2:-lifecycle}"
  echo "Schema reconcile summary [$env_name/$context]: ${SCHEMA_RECONCILE_LAST_STATUS} - ${SCHEMA_RECONCILE_LAST_MESSAGE}"
}

refresh_job_runtime_services() {
  local env_name="$1"
  local backend_container

  backend_container="$(backend_container_name_for_env "$env_name")" || return 1

  echo "Refreshing backend, celery worker, and celery beat for $env_name..."
  run_compose "$env_name" restart backend celery_worker celery_beat

  wait_for_backend_exec_ready "$env_name" "$backend_container" 10
}

run_live_schema_reconcile() {
  local env_name="$1"
  local require_running="${2:-true}"
  local backend_container

  backend_container="$(backend_container_name_for_env "$env_name")" || return 1
  record_schema_reconcile_status "running" "Starting Alembic reconcile for $env_name."

  if ! is_container_running "$backend_container"; then
    if [[ "$require_running" == "true" ]]; then
      record_schema_reconcile_status "failed" "Backend container '$backend_container' is not running."
      echo "Backend container '$backend_container' is not running; cannot apply Alembic migrations." >&2
      return 1
    fi

    record_schema_reconcile_status "skipped" "Backend container '$backend_container' is not running."
    echo "Backend container '$backend_container' is not running. Skipping post-sync Alembic reconcile."
    return 0
  fi

  if ! wait_for_backend_exec_ready "$env_name" "$backend_container" 10; then
    record_schema_reconcile_status "failed" "Backend container '$backend_container' was not ready for docker exec."
    return 1
  fi

  if ! run_alembic_upgrade_for_env "$env_name" "$backend_container"; then
    record_schema_reconcile_status "failed" "Alembic upgrade failed in '$backend_container'."
    echo "Alembic upgrade failed for $env_name." >&2
    return 1
  fi

  if ! refresh_job_runtime_services "$env_name"; then
    record_schema_reconcile_status "failed" "Runtime service refresh failed for $env_name."
    echo "Runtime service refresh failed for $env_name after Alembic upgrade." >&2
    return 1
  fi

  record_schema_reconcile_status "success" "Alembic upgrade and runtime refresh completed."
  echo "Schema reconcile completed for $env_name."
}

run_live_schema_reconcile_with_policy() {
  local env_name="$1"
  local require_running="${2:-true}"
  local context="${3:-start}"

  if run_live_schema_reconcile "$env_name" "$require_running"; then
    return 0
  fi

  if [[ "$env_name" == "dev" ]]; then
    echo "WARNING: Schema reconcile failed during '$context' in dev. Continuing startup flow."
    echo "WARNING DETAIL: ${SCHEMA_RECONCILE_LAST_MESSAGE}"
    return 0
  fi

  echo "Schema reconcile failed during '$context' in $env_name."
  echo "ERROR DETAIL: ${SCHEMA_RECONCILE_LAST_MESSAGE}" >&2
  return 1
}

run_sync_rebuild_if_requested() {
  local env_name="$1"
  local backend_container

  backend_container="$(backend_container_name_for_env "$env_name")" || return 1

  if [[ "$BUILD_MODE" == "none" ]]; then
    if is_container_running "$backend_container"; then
      echo "Backend container '$backend_container' is running. Applying live schema reconcile after sync..."
      run_live_schema_reconcile_with_policy "$env_name" true "sync"
      print_schema_reconcile_summary "$env_name" "sync"
      return $?
    fi

    echo "No rebuild requested after sync."
    echo "Backend container '$backend_container' is not running. Skipping post-sync Alembic reconcile."
    return
  fi

  if ! ensure_env_confirmation "$env_name" "sync-rebuild"; then
    echo "Sync rebuild cancelled by env safety confirmation."
    return 1
  fi

  echo "Running post-sync compose update ($(build_mode_label))..."
  preflight_startup "$env_name"
  run_compose_up_with_build_mode "$env_name"
  run_live_schema_reconcile_with_policy "$env_name" true "sync-rebuild"
  print_schema_reconcile_summary "$env_name" "sync-rebuild"
}

prepare_sync_branch() {
  git -C "$ROOT_DIR" fetch origin
  git -C "$ROOT_DIR" checkout dev
}

refresh_sync_blocker_snapshot() {
  local ahead_count
  local behind_count
  local line
  local ignored_count=0
  local filtered_status=""

  SYNC_BLOCKER_STATUS="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=all || true)"
  SYNC_BLOCKER_STATUS_FILTERED=""
  SYNC_BLOCKER_IGNORED_COUNT=0

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if [[ "$line" =~ landing/public/downloads/uah-browser-extension-alpha\.zip$ ]]; then
      ignored_count=$((ignored_count + 1))
      continue
    fi
    if [[ -n "$filtered_status" ]]; then
      filtered_status+=$'\n'
    fi
    filtered_status+="$line"
  done <<< "$SYNC_BLOCKER_STATUS"

  SYNC_BLOCKER_STATUS_FILTERED="$filtered_status"
  SYNC_BLOCKER_IGNORED_COUNT="$ignored_count"

  ahead_count="$(git -C "$ROOT_DIR" rev-list --count origin/dev..dev 2>/dev/null || echo 0)"
  behind_count="$(git -C "$ROOT_DIR" rev-list --count dev..origin/dev 2>/dev/null || echo 0)"

  if [[ "$ahead_count" =~ ^[0-9]+$ ]]; then
    SYNC_BLOCKER_AHEAD=$ahead_count
  else
    SYNC_BLOCKER_AHEAD=0
  fi

  if [[ "$behind_count" =~ ^[0-9]+$ ]]; then
    SYNC_BLOCKER_BEHIND=$behind_count
  else
    SYNC_BLOCKER_BEHIND=0
  fi

  if git -C "$ROOT_DIR" merge-base --is-ancestor dev origin/dev >/dev/null 2>&1; then
    SYNC_CAN_FAST_FORWARD=true
  else
    SYNC_CAN_FAST_FORWARD=false
  fi
}

sync_blockers_detected() {
  refresh_sync_blocker_snapshot

  if [[ -n "$SYNC_BLOCKER_STATUS_FILTERED" ]]; then
    return 0
  fi

  if [[ "$SYNC_CAN_FAST_FORWARD" != "true" ]]; then
    return 0
  fi

  return 1
}

print_sync_blocker_report() {
  local preview_limit=25
  local total_lines=0

  echo ""
  echo "Sync blocker detected. Safe sync cannot continue."
  echo "Repository: $ROOT_DIR"
  echo ""

  if [[ -n "$SYNC_BLOCKER_STATUS_FILTERED" ]]; then
    total_lines=$(printf '%s\n' "$SYNC_BLOCKER_STATUS_FILTERED" | sed '/^$/d' | wc -l | tr -d ' ')
    echo "Local changes ($total_lines):"
    printf '%s\n' "$SYNC_BLOCKER_STATUS_FILTERED" | sed -n "1,${preview_limit}p" | sed 's/^/  /'
    if ((total_lines > preview_limit)); then
      echo "  ... and $((total_lines - preview_limit)) more"
    fi
    echo ""
  fi

  if ((SYNC_BLOCKER_IGNORED_COUNT > 0)); then
    echo "Ignored local changes ($SYNC_BLOCKER_IGNORED_COUNT):"
    echo "  landing/public/downloads/uah-browser-extension-alpha.zip"
    echo ""
  fi

  if ((SYNC_BLOCKER_AHEAD > 0)); then
    echo "Local branch is ahead of origin/dev by $SYNC_BLOCKER_AHEAD commit(s):"
    git -C "$ROOT_DIR" --no-pager log --oneline --decorate -n 5 origin/dev..dev | sed 's/^/  /'
    if ((SYNC_BLOCKER_AHEAD > 5)); then
      echo "  ... and $((SYNC_BLOCKER_AHEAD - 5)) more"
    fi
    echo ""
  fi

  if [[ "$SYNC_CAN_FAST_FORWARD" != "true" ]]; then
    if ((SYNC_BLOCKER_AHEAD > 0 && SYNC_BLOCKER_BEHIND > 0)); then
      echo "Branch state: diverged from origin/dev (ahead $SYNC_BLOCKER_AHEAD, behind $SYNC_BLOCKER_BEHIND)."
    elif ((SYNC_BLOCKER_AHEAD > 0)); then
      echo "Branch state: local dev has commits not on origin/dev (ahead $SYNC_BLOCKER_AHEAD)."
    else
      echo "Branch state: fast-forward check failed."
    fi
    echo ""
  fi
}

confirm_hard_sync() {
  if [[ -t 0 ]]; then
    echo "This will discard local changes and local commits in $ROOT_DIR."
    read -rp "Type RESET to continue: " confirmation
    if [[ "$confirmation" != "RESET" ]]; then
      echo "Hard sync cancelled."
      return 1
    fi
  fi

  return 0
}

run_hard_sync_reset() {
  echo "[$(date -u)] Running hard sync (reset --hard origin/dev)..."
  git -C "$ROOT_DIR" reset --hard origin/dev
}

run_hard_sync_flow() {
  local show_snapshot="${1:-true}"

  prepare_sync_branch
  refresh_sync_blocker_snapshot

  if [[ "$show_snapshot" == "true" ]] && ([[ -n "$SYNC_BLOCKER_STATUS" ]] || ((SYNC_BLOCKER_AHEAD > 0)) || [[ "$SYNC_CAN_FAST_FORWARD" != "true" ]]); then
    print_sync_blocker_report
  fi

  if ! confirm_hard_sync; then
    return 1
  fi

  run_hard_sync_reset
}

prompt_sync_blocker_resolution() {
  while true; do
    echo "Choose next step:"
    echo "  1) abort  - exit without syncing"
    echo "  2) force  - hard sync (reset --hard origin/dev)"
    echo "  3) status - show full git status"
    echo "  4) diff   - show diff summary"
    read -rp "Choice [1-4]: " choice

    case "${choice,,}" in
      1|a|abort)
        echo "Sync aborted."
        return 1
        ;;
      2|f|force|hard)
        if run_hard_sync_flow false; then
          return 0
        fi
        ;;
      3|s|status)
        git -C "$ROOT_DIR" status -sb
        ;;
      4|d|diff)
        echo "--- Unstaged diff summary ---"
        git -C "$ROOT_DIR" --no-pager diff --stat || true
        echo "--- Staged diff summary ---"
        git -C "$ROOT_DIR" --no-pager diff --stat --cached || true
        ;;
      *)
        echo "Invalid selection."
        ;;
    esac

    echo ""
  done
}

run_safe_sync_flow() {
  local env_name="$1"

  echo "[$(date -u)] Running safe sync (fast-forward only)..."
  prepare_sync_branch

  if sync_blockers_detected; then
    print_sync_blocker_report

    if [[ -t 0 ]]; then
      if prompt_sync_blocker_resolution; then
        return 0
      fi
      return 1
    fi

    echo "Safe sync aborted in non-interactive mode due to blockers."
    echo "Run '$0 $env_name sync hard' for an explicit hard reset."
    return 1
  fi

  git -C "$ROOT_DIR" pull --ff-only origin dev
}

dev_sync() {
  local mode="${1:-safe}"

  case "$mode" in
    safe|ff|fast-forward)
      run_safe_sync_flow dev
      ;;
    hard|reset)
      run_hard_sync_flow true
      ;;
    *)
      echo "Unknown sync mode '$mode'. Use safe or hard." >&2
      exit 1
      ;;
  esac
}

normalize_bool_value() {
  local value="${1:-}"

  value="${value,,}"
  case "$value" in
    1|true|yes|on)
      echo "true"
      ;;
    0|false|no|off|"")
      echo "false"
      ;;
    *)
      echo "$value"
      ;;
  esac
}

is_truthy_value() {
  [[ "$(normalize_bool_value "$1")" == "true" ]]
}

display_env_value() {
  local value="${1:-}"

  if [[ -z "$value" ]]; then
    echo "<empty>"
    return
  fi

  echo "$value"
}

clip_text() {
  local value="${1:-}"
  local max_len="${2:-28}"

  if (( ${#value} <= max_len )); then
    echo "$value"
    return
  fi

  echo "${value:0:max_len-3}..."
}

env_policy_expected_value() {
  local env_name="$1"
  local key="$2"

  case "$key" in
    VITE_LOCAL_MODE)
      echo "backend"
      ;;
    DEV_AUTH_TEST_ACCOUNT_ENABLED)
      if [[ "$env_name" == "dev" ]]; then
        echo "true"
      else
        echo "false"
      fi
      ;;
    DEV_AUTH_TEST_IS_DEVELOPER)
      if [[ "$env_name" == "dev" ]]; then
        echo "true"
      else
        echo "false"
      fi
      ;;
    VITE_AUTH_NAMESPACE)
      echo "$env_name"
      ;;
    USE_LOCAL_PIPELINE)
      echo "false"
      ;;
    LOCAL_OCR_URL|LOCAL_LLM_URL)
      echo "http://10.8.0.8:11434"
      ;;
    REDIS_ENABLED)
      echo "false"
      ;;
    REDIS_URL)
      if [[ "$env_name" == "beta" ]]; then
        echo "redis://uah-beta-redis:6379/0"
      elif [[ "$env_name" == "dev" ]]; then
        echo "redis://uah-redis:6379/0"
      else
        echo "redis://uah-prod-redis:6379/0"
      fi
      ;;
    ENVIRONMENT)
      if [[ "$env_name" == "dev" ]]; then
        echo "development"
      elif [[ "$env_name" == "beta" ]]; then
        echo "beta"
      else
        echo "production"
      fi
      ;;
    ENV)
      echo "$env_name"
      ;;
    COMPOSE_PROJECT_NAME)
      echo "uah-$env_name"
      ;;
    *)
      echo ""
      ;;
  esac
}

env_policy_severity_rank() {
  case "$1" in
    error)
      echo 3
      ;;
    warn)
      echo 2
      ;;
    info)
      echo 1
      ;;
    *)
      echo 0
      ;;
  esac
}

env_policy_reset_state() {
  ENV_POLICY_ERROR_COUNT=0
  ENV_POLICY_WARN_COUNT=0
  ENV_POLICY_INFO_COUNT=0
  ENV_POLICY_CURRENT_VALUES=()
  ENV_POLICY_RECOMMENDED_VALUES=()
  ENV_POLICY_FINDING_LEVEL=()
  ENV_POLICY_PENDING_VALUES=()
  ENV_POLICY_MESSAGES=()
}

env_policy_add_finding() {
  local severity="$1"
  local key="$2"
  local message="$3"
  local existing_level="${ENV_POLICY_FINDING_LEVEL[$key]-}"
  local existing_rank
  local incoming_rank

  incoming_rank="$(env_policy_severity_rank "$severity")"
  existing_rank="$(env_policy_severity_rank "$existing_level")"

  if (( incoming_rank > existing_rank )); then
    ENV_POLICY_FINDING_LEVEL["$key"]="$severity"
  fi

  ENV_POLICY_MESSAGES+=("$severity|$key|$message")

  case "$severity" in
    error)
      ENV_POLICY_ERROR_COUNT=$((ENV_POLICY_ERROR_COUNT + 1))
      ;;
    warn)
      ENV_POLICY_WARN_COUNT=$((ENV_POLICY_WARN_COUNT + 1))
      ;;
    info)
      ENV_POLICY_INFO_COUNT=$((ENV_POLICY_INFO_COUNT + 1))
      ;;
  esac
}

env_policy_evaluate() {
  local env_name="$1"
  local key=""
  local current=""
  local expected=""
  local local_mode=""
  local dev_auth=""
  local namespace=""
  local env_var=""
  local env_name_var=""
  local compose_project=""
  local use_local_pipeline=""
  local local_ocr_url=""
  local local_llm_url=""
  local redis_enabled=""
  local redis_url=""

  env_policy_reset_state

  for key in "${ENV_POLICY_KEYS[@]}"; do
    current="$(get_env_value_or_default "$key" "")"
    expected="$(env_policy_expected_value "$env_name" "$key")"
    ENV_POLICY_CURRENT_VALUES["$key"]="$current"
    ENV_POLICY_RECOMMENDED_VALUES["$key"]="$expected"
  done

  local_mode="${ENV_POLICY_CURRENT_VALUES[VITE_LOCAL_MODE]-}"
  local_mode="${local_mode,,}"
  if [[ "$local_mode" == "mock" ]]; then
    if [[ "$env_name" == "dev" ]]; then
      env_policy_add_finding "warn" "VITE_LOCAL_MODE" "VITE_LOCAL_MODE=mock enables local mock data (localdev profile)."
    else
      env_policy_add_finding "error" "VITE_LOCAL_MODE" "VITE_LOCAL_MODE=mock is unsafe for $env_name and can start fake-data mode."
    fi
  elif [[ "$local_mode" != "backend" && -n "$local_mode" ]]; then
    env_policy_add_finding "warn" "VITE_LOCAL_MODE" "VITE_LOCAL_MODE should normally be backend (current: $local_mode)."
  fi

  dev_auth="${ENV_POLICY_CURRENT_VALUES[DEV_AUTH_TEST_ACCOUNT_ENABLED]-}"
  if is_truthy_value "$dev_auth"; then
    if [[ "$env_name" == "dev" ]]; then
      env_policy_add_finding "warn" "DEV_AUTH_TEST_ACCOUNT_ENABLED" "Dev auth test account is enabled. Keep only for intentional local testing."
    else
      env_policy_add_finding "error" "DEV_AUTH_TEST_ACCOUNT_ENABLED" "DEV_AUTH_TEST_ACCOUNT_ENABLED=true is unsafe for $env_name."
    fi
  fi

  namespace="${ENV_POLICY_CURRENT_VALUES[VITE_AUTH_NAMESPACE]-}"
  namespace="${namespace,,}"
  if [[ -z "$namespace" ]]; then
    env_policy_add_finding "warn" "VITE_AUTH_NAMESPACE" "VITE_AUTH_NAMESPACE is empty."
  elif [[ "$namespace" != "$env_name" ]]; then
    if [[ "$env_name" == "dev" ]]; then
      env_policy_add_finding "warn" "VITE_AUTH_NAMESPACE" "VITE_AUTH_NAMESPACE should usually be dev in dev context."
    else
      env_policy_add_finding "error" "VITE_AUTH_NAMESPACE" "VITE_AUTH_NAMESPACE must match $env_name (current: $namespace)."
    fi
  fi

  env_name_var="${ENV_POLICY_CURRENT_VALUES[ENVIRONMENT]-}"
  env_name_var="$(normalize_environment_label "$env_name_var")"
  if [[ -n "$env_name_var" && "$env_name_var" != "$env_name" ]]; then
    env_policy_add_finding "warn" "ENVIRONMENT" "ENVIRONMENT points to $env_name_var while current context is $env_name."
  fi

  env_var="${ENV_POLICY_CURRENT_VALUES[ENV]-}"
  env_var="$(normalize_environment_label "$env_var")"
  if [[ -n "$env_var" && "$env_var" != "$env_name" ]]; then
    env_policy_add_finding "warn" "ENV" "ENV points to $env_var while current context is $env_name."
  fi

  compose_project="${ENV_POLICY_CURRENT_VALUES[COMPOSE_PROJECT_NAME]-}"
  compose_project="${compose_project,,}"
  if [[ -z "$compose_project" ]]; then
    env_policy_add_finding "warn" "COMPOSE_PROJECT_NAME" "COMPOSE_PROJECT_NAME is empty; routing may be ambiguous."
  elif [[ "$compose_project" != *"$env_name"* ]]; then
    env_policy_add_finding "warn" "COMPOSE_PROJECT_NAME" "COMPOSE_PROJECT_NAME ($compose_project) does not include $env_name."
  fi

  use_local_pipeline="${ENV_POLICY_CURRENT_VALUES[USE_LOCAL_PIPELINE]-}"
  if is_truthy_value "$use_local_pipeline"; then
    env_policy_add_finding "warn" "USE_LOCAL_PIPELINE" "USE_LOCAL_PIPELINE is enabled; ensure Desktop Ollama route is intentional."

    local_ocr_url="${ENV_POLICY_CURRENT_VALUES[LOCAL_OCR_URL]-}"
    local_llm_url="${ENV_POLICY_CURRENT_VALUES[LOCAL_LLM_URL]-}"
    if [[ -z "$local_ocr_url" ]]; then
      env_policy_add_finding "warn" "LOCAL_OCR_URL" "LOCAL_OCR_URL is empty while USE_LOCAL_PIPELINE=true."
    fi
    if [[ -z "$local_llm_url" ]]; then
      env_policy_add_finding "warn" "LOCAL_LLM_URL" "LOCAL_LLM_URL is empty while USE_LOCAL_PIPELINE=true."
    fi
  fi

  redis_enabled="${ENV_POLICY_CURRENT_VALUES[REDIS_ENABLED]-}"
  redis_url="${ENV_POLICY_CURRENT_VALUES[REDIS_URL]-}"
  if is_truthy_value "$redis_enabled" && [[ -z "$redis_url" ]]; then
    env_policy_add_finding "warn" "REDIS_URL" "REDIS_URL is empty while REDIS_ENABLED=true."
  fi
}

env_policy_print_findings() {
  local finding
  local severity
  local key
  local message

  if (( ${#ENV_POLICY_MESSAGES[@]} == 0 )); then
    debug_print_ok "No risky env findings detected."
    return
  fi

  for finding in "${ENV_POLICY_MESSAGES[@]}"; do
    severity="${finding%%|*}"
    key="${finding#*|}"
    key="${key%%|*}"
    message="${finding#*|*|}"
    case "$severity" in
      error)
        debug_print_error "$key :: $message"
        ;;
      warn)
        debug_print_warn "$key :: $message"
        ;;
      *)
        debug_print_section "$key :: $message"
        ;;
    esac
  done
}

env_policy_key_description() {
  local env_name="$1"
  local key="$2"

  case "$key" in
    VITE_LOCAL_MODE)
      echo "Controls frontend data source mode. backend uses real APIs; mock enables fake local data."
      ;;
    DEV_AUTH_TEST_ACCOUNT_ENABLED)
      if [[ "$env_name" == "dev" ]]; then
        echo "Allows a seeded dev auth account for local testing. Keep disabled unless intentionally using test login."
      else
        echo "Must stay disabled outside dev to prevent test-account auth paths in $env_name."
      fi
      ;;
    DEV_AUTH_TEST_IS_DEVELOPER)
      echo "Marks the seeded dev auth account as developer-capable so frontend debug tools can be exercised safely."
      ;;
    VITE_AUTH_NAMESPACE)
      echo "Sets browser auth storage namespace. Must match the active environment to avoid cross-env auth leakage."
      ;;
    USE_LOCAL_PIPELINE)
      echo "Routes parsing/LLM calls to local desktop pipeline endpoints over VPN when enabled."
      ;;
    LOCAL_OCR_URL)
      echo "Desktop OCR endpoint used only when USE_LOCAL_PIPELINE is enabled."
      ;;
    LOCAL_LLM_URL)
      echo "Desktop LLM endpoint used only when USE_LOCAL_PIPELINE is enabled."
      ;;
    REDIS_ENABLED)
      echo "Enables Redis-backed queue and worker coordination behavior."
      ;;
    REDIS_URL)
      echo "Redis connection string used by queueing and background parse job processing."
      ;;
    ENVIRONMENT)
      echo "Primary runtime environment label for backend safety checks and config gating."
      ;;
    ENV)
      echo "Script-facing shorthand environment label. Keep aligned with ENVIRONMENT and compose context."
      ;;
    COMPOSE_PROJECT_NAME)
      echo "Docker compose namespace controlling container/network names and environment isolation."
      ;;
    *)
      echo ""
      ;;
  esac
}

env_policy_effective_value() {
  local key="$1"

  if [[ -n "${ENV_POLICY_PENDING_VALUES[$key]+set}" ]]; then
    echo "${ENV_POLICY_PENDING_VALUES[$key]-}"
    return
  fi

  echo "${ENV_POLICY_CURRENT_VALUES[$key]-}"
}

env_policy_pending_count() {
  local key
  local count=0

  for key in "${ENV_POLICY_KEYS[@]}"; do
    if [[ -n "${ENV_POLICY_PENDING_VALUES[$key]+set}" ]]; then
      count=$((count + 1))
    fi
  done

  echo "$count"
}

env_policy_print_matrix() {
  local env_name="$1"
  local key
  local current
  local recommended
  local level
  local marker
  local impact
  local index=1

  printf "  %-3s %-28s %-20s %-20s %-7s %-34s\n" "#" "Key" "Current" "Suggested" "State" "Impact"
  printf "  %-3s %-28s %-20s %-20s %-7s %-34s\n" "---" "----------------------------" "--------------------" "--------------------" "-------" "----------------------------------"

  for key in "${ENV_POLICY_KEYS[@]}"; do
    current="$(display_env_value "${ENV_POLICY_CURRENT_VALUES[$key]-}")"
    recommended="$(display_env_value "${ENV_POLICY_RECOMMENDED_VALUES[$key]-}")"
    level="${ENV_POLICY_FINDING_LEVEL[$key]-ok}"
    marker="$level"
    impact="$(env_policy_key_description "$env_name" "$key")"
    printf "  %-3s %-28s %-20s %-20s %-7s %-34s\n" "$index" "$key" "$(clip_text "$current" 20)" "$(clip_text "$recommended" 20)" "$marker" "$(clip_text "$impact" 34)"
    index=$((index + 1))
  done
}

env_policy_set_pending_value() {
  local key="$1"
  local value="$2"
  ENV_POLICY_PENDING_VALUES["$key"]="$value"
}

env_policy_collect_autofix_values() {
  local key
  local current
  local recommended
  local level

  ENV_POLICY_PENDING_VALUES=()
  for key in "${ENV_POLICY_KEYS[@]}"; do
    level="${ENV_POLICY_FINDING_LEVEL[$key]-}"
    if [[ "$level" != "error" && "$level" != "warn" ]]; then
      continue
    fi

    current="${ENV_POLICY_CURRENT_VALUES[$key]-}"
    recommended="${ENV_POLICY_RECOMMENDED_VALUES[$key]-}"
    if [[ -n "$recommended" && "$current" != "$recommended" ]]; then
      env_policy_set_pending_value "$key" "$recommended"
    fi
  done
}

env_policy_collect_mismatched_keys() {
  local key
  local current
  local recommended

  ENV_POLICY_MISMATCHED_KEYS=()

  for key in "${ENV_POLICY_KEYS[@]}"; do
    current="${ENV_POLICY_CURRENT_VALUES[$key]-}"
    recommended="${ENV_POLICY_RECOMMENDED_VALUES[$key]-}"

    if [[ -z "$recommended" || "$current" == "$recommended" ]]; then
      continue
    fi

    ENV_POLICY_MISMATCHED_KEYS+=("$key")
  done
}

env_policy_print_key_findings() {
  local key="$1"
  local finding
  local severity
  local finding_key
  local message
  local found=0

  for finding in "${ENV_POLICY_MESSAGES[@]}"; do
    severity="${finding%%|*}"
    finding_key="${finding#*|}"
    finding_key="${finding_key%%|*}"
    message="${finding#*|*|}"

    if [[ "$finding_key" != "$key" ]]; then
      continue
    fi

    found=1
    case "$severity" in
      error)
        debug_print_error "$message"
        ;;
      warn)
        debug_print_warn "$message"
        ;;
      *)
        debug_print_section "$message"
        ;;
    esac
  done

  if (( found == 0 )); then
    echo "  (No active findings for this key.)"
  fi
}

env_policy_print_pending_summary() {
  local env_name="$1"
  local key
  local index=1
  local current
  local pending
  local impact

  printf "  %-3s %-28s %-20s %-20s %-32s\n" "#" "Key" "Current" "Pending" "Impact"
  printf "  %-3s %-28s %-20s %-20s %-32s\n" "---" "----------------------------" "--------------------" "--------------------" "--------------------------------"

  for key in "${ENV_POLICY_KEYS[@]}"; do
    if [[ -z "${ENV_POLICY_PENDING_VALUES[$key]+set}" ]]; then
      continue
    fi

    current="$(display_env_value "${ENV_POLICY_CURRENT_VALUES[$key]-}")"
    pending="$(display_env_value "${ENV_POLICY_PENDING_VALUES[$key]-}")"
    impact="$(env_policy_key_description "$env_name" "$key")"
    printf "  %-3s %-28s %-20s %-20s %-32s\n" "$index" "$key" "$(clip_text "$current" 20)" "$(clip_text "$pending" 20)" "$(clip_text "$impact" 32)"
    index=$((index + 1))
  done

  if (( index == 1 )); then
    echo "  (No staged env updates.)"
  fi
}

env_policy_print_manual_key_menu() {
  local env_name="$1"
  local key
  local current
  local recommended
  local pending
  local impact
  local marker
  local index=1

  for key in "${ENV_POLICY_MISMATCHED_KEYS[@]}"; do
    current="$(display_env_value "${ENV_POLICY_CURRENT_VALUES[$key]-}")"
    recommended="$(display_env_value "${ENV_POLICY_RECOMMENDED_VALUES[$key]-}")"
    impact="$(env_policy_key_description "$env_name" "$key")"

    if [[ -n "${ENV_POLICY_PENDING_VALUES[$key]+set}" ]]; then
      pending="$(display_env_value "${ENV_POLICY_PENDING_VALUES[$key]-}")"
      marker="pending"
    else
      pending="<none>"
      marker="${ENV_POLICY_FINDING_LEVEL[$key]-ok}"
    fi

    printf "  %2d) %-28s state=%s\n" "$index" "$key" "$marker"
    printf "      current=%s\n" "$(clip_text "$current" 56)"
    printf "      suggested=%s\n" "$(clip_text "$recommended" 56)"
    printf "      staged=%s\n" "$(clip_text "$pending" 56)"
    printf "      impact=%s\n" "$(clip_text "$impact" 90)"
    index=$((index + 1))
  done
}

env_policy_edit_key_interactive() {
  local env_name="$1"
  local key="$2"
  local current="$3"
  local recommended="$4"
  local impact
  local existing_pending=""
  local base_value
  local selected_value
  local choice

  while true; do
    impact="$(env_policy_key_description "$env_name" "$key")"

    if [[ -n "${ENV_POLICY_PENDING_VALUES[$key]+set}" ]]; then
      existing_pending="${ENV_POLICY_PENDING_VALUES[$key]-}"
      base_value="$existing_pending"
    else
      existing_pending=""
      base_value="$current"
    fi

    debug_header "$env_name" "Env Safety :: Edit $key"
    debug_print_section "Key details"
    echo "  Key            : $key"
    echo "  Current value  : $(display_env_value "$current")"
    echo "  Suggested value: $(display_env_value "$recommended")"
    if [[ -n "${ENV_POLICY_PENDING_VALUES[$key]+set}" ]]; then
      echo "  Staged value   : $(display_env_value "$existing_pending")"
    else
      echo "  Staged value   : <none>"
    fi
    echo "  Impact         : $(clip_text "$impact" 110)"
    echo ""
    debug_print_section "Findings"
    env_policy_print_key_findings "$key"
    echo ""

    read -rp "  New value (blank keeps current staged/current value): " selected_value
    if [[ -z "$selected_value" ]]; then
      selected_value="$base_value"
    fi

    echo ""
    echo "  Proposed value: $(display_env_value "$selected_value")"
    echo "  Actions"
    echo "    1) Save proposed value"
    echo "    2) Save suggested value"
    echo "    3) Back to key list"
    echo "    4) Cancel manual review"
    read -rp "  Choice [1-4]: " choice

    case "$choice" in
      1)
        if [[ "$selected_value" == "$current" ]]; then
          unset 'ENV_POLICY_PENDING_VALUES[$key]'
        else
          env_policy_set_pending_value "$key" "$selected_value"
        fi
        return 0
        ;;
      2)
        if [[ "$recommended" == "$current" ]]; then
          unset 'ENV_POLICY_PENDING_VALUES[$key]'
        else
          env_policy_set_pending_value "$key" "$recommended"
        fi
        return 0
        ;;
      3)
        return 2
        ;;
      4)
        return 1
        ;;
      *)
        debug_print_warn "Invalid choice."
        debug_press_enter
        ;;
    esac
  done
}

env_policy_manual_review() {
  local env_name="$1"
  local choice
  local key_index
  local key
  local current
  local recommended
  local pending_count
  local edit_result=0

  ENV_POLICY_PENDING_VALUES=()

  while true; do
    env_policy_collect_mismatched_keys

    debug_header "$env_name" "Env Safety :: Manual Editor"
    debug_print_section "Numbered key list (mismatches only)"

    if (( ${#ENV_POLICY_MISMATCHED_KEYS[@]} == 0 )); then
      debug_print_ok "All tracked keys already match suggested values."
      echo ""
      echo "  1) Back"
      read -rp "  Choice [1]: " choice
      ENV_POLICY_PENDING_VALUES=()
      return 1
    fi

    env_policy_print_manual_key_menu "$env_name"
    echo ""
    debug_print_section "Staged updates"
    env_policy_print_pending_summary "$env_name"
    pending_count="$(env_policy_pending_count)"

    echo ""
    echo "  Choose next step:"
    echo "    <number>) Edit key"
    echo "    0) Save staged updates and continue"
    echo "    b) Back without applying"
    echo "    c) Cancel manual review"
    read -rp "  Choice: " choice

    case "${choice,,}" in
      0|save|done)
        if (( pending_count == 0 )); then
          debug_print_warn "No staged updates. Edit at least one key before saving."
          debug_press_enter
          continue
        fi
        return 0
        ;;
      b|back)
        ENV_POLICY_PENDING_VALUES=()
        return 1
        ;;
      c|cancel)
        ENV_POLICY_PENDING_VALUES=()
        echo "Manual review cancelled."
        return 1
        ;;
      *)
        if [[ "$choice" =~ ^[0-9]+$ ]]; then
          key_index=$((choice - 1))
          if (( key_index < 0 || key_index >= ${#ENV_POLICY_MISMATCHED_KEYS[@]} )); then
            debug_print_warn "Invalid key number."
            debug_press_enter
            continue
          fi

          key="${ENV_POLICY_MISMATCHED_KEYS[$key_index]}"
          current="${ENV_POLICY_CURRENT_VALUES[$key]-}"
          recommended="${ENV_POLICY_RECOMMENDED_VALUES[$key]-}"

          if env_policy_edit_key_interactive "$env_name" "$key" "$current" "$recommended"; then
            continue
          fi

          edit_result=$?
          if (( edit_result == 1 )); then
            ENV_POLICY_PENDING_VALUES=()
            echo "Manual review cancelled."
            return 1
          fi

          continue
        fi

        debug_print_warn "Invalid selection."
        debug_press_enter
        ;;
    esac
  done
}

env_policy_guided_autofix_for_key() {
  local env_name="$1"
  local key="$2"
  local step="$3"
  local total="$4"
  local current
  local recommended
  local impact
  local choice
  local custom_value
  local custom_choice

  current="${ENV_POLICY_CURRENT_VALUES[$key]-}"
  recommended="${ENV_POLICY_RECOMMENDED_VALUES[$key]-}"

  while true; do
    impact="$(env_policy_key_description "$env_name" "$key")"

    debug_header "$env_name" "Env Safety :: Suggested Fix $step/$total"
    debug_print_section "Confirm suggested update"
    echo "  Key            : $key"
    echo "  Current value  : $(display_env_value "$current")"
    echo "  Suggested value: $(display_env_value "$recommended")"
    echo "  Impact         : $(clip_text "$impact" 110)"
    echo ""
    debug_print_section "Findings"
    env_policy_print_key_findings "$key"
    echo ""
    echo "  Actions"
    echo "    1) Stage suggested value"
    echo "    2) Enter custom value"
    echo "    3) Skip this suggested fix"
    echo "    4) Cancel suggested-fix flow"
    read -rp "  Choice [1-4]: " choice

    case "$choice" in
      1)
        env_policy_set_pending_value "$key" "$recommended"
        return 0
        ;;
      2)
        read -rp "  Custom value for $key: " custom_value
        echo ""
        echo "  Proposed custom value: $(display_env_value "$custom_value")"
        echo "    1) Save custom value"
        echo "    2) Back"
        echo "    3) Cancel suggested-fix flow"
        read -rp "  Choice [1-3]: " custom_choice

        case "$custom_choice" in
          1)
            if [[ "$custom_value" == "$current" ]]; then
              unset 'ENV_POLICY_PENDING_VALUES[$key]'
            else
              env_policy_set_pending_value "$key" "$custom_value"
            fi
            return 0
            ;;
          2)
            continue
            ;;
          3)
            return 1
            ;;
          *)
            debug_print_warn "Invalid choice."
            debug_press_enter
            ;;
        esac
        ;;
      3)
        unset 'ENV_POLICY_PENDING_VALUES[$key]'
        return 0
        ;;
      4)
        return 1
        ;;
      *)
        debug_print_warn "Invalid choice."
        debug_press_enter
        ;;
    esac
  done
}

env_policy_guided_autofix() {
  local env_name="$1"
  local key
  local level
  local current
  local recommended
  local choice
  local pending_count
  local index=0
  local -a autofix_keys=()

  for key in "${ENV_POLICY_KEYS[@]}"; do
    level="${ENV_POLICY_FINDING_LEVEL[$key]-}"
    if [[ "$level" != "error" && "$level" != "warn" ]]; then
      continue
    fi

    current="${ENV_POLICY_CURRENT_VALUES[$key]-}"
    recommended="${ENV_POLICY_RECOMMENDED_VALUES[$key]-}"
    if [[ -z "$recommended" || "$current" == "$recommended" ]]; then
      continue
    fi

    autofix_keys+=("$key")
  done

  if (( ${#autofix_keys[@]} == 0 )); then
    debug_print_ok "No suggested fixes are needed."
    return 2
  fi

  ENV_POLICY_PENDING_VALUES=()

  for key in "${autofix_keys[@]}"; do
    index=$((index + 1))
    if ! env_policy_guided_autofix_for_key "$env_name" "$key" "$index" "${#autofix_keys[@]}"; then
      ENV_POLICY_PENDING_VALUES=()
      return 1
    fi
  done

  while true; do
    debug_header "$env_name" "Env Safety :: Suggested Fix Summary"
    debug_print_section "Selected updates"
    env_policy_print_pending_summary "$env_name"
    pending_count="$(env_policy_pending_count)"
    echo ""
    echo "  Choose next step:"
    echo "    1) Apply selected updates"
    echo "    2) Return without applying"
    read -rp "  Choice [1-2]: " choice

    case "$choice" in
      1)
        if (( pending_count == 0 )); then
          debug_print_warn "No updates selected to apply."
          debug_press_enter
          return 2
        fi
        return 0
        ;;
      2)
        ENV_POLICY_PENDING_VALUES=()
        return 1
        ;;
      *)
        debug_print_warn "Invalid choice."
        debug_press_enter
        ;;
    esac
  done
}

env_file_set_key_value() {
  local file_path="$1"
  local key="$2"
  local value="$3"
  local tmp_file

  tmp_file="$(mktemp)"

  awk -v key="$key" -v value="$value" '
    BEGIN { updated = 0 }
    {
      line = $0
      if (line ~ /^[[:space:]]*#/ || index(line, "=") == 0) {
        print line
        next
      }

      k = substr(line, 1, index(line, "=") - 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", k)

      if (k == key) {
        if (updated == 0) {
          print key "=" value
          updated = 1
        }
        next
      }

      print line
    }
    END {
      if (updated == 0) {
        print key "=" value
      }
    }
  ' "$file_path" > "$tmp_file"

  mv "$tmp_file" "$file_path"
}

env_policy_apply_pending_updates() {
  local env_file="$ROOT_DIR/.env"
  local backup_file
  local key
  local value
  local applied_count=0

  if (( ${#ENV_POLICY_PENDING_VALUES[@]} == 0 )); then
    echo "No pending env changes to apply."
    return 0
  fi

  if [[ ! -f "$env_file" ]]; then
    touch "$env_file"
  fi

  backup_file="$env_file.bak.$(date +%Y%m%d%H%M%S)"
  cp "$env_file" "$backup_file"

  for key in "${ENV_POLICY_KEYS[@]}"; do
    value="${ENV_POLICY_PENDING_VALUES[$key]-}"
    if [[ -z "${ENV_POLICY_PENDING_VALUES[$key]+set}" ]]; then
      continue
    fi
    env_file_set_key_value "$env_file" "$key" "$value"
    applied_count=$((applied_count + 1))
  done

  echo "Applied $applied_count env update(s). Backup: $backup_file"
  return 0
}

ensure_env_confirmation() {
  local env_name="$1"
  local action_name="$2"
  local mode="${3:-required}"
  local choice
  local guided_autofix_result=0

  if [[ "$ENV_CONFIRMATION_APPROVED" == true && "$ENV_CONFIRMATION_ENV" == "$env_name" ]]; then
    return 0
  fi

  env_policy_evaluate "$env_name"

  if [[ "$mode" == "preview" && ! -t 0 ]]; then
    return 0
  fi

  if [[ "$mode" != "preview" && ! -t 0 ]]; then
    if (( ENV_POLICY_ERROR_COUNT > 0 )); then
      echo "Env safety check failed for action '$action_name' in non-interactive mode." >&2
      env_policy_print_findings >&2
      echo "Run interactively to use abort/autofix/continue options: bash scripts/uah.sh" >&2
      return 1
    fi
    return 0
  fi

  if (( ENV_POLICY_ERROR_COUNT == 0 && ENV_POLICY_WARN_COUNT == 0 )) && [[ "$mode" != "preview" ]]; then
    ENV_CONFIRMATION_APPROVED=true
    ENV_CONFIRMATION_ENV="$env_name"
    return 0
  fi

  while true; do
    debug_header "$env_name" "Env Safety :: $action_name"
    debug_print_section "Current vs suggested non-sensitive values"
    env_policy_print_matrix "$env_name"
    echo ""
    debug_print_section "Findings"
    env_policy_print_findings
    echo ""
    echo "  Choose next step:"
    echo "    1) Continue with current values"
    echo "    2) Guided suggested fixes (confirm each key)"
    echo "    3) Numbered manual key editor"
    echo "    4) Abort"
    read -rp "  Choice [1-4]: " choice

    case "$choice" in
      1)
        if [[ "$env_name" == "prod" && $ENV_POLICY_ERROR_COUNT -gt 0 ]]; then
          debug_print_error "Continue is blocked for prod while critical findings exist."
          debug_press_enter
          continue
        fi
        ENV_CONFIRMATION_APPROVED=true
        ENV_CONFIRMATION_ENV="$env_name"
        return 0
        ;;
      2)
        if env_policy_guided_autofix "$env_name"; then
          guided_autofix_result=0
        else
          guided_autofix_result=$?
        fi

        if (( guided_autofix_result != 0 )); then
          if (( guided_autofix_result == 1 )); then
            debug_print_warn "Suggested-fix flow cancelled."
          else
            debug_print_warn "No selected updates to apply."
          fi
          debug_press_enter
          continue
        fi

        if ! env_policy_apply_pending_updates; then
          debug_print_error "Suggested-fix apply failed."
          debug_press_enter
          continue
        fi
        env_policy_evaluate "$env_name"
        if (( ENV_POLICY_ERROR_COUNT == 0 && ENV_POLICY_WARN_COUNT == 0 )); then
          ENV_CONFIRMATION_APPROVED=true
          ENV_CONFIRMATION_ENV="$env_name"
          return 0
        fi
        debug_print_warn "Suggested fixes applied, but some findings remain."
        debug_press_enter
        ;;
      3)
        if ! env_policy_manual_review "$env_name"; then
          debug_press_enter
          continue
        fi
        if ! env_policy_apply_pending_updates; then
          debug_print_error "Manual update apply failed."
          debug_press_enter
          continue
        fi
        env_policy_evaluate "$env_name"
        if (( ENV_POLICY_ERROR_COUNT == 0 && ENV_POLICY_WARN_COUNT == 0 )); then
          ENV_CONFIRMATION_APPROVED=true
          ENV_CONFIRMATION_ENV="$env_name"
          return 0
        fi
        debug_print_warn "Updates applied. Review remaining findings before continuing."
        debug_press_enter
        ;;
      4)
        return 1
        ;;
      *)
        debug_print_warn "Invalid choice."
        debug_press_enter
        ;;
    esac
  done
}

provider_known() {
  local provider_name="${1:-}"
  [[ -n "$provider_name" && -n "${PROVIDER_LABELS[$provider_name]+set}" ]]
}

provider_label() {
  local provider_name="$1"
  echo "${PROVIDER_LABELS[$provider_name]-$provider_name}"
}

provider_sweep_mode() {
  local provider_name="$1"
  echo "${PROVIDER_SWEEP_MODES[$provider_name]-unknown}"
}

provider_default_state() {
  local provider_name="$1"
  echo "${PROVIDER_DEFAULT_STATES[$provider_name]-dormant}"
}

provider_mutation_allowed() {
  local provider_name="$1"
  [[ "${PROVIDER_MUTATION_ALLOWED[$provider_name]-false}" == "true" ]]
}

provider_note() {
  local provider_name="$1"

  case "$provider_name" in
    the_muse)
      echo "Public jobs API with category sweeps and direct API-key auth."
      ;;
    arbeitnow)
      echo "No-auth global feed; pacing protects against Cloudflare burst blocking."
      ;;
    findwork)
      echo "Global jobs feed; token is optional in config but useful for steady access."
      ;;
    jooble)
      echo "Matrix sweeps over keywords and locations; API key is required."
      ;;
    adzuna)
      echo "Category sweeps with app_id/app_key auth and a daily background budget."
      ;;
    careerjet)
      echo "Intentionally unsupported for background ingest because it needs real end-user traffic context."
      ;;
    *)
      echo ""
      ;;
  esac
}

provider_field_label() {
  case "$1" in
    api_key)
      echo "API key"
      ;;
    app_id)
      echo "App ID"
      ;;
    app_key)
      echo "App key"
      ;;
    rate_limit_per_hour)
      echo "Rate limit per hour"
      ;;
    inter_request_delay)
      echo "Inter-request delay"
      ;;
    daily_request_budget)
      echo "Daily request budget"
      ;;
    page_size)
      echo "Page size"
      ;;
    *)
      echo "$1"
      ;;
  esac
}

provider_field_env_key() {
  local provider_name="$1"
  local field_name="$2"

  case "$provider_name:$field_name" in
    the_muse:api_key)
      echo "THE_MUSE_API_KEY"
      ;;
    the_muse:rate_limit_per_hour)
      echo "THE_MUSE_RATE_LIMIT_PER_HOUR"
      ;;
    arbeitnow:inter_request_delay)
      echo "ARBEITNOW_INTER_REQUEST_DELAY"
      ;;
    findwork:api_key)
      echo "FINDWORK_API_KEY"
      ;;
    findwork:inter_request_delay)
      echo "FINDWORK_INTER_REQUEST_DELAY"
      ;;
    jooble:api_key)
      echo "JOOBLE_API_KEY"
      ;;
    jooble:inter_request_delay)
      echo "JOOBLE_INTER_REQUEST_DELAY"
      ;;
    jooble:page_size)
      echo "JOOBLE_PAGE_SIZE"
      ;;
    adzuna:app_id)
      echo "ADZUNA_APP_ID"
      ;;
    adzuna:app_key)
      echo "ADZUNA_APP_KEY"
      ;;
    adzuna:daily_request_budget)
      echo "ADZUNA_DAILY_REQUEST_BUDGET"
      ;;
    *)
      echo ""
      ;;
  esac
}

provider_field_is_editable() {
  local provider_name="$1"
  local field_name="$2"
  [[ " ${PROVIDER_EDITABLE_FIELDS[$provider_name]-} " == *" $field_name "* ]]
}

provider_field_is_secret() {
  local provider_name="$1"
  local field_name="$2"
  [[ " ${PROVIDER_SECRET_FIELDS[$provider_name]-} " == *" $field_name "* ]]
}

provider_field_is_required() {
  local provider_name="$1"
  local field_name="$2"
  [[ " ${PROVIDER_REQUIRED_FIELDS[$provider_name]-} " == *" $field_name "* ]]
}

provider_field_is_optional() {
  local provider_name="$1"
  local field_name="$2"
  [[ " ${PROVIDER_OPTIONAL_FIELDS[$provider_name]-} " == *" $field_name "* ]]
}

provider_mask_secret_value() {
  local value="${1:-}"
  local value_length

  if [[ -z "$value" ]]; then
    echo "<empty>"
    return
  fi

  value_length=${#value}
  if (( value_length <= 4 )); then
    printf '%*s\n' "$value_length" '' | tr ' ' '*'
    return
  fi

  printf '%*s%s\n' "$((value_length - 4))" '' "${value: -4}" | tr ' ' '*'
}

provider_require_python3() {
  if command -v python3 >/dev/null 2>&1; then
    return 0
  fi
  echo "python3 is required for provider JSON editing helpers." >&2
  return 1
}

provider_get_field_value() {
  local provider_name="$1"
  local field_name="$2"
  local env_key

  env_key="$(provider_field_env_key "$provider_name" "$field_name")"
  if [[ -z "$env_key" ]]; then
    echo ""
    return
  fi

  get_env_value_or_default "$env_key" ""
}

provider_display_field_value() {
  local provider_name="$1"
  local field_name="$2"
  local value

  value="$(provider_get_field_value "$provider_name" "$field_name")"
  if provider_field_is_secret "$provider_name" "$field_name"; then
    provider_mask_secret_value "$value"
    return
  fi

  display_env_value "$value"
}

provider_validate_field_value() {
  local provider_name="$1"
  local field_name="$2"
  local value="$3"

  if ! provider_field_is_editable "$provider_name" "$field_name"; then
    echo "Field '$field_name' is not editable for provider '$provider_name'." >&2
    return 1
  fi

  case "$field_name" in
    rate_limit_per_hour|daily_request_budget|page_size)
      if ! [[ "$value" =~ ^[0-9]+$ ]] || (( value < 1 )); then
        echo "Field '$field_name' requires a positive integer." >&2
        return 1
      fi
      ;;
    inter_request_delay)
      if ! [[ "$value" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
        echo "Field '$field_name' requires a positive numeric value." >&2
        return 1
      fi
      ;;
    api_key|app_id|app_key)
      if [[ -z "$value" ]]; then
        echo "Field '$field_name' cannot be empty when set." >&2
        return 1
      fi
      ;;
    *)
      ;;
  esac

  return 0
}

provider_write_env_value() {
  local key="$1"
  local value="$2"
  local env_file="$ROOT_DIR/.env"

  if [[ ! -f "$env_file" ]]; then
    touch "$env_file"
  fi

  env_file_set_key_value "$env_file" "$key" "$value"
}

provider_controls_raw_json() {
  get_env_value_or_default JOB_PROVIDER_CONTROLS_JSON "{}"
}

provider_sync_enabled_raw_json() {
  get_env_value_or_default JOB_SYNC_ENABLED_PROVIDERS_JSON "[]"
}

provider_reset_override_cache() {
  PROVIDER_CONTROL_OVERRIDES=()
  PROVIDER_LEGACY_SCHEDULED=()
}

provider_load_override_cache() {
  local raw_controls
  local raw_sync
  local provider_name
  local field_name
  local value

  provider_reset_override_cache
  provider_require_python3 || return 1

  raw_controls="$(provider_controls_raw_json)"
  while IFS=$'\t' read -r provider_name field_name value; do
    [[ -z "$provider_name" || -z "$field_name" ]] && continue
    PROVIDER_CONTROL_OVERRIDES["$provider_name:$field_name"]="$value"
  done < <(
    PROVIDER_JSON_INPUT="$raw_controls" python3 - <<'PY'
import json
import os

raw = os.environ.get("PROVIDER_JSON_INPUT", "").strip()
if not raw:
    raise SystemExit(0)
try:
    parsed = json.loads(raw)
except json.JSONDecodeError:
    raise SystemExit(0)
if not isinstance(parsed, dict):
    raise SystemExit(0)
for provider_name, value in parsed.items():
    if not isinstance(provider_name, str) or not isinstance(value, dict):
        continue
    provider_key = provider_name.strip().lower()
    if not provider_key:
        continue
    for field_name, field_value in value.items():
        if not isinstance(field_name, str):
            continue
        normalized_field = field_name.strip().lower()
        if not normalized_field:
            continue
        if isinstance(field_value, bool):
            rendered = "true" if field_value else "false"
        elif isinstance(field_value, (int, float)):
            rendered = "true" if bool(field_value) else "false"
        elif isinstance(field_value, str):
            rendered = field_value.strip().lower()
        else:
            rendered = str(field_value).strip().lower()
        if rendered in {"true", "false"}:
            print(f"{provider_key}\t{normalized_field}\t{rendered}")
PY
  )

  raw_sync="$(provider_sync_enabled_raw_json)"
  while IFS= read -r provider_name; do
    [[ -z "$provider_name" ]] && continue
    PROVIDER_LEGACY_SCHEDULED["$provider_name"]="true"
  done < <(
    PROVIDER_JSON_INPUT="$raw_sync" python3 - <<'PY'
import json
import os

raw = os.environ.get("PROVIDER_JSON_INPUT", "").strip()
if not raw:
    raise SystemExit(0)
try:
    parsed = json.loads(raw)
except json.JSONDecodeError:
    raise SystemExit(0)
if not isinstance(parsed, list):
    raise SystemExit(0)
for value in parsed:
    provider = str(value).strip().lower()
    if provider:
        print(provider)
PY
  )
}

provider_default_toggle_value() {
  local provider_name="$1"
  local field_name="$2"
  local default_state

  default_state="$(provider_default_state "$provider_name")"

  case "$field_name" in
    ingest_enabled|display_enabled)
      if [[ "$default_state" == "active" ]]; then
        echo "true"
      else
        echo "false"
      fi
      ;;
    scheduled_enabled)
      if [[ "$default_state" == "active" && "$(provider_sweep_mode "$provider_name")" != "disabled" ]]; then
        echo "true"
      else
        echo "false"
      fi
      ;;
    *)
      echo "false"
      ;;
  esac
}

provider_compute_local_credentials() {
  local provider_name="$1"
  local field_name
  local env_key
  local value
  local -a missing_required=()
  local -a missing_optional=()

  if [[ "$provider_name" == "careerjet" ]]; then
    PROVIDER_STATUS_CREDENTIALS["$provider_name"]="unsupported"
    PROVIDER_STATUS_CREDENTIAL_STATE["$provider_name"]="warn"
    return
  fi

  if [[ -z "${PROVIDER_REQUIRED_FIELDS[$provider_name]-}" && -z "${PROVIDER_OPTIONAL_FIELDS[$provider_name]-}" ]]; then
    PROVIDER_STATUS_CREDENTIALS["$provider_name"]="not required"
    PROVIDER_STATUS_CREDENTIAL_STATE["$provider_name"]="ok"
    return
  fi

  for field_name in ${PROVIDER_REQUIRED_FIELDS[$provider_name]-}; do
    env_key="$(provider_field_env_key "$provider_name" "$field_name")"
    value="$(get_env_value_or_default "$env_key" "")"
    if [[ -z "$value" ]]; then
      missing_required+=("$field_name")
    fi
  done

  for field_name in ${PROVIDER_OPTIONAL_FIELDS[$provider_name]-}; do
    env_key="$(provider_field_env_key "$provider_name" "$field_name")"
    value="$(get_env_value_or_default "$env_key" "")"
    if [[ -z "$value" ]]; then
      missing_optional+=("$field_name")
    fi
  done

  if (( ${#missing_required[@]} > 0 )); then
    PROVIDER_STATUS_CREDENTIALS["$provider_name"]="missing required: ${missing_required[*]}"
    PROVIDER_STATUS_CREDENTIAL_STATE["$provider_name"]="error"
    return
  fi

  if (( ${#missing_optional[@]} > 0 )); then
    PROVIDER_STATUS_CREDENTIALS["$provider_name"]="optional empty: ${missing_optional[*]}"
    PROVIDER_STATUS_CREDENTIAL_STATE["$provider_name"]="warn"
    return
  fi

  PROVIDER_STATUS_CREDENTIALS["$provider_name"]="present"
  PROVIDER_STATUS_CREDENTIAL_STATE["$provider_name"]="ok"
}

provider_load_local_status_cache() {
  local provider_name
  local ingest_enabled
  local display_enabled
  local scheduled_enabled
  local status

  provider_load_override_cache || return 1

  PROVIDER_STATUS_SOURCE=()
  PROVIDER_STATUS_INGEST=()
  PROVIDER_STATUS_DISPLAY=()
  PROVIDER_STATUS_SCHEDULED=()
  PROVIDER_STATUS_STATE=()
  PROVIDER_STATUS_CREDENTIALS=()
  PROVIDER_STATUS_CREDENTIAL_STATE=()

  for provider_name in "${PROVIDER_NAMES[@]}"; do
    ingest_enabled="${PROVIDER_CONTROL_OVERRIDES[$provider_name:ingest_enabled]-$(provider_default_toggle_value "$provider_name" "ingest_enabled")}"
    display_enabled="${PROVIDER_CONTROL_OVERRIDES[$provider_name:display_enabled]-$(provider_default_toggle_value "$provider_name" "display_enabled")}"
    scheduled_enabled="${PROVIDER_CONTROL_OVERRIDES[$provider_name:scheduled_enabled]-$(provider_default_toggle_value "$provider_name" "scheduled_enabled")}"

    if [[ -n "${PROVIDER_LEGACY_SCHEDULED[$provider_name]+set}" && "$(provider_sweep_mode "$provider_name")" != "disabled" ]]; then
      scheduled_enabled="true"
    fi

    if [[ "$ingest_enabled" != "true" ]]; then
      scheduled_enabled="false"
    fi

    if [[ "$ingest_enabled" == "true" && "$display_enabled" == "true" ]] && { [[ "$scheduled_enabled" == "true" ]] || [[ "$(provider_default_state "$provider_name")" == "dormant" ]]; }; then
      status="active"
    elif [[ "$ingest_enabled" != "true" && "$display_enabled" != "true" && "$scheduled_enabled" != "true" ]]; then
      status="dormant"
    else
      status="partial"
    fi

    PROVIDER_STATUS_SOURCE["$provider_name"]="env"
    PROVIDER_STATUS_INGEST["$provider_name"]="$ingest_enabled"
    PROVIDER_STATUS_DISPLAY["$provider_name"]="$display_enabled"
    PROVIDER_STATUS_SCHEDULED["$provider_name"]="$scheduled_enabled"
    PROVIDER_STATUS_STATE["$provider_name"]="$status"
    provider_compute_local_credentials "$provider_name"
  done
}

provider_try_overlay_live_status() {
  local env_name="$1"
  local backend_container
  local provider_name
  local label
  local default_state
  local sweep_mode
  local scheduled_interval
  local ingest_enabled
  local display_enabled
  local scheduled_enabled
  local status
  local required
  local url

  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi

  backend_container="$(startup_backend_container_name "$env_name")"
  if ! is_container_running "$backend_container"; then
    return 1
  fi

  while IFS=$'\t' read -r provider_name label default_state sweep_mode scheduled_interval ingest_enabled display_enabled scheduled_enabled status required url; do
    [[ -z "$provider_name" ]] && continue
    PROVIDER_STATUS_SOURCE["$provider_name"]="api"
    PROVIDER_STATUS_INGEST["$provider_name"]="$ingest_enabled"
    PROVIDER_STATUS_DISPLAY["$provider_name"]="$display_enabled"
    PROVIDER_STATUS_SCHEDULED["$provider_name"]="$scheduled_enabled"
    PROVIDER_STATUS_STATE["$provider_name"]="$status"
  done < <(
    docker exec -i "$backend_container" python3 - <<'PY'
import json
import sys
import urllib.request

try:
    with urllib.request.urlopen("http://localhost:8000/api/providers/attribution", timeout=5) as response:
        payload = json.load(response)
except Exception:
    raise SystemExit(1)

for item in payload.get("providers") or []:
    attr = item.get("attribution") or {}
    fields = [
        str(item.get("provider") or "").strip().lower(),
        str(attr.get("label") or "").replace("\t", " ").replace("\n", " "),
        str(item.get("default_state") or ""),
        str(item.get("sweep_mode") or ""),
        "" if item.get("scheduled_interval_minutes") is None else str(item.get("scheduled_interval_minutes")),
        "true" if item.get("ingest_enabled") else "false",
        "true" if item.get("display_enabled") else "false",
        "true" if item.get("scheduled_enabled") else "false",
        str(item.get("status") or ""),
        "true" if attr.get("required") else "false",
        str(attr.get("url") or ""),
    ]
    print("\t".join(fields))
PY
  ) || return 1

  return 0
}

provider_refresh_status_cache() {
  local env_name="$1"
  local mode="${2:-auto}"

  provider_load_local_status_cache || return 1

  case "$mode" in
    env)
      ;;
    auto|live)
      provider_try_overlay_live_status "$env_name" || true
      ;;
    *)
      ;;
  esac

  return 0
}

provider_credentials_summary() {
  local provider_name="$1"
  echo "${PROVIDER_STATUS_CREDENTIALS[$provider_name]-unknown}"
}

provider_status_counts() {
  local active=0
  local partial=0
  local dormant=0
  local provider_name
  local status

  for provider_name in "${PROVIDER_NAMES[@]}"; do
    status="${PROVIDER_STATUS_STATE[$provider_name]-dormant}"
    case "$status" in
      active)
        active=$((active + 1))
        ;;
      partial)
        partial=$((partial + 1))
        ;;
      *)
        dormant=$((dormant + 1))
        ;;
    esac
  done

  echo "$active $partial $dormant"
}

provider_summary_label() {
  local env_name="$1"
  local mode="${2:-auto}"
  local active
  local partial
  local dormant
  local first_provider=""
  local source="env"
  local provider_name

  provider_refresh_status_cache "$env_name" "$mode" || return 1
  read -r active partial dormant < <(provider_status_counts)

  for provider_name in "${PROVIDER_NAMES[@]}"; do
    first_provider="$provider_name"
    break
  done
  if [[ -n "$first_provider" ]]; then
    source="${PROVIDER_STATUS_SOURCE[$first_provider]-env}"
  fi

  echo "Providers: ${active} active, ${partial} partial, ${dormant} dormant (source: ${source})"
}

provider_print_status_table() {
  local provider_name
  local index=1
  local ingest_enabled
  local display_enabled
  local scheduled_enabled
  local status
  local credentials
  local source

  printf "  %-3s %-12s %-16s %-9s %-8s %-8s %-10s %-14s %-30s\n" "#" "Provider" "Label" "Sweep" "Ingest" "Display" "Scheduled" "State" "Credentials"
  printf "  %-3s %-12s %-16s %-9s %-8s %-8s %-10s %-14s %-30s\n" "---" "------------" "----------------" "---------" "--------" "--------" "----------" "--------------" "------------------------------"
  for provider_name in "${PROVIDER_NAMES[@]}"; do
    ingest_enabled="${PROVIDER_STATUS_INGEST[$provider_name]-false}"
    display_enabled="${PROVIDER_STATUS_DISPLAY[$provider_name]-false}"
    scheduled_enabled="${PROVIDER_STATUS_SCHEDULED[$provider_name]-false}"
    status="${PROVIDER_STATUS_STATE[$provider_name]-dormant}"
    credentials="$(provider_credentials_summary "$provider_name")"
    source="${PROVIDER_STATUS_SOURCE[$provider_name]-env}"
    printf "  %-3s %-12s %-16s %-9s %-8s %-8s %-10s %-14s %-30s\n" \
      "$index" \
      "$provider_name" \
      "$(clip_text "$(provider_label "$provider_name")" 16)" \
      "$(provider_sweep_mode "$provider_name")" \
      "$ingest_enabled" \
      "$display_enabled" \
      "$scheduled_enabled" \
      "$(clip_text "$status/$source" 14)" \
      "$(clip_text "$credentials" 30)"
    index=$((index + 1))
  done
}

provider_assert_known() {
  local provider_name="$1"

  if provider_known "$provider_name"; then
    return 0
  fi

  echo "Unknown provider '$provider_name'." >&2
  echo "Known providers: ${PROVIDER_NAMES[*]}" >&2
  return 1
}

provider_assert_mutable() {
  local provider_name="$1"

  provider_assert_known "$provider_name" || return 1
  if provider_mutation_allowed "$provider_name"; then
    return 0
  fi

  echo "Provider '$provider_name' is intentionally read-only in uah.sh." >&2
  echo "$(provider_note "$provider_name")" >&2
  return 1
}

provider_write_controls_triplet() {
  local provider_name="$1"
  local ingest_enabled="$2"
  local display_enabled="$3"
  local scheduled_enabled="$4"
  local raw_controls
  local updated_controls

  provider_require_python3 || return 1
  raw_controls="$(provider_controls_raw_json)"
  updated_controls="$(
    PROVIDER_JSON_INPUT="$raw_controls" \
    PROVIDER_NAME="$provider_name" \
    PROVIDER_INGEST="$ingest_enabled" \
    PROVIDER_DISPLAY="$display_enabled" \
    PROVIDER_SCHEDULED="$scheduled_enabled" \
    python3 - <<'PY'
import json
import os

raw = os.environ.get("PROVIDER_JSON_INPUT", "").strip()
provider_name = os.environ["PROVIDER_NAME"].strip().lower()
data = {}
if raw:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}
    if isinstance(parsed, dict):
        data = parsed

data[provider_name] = {
    "ingest_enabled": os.environ["PROVIDER_INGEST"].strip().lower() == "true",
    "display_enabled": os.environ["PROVIDER_DISPLAY"].strip().lower() == "true",
    "scheduled_enabled": os.environ["PROVIDER_SCHEDULED"].strip().lower() == "true",
}
print(json.dumps(data, separators=(",", ":"), sort_keys=True))
PY
  )" || return 1

  provider_write_env_value "JOB_PROVIDER_CONTROLS_JSON" "$updated_controls"
  PROVIDER_CONFIG_MUTATED=true
  return 0
}

provider_sync_legacy_scheduled_env() {
  local provider_name
  local scheduled_enabled
  local ingest_enabled
  local legacy_json="["
  local first_item=true

  provider_load_override_cache || return 1

  for provider_name in "${PROVIDER_NAMES[@]}"; do
    ingest_enabled="${PROVIDER_CONTROL_OVERRIDES[$provider_name:ingest_enabled]-$(provider_default_toggle_value "$provider_name" "ingest_enabled")}"
    scheduled_enabled="${PROVIDER_CONTROL_OVERRIDES[$provider_name:scheduled_enabled]-$(provider_default_toggle_value "$provider_name" "scheduled_enabled")}"
    if [[ "$ingest_enabled" != "true" ]]; then
      scheduled_enabled="false"
    fi
    if [[ "$scheduled_enabled" == "true" && "$(provider_sweep_mode "$provider_name")" != "disabled" ]]; then
      if [[ "$first_item" == true ]]; then
        first_item=false
      else
        legacy_json+=","
      fi
      legacy_json+="\"$provider_name\""
    fi
  done
  legacy_json+="]"

  provider_write_env_value "JOB_SYNC_ENABLED_PROVIDERS_JSON" "$legacy_json"
  return 0
}

provider_update_control_state() {
  local env_name="$1"
  local provider_name="$2"
  local action="$3"
  local apply_ingest="$4"
  local apply_display="$5"
  local apply_scheduled="$6"
  local ingest_enabled
  local display_enabled
  local scheduled_enabled

  provider_assert_mutable "$provider_name" || return 1
  provider_refresh_status_cache "$env_name" "env" || true

  ingest_enabled="${PROVIDER_STATUS_INGEST[$provider_name]-$(provider_default_toggle_value "$provider_name" "ingest_enabled")}"
  display_enabled="${PROVIDER_STATUS_DISPLAY[$provider_name]-$(provider_default_toggle_value "$provider_name" "display_enabled")}"
  scheduled_enabled="${PROVIDER_STATUS_SCHEDULED[$provider_name]-$(provider_default_toggle_value "$provider_name" "scheduled_enabled")}"

  if [[ "$apply_ingest" == "true" ]]; then
    if [[ "$action" == "enable" ]]; then
      ingest_enabled="true"
    else
      ingest_enabled="false"
    fi
  fi

  if [[ "$apply_display" == "true" ]]; then
    if [[ "$action" == "enable" ]]; then
      display_enabled="true"
    else
      display_enabled="false"
    fi
  fi

  if [[ "$apply_scheduled" == "true" ]]; then
    if [[ "$action" == "enable" ]]; then
      scheduled_enabled="true"
    else
      scheduled_enabled="false"
    fi
  fi

  if [[ "$scheduled_enabled" == "true" ]]; then
    ingest_enabled="true"
  fi
  if [[ "$ingest_enabled" != "true" ]]; then
    scheduled_enabled="false"
  fi

  provider_write_controls_triplet "$provider_name" "$ingest_enabled" "$display_enabled" "$scheduled_enabled" || return 1
  provider_sync_legacy_scheduled_env || return 1
  provider_refresh_status_cache "$env_name" "env" || true
  return 0
}

provider_set_config_field() {
  local provider_name="$1"
  local field_name="$2"
  local value="$3"
  local env_key

  provider_assert_mutable "$provider_name" || return 1
  provider_validate_field_value "$provider_name" "$field_name" "$value" || return 1
  env_key="$(provider_field_env_key "$provider_name" "$field_name")"
  if [[ -z "$env_key" ]]; then
    echo "No env mapping exists for $provider_name.$field_name." >&2
    return 1
  fi

  provider_write_env_value "$env_key" "$value"
  PROVIDER_CONFIG_MUTATED=true
  return 0
}

provider_clear_config_field() {
  local provider_name="$1"
  local field_name="$2"
  local env_key

  provider_assert_mutable "$provider_name" || return 1
  if ! provider_field_is_editable "$provider_name" "$field_name"; then
    echo "Field '$field_name' is not editable for provider '$provider_name'." >&2
    return 1
  fi
  if ! provider_field_is_secret "$provider_name" "$field_name"; then
    echo "Field '$field_name' is not treated as a secret clearable field." >&2
    return 1
  fi

  env_key="$(provider_field_env_key "$provider_name" "$field_name")"
  provider_write_env_value "$env_key" ""
  PROVIDER_CONFIG_MUTATED=true
  return 0
}

provider_restart_runtime_services() {
  local env_name="$1"

  if [[ "$env_name" == "prod" ]]; then
    echo "Provider runtime restart is scaffold-only for prod right now."
    return 1
  fi

  if ! refresh_job_runtime_services "$env_name"; then
    return 1
  fi

  PROVIDER_CONFIG_MUTATED=false
}

provider_prompt_restart_if_needed() {
  local env_name="$1"
  local restart_choice

  if [[ "$PROVIDER_CONFIG_MUTATED" != true ]]; then
    return 0
  fi

  if [[ ! -t 0 ]]; then
    echo "Provider config changed in .env. Restart backend/celery services to apply the update."
    return 0
  fi

  echo ""
  read -rp "Restart backend + celery services now? [y/N]: " restart_choice
  if [[ "${restart_choice,,}" == "y" || "${restart_choice,,}" == "yes" ]]; then
    provider_restart_runtime_services "$env_name" || true
  fi
}

provider_list_schedule_categories() {
  local raw_json

  provider_require_python3 || return 1
  raw_json="$(get_env_value_or_default JOB_SYNC_CATEGORY_SCHEDULE_JSON "")"

  if [[ -n "$raw_json" ]]; then
    while IFS= read -r category_name; do
      [[ -n "$category_name" ]] && echo "$category_name"
    done < <(
      PROVIDER_JSON_INPUT="$raw_json" python3 - <<'PY'
import json
import os

raw = os.environ.get("PROVIDER_JSON_INPUT", "").strip()
if not raw:
    raise SystemExit(0)
try:
    parsed = json.loads(raw)
except json.JSONDecodeError:
    raise SystemExit(0)
if not isinstance(parsed, dict):
    raise SystemExit(0)
for key in parsed.keys():
    if isinstance(key, str) and key.strip():
        print(key.strip())
PY
    )
    return 0
  fi

  printf '%s\n' "${PROVIDER_DEFAULT_CATEGORIES[@]}"
}

provider_queue_sync_now() {
  local env_name="$1"
  local provider_name="$2"
  local category_name="${3:-}"
  local backend_container

  provider_assert_known "$provider_name" || return 1
  provider_refresh_status_cache "$env_name" "env" || true
  if [[ "${PROVIDER_STATUS_INGEST[$provider_name]-false}" != "true" ]]; then
    echo "Provider '$provider_name' is not ingest-enabled, so sync-now is blocked." >&2
    return 1
  fi
  backend_container="$(startup_backend_container_name "$env_name")"

  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker CLI is required to queue provider sync jobs." >&2
    return 1
  fi
  if ! is_container_running "$backend_container"; then
    echo "Backend container '$backend_container' is not running, so sync-now cannot dispatch." >&2
    return 1
  fi

  docker exec -i \
    -e UAH_PROVIDER_NAME="$provider_name" \
    -e UAH_PROVIDER_CATEGORY="$category_name" \
    "$backend_container" \
    python3 - <<'PY'
import os

from app.providers.registry import get_provider_definition
from app.tasks.job_sync import sweep_category, sweep_provider

provider_name = os.environ.get("UAH_PROVIDER_NAME", "").strip().lower()
category_name = os.environ.get("UAH_PROVIDER_CATEGORY", "").strip()
definition = get_provider_definition(provider_name)

if definition.sweep_mode == "category":
    if not category_name:
        raise SystemExit("Category providers require a category for sync-now.")
    sweep_category.delay(provider=provider_name, category=category_name)
    print(f"queued category sweep for {provider_name}:{category_name}")
elif definition.sweep_mode in {"global", "matrix"}:
    sweep_provider.delay(provider=provider_name)
    print(f"queued provider sweep for {provider_name}")
else:
    raise SystemExit(f"Provider '{provider_name}' does not support sync-now.")
PY
}

provider_print_details() {
  local env_name="$1"
  local provider_name="$2"
  local field_name

  provider_assert_known "$provider_name" || return 1
  provider_refresh_status_cache "$env_name" "auto" || true

  debug_header "$env_name" "Providers :: $(provider_label "$provider_name")"
  debug_print_section "Provider details"
  echo "  Label             : $(provider_label "$provider_name")"
  echo "  Slug              : $provider_name"
  echo "  Sweep mode        : $(provider_sweep_mode "$provider_name")"
  echo "  Default state     : $(provider_default_state "$provider_name")"
  echo "  Status source     : ${PROVIDER_STATUS_SOURCE[$provider_name]-env}"
  echo "  Ingest enabled    : ${PROVIDER_STATUS_INGEST[$provider_name]-false}"
  echo "  Display enabled   : ${PROVIDER_STATUS_DISPLAY[$provider_name]-false}"
  echo "  Scheduled enabled : ${PROVIDER_STATUS_SCHEDULED[$provider_name]-false}"
  echo "  Resolved status   : ${PROVIDER_STATUS_STATE[$provider_name]-dormant}"
  echo "  Credentials       : $(provider_credentials_summary "$provider_name")"
  echo "  Mutations allowed : ${PROVIDER_MUTATION_ALLOWED[$provider_name]-false}"
  echo ""
  debug_print_section "Editable config"
  if [[ -z "${PROVIDER_EDITABLE_FIELDS[$provider_name]-}" ]]; then
    echo "  (No editable fields in uah.sh.)"
  else
    for field_name in ${PROVIDER_EDITABLE_FIELDS[$provider_name]-}; do
      echo "  $(provider_field_label "$field_name") [$field_name] :: $(provider_display_field_value "$provider_name" "$field_name")"
    done
  fi
  echo ""
  debug_print_section "Notes"
  echo "  $(provider_note "$provider_name")"
}

provider_cli_list() {
  local env_name="$1"
  local mode="${2:-auto}"
  local active
  local partial
  local dormant

  provider_refresh_status_cache "$env_name" "$mode" || return 1
  read -r active partial dormant < <(provider_status_counts)

  echo "Provider status for $env_name"
  echo ""
  provider_print_status_table
  echo ""
  echo "Summary: $active active, $partial partial, $dormant dormant"
}

provider_cli_show() {
  local env_name="$1"
  local provider_name="$2"

  provider_print_details "$env_name" "$provider_name"
}

provider_parse_toggle_flags() {
  local apply_ingest=false
  local apply_display=false
  local apply_scheduled=false
  local arg

  for arg in "$@"; do
    case "$arg" in
      --all)
        apply_ingest=true
        apply_display=true
        apply_scheduled=true
        ;;
      --ingest)
        apply_ingest=true
        ;;
      --display)
        apply_display=true
        ;;
      --scheduled)
        apply_scheduled=true
        ;;
      *)
        echo "Unknown toggle option '$arg'." >&2
        return 1
        ;;
    esac
  done

  if [[ "$apply_ingest" == false && "$apply_display" == false && "$apply_scheduled" == false ]]; then
    apply_ingest=true
    apply_display=true
    apply_scheduled=true
  fi

  echo "$apply_ingest $apply_display $apply_scheduled"
}

provider_cli_toggle() {
  local env_name="$1"
  local action="$2"
  local provider_name="$3"
  shift 3
  local apply_ingest
  local apply_display
  local apply_scheduled

  read -r apply_ingest apply_display apply_scheduled < <(provider_parse_toggle_flags "$@") || return 1

  provider_update_control_state "$env_name" "$provider_name" "$action" "$apply_ingest" "$apply_display" "$apply_scheduled" || return 1
  echo "Updated provider '$provider_name' via '$action'."
  provider_cli_list "$env_name" "env"
  provider_prompt_restart_if_needed "$env_name"
}

provider_cli_set() {
  local env_name="$1"
  local provider_name="$2"
  local field_name="$3"
  local value="$4"

  provider_set_config_field "$provider_name" "$field_name" "$value" || return 1
  echo "Updated $provider_name.$field_name."
  provider_prompt_restart_if_needed "$env_name"
}

provider_cli_clear() {
  local env_name="$1"
  local provider_name="$2"
  local field_name="$3"

  provider_clear_config_field "$provider_name" "$field_name" || return 1
  echo "Cleared secret field $provider_name.$field_name."
  provider_prompt_restart_if_needed "$env_name"
}

provider_cli_sync_now() {
  local env_name="$1"
  local provider_name="$2"
  shift 2
  local category_name=""
  local arg

  while (($#)); do
    arg="$1"
    case "$arg" in
      --category)
        shift
        if (($# == 0)); then
          echo "--category requires a value." >&2
          return 1
        fi
        category_name="$1"
        ;;
      *)
        echo "Unknown sync-now option '$arg'." >&2
        return 1
        ;;
    esac
    shift
  done

  if [[ "$(provider_sweep_mode "$provider_name")" == "category" && -z "$category_name" ]]; then
    echo "Provider '$provider_name' requires --category for sync-now." >&2
    return 1
  fi

  provider_queue_sync_now "$env_name" "$provider_name" "$category_name"
}

print_provider_usage() {
  cat <<'EOF'
Provider subcommands:
  bash scripts/uah.sh <env> providers
  bash scripts/uah.sh <env> providers list [--live|--env]
  bash scripts/uah.sh <env> providers show <provider>
  bash scripts/uah.sh <env> providers enable <provider> [--ingest] [--display] [--scheduled] [--all]
  bash scripts/uah.sh <env> providers disable <provider> [--ingest] [--display] [--scheduled] [--all]
  bash scripts/uah.sh <env> providers set <provider> <field> <value>
  bash scripts/uah.sh <env> providers clear <provider> <field>
  bash scripts/uah.sh <env> providers sync-now <provider> [--category <name>]
EOF
}

provider_select_interactive() {
  local prompt_label="${1:-provider}"
  local include_mutable_only="${2:-false}"
  local choice
  local provider_name
  local index=1
  local -a selectable=()

  echo ""
  echo "  Choose $prompt_label:"
  for provider_name in "${PROVIDER_NAMES[@]}"; do
    if [[ "$include_mutable_only" == "true" ]] && ! provider_mutation_allowed "$provider_name"; then
      continue
    fi
    printf "    %2d) %-12s %s\n" "$index" "$provider_name" "$(provider_label "$provider_name")"
    selectable+=("$provider_name")
    index=$((index + 1))
  done
  echo "     0) back"
  read -rp "  Choice [0-$((index - 1))]: " choice

  if [[ "$choice" == "0" || -z "$choice" ]]; then
    echo ""
    return
  fi
  if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    echo ""
    return
  fi
  choice=$((choice - 1))
  if (( choice < 0 || choice >= ${#selectable[@]} )); then
    echo ""
    return
  fi

  echo "${selectable[$choice]}"
}

provider_select_field_interactive() {
  local provider_name="$1"
  local only_secret="${2:-false}"
  local choice
  local field_name
  local index=1
  local -a selectable=()

  echo ""
  echo "  Choose field for $(provider_label "$provider_name"):"
  for field_name in ${PROVIDER_EDITABLE_FIELDS[$provider_name]-}; do
    if [[ "$only_secret" == "true" ]] && ! provider_field_is_secret "$provider_name" "$field_name"; then
      continue
    fi
    printf "    %2d) %-20s current=%s\n" "$index" "$field_name" "$(clip_text "$(provider_display_field_value "$provider_name" "$field_name")" 28)"
    selectable+=("$field_name")
    index=$((index + 1))
  done
  echo "     0) back"
  read -rp "  Choice [0-$((index - 1))]: " choice

  if [[ "$choice" == "0" || -z "$choice" ]]; then
    echo ""
    return
  fi
  if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    echo ""
    return
  fi
  choice=$((choice - 1))
  if (( choice < 0 || choice >= ${#selectable[@]} )); then
    echo ""
    return
  fi

  echo "${selectable[$choice]}"
}

provider_select_category_interactive() {
  local choice
  local index=1
  local category_name
  local -a categories=()

  mapfile -t categories < <(provider_list_schedule_categories)

  echo ""
  echo "  Choose category:"
  for category_name in "${categories[@]}"; do
    printf "    %2d) %s\n" "$index" "$category_name"
    index=$((index + 1))
  done
  echo "     0) back"
  read -rp "  Choice [0-$((index - 1))]: " choice

  if [[ "$choice" == "0" || -z "$choice" ]]; then
    echo ""
    return
  fi
  if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    echo ""
    return
  fi
  choice=$((choice - 1))
  if (( choice < 0 || choice >= ${#categories[@]} )); then
    echo ""
    return
  fi

  echo "${categories[$choice]}"
}

provider_toggle_interactive() {
  local env_name="$1"
  local action="$2"
  local provider_name
  local choice
  local apply_ingest=false
  local apply_display=false
  local apply_scheduled=false

  provider_name="$(provider_select_interactive "provider to ${action}" "true")"
  if [[ -z "$provider_name" ]]; then
    return 1
  fi

  echo ""
  echo "  Toggle target:"
  echo "    1) all"
  echo "    2) ingest"
  echo "    3) display"
  echo "    4) scheduled"
  echo "    0) back"
  read -rp "  Choice [1-4/0]: " choice

  case "$choice" in
    1)
      apply_ingest=true
      apply_display=true
      apply_scheduled=true
      ;;
    2)
      apply_ingest=true
      ;;
    3)
      apply_display=true
      ;;
    4)
      apply_scheduled=true
      ;;
    *)
      return 1
      ;;
  esac

  provider_update_control_state "$env_name" "$provider_name" "$action" "$apply_ingest" "$apply_display" "$apply_scheduled" || return 1
  echo "Updated provider '$provider_name'."
  provider_prompt_restart_if_needed "$env_name"
  debug_press_enter
}

provider_edit_config_interactive() {
  local env_name="$1"
  local provider_name
  local field_name
  local new_value

  provider_name="$(provider_select_interactive "provider to edit" "true")"
  if [[ -z "$provider_name" ]]; then
    return 1
  fi
  field_name="$(provider_select_field_interactive "$provider_name" "false")"
  if [[ -z "$field_name" ]]; then
    return 1
  fi

  read -rp "  New value for $provider_name.$field_name: " new_value
  if [[ -z "$new_value" ]]; then
    echo "No value entered."
    debug_press_enter
    return 1
  fi

  provider_set_config_field "$provider_name" "$field_name" "$new_value" || {
    debug_press_enter
    return 1
  }
  echo "Updated $provider_name.$field_name."
  provider_prompt_restart_if_needed "$env_name"
  debug_press_enter
}

provider_clear_secret_interactive() {
  local env_name="$1"
  local provider_name
  local field_name
  local choice

  provider_name="$(provider_select_interactive "provider secret to clear" "true")"
  if [[ -z "$provider_name" ]]; then
    return 1
  fi
  field_name="$(provider_select_field_interactive "$provider_name" "true")"
  if [[ -z "$field_name" ]]; then
    return 1
  fi

  read -rp "  Clear secret $provider_name.$field_name? [y/N]: " choice
  if [[ "${choice,,}" != "y" && "${choice,,}" != "yes" ]]; then
    return 1
  fi

  provider_clear_config_field "$provider_name" "$field_name" || {
    debug_press_enter
    return 1
  }
  echo "Cleared $provider_name.$field_name."
  provider_prompt_restart_if_needed "$env_name"
  debug_press_enter
}

provider_sync_now_interactive() {
  local env_name="$1"
  local provider_name
  local category_name=""

  provider_name="$(provider_select_interactive "provider to sync now" "false")"
  if [[ -z "$provider_name" ]]; then
    return 1
  fi

  if [[ "$(provider_sweep_mode "$provider_name")" == "category" ]]; then
    category_name="$(provider_select_category_interactive)"
    if [[ -z "$category_name" ]]; then
      return 1
    fi
  fi

  if provider_queue_sync_now "$env_name" "$provider_name" "$category_name"; then
    debug_press_enter
    return 0
  fi

  debug_press_enter
  return 1
}

provider_dashboard() {
  local env_name="$1"
  local choice
  local provider_name

  while true; do
    provider_refresh_status_cache "$env_name" "auto" || true
    debug_header "$env_name" "Providers"
    debug_print_section "Provider dashboard"
    provider_print_status_table
    echo ""
    echo "  Actions"
    echo "    1) Inspect provider"
    echo "    2) Enable provider/toggles"
    echo "    3) Disable provider/toggles"
    echo "    4) Edit/apply provider config"
    echo "    5) Clear provider secret"
    echo "    6) Sync provider now"
    echo "    7) Restart backend + workers"
    echo "    8) Refresh status"
    echo "    0) Back"
    read -rp "  Choice [1-8/0]: " choice

    case "$choice" in
      1)
        provider_name="$(provider_select_interactive "provider to inspect" "false")"
        if [[ -n "$provider_name" ]]; then
          provider_print_details "$env_name" "$provider_name"
          debug_press_enter
        fi
        ;;
      2)
        provider_toggle_interactive "$env_name" "enable" || true
        ;;
      3)
        provider_toggle_interactive "$env_name" "disable" || true
        ;;
      4)
        provider_edit_config_interactive "$env_name" || true
        ;;
      5)
        provider_clear_secret_interactive "$env_name" || true
        ;;
      6)
        provider_sync_now_interactive "$env_name" || true
        ;;
      7)
        provider_restart_runtime_services "$env_name" || true
        debug_press_enter
        ;;
      8)
        ;;
      0)
        return 0
        ;;
      *)
        debug_print_warn "Invalid selection."
        debug_press_enter
        ;;
    esac
  done
}

run_providers() {
  local env_name="$1"
  shift || true
  local subcommand="${1:-}"
  local mode="auto"

  if [[ -z "$subcommand" ]]; then
    if [[ -t 0 ]]; then
      provider_dashboard "$env_name"
      return
    fi
    print_provider_usage >&2
    return 1
  fi

  shift || true
  case "$subcommand" in
    help|-h|--help)
      print_provider_usage
      ;;
    list)
      if [[ "${1:-}" == "--live" ]]; then
        mode="live"
      elif [[ "${1:-}" == "--env" ]]; then
        mode="env"
      elif [[ -n "${1:-}" ]]; then
        echo "Unknown providers list option '$1'." >&2
        return 1
      fi
      provider_cli_list "$env_name" "$mode"
      ;;
    show)
      if [[ -z "${1:-}" ]]; then
        echo "providers show requires a provider slug." >&2
        return 1
      fi
      provider_cli_show "$env_name" "$1"
      ;;
    enable|disable)
      if [[ -z "${1:-}" ]]; then
        echo "providers $subcommand requires a provider slug." >&2
        return 1
      fi
      provider_cli_toggle "$env_name" "$subcommand" "$@"
      ;;
    set)
      if [[ $# -lt 3 ]]; then
        echo "providers set requires <provider> <field> <value>." >&2
        return 1
      fi
      provider_cli_set "$env_name" "$1" "$2" "$3"
      ;;
    clear)
      if [[ $# -lt 2 ]]; then
        echo "providers clear requires <provider> <field>." >&2
        return 1
      fi
      provider_cli_clear "$env_name" "$1" "$2"
      ;;
    sync-now)
      if [[ -z "${1:-}" ]]; then
        echo "providers sync-now requires a provider slug." >&2
        return 1
      fi
      provider_cli_sync_now "$env_name" "$@"
      ;;
    *)
      echo "Unknown providers subcommand '$subcommand'." >&2
      print_provider_usage >&2
      return 1
      ;;
  esac
}

startup_backend_container_name() {
  case "$1" in
    dev)
      echo "uah-dev-backend"
      ;;
    beta)
      echo "uah-beta-backend"
      ;;
    *)
      echo "uah-prod-backend"
      ;;
  esac
}

startup_network_name() {
  case "$1" in
    dev)
      echo "uah-infra"
      ;;
    beta)
      echo "uah-beta-infra"
      ;;
    *)
      echo "uah-prod-infra"
      ;;
  esac
}

startup_status_chip() {
  local state="$1"
  local label="$2"

  case "$state" in
    ok)
      echo -e "  ${GREEN}●${NC} ${label}"
      ;;
    warn)
      echo -e "  ${YELLOW}●${NC} ${label}"
      ;;
    *)
      echo -e "  ${RED}●${NC} ${label}"
      ;;
  esac
}

startup_header() {
  local env_name="$1"

  if [[ -t 1 ]]; then
    clear
  fi

  echo -e "${BOLD}${CYAN}"
  echo "  ██╗   ██╗ █████╗ ██╗  ██╗"
  echo "  ██║   ██║██╔══██╗██║  ██║"
  echo "  ██║   ██║███████║███████║"
  echo "  ██║   ██║██╔══██║██╔══██║"
  echo "  ╚██████╔╝██║  ██║██║  ██║"
  echo "   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝"
  echo -e "${NC}${BOLD}  Control Center :: ${env_name^^}${NC}"
  echo -e "${CYAN}  ─────────────────────────────────────────────────────────────${NC}"
  echo ""
}

startup_quick_hud() {
  local env_name="$1"
  local backend_container
  local network_name
  local provider_summary
  local extension_dir
  local landing_dir

  backend_container="$(startup_backend_container_name "$env_name")"
  network_name="$(startup_network_name "$env_name")"
  extension_dir="$ROOT_DIR/uah-browser-extension"
  landing_dir="$ROOT_DIR/landing"

  debug_print_section "Quick HUD"
  startup_status_chip "ok" "Environment: $env_name (source: $DETECTED_ENV_SOURCE)"
  startup_status_chip "ok" "Build mode: $(build_mode_label)"

  if command -v docker >/dev/null 2>&1; then
    startup_status_chip "ok" "Docker CLI: available"
    if docker compose version >/dev/null 2>&1; then
      startup_status_chip "ok" "Docker Compose: available"
    else
      startup_status_chip "error" "Docker Compose: missing plugin"
    fi

    if is_container_running "$backend_container"; then
      startup_status_chip "ok" "Backend container: running ($backend_container)"
    else
      startup_status_chip "warn" "Backend container: not running ($backend_container)"
    fi

    if docker network inspect "$network_name" >/dev/null 2>&1; then
      startup_status_chip "ok" "Primary network: present ($network_name)"
    else
      startup_status_chip "warn" "Primary network: missing ($network_name)"
    fi
  else
    startup_status_chip "error" "Docker CLI: unavailable"
  fi

  env_policy_evaluate "$env_name"
  if (( ENV_POLICY_ERROR_COUNT > 0 )); then
    startup_status_chip "error" "Env safety: ${ENV_POLICY_ERROR_COUNT} critical, ${ENV_POLICY_WARN_COUNT} warnings"
  elif (( ENV_POLICY_WARN_COUNT > 0 )); then
    startup_status_chip "warn" "Env safety: ${ENV_POLICY_WARN_COUNT} warning(s)"
  else
    startup_status_chip "ok" "Env safety: clean"
  fi

  provider_summary="$(provider_summary_label "$env_name" "auto" 2>/dev/null || provider_summary_label "$env_name" "env" 2>/dev/null || true)"
  if [[ -n "$provider_summary" ]]; then
    startup_status_chip "ok" "$provider_summary"
  fi

  if [[ -d "$extension_dir" && -d "$landing_dir" ]]; then
    if command -v npm >/dev/null 2>&1; then
      startup_status_chip "ok" "Extension repack readiness: host npm available"
    elif command -v docker >/dev/null 2>&1; then
      startup_status_chip "warn" "Extension repack readiness: host npm missing, Docker fallback available"
    else
      startup_status_chip "error" "Extension repack readiness: blocked (need npm or docker)"
    fi
  else
    startup_status_chip "warn" "Extension repack readiness: missing extension or landing directory"
  fi
}

extension_zip_note_file() {
  echo "$ROOT_DIR/.ops-state/uah-browser-extension-alpha.last-repacked.txt"
}

extension_zip_target_file() {
  echo "$ROOT_DIR/landing/public/downloads/uah-browser-extension-alpha.zip"
}

extension_zip_last_repacked_label() {
  local note_file
  note_file="$(extension_zip_note_file)"
  if [[ -f "$note_file" ]]; then
    local line
    line="$(sed -n '1p' "$note_file" 2>/dev/null || true)"
    if [[ -n "$line" ]]; then
      echo "$line"
      return
    fi
  fi
  echo "not yet repacked"
}

choose_environment_interactive() {
  local current_env="$1"
  local choice

  echo ""
  echo "  Select environment context:"
  echo "    1) dev"
  echo "    2) beta"
  echo "    3) prod"
  echo "    0) keep current ($current_env)"
  read -rp "  Choice [1-3/0]: " choice

  case "$choice" in
    1)
      echo "dev"
      ;;
    2)
      echo "beta"
      ;;
    3)
      echo "prod"
      ;;
    0|"")
      echo "$current_env"
      ;;
    *)
      echo "$current_env"
      ;;
  esac
}

configure_audit_wizard_args() {
  local mode_choice
  local mode_value="full"
  local fix_choice
  local fail_choice
  local json_choice
  local json_path

  EXTRA_ARGS=()

  echo ""
  echo "  Audit mode"
  echo "    1) full"
  echo "    2) repo"
  echo "    3) docker"
  echo "    4) host"
  read -rp "  Choice [1-4, default 1]: " mode_choice

  case "$mode_choice" in
    2)
      mode_value="repo"
      ;;
    3)
      mode_value="docker"
      ;;
    4)
      mode_value="host"
      ;;
    *)
      mode_value="full"
      ;;
  esac
  EXTRA_ARGS+=("--mode" "$mode_value")

  read -rp "  Apply suggested fixes automatically? [y/N]: " fix_choice
  if [[ "${fix_choice,,}" == "y" || "${fix_choice,,}" == "yes" ]]; then
    EXTRA_ARGS+=("--fix")
  fi

  read -rp "  Fail build on warnings? [y/N]: " fail_choice
  if [[ "${fail_choice,,}" == "y" || "${fail_choice,,}" == "yes" ]]; then
    EXTRA_ARGS+=("--fail-on-warn")
  fi

  read -rp "  Emit JSON report? [y/N]: " json_choice
  if [[ "${json_choice,,}" == "y" || "${json_choice,,}" == "yes" ]]; then
    read -rp "  JSON output path (blank = default): " json_path
    if [[ -n "$json_path" ]]; then
      EXTRA_ARGS+=("--json" "$json_path")
    else
      EXTRA_ARGS+=("--json")
    fi
  fi
}

choose_action() {
  local active_env="$1"
  local choice
  local selected_env
  local audit_mode
  local script_doctor_choice

  # shellcheck disable=SC1091
  source "$ROOT_DIR/scripts/lib/ops_console_menus.sh"

  if [[ ! -t 0 ]]; then
    echo "Action argument required in non-interactive mode: start|stop|restart|debug|sync|cert-sync|audit|providers|…" >&2
    exit 1
  fi

  while true; do
    startup_header "$active_env"
    startup_quick_hud "$active_env"
    echo ""
    echo "  Lifecycle"
    printf '    %2d)  %s\n' 1 "start" 2 "stop" 3 "restart"
    echo ""
    echo "  Deploy"
    printf '    %2d)  %s\n' 4 "sync" 5 "cert-sync (dev only)"
    printf '    %2d)  %s\n' 21 "repack extension zip (landing download)"
    echo "        last repacked: $(extension_zip_last_repacked_label)"
    echo ""
    echo "  Governance"
    printf '    %2d)  %s\n' 6 "security audit" 7 "providers" 8 "env safety review"
    echo ""
    echo "  Observability"
    echo "  (submenus; choose 0 in submenu to return here)"
    printf '    %2d)  %s\n' 9 "connectivity" 10 "logs" 11 "queue"
    echo ""
    echo "  Data and access"
    printf '    %2d)  %s\n' 12 "database" 13 "users" 14 "invites" 15 "networking"
    echo ""
    echo "  Advanced"
    printf '    %2d)  %s\n' 16 "script doctor" 17 "backend status snapshot" 18 "open full ops console (classic menu)"
    echo ""
    echo "  Session"
    printf '    %2d)  %s\n' 19 "switch environment" 20 "rebuild options" 0 "exit"
    echo ""
    read -rp "  Choice [0-21]: " choice

    case "$choice" in
      1)
        if ! configure_rebuild_ui_for_action "$active_env" "start"; then
          continue
        fi
        ACTION="start"
        ENV_NAME="$active_env"
        return
        ;;
      2)
        build_mode_reset_selection
        ACTION="stop"
        ENV_NAME="$active_env"
        return
        ;;
      3)
        if ! configure_rebuild_ui_for_action "$active_env" "restart"; then
          continue
        fi
        ACTION="restart"
        ENV_NAME="$active_env"
        return
        ;;
      4)
        if ! configure_rebuild_ui_for_action "$active_env" "sync"; then
          continue
        fi
        ACTION="sync"
        ENV_NAME="$active_env"
        return
        ;;
      5)
        if [[ "$active_env" != "dev" ]]; then
          debug_print_warn "cert-sync is only supported for dev."
          debug_press_enter
          continue
        fi
        build_mode_reset_selection
        ACTION="cert-sync"
        ENV_NAME="$active_env"
        return
        ;;
      6)
        echo ""
        echo "  Security audit:"
        echo "    1) Run with default options"
        echo "    2) Configure wizard (mode, --fix, JSON, …)"
        read -rp "  Choice [1/2, default 1]: " audit_mode
        build_mode_reset_selection
        ENV_NAME="$active_env"
        if [[ "${audit_mode:-1}" == "2" ]]; then
          configure_audit_wizard_args
        fi
        ACTION="audit"
        return
        ;;
      7)
        build_mode_reset_selection
        ACTION="providers"
        ENV_NAME="$active_env"
        return
        ;;
      8)
        ensure_env_confirmation "$active_env" "env safety review" "preview" || true
        ;;
      9)
        OPS_ROOT_DIR="$ROOT_DIR" uah_ops_dispatch_submenu "$active_env" menu_connectivity || true
        ;;
      10)
        OPS_ROOT_DIR="$ROOT_DIR" uah_ops_dispatch_submenu "$active_env" menu_logs || true
        ;;
      11)
        OPS_ROOT_DIR="$ROOT_DIR" uah_ops_dispatch_submenu "$active_env" menu_queue || true
        ;;
      12)
        OPS_ROOT_DIR="$ROOT_DIR" uah_ops_dispatch_submenu "$active_env" menu_database || true
        ;;
      13)
        OPS_ROOT_DIR="$ROOT_DIR" uah_ops_dispatch_submenu "$active_env" menu_users || true
        ;;
      14)
        build_mode_reset_selection
        ACTION="debug"
        EXTRA_ARGS=("invites" "menu")
        ENV_NAME="$active_env"
        return
        ;;
      15)
        OPS_ROOT_DIR="$ROOT_DIR" uah_ops_dispatch_submenu "$active_env" menu_network || true
        ;;
      16)
        echo ""
        read -rp "  Script doctor: 1) audit  2) fix CRLF  [1/2]: " script_doctor_choice
        build_mode_reset_selection
        ENV_NAME="$active_env"
        if [[ "$script_doctor_choice" == "2" ]]; then
          ACTION="debug"
          EXTRA_ARGS=("scripts" "fix")
        else
          ACTION="debug"
          EXTRA_ARGS=("scripts" "audit")
        fi
        return
        ;;
      17)
        run_debug "$active_env" status
        debug_press_enter
        ;;
      18)
        build_mode_reset_selection
        ACTION="debug"
        EXTRA_ARGS=()
        ENV_NAME="$active_env"
        return
        ;;
      19)
        selected_env="$(choose_environment_interactive "$active_env")"
        active_env="$selected_env"
        ;;
      20)
        configure_rebuild_ui_for_action "$active_env" "menu" || true
        ;;
      21)
        build_mode_reset_selection
        ACTION="debug"
        EXTRA_ARGS=("extension" "repack")
        ENV_NAME="$active_env"
        return
        ;;
      0)
        echo "Cancelled."
        exit 0
        ;;
      *)
        debug_print_warn "Invalid action selection."
        debug_press_enter
        ;;
    esac
  done
}

print_usage() {
  cat <<'EOF'
UAH lifecycle command suite

Usage:
  bash scripts/uah.sh [environment] <action> [options]
  bash scripts/uah.sh --help

Environments:
  dev | beta | prod

Environment selection:
  - If omitted, the script auto-detects environment from current path and root .env.
  - In interactive mode, startup opens a rich menu + HUD before action selection.
  - The menu lets you switch environment and review/confirm key non-sensitive env values.
  - The menu also includes rebuild controls for start/restart/sync (none, all, or service-level rebuild).
  - Detection checks /environments/<env> path segments first, then ENVIRONMENT/ENV/COMPOSE_PROJECT_NAME.
  - If detection fails, pass environment explicitly.

Actions:
  start | stop | restart | debug | sync | cert-sync | audit | providers

Deprecated (prints a hint; use interactive Control Center instead):
  tools | tooling | ui

Debug:
  bash scripts/uah.sh <env> debug
  bash scripts/uah.sh <env> debug help
  bash scripts/uah.sh <env> debug status
  bash scripts/uah.sh <env> debug connectivity [full|ollama|redis|db|vpn-ping|host-ollama|containers|env|wireguard|cert]
  bash scripts/uah.sh <env> debug logs [backend|frontend|landing|cloudflared|redis|db] [--tail N] [--follow] [--raw|--errors|--filtered]
  bash scripts/uah.sh <env> debug queue [status|clear|clear-redis|clear-stuck|active|recent|failed|retry <id>|test-parse <local|cloud|rules>]
  bash scripts/uah.sh <env> debug database [isolation|user-count|resume-count|parse-stats|recent|raw <SQL>|size]
  bash scripts/uah.sh <env> debug users [list|show <email>|toggle-active <email> <true|false>|toggle-developer <email> <true|false>|reset-password <email> <password>]
  bash scripts/uah.sh <env> debug invites [menu|ui|interactive|list [all|used|unused|active|inactive]|show <code>|create <count> [max_uses] [expires_in_or_iso] [name]|revoke <code>|stats|audit [tail]]
  bash scripts/uah.sh <env> debug scripts [audit|fix]
  bash scripts/uah.sh <env> debug network [show-topology|show-routes|show-docker-user|show-vpn-iptables|apply-route|rollback-route|check-route]
  bash scripts/uah.sh beta debug network [apply-bridge|remove-bridge|full-reapply|rollback-all]

Build options (for start, restart, sync only):
  --no-build
  --build | --build-all
  --build-frontend
  --build-backend
  --build-db
  --build-redis
  --build-cloudflared (beta only)
  --build-landing (beta only)
  --build-service <name>
  --build-service=<name>

Sync mode:
  dev sync [safe|hard]   (default: safe)
  beta sync [safe|hard]  (default: safe)

Audit options:
  --env-file <path>
  --mode <full|repo|docker|host>
  --fix
  --fail-on-warn
  --json [path]

Provider options:
  providers list [--live|--env]
  providers show <provider>
  providers enable <provider> [--ingest] [--display] [--scheduled] [--all]
  providers disable <provider> [--ingest] [--display] [--scheduled] [--all]
  providers set <provider> <field> <value>
  providers clear <provider> <field>
  providers sync-now <provider> [--category <name>]

Safe sync behavior:
  Detects local blockers before pull (dirty files, local commits, diverged state).
  In interactive mode, you'll be prompted to abort or force hard sync.

Env safety behavior:
  start/restart/sync-rebuild paths run an env safety check.
  Interactive mode offers: Continue, Guided suggested fixes (confirm each), Numbered manual key editor, Abort.
  Non-interactive mode fails if critical env safety findings are detected.

Examples:
  bash scripts/uah.sh dev start
  bash scripts/uah.sh dev restart --build-frontend --build-backend
  bash scripts/uah.sh beta restart --build-all
  bash scripts/uah.sh dev sync hard
  bash scripts/uah.sh dev sync --build-all
  bash scripts/uah.sh beta sync --build-frontend
  bash scripts/uah.sh dev debug status
  bash scripts/uah.sh beta debug users reset-password user@example.com NewPass123
  bash scripts/uah.sh dev providers list --live
  bash scripts/uah.sh dev providers enable jooble --display
EOF
}

run_compose() {
  local env_name="$1"
  shift

  if [[ "$env_name" == "dev" ]]; then
    docker compose --env-file "$ROOT_DIR/.env" -f "$ROOT_DIR/docker-compose.yml" "$@"
    return
  fi

  if [[ "$env_name" == "beta" ]]; then
    REDIS_HOST_PORT="${BETA_REDIS_HOST_PORT:-6380}" \
      docker compose --env-file "$ROOT_DIR/.env" -f "$ROOT_DIR/docker-compose.yml" -f "$ROOT_DIR/docker-compose.beta.yml" "$@"
    return
  fi

  echo "Compose commands are scaffolded for prod. Provide prod compose details before running '$*'." >&2
  exit 2
}

prod_scaffold() {
  local action="$1"
  echo "Prod mode is scaffold-only right now."
  echo "Requested action '$action' was not executed."
  echo "Add prod compose/container/network details before enabling prod operations."
  return 2
}

sync_dev_cert() {
  local mode="${1:-strict}"
  local cert_required="true"

  if [[ "$mode" == "optional" ]]; then
    cert_required="false"
  fi

  CERT_REQUIRED="$cert_required" bash "$ROOT_DIR/scripts/dev/certbot-sync-dev-cert.sh"
}

dev_backend_connectivity_check_once() {
  docker exec uah-dev-backend python3 - <<'PY'
import httpx
import sys

try:
    response = httpx.get('http://localhost:8000/api/', timeout=5)
    print('BACKEND: OK -', response.status_code)
    sys.exit(0)
except Exception as exc:
    print('BACKEND: FAILED -', type(exc).__name__, str(exc))
    sys.exit(1)
PY
}

wait_for_dev_backend_ready() {
  local max_attempts=6
  local attempt=1
  local delay=2

  while ((attempt <= max_attempts)); do
    echo "  readiness attempt $attempt/$max_attempts..."
    if dev_backend_connectivity_check_once; then
      return 0
    fi

    if ((attempt < max_attempts)); then
      echo "  Backend not ready yet. Retrying in ${delay}s..."
      sleep "$delay"
      if ((delay < 10)); then
        delay=$((delay + 2))
      fi
    fi

    attempt=$((attempt + 1))
  done

  return 1
}

dev_start() {
  echo "=== UAH Dev Start ==="

  echo "[1/7] Running preflight checks..."
  preflight_startup dev

  echo "[2/7] Starting containers ($(build_mode_label))..."
  run_compose_up_with_build_mode dev

  echo "[3/7] Applying Alembic migrations and refreshing runtime services..."
  run_live_schema_reconcile_with_policy dev true "start"

  echo "[4/7] Applying WireGuard host route..."
  VPN_CONTAINER=uah-dev-vpn \
  BACKEND_CONTAINER=uah-dev-backend \
  NETWORK_NAME=uah-infra \
  ROUTE_OWNER=dev \
  bash "$ROOT_DIR/scripts/dev/network/apply_desktop_ollama_temp_route.sh"

  echo "[5/7] Waiting for backend to be ready..."
  if ! wait_for_dev_backend_ready; then
    echo "Backend readiness check failed after retries." >&2
    echo "Run: bash scripts/uah.sh dev debug logs backend --tail 120 --errors" >&2
    echo ""
    run_compose dev ps || true
    return 1
  fi

  echo "[6/7] Syncing cert to frontend..."
  if ! sync_dev_cert optional; then
    echo "Cert sync warning: unable to sync certs now."
    echo "You can retry later with: bash scripts/uah.sh dev cert-sync"
  fi

  echo "[7/7] Connectivity check..."
  if ! dev_backend_connectivity_check_once; then
    echo "Backend failed final connectivity check." >&2
    echo "Run: bash scripts/uah.sh dev debug status" >&2
    echo ""
    run_compose dev ps || true
    return 1
  fi

  echo ""
  run_compose dev ps
  echo ""
  print_schema_reconcile_summary dev "start"
  echo "=== Dev stack started ==="
  echo "Access: https://dev.uahapp.com (VPN required)"
}

dev_stop() {
  echo "=== UAH Dev Stop ==="

  echo "[1/4] Clearing stuck DB jobs..."
  docker exec uah-dev-db psql -U uah -d uah_dev -c "
  UPDATE parse_jobs
  SET status='failed', error_message='Cleared on shutdown', updated_at=now()
  WHERE status IN ('queued','parsing','validating');
" 2>/dev/null || echo "DB not running, skipping."

  echo "[2/4] Clearing Redis..."
  docker exec uah-redis redis-cli FLUSHDB 2>/dev/null || echo "Redis not running, skipping."

  echo "[3/4] Rolling back dev WireGuard route rules..."
  VPN_CONTAINER=uah-dev-vpn \
  BACKEND_CONTAINER=uah-dev-backend \
  NETWORK_NAME=uah-infra \
  ROUTE_OWNER=dev \
  bash "$ROOT_DIR/scripts/dev/network/rollback_desktop_ollama_temp_route.sh" 2>/dev/null || echo "Rollback script not available or nothing to rollback."

  echo "[4/4] Stopping containers..."
  run_compose dev down

  echo ""
  echo "=== Dev stack stopped cleanly ==="
  echo "VPN and VPN UI left running."
}

dev_restart() {
  echo "=== UAH Dev Restart ($(build_mode_label)) ==="
  dev_stop
  echo ""
  sleep 3
  if ! dev_start; then
    return 1
  fi
}

beta_start() {
  local beta_backend_running="false"
  local beta_backend_port_ok="false"
  local beta_ollama_ok="false"
  local -a required_beta_services=(backend frontend db redis cloudflared landing)
  local beta_bridge
  local infra_bridge
  local beta_br
  local infra_br

  if [[ ! -f "$ROOT_DIR/docker-compose.yml" || ! -f "$ROOT_DIR/docker-compose.beta.yml" ]]; then
    echo "Missing required compose files at repo root." >&2
    exit 1
  fi

  echo "=== UAH Beta Start ==="

  echo "[1/7] Running preflight checks..."
  preflight_startup beta

  echo "[2/7] Starting containers ($(build_mode_label))..."
  run_compose_up_with_build_mode beta

  echo "[2b/7] Ensuring required beta services are running..."
  run_compose beta up -d "${required_beta_services[@]}"

  echo "[2c/7] Verifying live frontend asset integrity..."
  if ! verify_frontend_asset_integrity beta "https://beta.uahapp.com"; then
    notify_discord "**Beta start FAILED** frontend index/chunk integrity check failed" 15158332
    run_compose beta ps || true
    return 1
  fi

  echo "[3/8] Applying Alembic migrations and refreshing runtime services..."
  if ! run_live_schema_reconcile_with_policy beta true "start"; then
    notify_discord "**Beta start FAILED** during Alembic upgrade or runtime refresh" 15158332
    run_compose beta ps || true
    return 1
  fi

  echo "[4/8] Applying WireGuard host route..."
  VPN_CONTAINER=uah-dev-vpn \
  BACKEND_CONTAINER=uah-beta-backend \
  NETWORK_NAME=uah-infra \
  SOURCE_CIDR=172.18.0.0/16 \
  ROUTE_OWNER=beta \
  bash "$ROOT_DIR/scripts/beta/network/apply_desktop_ollama_temp_route.sh"

  echo "[5/8] Allowing cross-bridge Docker traffic..."
  beta_bridge=$(docker network inspect uah-beta-infra --format '{{.Id}}' | cut -c1-12)
  infra_bridge=$(docker network inspect uah-infra --format '{{.Id}}' | cut -c1-12)
  beta_br="br-${beta_bridge}"
  infra_br="br-${infra_bridge}"

  sudo iptables -C DOCKER-USER -i "$beta_br" -o "$infra_br" -j ACCEPT 2>/dev/null || \
    sudo iptables -I DOCKER-USER -i "$beta_br" -o "$infra_br" -j ACCEPT

  sudo iptables -C DOCKER-USER -i "$infra_br" -o "$beta_br" -j ACCEPT 2>/dev/null || \
    sudo iptables -I DOCKER-USER -i "$infra_br" -o "$beta_br" -j ACCEPT

  echo "[6/8] Waiting for backend to settle..."
  sleep 12

  echo "[7/8] Connectivity check..."
  if docker exec uah-beta-backend python3 -c "
import httpx
import sys
try:
    r = httpx.get('http://10.8.0.8:11434/api/tags', timeout=8)
    models = [m['name'] for m in r.json().get('models', [])]
    print('LOCAL OLLAMA: OK -', models)
    sys.exit(0)
except Exception as e:
    print('LOCAL OLLAMA: FAILED -', type(e).__name__, str(e))
    sys.exit(1)
"; then
    beta_ollama_ok="true"
  fi

  if docker inspect -f '{{.State.Running}}' uah-beta-backend 2>/dev/null | grep -qx 'true'; then
    beta_backend_running="true"
  fi

  if docker exec uah-beta-backend python3 -c "
import socket
import sys
try:
    conn = socket.create_connection(('127.0.0.1', 8000), 5)
    conn.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" >/dev/null 2>&1; then
    beta_backend_port_ok="true"
  fi

  echo ""
  run_compose beta ps
  echo ""
  print_schema_reconcile_summary beta "start"
  echo "=== Beta stack started ==="

  if [[ "$beta_backend_running" == "true" && "$beta_backend_port_ok" == "true" && "$beta_ollama_ok" == "true" ]]; then
    notify_discord "**Beta start healthy**: backend running, backend port 8000 reachable, ollama reachable" 3066993
  elif [[ "$beta_backend_running" == "true" && "$beta_backend_port_ok" == "true" ]]; then
    notify_discord "**Beta start degraded**: backend running and reachable, but ollama connectivity failed" 16776960
  else
    notify_discord "**Beta start FAILED health**: backend running=$beta_backend_running, port8000=$beta_backend_port_ok, ollama=$beta_ollama_ok" 15158332
  fi
}

beta_stop() {
  echo "=== UAH Beta Stop ==="

  echo "[1/4] Clearing Redis queue and stuck jobs..."
  docker exec uah-beta-redis redis-cli FLUSHDB 2>/dev/null || echo "Redis not running, skipping."

  docker exec uah-beta-db psql -U uah -d uah_beta -c "
  UPDATE parse_jobs
  SET status='failed', error_message='Cleared on shutdown', updated_at=now()
  WHERE status IN ('queued','parsing','validating');
" 2>/dev/null || echo "DB not running, skipping."

  echo "[2/4] Rolling back WireGuard iptables rules..."
  VPN_CONTAINER=uah-dev-vpn \
  BACKEND_CONTAINER=uah-beta-backend \
  NETWORK_NAME=uah-infra \
  SOURCE_CIDR=172.18.0.0/16 \
  ROUTE_OWNER=beta \
  bash "$ROOT_DIR/scripts/beta/network/rollback_desktop_ollama_temp_route.sh" 2>/dev/null || echo "Rollback script not available or nothing to rollback."

  echo "[3/4] Removing cross-bridge Docker rules..."
  local beta_bridge
  local infra_bridge

  beta_bridge=$(docker network inspect uah-beta-infra --format '{{.Id}}' 2>/dev/null | cut -c1-12)
  infra_bridge=$(docker network inspect uah-infra --format '{{.Id}}' 2>/dev/null | cut -c1-12)

  if [[ -n "$beta_bridge" && -n "$infra_bridge" ]]; then
    local beta_br="br-${beta_bridge}"
    local infra_br="br-${infra_bridge}"
    sudo iptables -D DOCKER-USER -i "$beta_br" -o "$infra_br" -j ACCEPT 2>/dev/null || true
    sudo iptables -D DOCKER-USER -i "$infra_br" -o "$beta_br" -j ACCEPT 2>/dev/null || true
    echo "Cross-bridge rules removed."
  else
    echo "Networks already gone, skipping iptables cleanup."
  fi

  echo "[4/4] Stopping containers..."
  run_compose beta down

  echo ""
  echo "=== Beta stack stopped cleanly ==="
  echo "VPN and VPN UI left running - use wg-easy to manage those separately."
}

beta_restart() {
  echo "=== UAH Beta Restart ($(build_mode_label)) ==="
  beta_stop
  echo ""
  sleep 3
  beta_start
}

beta_sync() {
  local mode="${1:-safe}"

  case "$mode" in
    safe|ff|fast-forward)
      if ! run_safe_sync_flow beta; then
        notify_discord "**Beta sync FAILED** in safe mode" 15158332
        return 1
      fi
      ;;
    hard|reset)
      if ! run_hard_sync_flow true; then
        notify_discord "**Beta sync FAILED** in hard mode" 15158332
        return 1
      fi
      ;;
    *)
      echo "Unknown sync mode '$mode'. Use safe or hard." >&2
      exit 1
      ;;
  esac
}

sql_escape_literal() {
  local value="$1"
  value="${value//\'/\'\'}"
  printf '%s' "$value"
}

debug_show_status() {
  local env_name="$1"
  local ollama_ok=0
  local provider_summary

  debug_profile_init "$env_name"
  debug_header "$env_name" "Status"

  if docker ps --format '{{.Names}}' | grep -Fxq "$DEBUG_BACKEND_CONTAINER"; then
    debug_print_ok "Backend container is running: $DEBUG_BACKEND_CONTAINER"
    if docker exec "$DEBUG_BACKEND_CONTAINER" python3 -c "import httpx; httpx.get('http://10.8.0.8:11434/api/tags', timeout=3)" >/dev/null 2>&1; then
      ollama_ok=1
      debug_print_ok "Desktop Ollama is reachable from backend"
    else
      debug_print_warn "Desktop Ollama is not reachable from backend"
    fi
  else
    debug_print_error "Backend container is offline: $DEBUG_BACKEND_CONTAINER"
  fi

  echo ""
  debug_print_section "Container status"
  run_compose "$env_name" ps
  echo ""
  debug_print_section "Summary"
  provider_summary="$(provider_summary_label "$env_name" "auto" 2>/dev/null || provider_summary_label "$env_name" "env" 2>/dev/null || true)"
  if [[ -n "$provider_summary" ]]; then
    debug_print_section "$provider_summary"
  fi
  if [[ "$ollama_ok" == "1" ]]; then
    debug_print_ok "Status: ONLINE"
  else
    debug_print_warn "Status: PARTIAL/DEGRADED"
  fi
}

debug_connectivity() {
  local env_name="$1"
  local check_type="${2:-full}"

  debug_profile_init "$env_name"

  case "$check_type" in
    full)
      debug_show_status "$env_name"
      echo ""
      debug_print_section "Backend -> Redis"
      docker exec "$DEBUG_BACKEND_CONTAINER" python3 -c "import redis, os; c=redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://$DEBUG_REDIS_CONTAINER:6379/0')); print('  ping=', c.ping())" 2>&1 | sed 's/^/  /' || true
      echo ""
      debug_print_section "Backend -> Database"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT current_database(), now();" 2>&1 | sed 's/^/  /' || true
      echo ""
      debug_print_section "VPN -> Desktop ping"
      docker exec uah-dev-vpn ping -c 2 10.8.0.8 2>&1 | sed 's/^/  /' || true
      ;;
    ollama)
      debug_header "$env_name" "Connectivity :: Ollama"
      docker exec "$DEBUG_BACKEND_CONTAINER" python3 -c "import httpx, json; r=httpx.get('http://10.8.0.8:11434/api/tags', timeout=8); print('status=', r.status_code); print(json.dumps([m.get('name') for m in r.json().get('models', [])], indent=2))" 2>&1 | sed 's/^/  /'
      ;;
    redis)
      debug_header "$env_name" "Connectivity :: Redis"
      docker exec "$DEBUG_BACKEND_CONTAINER" python3 -c "import redis, os; c=redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://$DEBUG_REDIS_CONTAINER:6379/0')); print('ping=', c.ping()); print('queue_depth=', c.llen('uah:parse_jobs'))" 2>&1 | sed 's/^/  /'
      ;;
    db|database)
      debug_header "$env_name" "Connectivity :: Database"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT current_database(), inet_server_addr(), now();" 2>&1 | sed 's/^/  /'
      ;;
    vpn-ping)
      debug_header "$env_name" "Connectivity :: VPN ping"
      docker exec uah-dev-vpn ping -c 4 10.8.0.8 2>&1 | sed 's/^/  /'
      ;;
    host-ollama)
      debug_header "$env_name" "Connectivity :: Host to Ollama"
      curl -s --max-time 8 http://10.8.0.8:11434/api/tags 2>/dev/null | python3 -c "import json,sys; data=json.load(sys.stdin); print('  OK'); [print('  -', m.get('name')) for m in data.get('models', [])]" 2>/dev/null || debug_print_error "Host could not reach desktop Ollama"
      ;;
    containers)
      debug_header "$env_name" "Connectivity :: Containers"
      run_compose "$env_name" ps
      ;;
    env|settings)
      debug_header "$env_name" "Connectivity :: Active settings"
      docker exec "$DEBUG_BACKEND_CONTAINER" python3 -c "from app.core.config import settings; print('POSTGRES_HOST=', settings.POSTGRES_HOST); print('POSTGRES_DB=', settings.POSTGRES_DB); print('USE_LOCAL_PIPELINE=', settings.USE_LOCAL_PIPELINE); print('REDIS_ENABLED=', settings.REDIS_ENABLED); print('REDIS_URL=', settings.REDIS_URL); print('ZAI_API_KEY set=', bool(settings.ZAI_API_KEY))" 2>&1 | sed 's/^/  /'
      ;;
    wireguard)
      debug_header "$env_name" "Connectivity :: WireGuard"
      docker exec uah-dev-vpn wg show 2>&1 | sed 's/^/  /'
      ;;
    cert)
      if [[ "$env_name" != "dev" ]]; then
        echo "Cert diagnostics are only supported for dev." >&2
        exit 1
      fi
      debug_header "$env_name" "Connectivity :: Cert status"
      debug_print_section "Volume cert"
      openssl x509 -in "$ROOT_DIR/volumes/certs/dev/tls.crt" -noout -dates -subject 2>&1 | sed 's/^/  /' || true
      echo ""
      debug_print_section "Live LE cert"
      sudo openssl x509 -in /etc/letsencrypt/live/dev.uahapp.com/fullchain.pem -noout -dates -subject 2>&1 | sed 's/^/  /' || true
      ;;
    *)
      echo "Unknown connectivity check '$check_type'." >&2
      echo "Supported: full, ollama, redis, db, vpn-ping, host-ollama, containers, env, wireguard, cert" >&2
      exit 1
      ;;
  esac
}

debug_logs() {
  local env_name="$1"
  shift || true

  local service="backend"
  local tail_lines="50"
  local follow="false"
  local mode="filtered"

  while (($#)); do
    case "$1" in
      backend|frontend|landing|cloudflared|redis|db)
        service="$1"
        ;;
      --tail)
        tail_lines="${2:-}"
        if [[ -z "$tail_lines" ]]; then
          echo "--tail requires a value." >&2
          exit 1
        fi
        shift
        ;;
      --follow|-f)
        follow="true"
        ;;
      --raw)
        mode="raw"
        ;;
      --errors)
        mode="errors"
        ;;
      --filtered)
        mode="filtered"
        ;;
      *)
        echo "Unknown logs option '$1'." >&2
        exit 1
        ;;
    esac
    shift
  done

  if [[ "$env_name" == "dev" && "$service" == "cloudflared" ]]; then
    echo "cloudflared logs are beta-specific." >&2
    exit 1
  fi

  if [[ "$env_name" == "dev" && "$service" == "landing" ]]; then
    echo "landing logs are beta-specific." >&2
    exit 1
  fi

  if [[ "$env_name" == "beta" && "$service" == "frontend" ]]; then
    debug_print_warn "Using frontend logs on beta; cloudflared is usually the relevant edge service."
  fi

  debug_header "$env_name" "Logs :: $service"

  if [[ "$follow" == "true" ]]; then
    if [[ "$mode" == "errors" ]]; then
      run_compose "$env_name" logs -f --tail="$tail_lines" "$service" 2>&1 | grep -iE "error|exception|failed|traceback|critical" || true
      return
    fi
    if [[ "$mode" == "filtered" && "$service" == "backend" ]]; then
      run_compose "$env_name" logs -f --tail="$tail_lines" "$service" 2>&1 | grep -v "sqlalchemy" | grep -v "SELECT" | grep -v "FROM " | grep -v "WHERE " | grep -v "LIMIT " | grep -v "cached since" || true
      return
    fi
    run_compose "$env_name" logs -f --tail="$tail_lines" "$service"
    return
  fi

  if [[ "$mode" == "errors" ]]; then
    run_compose "$env_name" logs --tail="$tail_lines" "$service" 2>&1 | grep -iE "error|exception|failed|traceback|critical" || true
    return
  fi

  if [[ "$mode" == "filtered" && "$service" == "backend" ]]; then
    run_compose "$env_name" logs --tail="$tail_lines" "$service" 2>&1 | grep -v "sqlalchemy" | grep -v "SELECT" | grep -v "FROM " | grep -v "WHERE " | grep -v "LIMIT " | grep -v "cached since" || true
    return
  fi

  run_compose "$env_name" logs --tail="$tail_lines" "$service"
}

debug_queue() {
  local env_name="$1"
  local action="${2:-status}"
  local arg="${3:-}"
  local method

  debug_profile_init "$env_name"
  debug_header "$env_name" "Queue :: $action"

  case "$action" in
    status)
      debug_print_section "Redis queue depth"
      docker exec "$DEBUG_REDIS_CONTAINER" redis-cli LLEN uah:parse_jobs 2>&1 | sed 's/^/  /'
      echo ""
      debug_print_section "DB job counts by status"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT status, COUNT(*) as count FROM parse_jobs GROUP BY status ORDER BY count DESC;" 2>&1 | sed 's/^/  /'
      ;;
    clear)
      docker exec "$DEBUG_REDIS_CONTAINER" redis-cli FLUSHDB 2>&1 | sed 's/^/  /'
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "UPDATE parse_jobs SET status='failed', error_message='Cleared by admin', updated_at=now() WHERE status IN ('queued','parsing','validating');" 2>&1 | sed 's/^/  /'
      ;;
    clear-redis)
      docker exec "$DEBUG_REDIS_CONTAINER" redis-cli FLUSHDB 2>&1 | sed 's/^/  /'
      ;;
    clear-stuck)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "UPDATE parse_jobs SET status='failed', error_message='Cleared by admin', updated_at=now() WHERE status IN ('queued','parsing','validating') RETURNING id, status, updated_at;" 2>&1 | sed 's/^/  /'
      ;;
    active)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT id, user_id, method, status, progress_stage, error_code, created_at, updated_at FROM parse_jobs WHERE status IN ('queued','parsing','validating') ORDER BY created_at ASC;" 2>&1 | sed 's/^/  /'
      ;;
    recent)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT id, user_id, method, status, error_code, LEFT(error_message,40) as error_msg, updated_at FROM parse_jobs ORDER BY updated_at DESC LIMIT 20;" 2>&1 | sed 's/^/  /'
      ;;
    failed)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT id, user_id, method, error_code, LEFT(error_message,60) as error_msg, updated_at FROM parse_jobs WHERE status='failed' ORDER BY updated_at DESC LIMIT 20;" 2>&1 | sed 's/^/  /'
      ;;
    retry)
      if [[ -z "$arg" ]]; then
        echo "Usage: bash scripts/uah.sh <env> debug queue retry <job_id>" >&2
        exit 1
      fi
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "UPDATE parse_jobs SET status='queued', error_code=NULL, error_message=NULL, progress_stage='Queued…', updated_at=now() WHERE id=$arg AND status='failed' RETURNING id, status, updated_at;" 2>&1 | sed 's/^/  /'
      ;;
    test-parse)
      method="${arg:-local}"
      if [[ "$method" != "local" && "$method" != "cloud" && "$method" != "rules" ]]; then
        echo "Invalid parse method '$method'. Use local|cloud|rules." >&2
        exit 1
      fi
      docker exec -i -e UAH_PARSE_METHOD="$method" "$DEBUG_BACKEND_CONTAINER" python3 - <<'PY'
import json
import os
import httpx

method = os.environ.get("UAH_PARSE_METHOD", "local")
try:
    response = httpx.post("http://localhost:8000/api/internal/test-parse", json={"method": method}, timeout=60)
    print("status=", response.status_code)
    print(json.dumps(response.json(), indent=2)[:1000])
except Exception as exc:
    print("test parse failed:", type(exc).__name__, str(exc))
PY
      ;;
    *)
      echo "Unknown queue action '$action'." >&2
      echo "Supported: status, clear, clear-redis, clear-stuck, active, recent, failed, retry <id>, test-parse [local|cloud|rules]" >&2
      exit 1
      ;;
  esac
}

debug_database() {
  local env_name="$1"
  local action="${2:-parse-stats}"
  shift 2 || true

  debug_profile_init "$env_name"
  debug_header "$env_name" "Database :: $action"

  case "$action" in
    isolation)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT current_database(), inet_server_addr(), version();" 2>&1 | sed 's/^/  /'
      ;;
    user-count)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT COUNT(*) as total_users FROM users;" 2>&1 | sed 's/^/  /'
      ;;
    resume-count)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT COUNT(*) as total_resumes FROM resumes;" 2>&1 | sed 's/^/  /'
      ;;
    parse-stats)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT method, status, COUNT(*) as count FROM parse_jobs GROUP BY method, status ORDER BY method, status;" 2>&1 | sed 's/^/  /'
      ;;
    recent)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT id, user_id, method, status, error_code, LEFT(error_message,40) as error_msg, updated_at FROM parse_jobs ORDER BY updated_at DESC LIMIT 20;" 2>&1 | sed 's/^/  /'
      ;;
    raw)
      if (($# == 0)); then
        echo "Usage: bash scripts/uah.sh <env> debug database raw <SQL>" >&2
        exit 1
      fi
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "$*" 2>&1 | sed 's/^/  /'
      ;;
    size)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT pg_size_pretty(pg_database_size(current_database())) as db_size;" 2>&1 | sed 's/^/  /'
      ;;
    *)
      echo "Unknown database action '$action'." >&2
      echo "Supported: isolation, user-count, resume-count, parse-stats, recent, raw <SQL>, size" >&2
      exit 1
      ;;
  esac
}

debug_users() {
  local env_name="$1"
  local action="${2:-list}"
  local user_email="${3:-}"
  local arg="${4:-}"
  local escaped_user_email

  if [[ "$env_name" != "dev" && "$env_name" != "beta" ]]; then
    echo "User admin operations are only supported for dev and beta." >&2
    exit 1
  fi

  debug_profile_init "$env_name"
  debug_header "$env_name" "Users :: $action"

  case "$action" in
    list)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT id, username, email, first_name, is_active, is_admin, is_developer, created_at FROM users ORDER BY id;" 2>&1 | sed 's/^/  /'
      ;;
    show)
      if [[ -z "$user_email" ]]; then
        echo "Usage: bash scripts/uah.sh $env_name debug users show <email>" >&2
        exit 1
      fi
      escaped_user_email="$(sql_escape_literal "$user_email")"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT id, username, email, first_name, last_name, is_active, is_admin, is_developer, email_verified, created_at, updated_at FROM users WHERE lower(email)=lower('${escaped_user_email}');" 2>&1 | sed 's/^/  /'
      ;;
    toggle-active)
      if [[ -z "$user_email" || -z "$arg" ]]; then
        echo "Usage: bash scripts/uah.sh $env_name debug users toggle-active <email> <true|false>" >&2
        exit 1
      fi
      if [[ "$arg" != "true" && "$arg" != "false" ]]; then
        echo "toggle-active requires true or false." >&2
        exit 1
      fi
      escaped_user_email="$(sql_escape_literal "$user_email")"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "UPDATE users SET is_active=$arg WHERE lower(email)=lower('${escaped_user_email}') RETURNING email, is_active;" 2>&1 | sed 's/^/  /'
      ;;
    toggle-developer)
      if [[ -z "$user_email" || -z "$arg" ]]; then
        echo "Usage: bash scripts/uah.sh $env_name debug users toggle-developer <email> <true|false>" >&2
        exit 1
      fi
      if [[ "$arg" != "true" && "$arg" != "false" ]]; then
        echo "toggle-developer requires true or false." >&2
        exit 1
      fi
      escaped_user_email="$(sql_escape_literal "$user_email")"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "UPDATE users SET is_developer=$arg WHERE lower(email)=lower('${escaped_user_email}') RETURNING email, is_developer;" 2>&1 | sed 's/^/  /'
      ;;
    reset-password)
      if [[ -z "$user_email" || -z "$arg" ]]; then
        echo "Usage: bash scripts/uah.sh $env_name debug users reset-password <email> <password>" >&2
        exit 1
      fi
      BACKEND_CONTAINER="$DEBUG_BACKEND_CONTAINER" bash "$ROOT_DIR/scripts/dev/diagnostic/reset-user-password.sh" "$user_email" "$arg"
      ;;
    *)
      echo "Unknown users action '$action'." >&2
      echo "Supported: list, show <email>, toggle-active <email> <true|false>, toggle-developer <email> <true|false>, reset-password <email> <password>" >&2
      exit 1
      ;;
  esac
}

debug_invites() {
  local env_name="$1"
  local action="${2:-list}"
  local arg="${3:-}"
  local arg2="${4:-}"
  local arg3="${5:-}"
  local arg4="${6:-}"
  local tail_lines="${arg:-120}"
  local escaped_code
  local filter_sql="1=1"

  if [[ "$env_name" != "dev" && "$env_name" != "beta" ]]; then
    echo "Invite management is only supported for dev and beta." >&2
    exit 1
  fi

  if [[ "$action" == "menu" || "$action" == "ui" || "$action" == "interactive" ]]; then
    debug_invites_menu "$env_name"
    return
  fi

  debug_profile_init "$env_name"
  debug_header "$env_name" "Invites :: $action"

  case "$action" in
    list)
      case "${arg:-all}" in
        all)
          filter_sql="1=1"
          ;;
        used)
          filter_sql="use_count > 0"
          ;;
        unused)
          filter_sql="use_count = 0"
          ;;
        active)
          filter_sql="is_active = true"
          ;;
        inactive)
          filter_sql="is_active = false"
          ;;
        *)
          echo "Unknown invite list filter '${arg}'." >&2
          echo "Supported: all, used, unused, active, inactive" >&2
          exit 1
          ;;
      esac
          docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -P pager=off -P border=2 -c "SELECT code, COALESCE(name, '-') AS name, CASE WHEN is_active=false THEN 'revoked' WHEN expires_at IS NOT NULL AND expires_at <= now() THEN 'expired' WHEN use_count >= max_uses THEN 'depleted' ELSE 'available' END AS state, max_uses, use_count, GREATEST(max_uses - use_count, 0) AS remaining_uses, created_by, COALESCE(used_by::text, '-') AS last_used_by, COALESCE(to_char(expires_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') || 'Z', '-') AS expires_utc, to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') || 'Z' AS created_utc FROM invites WHERE ${filter_sql} ORDER BY created_at DESC LIMIT 200;" 2>&1 | sed 's/^/  /'
      ;;
    show)
      if [[ -z "$arg" ]]; then
        echo "Usage: bash scripts/uah.sh $env_name debug invites show <code>" >&2
        exit 1
      fi
      escaped_code="$(sql_escape_literal "$arg")"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT id, code, name, is_active, max_uses, use_count, created_by, used_by AS last_used_by, used_at AS last_used_at, expires_at, created_at FROM invites WHERE code='${escaped_code}';" 2>&1 | sed 's/^/  /'
      ;;
    create)
      if [[ -z "$arg" ]]; then
        echo "Usage: bash scripts/uah.sh $env_name debug invites create <count> [max_uses] [expires_in_or_iso] [name]" >&2
        exit 1
      fi
      if ! [[ "$arg" =~ ^[0-9]+$ ]] || ((arg < 1 || arg > 50)); then
        echo "Invite create count must be between 1 and 50." >&2
        exit 1
      fi
      if [[ -z "$arg2" ]]; then
        arg2="1"
      fi
      if ! [[ "$arg2" =~ ^[0-9]+$ ]] || ((arg2 < 1 || arg2 > 10000)); then
        echo "Invite max uses must be between 1 and 10000." >&2
        exit 1
      fi
      docker exec -i -e UAH_INVITE_COUNT="$arg" -e UAH_INVITE_MAX_USES="$arg2" -e UAH_INVITE_EXPIRES_SPEC="$arg3" -e UAH_INVITE_NAME="$arg4" "$DEBUG_BACKEND_CONTAINER" python3 - <<'PY'
import os
import sys

from app.api.admin import _build_invites, parse_invite_expiry_spec
from app.db.session import SessionLocal
from app.models.user import User

count = int(os.environ.get("UAH_INVITE_COUNT", "1"))
max_uses = int(os.environ.get("UAH_INVITE_MAX_USES", "1"))
expires_raw = os.environ.get("UAH_INVITE_EXPIRES_SPEC")
invite_name = (os.environ.get("UAH_INVITE_NAME") or "").strip() or None

db = SessionLocal()
try:
    try:
        expires_at = parse_invite_expiry_spec(expires_raw)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

    admin_user = db.query(User).filter(User.is_admin.is_(True)).order_by(User.id.asc()).first()
    if not admin_user:
        print("No admin user exists; cannot assign created_by for invite codes.", file=sys.stderr)
        raise SystemExit(1)

    invites = _build_invites(
        db=db,
        current_user=admin_user,
        count=count,
        expires_at=expires_at,
        max_uses=max_uses,
        name=invite_name,
    )

    print(f"Created {len(invites)} invite(s) (max_uses={max_uses}, name={invite_name or '-'}):")
    for invite in invites:
        print(invite.code)
finally:
    db.close()
PY
      ;;
    revoke)
      if [[ -z "$arg" ]]; then
        echo "Usage: bash scripts/uah.sh $env_name debug invites revoke <code>" >&2
        exit 1
      fi
      escaped_code="$(sql_escape_literal "$arg")"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "UPDATE invites SET is_active=false WHERE code='${escaped_code}' RETURNING code, is_active;" 2>&1 | sed 's/^/  /'
      ;;
    stats)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE is_active) AS active, COUNT(*) FILTER (WHERE NOT is_active) AS inactive, COUNT(*) FILTER (WHERE use_count > 0) AS used, COUNT(*) FILTER (WHERE use_count = 0) AS unused, SUM(max_uses) AS total_capacity, SUM(use_count) AS consumed_uses, SUM(GREATEST(max_uses - use_count, 0)) AS remaining_uses FROM invites;" 2>&1 | sed 's/^/  /'
      ;;
    audit)
      if ! [[ "$tail_lines" =~ ^[0-9]+$ ]] || ((tail_lines < 1 || tail_lines > 5000)); then
        echo "Invite audit tail must be between 1 and 5000 lines." >&2
        exit 1
      fi
      run_compose "$env_name" logs --tail="$tail_lines" backend 2>&1 | grep "invite_admin" | sed 's/^/  /' || true
      ;;
    *)
      echo "Unknown invites action '$action'." >&2
      echo "Supported: menu|ui|interactive, list [all|used|unused|active|inactive], show <code>, create <count> [max_uses] [expires_in_or_iso] [name], revoke <code>, stats, audit [tail]" >&2
      exit 1
      ;;
  esac
}

debug_invites_menu() {
  local env_name="$1"
  local stats_line
  local total
  local active
  local inactive
  local used
  local unused
  local choice
  local filter
  local code
  local count
  local max_uses
  local expires_in
  local invite_name

  debug_profile_init "$env_name"

  while true; do
    debug_header "$env_name" "Invites :: Console"

    stats_line="$(docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -At -F '|' -c "SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE is_active) AS active, COUNT(*) FILTER (WHERE NOT is_active) AS inactive, COUNT(*) FILTER (WHERE use_count > 0) AS used, COUNT(*) FILTER (WHERE use_count = 0) AS unused FROM invites;" 2>/dev/null | tail -n 1 || true)"
    IFS='|' read -r total active inactive used unused <<< "$stats_line"

    echo -e "${BOLD}  Invite Management${NC}"
    echo ""
    echo "  Summary"
    echo "    Total:    ${total:-0}"
    echo "    Active:   ${active:-0}"
    echo "    Inactive: ${inactive:-0}"
    echo "    Used:     ${used:-0}"
    echo "    Unused:   ${unused:-0}"
    echo ""
    echo "  Actions"
    echo "    1) List invites (all)"
    echo "    2) List invites (filtered)"
    echo "    3) Show invite by code"
    echo "    4) Create invite(s)"
    echo "    5) Revoke invite"
    echo "    6) View stats"
    echo "    7) View invite audit events"
    echo "    0) Back"
    echo ""
    read -rp "  Choice [0-7]: " choice

    case "$choice" in
      1)
        debug_invites "$env_name" list all
        debug_press_enter
        ;;
      2)
        echo ""
        echo "  Filters: all, used, unused, active, inactive"
        read -rp "  Filter [all]: " filter
        filter="${filter:-all}"
        debug_invites "$env_name" list "$filter"
        debug_press_enter
        ;;
      3)
        read -rp "  Invite code: " code
        if [[ -z "$code" ]]; then
          debug_print_warn "Invite code is required."
        else
          debug_invites "$env_name" show "$code"
        fi
        debug_press_enter
        ;;
      4)
        read -rp "  Count [1-50]: " count
        if [[ -z "$count" ]]; then
          count="1"
        fi
        read -rp "  Max uses per invite [1]: " max_uses
        max_uses="${max_uses:-1}"
        echo "  Expiry examples: 1w, 1hr, 1min, 1m, 1y, or ISO8601"
        read -rp "  Expires in (blank for none): " expires_in
        read -rp "  Invite name/label (blank for none): " invite_name
        debug_invites "$env_name" create "$count" "$max_uses" "$expires_in" "$invite_name"
        debug_press_enter
        ;;
      5)
        read -rp "  Invite code to revoke: " code
        if [[ -z "$code" ]]; then
          debug_print_warn "Invite code is required."
        else
          debug_invites "$env_name" revoke "$code"
        fi
        debug_press_enter
        ;;
      6)
        debug_invites "$env_name" stats
        debug_press_enter
        ;;
      7)
        read -rp "  Tail lines [120]: " count
        count="${count:-120}"
        debug_invites "$env_name" audit "$count"
        debug_press_enter
        ;;
      0)
        return
        ;;
      *)
        debug_print_warn "Invalid choice '$choice'."
        debug_press_enter
        ;;
    esac
  done
}

debug_network() {
  local env_name="$1"
  local action="${2:-show-topology}"
  local beta_bridge
  local infra_bridge
  local beta_br
  local infra_br

  debug_profile_init "$env_name"
  debug_header "$env_name" "Network :: $action"

  case "$action" in
    show-topology)
      if [[ "$env_name" == "beta" ]]; then
        debug_print_section "uah-infra"
        docker network inspect uah-infra --format '{{range $k,$v := .Containers}}  {{$v.Name}}={{$v.IPv4Address}}{{"\n"}}{{end}}' 2>/dev/null || true
        echo ""
      fi
      debug_print_section "$DEBUG_MAIN_NETWORK"
      docker network inspect "$DEBUG_MAIN_NETWORK" --format '{{range $k,$v := .Containers}}  {{$v.Name}}={{$v.IPv4Address}}{{"\n"}}{{end}}' 2>/dev/null || true
      ;;
    show-routes)
      sudo ip route show | grep -E "10.8|172.18|172.21" || true
      ;;
    show-docker-user)
      sudo iptables -L DOCKER-USER -n -v
      ;;
    show-vpn-iptables)
      debug_print_section "FORWARD"
      docker exec uah-dev-vpn iptables -L FORWARD -n -v 2>&1 | sed 's/^/  /'
      echo ""
      debug_print_section "NAT POSTROUTING"
      docker exec uah-dev-vpn iptables -t nat -L POSTROUTING -n -v 2>&1 | sed 's/^/  /'
      ;;
    apply-route)
      if [[ "$env_name" == "dev" ]]; then
        VPN_CONTAINER=uah-dev-vpn BACKEND_CONTAINER="$DEBUG_BACKEND_CONTAINER" NETWORK_NAME=uah-infra ROUTE_OWNER=dev bash "$ROOT_DIR/scripts/dev/network/apply_desktop_ollama_temp_route.sh"
      else
        VPN_CONTAINER=uah-dev-vpn BACKEND_CONTAINER="$DEBUG_BACKEND_CONTAINER" NETWORK_NAME=uah-infra SOURCE_CIDR=172.18.0.0/16 ROUTE_OWNER=beta bash "$ROOT_DIR/scripts/beta/network/apply_desktop_ollama_temp_route.sh"
      fi
      ;;
    rollback-route)
      if [[ "$env_name" == "dev" ]]; then
        VPN_CONTAINER=uah-dev-vpn BACKEND_CONTAINER="$DEBUG_BACKEND_CONTAINER" NETWORK_NAME=uah-infra ROUTE_OWNER=dev bash "$ROOT_DIR/scripts/dev/network/rollback_desktop_ollama_temp_route.sh"
      else
        VPN_CONTAINER=uah-dev-vpn BACKEND_CONTAINER="$DEBUG_BACKEND_CONTAINER" NETWORK_NAME=uah-infra SOURCE_CIDR=172.18.0.0/16 ROUTE_OWNER=beta bash "$ROOT_DIR/scripts/beta/network/rollback_desktop_ollama_temp_route.sh"
      fi
      ;;
    check-route)
      BACKEND_CONTAINER="$DEBUG_BACKEND_CONTAINER" bash "$ROOT_DIR/scripts/beta/network/check_desktop_ollama_temp_route.sh"
      ;;
    apply-bridge)
      if [[ "$env_name" != "beta" ]]; then
        echo "apply-bridge is beta-only." >&2
        exit 1
      fi
      beta_bridge=$(docker network inspect uah-beta-infra --format '{{.Id}}' | cut -c1-12)
      infra_bridge=$(docker network inspect uah-infra --format '{{.Id}}' | cut -c1-12)
      beta_br="br-${beta_bridge}"
      infra_br="br-${infra_bridge}"
      sudo iptables -C DOCKER-USER -i "$beta_br" -o "$infra_br" -j ACCEPT 2>/dev/null || sudo iptables -I DOCKER-USER -i "$beta_br" -o "$infra_br" -j ACCEPT
      sudo iptables -C DOCKER-USER -i "$infra_br" -o "$beta_br" -j ACCEPT 2>/dev/null || sudo iptables -I DOCKER-USER -i "$infra_br" -o "$beta_br" -j ACCEPT
      debug_print_ok "Cross-bridge rules applied: $beta_br <-> $infra_br"
      ;;
    remove-bridge)
      if [[ "$env_name" != "beta" ]]; then
        echo "remove-bridge is beta-only." >&2
        exit 1
      fi
      beta_bridge=$(docker network inspect uah-beta-infra --format '{{.Id}}' 2>/dev/null | cut -c1-12)
      infra_bridge=$(docker network inspect uah-infra --format '{{.Id}}' 2>/dev/null | cut -c1-12)
      if [[ -n "$beta_bridge" && -n "$infra_bridge" ]]; then
        sudo iptables -D DOCKER-USER -i "br-${beta_bridge}" -o "br-${infra_bridge}" -j ACCEPT 2>/dev/null || true
        sudo iptables -D DOCKER-USER -i "br-${infra_bridge}" -o "br-${beta_bridge}" -j ACCEPT 2>/dev/null || true
      fi
      debug_print_ok "Cross-bridge rules removed"
      ;;
    full-reapply)
      if [[ "$env_name" != "beta" ]]; then
        echo "full-reapply is beta-only." >&2
        exit 1
      fi
      debug_network "$env_name" apply-route
      echo ""
      debug_network "$env_name" apply-bridge
      ;;
    rollback-all)
      if [[ "$env_name" != "beta" ]]; then
        echo "rollback-all is beta-only." >&2
        exit 1
      fi
      debug_network "$env_name" rollback-route
      echo ""
      debug_network "$env_name" remove-bridge
      ;;
    *)
      echo "Unknown network action '$action'." >&2
      echo "Supported: show-topology, show-routes, show-docker-user, show-vpn-iptables, apply-route, rollback-route, check-route"
      echo "Beta-only: apply-bridge, remove-bridge, full-reapply, rollback-all"
      exit 1
      ;;
  esac
}

script_doctor_has_strict_mode() {
  local file_path="$1"
  grep -Eq '^[[:space:]]*set -euo pipefail|^[[:space:]]*set -eu' "$file_path"
}

script_doctor_has_shebang() {
  local file_path="$1"
  local first_line=""
  first_line="$(head -n 1 "$file_path" 2>/dev/null || true)"
  [[ "$first_line" == '#!'* ]]
}

script_doctor_has_crlf() {
  local file_path="$1"
  grep -q $'\r' "$file_path"
}

script_doctor_normalize_lf() {
  local file_path="$1"
  sed -i 's/\r$//' "$file_path"
}

debug_scripts() {
  local env_name="$1"
  local action="${2:-audit}"
  local file_path
  local rel_path
  local parse_ok
  local strict_ok
  local shebang_ok
  local crlf_flag
  local changed_count=0
  local total=0
  local parse_fail=0
  local strict_missing=0
  local shebang_missing=0
  local crlf_count=0
  local -a script_files=()

  case "$action" in
    audit|scan|check|fix)
      ;;
    *)
      echo "Unknown scripts action '$action'." >&2
      echo "Supported: audit, fix" >&2
      exit 1
      ;;
  esac

  mapfile -t script_files < <(find "$ROOT_DIR/scripts" -type f -name "*.sh" | sort)

  debug_header "$env_name" "Scripts :: ${action^^}"
  debug_print_section "Script Doctor"

  if [[ ${#script_files[@]} -eq 0 ]]; then
    debug_print_warn "No shell scripts found under scripts/."
    return 0
  fi

  printf "  %-52s %-6s %-6s %-8s %-6s\n" "Script" "Parse" "Strict" "Shebang" "CRLF"
  printf "  %-52s %-6s %-6s %-8s %-6s\n" "----------------------------------------------------" "-----" "------" "-------" "----"

  for file_path in "${script_files[@]}"; do
    rel_path="${file_path#$ROOT_DIR/}"
    total=$((total + 1))

    if bash -n "$file_path" >/dev/null 2>&1; then
      parse_ok="ok"
    else
      parse_ok="fail"
      parse_fail=$((parse_fail + 1))
    fi

    if script_doctor_has_strict_mode "$file_path"; then
      strict_ok="ok"
    else
      strict_ok="miss"
      strict_missing=$((strict_missing + 1))
    fi

    if script_doctor_has_shebang "$file_path"; then
      shebang_ok="ok"
    else
      shebang_ok="miss"
      shebang_missing=$((shebang_missing + 1))
    fi

    if script_doctor_has_crlf "$file_path"; then
      crlf_flag="yes"
      crlf_count=$((crlf_count + 1))
      if [[ "$action" == "fix" ]]; then
        script_doctor_normalize_lf "$file_path"
        changed_count=$((changed_count + 1))
      fi
    else
      crlf_flag="no"
    fi

    printf "  %-52s %-6s %-6s %-8s %-6s\n" "$rel_path" "$parse_ok" "$strict_ok" "$shebang_ok" "$crlf_flag"
  done

  echo ""
  debug_print_section "Summary"
  startup_status_chip "ok" "Scripts scanned: $total"

  if ((parse_fail > 0)); then
    startup_status_chip "error" "Parse failures: $parse_fail"
  else
    startup_status_chip "ok" "Parse failures: 0"
  fi

  if ((strict_missing > 0)); then
    startup_status_chip "warn" "Missing strict mode: $strict_missing"
  else
    startup_status_chip "ok" "Missing strict mode: 0"
  fi

  if ((shebang_missing > 0)); then
    startup_status_chip "warn" "Missing shebang: $shebang_missing"
  else
    startup_status_chip "ok" "Missing shebang: 0"
  fi

  if ((crlf_count > 0)); then
    if [[ "$action" == "fix" ]]; then
      startup_status_chip "ok" "CRLF normalized: $changed_count file(s)"
    else
      startup_status_chip "warn" "CRLF files: $crlf_count"
    fi
  else
    startup_status_chip "ok" "CRLF files: 0"
  fi
}

debug_extension() {
  local env_name="$1"
  local action="${2:-status}"
  local extension_dir="$ROOT_DIR/uah-browser-extension"
  local landing_downloads_dir="$ROOT_DIR/landing/public/downloads"
  local zip_target
  local note_file
  local legacy_note_file
  local timestamp_utc
  local timestamp_iso
  local commit_sha
  local source_count
  local source_count_trimmed
  local used_builder_label="host npm"
  local extension_env_file
  local extension_env_example
  local default_app_origin
  local default_api_origin
  local default_auth_namespace
  local public_note_file

  extension_env_file="$extension_dir/.env"
  extension_env_example="$extension_dir/.env.example"
  public_note_file="$ROOT_DIR/landing/public/downloads/uah-browser-extension-alpha.last-repacked.txt"

  case "$env_name" in
    dev)
      default_app_origin="https://dev.uahapp.com"
      default_api_origin="https://dev.uahapp.com"
      default_auth_namespace="dev"
      ;;
    beta)
      default_app_origin="https://beta.uahapp.com"
      default_api_origin="https://beta.uahapp.com"
      default_auth_namespace="beta"
      ;;
    *)
      default_app_origin="https://uahapp.com"
      default_api_origin="https://uahapp.com"
      default_auth_namespace="prod"
      ;;
  esac

  zip_target="$(extension_zip_target_file)"
  note_file="$(extension_zip_note_file)"
  legacy_note_file="$ROOT_DIR/landing/public/downloads/uah-browser-extension-alpha.last-repacked.txt"

  case "$action" in
    repack|repack-zip|refresh-zip)
      debug_header "$env_name" "Extension ZIP Repack"
      debug_print_section "Target"
      echo "  Extension source: $extension_dir"
      echo "  Landing zip path: $zip_target"
      echo ""

      if [[ ! -d "$extension_dir" ]]; then
        debug_print_error "Missing extension directory: $extension_dir"
        exit 1
      fi
      if [[ ! -d "$ROOT_DIR/landing" ]]; then
        debug_print_error "Missing landing directory: $ROOT_DIR/landing"
        exit 1
      fi
      if [[ ! -f "$extension_env_file" ]]; then
        debug_print_warn "Missing $extension_env_file. Creating one for extension build."
        if [[ -f "$extension_env_example" ]]; then
          cp "$extension_env_example" "$extension_env_file"
        else
          cat > "$extension_env_file" <<'EOF'
VITE_EXTENSION_APP_ORIGIN=
VITE_EXTENSION_API_ORIGIN=
VITE_EXTENSION_AUTH_NAMESPACE=
EOF
        fi
      fi

      debug_print_section "Safe target profile"
      echo "  app origin: $default_app_origin"
      echo "  api origin: $default_api_origin"
      echo "  auth namespace: $default_auth_namespace"

      # Enforce safe per-environment extension env and reject risky keys.
      if ! python3 - "$extension_env_file" "$env_name" "$default_app_origin" "$default_api_origin" "$default_auth_namespace" <<'PY'
from pathlib import Path
import re
import sys

env_path = Path(sys.argv[1])
env_name = sys.argv[2]
safe_app_origin = sys.argv[3]
safe_api_origin = sys.argv[4]
safe_auth_namespace = sys.argv[5]
raw = env_path.read_text(encoding="utf-8")
lines = raw.splitlines()
required = {
    "VITE_EXTENSION_APP_ORIGIN": safe_app_origin,
    "VITE_EXTENSION_API_ORIGIN": safe_api_origin,
    "VITE_EXTENSION_AUTH_NAMESPACE": safe_auth_namespace,
}
allowed_vite = set(required.keys()) | {"VITE_EXTENSION_AUTH_COOKIE_NAME"}
forbidden_fragments = (
    "API_KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PRIVATE_KEY",
    "ACCESS_KEY",
    "OPENAI",
    "ANTHROPIC",
    "GEMINI",
    "AWS_",
    "CLOUDFLARE_",
)

present = {}
kv = {}
for idx, line in enumerate(lines):
    m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$", line)
    if not m:
        continue
    key = m.group(1)
    present[key] = idx
    value = m.group(2).strip().strip('"').strip("'")
    kv[key] = value

violations = []
for key, value in kv.items():
    key_upper = key.upper()
    if key.startswith("VITE_") and key not in allowed_vite:
        violations.append(f"Unexpected VITE key in extension env: {key}")
    if value and any(fragment in key_upper for fragment in forbidden_fragments):
        violations.append(f"Potential secret-like key is not allowed in extension env: {key}")

if violations:
    print("Unsafe extension env detected; refusing repack:", file=sys.stderr)
    for item in violations:
        print(f"- {item}", file=sys.stderr)
    raise SystemExit(1)

for key, default in required.items():
    if key in present:
        # Always force safe profile values during repack.
        lines[present[key]] = f"{key}={default}"
    else:
        lines.append(f"{key}={default}")

# Optional cookie override can remain if present and non-empty.
if "VITE_EXTENSION_AUTH_COOKIE_NAME" in present:
    idx = present["VITE_EXTENSION_AUTH_COOKIE_NAME"]
    current_value = lines[idx].split("=", 1)[1].strip().strip('"').strip("'")
    if not current_value:
        lines[idx] = f"VITE_EXTENSION_AUTH_COOKIE_NAME=uah_auth_{safe_auth_namespace}"

# Safety guard: enforce approved live hosts for each environment profile.
allowed_hosts = {
    "dev": {"https://dev.uahapp.com"},
    "beta": {"https://beta.uahapp.com"},
    "prod": {"https://uahapp.com", "https://www.uahapp.com"},
}.get(env_name, {"https://uahapp.com"})

if required["VITE_EXTENSION_APP_ORIGIN"] not in allowed_hosts or required["VITE_EXTENSION_API_ORIGIN"] not in allowed_hosts:
    raise SystemExit("Configured extension origins are not allowed for this environment profile.")

env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
PY
      then
        debug_print_error "Unsafe extension .env detected. Repack aborted."
        exit 1
      fi
      if ! command -v python3 >/dev/null 2>&1; then
        debug_print_error "python3 is required for zip packaging but was not found in PATH."
        exit 1
      fi

      mkdir -p "$landing_downloads_dir"
      mkdir -p "$(dirname "$note_file")"
      mkdir -p "$(dirname "$public_note_file")"
      rm -f "$legacy_note_file"

      debug_print_section "Build extension"
      if command -v npm >/dev/null 2>&1; then
        if ! (
          cd "$extension_dir"
          npm run build
        ); then
          debug_print_error "Extension build failed with host npm. Zip was not updated."
          exit 1
        fi
      else
        used_builder_label="docker node"
        debug_print_warn "Host npm not found. Falling back to Dockerized Node build."
        if ! command -v docker >/dev/null 2>&1; then
          debug_print_error "docker is not available, and host npm is missing."
          debug_print_warn "Install npm or docker on this host before running repack."
          exit 1
        fi
        if ! docker run --rm \
          --user "$(id -u):$(id -g)" \
          -e HOME=/tmp \
          -e npm_config_cache=/tmp/.npm \
          -v "$ROOT_DIR:/repo" \
          -w /repo/uah-browser-extension \
          node:22-bookworm \
          bash -lc "set -euo pipefail; npm ci --include=optional || npm ci; if ! node -e \"require('@rollup/rollup-linux-x64-gnu')\" >/dev/null 2>&1; then npm install --no-save --include=optional @rollup/rollup-linux-x64-gnu; fi; npm run build"; then
          debug_print_error "Dockerized extension build failed. Zip was not updated."
          exit 1
        fi
      fi
      if [[ ! -f "$extension_dir/dist/manifest.json" ]]; then
        debug_print_error "Build did not produce dist/manifest.json. Zip was not updated."
        exit 1
      fi
      echo ""

      debug_print_section "Repack zip"
      if ! python3 - "$extension_dir/dist" "$zip_target" <<'PY'
import pathlib
import sys
import zipfile

dist_dir = pathlib.Path(sys.argv[1])
zip_path = pathlib.Path(sys.argv[2])
if not dist_dir.exists():
    raise SystemExit(f"dist directory missing: {dist_dir}")

files = [p for p in dist_dir.rglob("*") if p.is_file()]
if not files:
    raise SystemExit(f"no files found under: {dist_dir}")

zip_path.parent.mkdir(parents=True, exist_ok=True)
if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for file_path in files:
        zf.write(file_path, file_path.relative_to(dist_dir).as_posix())
PY
      then
        debug_print_error "Zip repack failed. Existing artifact was left unchanged."
        exit 1
      fi

      source_count="$(python3 - "$extension_dir/dist" <<'PY'
import pathlib, sys
dist_dir = pathlib.Path(sys.argv[1])
print(sum(1 for p in dist_dir.rglob("*") if p.is_file()))
PY
)"
      source_count_trimmed="$(printf '%s' "$source_count" | tr -d '[:space:]')"
      if [[ -z "$source_count_trimmed" || ! "$source_count_trimmed" =~ ^[0-9]+$ || "$source_count_trimmed" == "0" ]]; then
        debug_print_error "Source file count was invalid ($source_count). Refusing to mark repack successful."
        exit 1
      fi

      timestamp_utc="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
      timestamp_iso="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
      commit_sha="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"

      cat > "$note_file" <<EOF
last repacked: $timestamp_utc
iso: $timestamp_iso
commit: $commit_sha
artifact: /downloads/uah-browser-extension-alpha.zip
source_files: $source_count_trimmed
EOF
      cp "$note_file" "$public_note_file"

      debug_print_ok "Extension zip refreshed."
      echo "  build path: $used_builder_label"
      echo "  -> $zip_target"
      echo "  metadata: $public_note_file"
      echo ""
      debug_print_section "Last repacked note"
      sed 's/^/  /' "$note_file"
      ;;
    status|show|note)
      debug_header "$env_name" "Extension ZIP Repack Status"
      debug_print_section "Artifact"
      echo "  zip: $zip_target"
      echo "  note: $note_file"
      echo ""
      if [[ -f "$note_file" ]]; then
        debug_print_ok "Found last repacked note."
        sed 's/^/  /' "$note_file"
      elif [[ -f "$legacy_note_file" ]]; then
        debug_print_warn "Found legacy note path; it no longer blocks sync and can be removed."
        echo "  legacy note: $legacy_note_file"
      else
        debug_print_warn "No repack note found yet."
      fi
      ;;
    *)
      echo "Unknown extension action '$action'." >&2
      echo "Supported: repack, status" >&2
      exit 1
      ;;
  esac
}

print_debug_usage() {
  cat <<'EOF'
Debug subcommands:
  bash scripts/uah.sh <env> debug
  bash scripts/uah.sh <env> debug status
  bash scripts/uah.sh <env> debug connectivity [full|ollama|redis|db|vpn-ping|host-ollama|containers|env|wireguard|cert]
  bash scripts/uah.sh <env> debug logs [backend|frontend|landing|cloudflared|redis|db] [--tail N] [--follow] [--raw|--errors|--filtered]
  bash scripts/uah.sh <env> debug queue [status|clear|clear-redis|clear-stuck|active|recent|failed|retry <id>|test-parse <local|cloud|rules>]
  bash scripts/uah.sh <env> debug database [isolation|user-count|resume-count|parse-stats|recent|raw <SQL>|size]
  bash scripts/uah.sh <env> debug users [list|show <email>|toggle-active <email> <true|false>|toggle-developer <email> <true|false>|reset-password <email> <password>]
  bash scripts/uah.sh <env> debug invites [menu|ui|interactive|list [all|used|unused|active|inactive]|show <code>|create <count> [max_uses] [expires_in_or_iso] [name]|revoke <code>|stats|audit [tail]]
  bash scripts/uah.sh <env> debug network [show-topology|show-routes|show-docker-user|show-vpn-iptables|apply-route|rollback-route|check-route]
  bash scripts/uah.sh <env> debug scripts [audit|fix]
  bash scripts/uah.sh <env> debug extension [repack|status]
  bash scripts/uah.sh beta debug network [apply-bridge|remove-bridge|full-reapply|rollback-all]
EOF
}

run_debug() {
  local env_name="$1"
  local topic="${2:-menu}"
  shift 2 || true

  if [[ "$env_name" == "prod" ]]; then
    prod_scaffold "debug"
  fi

  case "$topic" in
    ""|menu|interactive)
      if [[ "$env_name" == "dev" ]]; then
        bash "$ROOT_DIR/scripts/dev/diagnostic/dev-debug.sh"
      else
        bash "$ROOT_DIR/scripts/beta/diagnostic/beta-debug.sh"
      fi
      ;;
    help|-h|--help)
      print_debug_usage
      ;;
    status)
      debug_show_status "$env_name"
      ;;
    connectivity)
      debug_connectivity "$env_name" "${1:-full}"
      ;;
    logs)
      debug_logs "$env_name" "$@"
      ;;
    queue)
      debug_queue "$env_name" "$@"
      ;;
    database|db)
      debug_database "$env_name" "$@"
      ;;
    users)
      debug_users "$env_name" "$@"
      ;;
    invites|invite)
      debug_invites "$env_name" "$@"
      ;;
    network)
      debug_network "$env_name" "$@"
      ;;
    scripts)
      debug_scripts "$env_name" "${1:-audit}"
      ;;
    extension)
      debug_extension "$env_name" "${1:-status}"
      ;;
    route-check)
      debug_network "$env_name" check-route
      ;;
    reset-password)
      debug_users "$env_name" reset-password "$@"
      ;;
    *)
      echo "Unknown debug topic '$topic'." >&2
      print_debug_usage >&2
      exit 1
      ;;
  esac
}

run_audit() {
  local env_name="$1"
  shift

  if [[ "$env_name" == "dev" ]]; then
    bash "$ROOT_DIR/scripts/dev/diagnostic/dev-security-audit.sh" "$@"
    return
  fi

  if [[ "$env_name" == "beta" ]]; then
    bash "$ROOT_DIR/scripts/beta/diagnostic/beta-security-audit.sh" "$@"
    return
  fi

  bash "$ROOT_DIR/scripts/prod/prod-security-audit.sh" "$@"
}

interactive_reset_iteration_state() {
  ACTION=""
  EXTRA_ARGS=()
  build_mode_reset_selection
}

interactive_post_action_pause() {
  if [[ -t 0 ]]; then
    echo ""
    read -rp "Press Enter to return to Control Center... " _unused
  fi
}

run_selected_action() {
  local env_name="$1"
  local action="$2"
  shift 2
  local -a action_args=("$@")

  notify_discord "**uah.sh started** by \`$(whoami)\` on \`$(hostname)\` for action \`$action\` in \`$env_name\`" 16776960

  if [[ "$env_name" == "prod" && "$action" != "audit" && "$action" != "providers" ]]; then
    prod_scaffold "$action"
    return $?
  fi

  if [[ "$action" == "start" || "$action" == "restart" || "$action" == "sync" ]]; then
    validate_build_services_for_env "$env_name"
  fi

  case "$action" in
    start)
      if ! ensure_env_confirmation "$env_name" "start"; then
        echo "Start cancelled by env safety confirmation."
        return 1
      fi
      if [[ "$env_name" == "dev" ]]; then
        dev_start
      else
        beta_start
      fi
      ;;
    stop)
      if [[ "$env_name" == "dev" ]]; then
        dev_stop
      else
        beta_stop
      fi
      ;;
    restart)
      if ! ensure_env_confirmation "$env_name" "restart"; then
        echo "Restart cancelled by env safety confirmation."
        return 1
      fi
      if [[ "$env_name" == "dev" ]]; then
        dev_restart
      else
        beta_restart
      fi
      ;;
    debug)
      run_debug "$env_name" "${action_args[@]}"
      ;;
    cert-sync)
      if [[ "$env_name" != "dev" ]]; then
        echo "cert-sync is only supported for dev right now." >&2
        return 1
      fi
      sync_dev_cert strict
      ;;
    sync)
      if [[ "$env_name" == "beta" ]]; then
        local beta_sync_mode="${action_args[0]:-safe}"
        local commit_sha

        if ! beta_sync "$beta_sync_mode"; then
          return 1
        fi
        if ! run_sync_rebuild_if_requested beta; then
          notify_discord "**Beta sync FAILED** during post-sync Alembic reconcile" 15158332
          return 1
        fi

        commit_sha="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
        notify_discord "**Beta synced** to commit \`$commit_sha\` (mode: $beta_sync_mode)" 3066993
      elif [[ "$env_name" == "dev" ]]; then
        dev_sync "${action_args[0]:-safe}"
        run_sync_rebuild_if_requested dev
      else
        prod_scaffold "sync"
        return $?
      fi
      ;;
    audit)
      run_audit "$env_name" "${action_args[@]}"
      ;;
    providers)
      run_providers "$env_name" "${action_args[@]}"
      ;;
    tools|tooling|ui)
      echo "The tools / tooling / ui aliases are deprecated. Run the same command with no action to open the Control Center." >&2
      echo "Example: bash scripts/uah.sh ${env_name}" >&2
      return 1
      ;;
    *)
      echo "Unknown action '$action'." >&2
      return 1
      ;;
  esac
}

ENV_NAME=""
ACTION=""
EXTRA_ARGS=()
SHOW_HELP=false
DETECTED_ENV=""
INTERACTIVE_CONTROL_CENTER=false

while (($#)); do
  case "$1" in
    -h|--help)
      if [[ "$ACTION" == "debug" || "$ACTION" == "audit" || "$ACTION" == "providers" ]]; then
        EXTRA_ARGS+=("$1")
      else
        SHOW_HELP=true
      fi
      ;;
    help)
      if [[ -z "$ENV_NAME" && -z "$ACTION" ]]; then
        SHOW_HELP=true
      else
        EXTRA_ARGS+=("$1")
      fi
      ;;
    --no-build)
      FLAG_NO_BUILD=true
      ;;
    --build|--build-all)
      FLAG_BUILD_ALL=true
      ;;
    --build-backend)
      validate_and_add_build_service "backend"
      ;;
    --build-frontend)
      validate_and_add_build_service "frontend"
      ;;
    --build-db)
      validate_and_add_build_service "db"
      ;;
    --build-redis)
      validate_and_add_build_service "redis"
      ;;
    --build-cloudflared)
      validate_and_add_build_service "cloudflared"
      ;;
    --build-landing)
      validate_and_add_build_service "landing"
      ;;
    --build-service)
      shift
      if (($# == 0)); then
        echo "--build-service requires a service name." >&2
        exit 1
      fi
      validate_and_add_build_service "$1"
      ;;
    --build-service=*)
      validate_and_add_build_service "${1#*=}"
      ;;
    --)
      shift
      while (($#)); do
        EXTRA_ARGS+=("$1")
        shift
      done
      break
      ;;
    dev|beta|prod)
      if [[ -z "$ENV_NAME" ]]; then
        ENV_NAME="$1"
      else
        EXTRA_ARGS+=("$1")
      fi
      ;;
    start|stop|restart|debug|sync|cert-sync|audit|providers|tools|tooling|ui)
      if [[ -z "$ACTION" ]]; then
        ACTION="$1"
      else
        EXTRA_ARGS+=("$1")
      fi
      ;;
    -*)
      if [[ "$ACTION" == "debug" || "$ACTION" == "audit" || "$ACTION" == "providers" ]]; then
        EXTRA_ARGS+=("$1")
      else
        echo "Unknown option '$1'. Use --help for usage." >&2
        exit 1
      fi
      ;;
    *)
      EXTRA_ARGS+=("$1")
      ;;
  esac
  shift
done

if [[ "$SHOW_HELP" == true ]]; then
  print_usage
  exit 0
fi

DETECTED_ENV="$(detect_environment_context)"

if [[ -z "$ENV_NAME" ]]; then
  ENV_NAME="$DETECTED_ENV"
  if [[ -z "$ENV_NAME" ]]; then
    echo "Could not auto-detect environment from current path or .env." >&2
    echo "Pass environment explicitly as the first argument: dev|beta|prod" >&2
    exit 1
  fi
  echo "Auto-detected environment: $ENV_NAME"
elif [[ -n "$DETECTED_ENV" && "$DETECTED_ENV" != "$ENV_NAME" ]]; then
  echo "Warning: explicit environment '$ENV_NAME' differs from detected context '$DETECTED_ENV'." >&2
fi

if [[ -z "$ACTION" ]]; then
  if [[ -t 0 ]]; then
    INTERACTIVE_CONTROL_CENTER=true
  else
    echo "Action argument required in non-interactive mode: start|stop|restart|debug|sync|cert-sync|audit|providers" >&2
    exit 1
  fi
fi

if [[ "$INTERACTIVE_CONTROL_CENTER" == true ]]; then
  while true; do
    local_action_status=0
    choose_action "$ENV_NAME"
    resolve_build_mode
    validate_build_mode_for_action "$ACTION"

    if run_selected_action "$ENV_NAME" "$ACTION" "${EXTRA_ARGS[@]}"; then
      local_action_status=0
    else
      local_action_status=$?
      echo ""
      echo "Action '$ACTION' failed with exit code $local_action_status."
    fi

    interactive_reset_iteration_state
    interactive_post_action_pause
  done
else
  resolve_build_mode
  validate_build_mode_for_action "$ACTION"
  if run_selected_action "$ENV_NAME" "$ACTION" "${EXTRA_ARGS[@]}"; then
    :
  else
    action_status=$?
    exit "$action_status"
  fi
fi
