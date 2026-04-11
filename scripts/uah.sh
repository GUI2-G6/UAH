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
      echo "backend frontend db redis cloudflared"
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
        backend|frontend|db|redis|cloudflared)
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
      echo "backend frontend db redis cloudflared"
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

run_sync_rebuild_if_requested() {
  local env_name="$1"

  if [[ "$BUILD_MODE" == "none" ]]; then
    echo "No rebuild requested after sync."
    return
  fi

  if ! ensure_env_confirmation "$env_name" "sync-rebuild"; then
    echo "Sync rebuild cancelled by env safety confirmation."
    return 1
  fi

  echo "Running post-sync compose update ($(build_mode_label))..."
  preflight_startup "$env_name"
  run_compose_up_with_build_mode "$env_name"
}

prepare_sync_branch() {
  git -C "$ROOT_DIR" fetch origin
  git -C "$ROOT_DIR" checkout dev
}

refresh_sync_blocker_snapshot() {
  local ahead_count
  local behind_count

  SYNC_BLOCKER_STATUS="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=all || true)"

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

  if [[ -n "$SYNC_BLOCKER_STATUS" ]]; then
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

  if [[ -n "$SYNC_BLOCKER_STATUS" ]]; then
    total_lines=$(printf '%s\n' "$SYNC_BLOCKER_STATUS" | sed '/^$/d' | wc -l | tr -d ' ')
    echo "Local changes ($total_lines):"
    printf '%s\n' "$SYNC_BLOCKER_STATUS" | sed -n "1,${preview_limit}p" | sed 's/^/  /'
    if ((total_lines > preview_limit)); then
      echo "  ... and $((total_lines - preview_limit)) more"
    fi
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

  backend_container="$(startup_backend_container_name "$env_name")"
  network_name="$(startup_network_name "$env_name")"

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

choose_action() {
  local active_env="$1"
  local choice
  local selected_env

  if [[ ! -t 0 ]]; then
    echo "Action argument required in non-interactive mode: start|stop|restart|debug|sync|cert-sync|audit" >&2
    exit 1
  fi

  while true; do
    startup_header "$active_env"
    startup_quick_hud "$active_env"
    echo ""
    echo "  Actions"
    echo "    1) start"
    echo "    2) stop"
    echo "    3) restart"
    echo "    4) debug"
    echo "    5) sync"
    echo "    6) cert-sync"
    echo "    7) audit"
    echo "    8) review env values"
    echo "    9) switch environment"
    echo "   10) rebuild options"
    echo "    0) exit"
    read -rp "  Choice [1-10/0]: " choice

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
        build_mode_reset_selection
        ACTION="debug"
        ENV_NAME="$active_env"
        return
        ;;
      5)
        if ! configure_rebuild_ui_for_action "$active_env" "sync"; then
          continue
        fi
        ACTION="sync"
        ENV_NAME="$active_env"
        return
        ;;
      6)
        build_mode_reset_selection
        ACTION="cert-sync"
        ENV_NAME="$active_env"
        return
        ;;
      7)
        build_mode_reset_selection
        ACTION="audit"
        ENV_NAME="$active_env"
        return
        ;;
      8)
        ensure_env_confirmation "$active_env" "preflight review" "preview" || true
        ;;
      9)
        selected_env="$(choose_environment_interactive "$active_env")"
        active_env="$selected_env"
        ;;
      10)
        configure_rebuild_ui_for_action "$active_env" "menu" || true
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
  start | stop | restart | debug | sync | cert-sync | audit

Debug:
  bash scripts/uah.sh <env> debug
  bash scripts/uah.sh <env> debug help
  bash scripts/uah.sh <env> debug status
  bash scripts/uah.sh <env> debug connectivity [full|ollama|redis|db|vpn-ping|host-ollama|containers|env|wireguard|cert]
  bash scripts/uah.sh <env> debug logs [backend|frontend|cloudflared|redis|db] [--tail N] [--follow] [--raw|--errors|--filtered]
  bash scripts/uah.sh <env> debug queue [status|clear|clear-redis|clear-stuck|active|recent|failed|retry <id>|test-parse <local|cloud|rules>]
  bash scripts/uah.sh <env> debug database [isolation|user-count|resume-count|parse-stats|recent|raw <SQL>|size]
  bash scripts/uah.sh dev debug users [list|show <username>|toggle-active <username> <true|false>|toggle-developer <username> <true|false>|reset-password <username> <password>]
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
  bash scripts/uah.sh dev debug users reset-password testuser NewPass123
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

  echo "[1/6] Running preflight checks..."
  preflight_startup dev

  echo "[2/6] Applying WireGuard host route..."
  VPN_CONTAINER=uah-dev-vpn \
  BACKEND_CONTAINER=uah-dev-backend \
  NETWORK_NAME=uah-infra \
  ROUTE_OWNER=dev \
  bash "$ROOT_DIR/scripts/dev/network/apply_desktop_ollama_temp_route.sh"

  echo "[3/6] Starting containers ($(build_mode_label))..."
  run_compose_up_with_build_mode dev

  echo "[4/6] Waiting for backend to be ready..."
  if ! wait_for_dev_backend_ready; then
    echo "Backend readiness check failed after retries." >&2
    echo "Run: bash scripts/uah.sh dev debug logs backend --tail 120 --errors" >&2
    echo ""
    run_compose dev ps || true
    return 1
  fi

  echo "[5/6] Syncing cert to frontend..."
  if ! sync_dev_cert optional; then
    echo "Cert sync warning: unable to sync certs now."
    echo "You can retry later with: bash scripts/uah.sh dev cert-sync"
  fi

  echo "[6/6] Connectivity check..."
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

  if [[ ! -f "$ROOT_DIR/docker-compose.yml" || ! -f "$ROOT_DIR/docker-compose.beta.yml" ]]; then
    echo "Missing required compose files at repo root." >&2
    exit 1
  fi

  echo "=== UAH Beta Start ==="

  echo "[1/6] Running preflight checks..."
  preflight_startup beta

  echo "[2/6] Starting containers ($(build_mode_label))..."
  run_compose_up_with_build_mode beta

  echo "[3/6] Waiting for backend to be ready..."
  sleep 12

  echo "[4/6] Applying WireGuard host route..."
  VPN_CONTAINER=uah-dev-vpn \
  BACKEND_CONTAINER=uah-beta-backend \
  NETWORK_NAME=uah-infra \
  SOURCE_CIDR=172.18.0.0/16 \
  ROUTE_OWNER=beta \
  bash "$ROOT_DIR/scripts/beta/network/apply_desktop_ollama_temp_route.sh"

  echo "[5/6] Allowing cross-bridge Docker traffic..."
  local beta_bridge
  local infra_bridge
  local beta_br
  local infra_br

  beta_bridge=$(docker network inspect uah-beta-infra --format '{{.Id}}' | cut -c1-12)
  infra_bridge=$(docker network inspect uah-infra --format '{{.Id}}' | cut -c1-12)
  beta_br="br-${beta_bridge}"
  infra_br="br-${infra_bridge}"

  sudo iptables -C DOCKER-USER -i "$beta_br" -o "$infra_br" -j ACCEPT 2>/dev/null || \
    sudo iptables -I DOCKER-USER -i "$beta_br" -o "$infra_br" -j ACCEPT

  sudo iptables -C DOCKER-USER -i "$infra_br" -o "$beta_br" -j ACCEPT 2>/dev/null || \
    sudo iptables -I DOCKER-USER -i "$infra_br" -o "$beta_br" -j ACCEPT

  echo "[6/6] Connectivity check..."
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
  local commit_sha

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

  commit_sha="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  notify_discord "**Beta synced** to commit \`$commit_sha\` (mode: $mode)" 3066993
}

sql_escape_literal() {
  local value="$1"
  value="${value//\'/\'\'}"
  printf '%s' "$value"
}

debug_show_status() {
  local env_name="$1"
  local ollama_ok=0

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
      backend|frontend|cloudflared|redis|db)
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
  local username="${3:-}"
  local arg="${4:-}"
  local escaped_username

  if [[ "$env_name" != "dev" ]]; then
    echo "User admin operations are only supported for dev." >&2
    exit 1
  fi

  debug_profile_init "$env_name"
  debug_header "$env_name" "Users :: $action"

  case "$action" in
    list)
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT id, username, email, first_name, is_active, is_admin, is_developer, created_at FROM users ORDER BY id;" 2>&1 | sed 's/^/  /'
      ;;
    show)
      if [[ -z "$username" ]]; then
        echo "Usage: bash scripts/uah.sh dev debug users show <username>" >&2
        exit 1
      fi
      escaped_username="$(sql_escape_literal "$username")"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT id, username, email, first_name, last_name, is_active, is_admin, is_developer, email_verified, created_at, updated_at FROM users WHERE username='${escaped_username}';" 2>&1 | sed 's/^/  /'
      ;;
    toggle-active)
      if [[ -z "$username" || -z "$arg" ]]; then
        echo "Usage: bash scripts/uah.sh dev debug users toggle-active <username> <true|false>" >&2
        exit 1
      fi
      if [[ "$arg" != "true" && "$arg" != "false" ]]; then
        echo "toggle-active requires true or false." >&2
        exit 1
      fi
      escaped_username="$(sql_escape_literal "$username")"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "UPDATE users SET is_active=$arg WHERE username='${escaped_username}' RETURNING username, is_active;" 2>&1 | sed 's/^/  /'
      ;;
    toggle-developer)
      if [[ -z "$username" || -z "$arg" ]]; then
        echo "Usage: bash scripts/uah.sh dev debug users toggle-developer <username> <true|false>" >&2
        exit 1
      fi
      if [[ "$arg" != "true" && "$arg" != "false" ]]; then
        echo "toggle-developer requires true or false." >&2
        exit 1
      fi
      escaped_username="$(sql_escape_literal "$username")"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "UPDATE users SET is_developer=$arg WHERE username='${escaped_username}' RETURNING username, is_developer;" 2>&1 | sed 's/^/  /'
      ;;
    reset-password)
      if [[ -z "$username" || -z "$arg" ]]; then
        echo "Usage: bash scripts/uah.sh dev debug users reset-password <username> <password>" >&2
        exit 1
      fi
      bash "$ROOT_DIR/scripts/dev/diagnostic/reset-user-password.sh" "$username" "$arg"
      ;;
    *)
      echo "Unknown users action '$action'." >&2
      echo "Supported: list, show <username>, toggle-active <username> <true|false>, toggle-developer <username> <true|false>, reset-password <username> <password>" >&2
      exit 1
      ;;
  esac
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

print_debug_usage() {
  cat <<'EOF'
Debug subcommands:
  bash scripts/uah.sh <env> debug
  bash scripts/uah.sh <env> debug status
  bash scripts/uah.sh <env> debug connectivity [full|ollama|redis|db|vpn-ping|host-ollama|containers|env|wireguard|cert]
  bash scripts/uah.sh <env> debug logs [backend|frontend|cloudflared|redis|db] [--tail N] [--follow] [--raw|--errors|--filtered]
  bash scripts/uah.sh <env> debug queue [status|clear|clear-redis|clear-stuck|active|recent|failed|retry <id>|test-parse <local|cloud|rules>]
  bash scripts/uah.sh <env> debug database [isolation|user-count|resume-count|parse-stats|recent|raw <SQL>|size]
  bash scripts/uah.sh dev debug users [list|show <username>|toggle-active <username> <true|false>|toggle-developer <username> <true|false>|reset-password <username> <password>]
  bash scripts/uah.sh <env> debug network [show-topology|show-routes|show-docker-user|show-vpn-iptables|apply-route|rollback-route|check-route]
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
    network)
      debug_network "$env_name" "$@"
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

  if [[ "$env_name" == "prod" && "$action" != "audit" ]]; then
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
        beta_sync "${action_args[0]:-safe}"
        run_sync_rebuild_if_requested beta
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
      if [[ "$ACTION" == "debug" || "$ACTION" == "audit" ]]; then
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
    start|stop|restart|debug|sync|cert-sync|audit)
      if [[ -z "$ACTION" ]]; then
        ACTION="$1"
      else
        EXTRA_ARGS+=("$1")
      fi
      ;;
    -*)
      if [[ "$ACTION" == "debug" || "$ACTION" == "audit" ]]; then
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
    echo "Action argument required in non-interactive mode: start|stop|restart|debug|sync|cert-sync|audit" >&2
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
