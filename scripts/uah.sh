#!/usr/bin/env bash
set -euo pipefail

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
    echo "$pwd_env"
    return
  fi

  if [[ "$ROOT_DIR" =~ /environments/(dev|beta|prod)(/|$) ]]; then
    root_env="${BASH_REMATCH[1]}"
    echo "$root_env"
    return
  fi

  env_var="$(normalize_environment_label "$(get_env_value_or_default ENVIRONMENT "")")"
  if [[ -n "$env_var" ]]; then
    echo "$env_var"
    return
  fi

  env_var="$(normalize_environment_label "$(get_env_value_or_default ENV "")")"
  if [[ -n "$env_var" ]]; then
    echo "$env_var"
    return
  fi

  compose_project="$(get_env_value_or_default COMPOSE_PROJECT_NAME "")"
  compose_project="${compose_project,,}"
  if [[ "$compose_project" == *"beta"* ]]; then
    echo "beta"
    return
  fi
  if [[ "$compose_project" == *"prod"* ]]; then
    echo "prod"
    return
  fi
  if [[ "$compose_project" == *"dev"* || "$compose_project" == *"local"* ]]; then
    echo "dev"
    return
  fi

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
  bash scripts/uah.sh dev debug users [list|show <username>|toggle-active <username> <true|false>|reset-password <username> <password>]
  bash scripts/uah.sh <env> debug network [show-topology|show-routes|show-docker-user|show-vpn-iptables|apply-route|rollback-route|check-route]
  bash scripts/uah.sh beta debug network [apply-bridge|remove-bridge|full-reapply|rollback-all]

Build options (for start, restart, sync only):
  --no-build
  --build | --build-all
  --build-frontend
  --build-backend
  --build-db
  --build-redis
  --build-cloudflared
  --build-service <name>
  --build-service=<name>

Sync mode:
  dev sync [safe|hard]
  beta sync [safe|hard]

Audit options:
  --env-file <path>
  --mode <full|repo|docker|host>
  --fix
  --fail-on-warn
  --json [path]

Safe sync behavior:
  Detects local blockers before pull (dirty files, local commits, diverged state).
  In interactive mode, you'll be prompted to abort or force hard sync.

Examples:
  bash scripts/uah.sh dev start
  bash scripts/uah.sh dev restart --build-frontend --build-backend
  bash scripts/uah.sh beta restart --build-all
  bash scripts/uah.sh dev sync hard
  bash scripts/uah.sh dev sync --build-all
  bash scripts/uah.sh beta sync safe --build-frontend
  bash scripts/uah.sh dev debug status
  bash scripts/uah.sh dev debug users reset-password testuser NewPass123
EOF
}

choose_action() {
  if [[ ! -t 0 ]]; then
    echo "Action argument required in non-interactive mode: start|stop|restart|debug|sync|cert-sync|audit" >&2
    exit 1
  fi

  echo "Select action:" >&2
  echo "  1) start" >&2
  echo "  2) stop" >&2
  echo "  3) restart" >&2
  echo "  4) debug" >&2
  echo "  5) sync" >&2
  echo "  6) cert-sync" >&2
  echo "  7) audit" >&2
  read -rp "Choice [1-7]: " choice
  case "$choice" in
    1) echo "start" ;;
    2) echo "stop" ;;
    3) echo "restart" ;;
    4) echo "debug" ;;
    5) echo "sync" ;;
    6) echo "cert-sync" ;;
    7) echo "audit" ;;
    *)
      echo "Invalid action selection." >&2
      exit 1
      ;;
  esac
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
  exit 2
}

sync_dev_cert() {
  bash "$ROOT_DIR/scripts/dev/certbot-sync-dev-cert.sh"
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
  sleep 12

  echo "[5/6] Syncing cert to frontend..."
  if ! sync_dev_cert; then
    echo "Cert sync skipped."
  fi

  echo "[6/6] Connectivity check..."
  docker exec uah-dev-backend python3 -c "
import httpx
try:
    r = httpx.get('http://localhost:8000/api/', timeout=5)
    print('BACKEND: OK -', r.status_code)
except Exception as e:
    print('BACKEND: FAILED -', type(e).__name__, str(e))
" 2>/dev/null || true

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
  dev_start
}

beta_start() {
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
  docker exec uah-beta-backend python3 -c "
import httpx
try:
    r = httpx.get('http://10.8.0.8:11434/api/tags', timeout=8)
    models = [m['name'] for m in r.json().get('models', [])]
    print('LOCAL OLLAMA: OK -', models)
except Exception as e:
    print('LOCAL OLLAMA: FAILED -', type(e).__name__, str(e))
" || true

  echo ""
  run_compose beta ps
  echo ""
  echo "=== Beta stack started ==="
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
  local mode="${1:-}"

  if [[ -z "$mode" ]]; then
    if [[ ! -t 0 ]]; then
      echo "Provide sync mode in non-interactive mode: safe|hard" >&2
      exit 1
    fi

    echo "Choose beta sync mode:"
    echo "  1) safe  - checkout dev and pull --ff-only"
    echo "  2) hard  - checkout dev and reset --hard origin/dev"
    echo "  0) cancel"
    read -rp "Choice [1-2/0]: " selection

    case "$selection" in
      1) mode="safe" ;;
      2) mode="hard" ;;
      0)
        echo "Sync cancelled."
        return
        ;;
      *)
        echo "Invalid sync mode selection." >&2
        exit 1
        ;;
    esac
  fi

  case "$mode" in
    safe|ff|fast-forward)
      run_safe_sync_flow beta
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
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT id, username, email, first_name, is_active, created_at FROM users ORDER BY id;" 2>&1 | sed 's/^/  /'
      ;;
    show)
      if [[ -z "$username" ]]; then
        echo "Usage: bash scripts/uah.sh dev debug users show <username>" >&2
        exit 1
      fi
      escaped_username="$(sql_escape_literal "$username")"
      docker exec "$DEBUG_DB_CONTAINER" psql -U uah -d "$DEBUG_DB_NAME" -c "SELECT id, username, email, first_name, last_name, is_active, email_verified, created_at, updated_at FROM users WHERE username='${escaped_username}';" 2>&1 | sed 's/^/  /'
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
    reset-password)
      if [[ -z "$username" || -z "$arg" ]]; then
        echo "Usage: bash scripts/uah.sh dev debug users reset-password <username> <password>" >&2
        exit 1
      fi
      bash "$ROOT_DIR/scripts/dev/diagnostic/reset-user-password.sh" "$username" "$arg"
      ;;
    *)
      echo "Unknown users action '$action'." >&2
      echo "Supported: list, show <username>, toggle-active <username> <true|false>, reset-password <username> <password>" >&2
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
  bash scripts/uah.sh dev debug users [list|show <username>|toggle-active <username> <true|false>|reset-password <username> <password>]
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

ENV_NAME=""
ACTION=""
EXTRA_ARGS=()
SHOW_HELP=false
DETECTED_ENV=""

while (($#)); do
  case "$1" in
    -h|--help)
      SHOW_HELP=true
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
      echo "Unknown option '$1'. Use --help for usage." >&2
      exit 1
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
  ACTION="$(choose_action)"
fi

resolve_build_mode
validate_build_mode_for_action "$ACTION"

if [[ "$ENV_NAME" == "prod" && "$ACTION" != "audit" ]]; then
  prod_scaffold "$ACTION"
fi

case "$ACTION" in
  start)
    if [[ "$ENV_NAME" == "dev" ]]; then
      dev_start
    else
      beta_start
    fi
    ;;
  stop)
    if [[ "$ENV_NAME" == "dev" ]]; then
      dev_stop
    else
      beta_stop
    fi
    ;;
  restart)
    if [[ "$ENV_NAME" == "dev" ]]; then
      dev_restart
    else
      beta_restart
    fi
    ;;
  debug)
    run_debug "$ENV_NAME" "${EXTRA_ARGS[@]}"
    ;;
  cert-sync)
    if [[ "$ENV_NAME" != "dev" ]]; then
      echo "cert-sync is only supported for dev right now." >&2
      exit 1
    fi
    sync_dev_cert
    ;;
  sync)
    if [[ "$ENV_NAME" == "beta" ]]; then
      beta_sync "${EXTRA_ARGS[0]:-}"
      run_sync_rebuild_if_requested beta
    elif [[ "$ENV_NAME" == "dev" ]]; then
      dev_sync "${EXTRA_ARGS[0]:-safe}"
      run_sync_rebuild_if_requested dev
    else
      prod_scaffold "sync"
    fi
    ;;
  audit)
    run_audit "$ENV_NAME" "${EXTRA_ARGS[@]}"
    ;;
  *)
    echo "Unknown action '$ACTION'." >&2
    exit 1
    ;;
esac
