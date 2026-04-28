#!/usr/bin/env bash
# Dispatcher for ops console submenus (sourced from scripts/uah.sh Control Center).
# Implementation lives in ops_console_beta.sh / ops_console_dev.sh.

uah_ops_dispatch_submenu() {
  local env_name="${1:?}"
  local fn_name="${2:?}"
  local root="${OPS_ROOT_DIR:-${ROOT_DIR:?}}"

  case "$env_name" in
    beta)
      # shellcheck source=ops_console_beta.sh
      source "$root/scripts/lib/ops_console_beta.sh"
      ops_console_beta_init
      "$fn_name"
      ;;
    dev)
      # shellcheck source=ops_console_dev.sh
      source "$root/scripts/lib/ops_console_dev.sh"
      ops_console_dev_init
      "$fn_name"
      ;;
    prod)
      echo "This action is not available for prod from the Control Center." >&2
      return 1
      ;;
    *)
      echo "Unknown environment '$env_name'." >&2
      return 1
      ;;
  esac
}
