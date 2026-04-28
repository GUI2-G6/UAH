#!/usr/bin/env bash
# Thin wrapper — implementation: scripts/lib/ops_console_dev.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export OPS_ROOT_DIR="$ROOT_DIR"
# shellcheck source=../../lib/ops_console_dev.sh
source "$ROOT_DIR/scripts/lib/ops_console_dev.sh"
ops_console_dev_init
ops_dev_main_loop
