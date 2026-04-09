#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

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

  echo "[1/4] Starting containers..."
  run_compose dev up -d

  echo "[2/4] Waiting for backend to be ready..."
  sleep 12

  echo "[3/4] Syncing cert to frontend..."
  if ! sync_dev_cert; then
    echo "Cert sync skipped."
  fi

  echo "[4/4] Connectivity check..."
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
  echo "=== UAH Dev Restart ==="
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

  echo "[1/5] Starting containers..."
  run_compose beta up -d

  echo "[2/5] Waiting for backend to be ready..."
  sleep 12

  echo "[3/5] Applying WireGuard host route..."
  VPN_CONTAINER=uah-dev-vpn \
  BACKEND_CONTAINER=uah-beta-backend \
  NETWORK_NAME=uah-infra \
  SOURCE_CIDR=172.18.0.0/16 \
  bash "$ROOT_DIR/scripts/beta/network/apply_desktop_ollama_temp_route.sh"

  echo "[4/5] Allowing cross-bridge Docker traffic..."
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

  echo "[5/5] Connectivity check..."
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
  echo "=== UAH Beta Restart ==="
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
      echo "[$(date -u)] Running safe sync (fast-forward only)..."
      git -C "$ROOT_DIR" fetch origin
      git -C "$ROOT_DIR" checkout dev
      git -C "$ROOT_DIR" pull --ff-only origin dev
      ;;
    hard|reset)
      if [[ -t 0 ]]; then
        echo "This will discard local changes in $ROOT_DIR."
        read -rp "Type RESET to continue: " confirmation
        if [[ "$confirmation" != "RESET" ]]; then
          echo "Hard sync cancelled."
          return
        fi
      fi
      echo "[$(date -u)] Running hard sync (reset --hard origin/dev)..."
      git -C "$ROOT_DIR" fetch origin
      git -C "$ROOT_DIR" checkout dev
      git -C "$ROOT_DIR" reset --hard origin/dev
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

while (($#)); do
  case "$1" in
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
    *)
      EXTRA_ARGS+=("$1")
      ;;
  esac
  shift
done

if [[ -z "$ENV_NAME" ]]; then
  ENV_NAME="$(choose_environment)"
fi

if [[ -z "$ACTION" ]]; then
  ACTION="$(choose_action)"
fi

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
    elif [[ "$ENV_NAME" == "dev" ]]; then
      echo "Dev sync uses fast-forward only."
      git -C "$ROOT_DIR" fetch origin
      git -C "$ROOT_DIR" checkout dev
      git -C "$ROOT_DIR" pull --ff-only origin dev
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
