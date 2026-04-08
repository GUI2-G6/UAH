#!/usr/bin/env bash
set -euo pipefail

DESKTOP_IP="${DESKTOP_IP:-10.8.0.8}"
DESKTOP_PORT="${DESKTOP_PORT:-11434}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-uah-dev-backend}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd curl
require_cmd docker

echo "[1/3] Host route check"
ip route get "$DESKTOP_IP"

echo "[2/3] Host -> desktop Ollama"
curl -sS --max-time 8 "http://${DESKTOP_IP}:${DESKTOP_PORT}/api/tags" | head -c 400 && echo

echo "[3/3] Backend container -> desktop Ollama"
docker exec -e DESKTOP_IP="$DESKTOP_IP" -e DESKTOP_PORT="$DESKTOP_PORT" "$BACKEND_CONTAINER" python - <<'PY'
import requests
import sys
import os

url = f"http://{os.environ['DESKTOP_IP']}:{os.environ['DESKTOP_PORT']}/api/tags"
try:
    r = requests.get(url, timeout=8)
    print("status=", r.status_code)
    print(r.text[:400])
except Exception as exc:
    print("backend request failed:", type(exc).__name__, str(exc))
    sys.exit(1)
PY

echo "Connectivity checks completed."
