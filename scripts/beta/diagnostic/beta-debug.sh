#!/usr/bin/env bash
# Thin wrapper — implementation: scripts/lib/ops_console_beta.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export OPS_ROOT_DIR="$ROOT_DIR"
# shellcheck source=../../lib/ops_console_beta.sh
source "$ROOT_DIR/scripts/lib/ops_console_beta.sh"
ops_console_beta_init
ops_beta_main_loop
