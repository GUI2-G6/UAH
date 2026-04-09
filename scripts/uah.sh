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
  bash scripts/uah.sh <environment> <action> [options]
  bash scripts/uah.sh --help

Environments:
  dev | beta | prod

Actions:
  start | stop | restart | debug | sync | cert-sync | audit

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
EOF
}

choose_environment() {
  if [[ ! -t 0 ]]; then
    echo "Environment argument required in non-interactive mode: dev|beta|prod" >&2
    exit 1
  fi

  echo "Select environment:" >&2
  echo "  1) dev" >&2
  echo "  2) beta" >&2
  echo "  3) prod" >&2
  read -rp "Choice [1-3]: " choice
  case "$choice" in
    1) echo "dev" ;;
    2) echo "beta" ;;
    3) echo "prod" ;;
    *)
      echo "Invalid environment selection." >&2
      exit 1
      ;;
  esac
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

  echo "[1/5] Running preflight checks..."
  preflight_startup dev

  echo "[2/5] Starting containers ($(build_mode_label))..."
  run_compose_up_with_build_mode dev

  echo "[3/5] Waiting for backend to be ready..."
  sleep 12

  echo "[4/5] Syncing cert to frontend..."
  if ! sync_dev_cert; then
    echo "Cert sync skipped."
  fi

  echo "[5/5] Connectivity check..."
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

  echo "[1/3] Clearing stuck DB jobs..."
  docker exec uah-dev-db psql -U uah -d uah_dev -c "
  UPDATE parse_jobs
  SET status='failed', error_message='Cleared on shutdown', updated_at=now()
  WHERE status IN ('queued','parsing','validating');
" 2>/dev/null || echo "DB not running, skipping."

  echo "[2/3] Clearing Redis..."
  docker exec uah-redis redis-cli FLUSHDB 2>/dev/null || echo "Redis not running, skipping."

  echo "[3/3] Stopping containers..."
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

run_debug() {
  local env_name="$1"
  if [[ "$env_name" == "dev" ]]; then
    bash "$ROOT_DIR/scripts/dev/diagnostic/dev-debug.sh"
    return
  fi
  if [[ "$env_name" == "beta" ]]; then
    bash "$ROOT_DIR/scripts/beta/diagnostic/beta-debug.sh"
    return
  fi
  prod_scaffold "debug"
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

while (($#)); do
  case "$1" in
    -h|--help|help)
      SHOW_HELP=true
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

if [[ -z "$ENV_NAME" ]]; then
  ENV_NAME="$(choose_environment)"
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
    run_debug "$ENV_NAME"
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
