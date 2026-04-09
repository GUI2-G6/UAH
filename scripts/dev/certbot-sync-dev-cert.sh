#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

CERT_SRC="${CERT_SRC:-/etc/letsencrypt/live/dev.uahapp.com/fullchain.pem}"
KEY_SRC="${KEY_SRC:-/etc/letsencrypt/live/dev.uahapp.com/privkey.pem}"
CERT_DEST_DIR="${CERT_DEST_DIR:-$ROOT_DIR/volumes/certs/dev}"
FRONTEND_CONTAINER="${FRONTEND_CONTAINER:-uah-dev-frontend}"

if [[ ! -f "$CERT_SRC" ]]; then
  echo "Cert source not found: $CERT_SRC" >&2
  exit 1
fi

if [[ ! -f "$KEY_SRC" ]]; then
  echo "Key source not found: $KEY_SRC" >&2
  exit 1
fi

mkdir -p "$CERT_DEST_DIR"

sudo cp "$CERT_SRC" "$CERT_DEST_DIR/tls.crt"
sudo cp "$KEY_SRC" "$CERT_DEST_DIR/tls.key"

docker exec "$FRONTEND_CONTAINER" nginx -s reload 2>/dev/null || echo "Frontend reload skipped."

echo "Dev cert synced to $CERT_DEST_DIR and frontend reload attempted."
