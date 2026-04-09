#!/usr/bin/env bash
set -euo pipefail

DESKTOP_IP="${DESKTOP_IP:-10.8.0.8}"
DESKTOP_PORT="${DESKTOP_PORT:-11434}"
VPN_CONTAINER="${VPN_CONTAINER:-uah-dev-vpn}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-uah-dev-backend}"
ROUTE_OWNER="${ROUTE_OWNER:-dev}"
BACKEND_CONTAINERS_PRESERVE="${BACKEND_CONTAINERS_PRESERVE:-uah-dev-backend uah-beta-backend}"

is_backend_running() {
  local container_name="$1"
  docker ps --format '{{.Names}}' | grep -Fxq "$container_name"
}

should_preserve_route() {
  local container_name

  for container_name in $BACKEND_CONTAINERS_PRESERVE; do
    [[ -z "$container_name" ]] && continue
    if [[ "$container_name" == "$BACKEND_CONTAINER" ]]; then
      continue
    fi
    if is_backend_running "$container_name"; then
      echo "Detected running sibling backend '$container_name'; preserving shared host route."
      return 0
    fi
  done

  return 1
}

if ! docker ps --format '{{.Names}}' | grep -Fxq "$VPN_CONTAINER"; then
  echo "VPN container '$VPN_CONTAINER' is not running. Continuing with host route cleanup only."
else
  NETWORK_NAME="${NETWORK_NAME:-$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{printf "%s\n" $k}}{{end}}' "$VPN_CONTAINER" | head -n1)}"
  LEGACY_SOURCE_CIDR="$(docker network inspect "$NETWORK_NAME" -f '{{(index .IPAM.Config 0).Subnet}}' 2>/dev/null || true)"
  BACKEND_IP=""
  if docker ps --format '{{.Names}}' | grep -Fxq "$BACKEND_CONTAINER"; then
    BACKEND_IP="$(docker inspect -f "{{with index .NetworkSettings.Networks \"$NETWORK_NAME\"}}{{.IPAddress}}{{end}}" "$BACKEND_CONTAINER" 2>/dev/null || true)"
  fi

  if [[ -n "${SOURCE_CIDR:-}" ]]; then
    CANDIDATE_SOURCE_CIDRS=("$SOURCE_CIDR")
  else
    CANDIDATE_SOURCE_CIDRS=()
  fi

  if [[ -n "$BACKEND_IP" ]]; then
    CANDIDATE_SOURCE_CIDRS+=("${BACKEND_IP}/32")
  fi
  if [[ -n "$LEGACY_SOURCE_CIDR" ]]; then
    CANDIDATE_SOURCE_CIDRS+=("$LEGACY_SOURCE_CIDR")
  fi

  echo "Removing scoped iptables rules inside ${VPN_CONTAINER}"
  for cidr in "${CANDIDATE_SOURCE_CIDRS[@]}"; do
    [[ -z "$cidr" ]] && continue
    docker exec "$VPN_CONTAINER" sh -lc "iptables -D FORWARD -i eth0 -o wg0 -p tcp -s ${cidr} -d ${DESKTOP_IP}/32 --dport ${DESKTOP_PORT} -m comment --comment uah-route:${ROUTE_OWNER} -j ACCEPT" || true
    docker exec "$VPN_CONTAINER" sh -lc "iptables -D FORWARD -i wg0 -o eth0 -p tcp -s ${DESKTOP_IP}/32 --sport ${DESKTOP_PORT} -d ${cidr} -m conntrack --ctstate ESTABLISHED,RELATED -m comment --comment uah-route:${ROUTE_OWNER} -j ACCEPT" || true
    docker exec "$VPN_CONTAINER" sh -lc "iptables -t nat -D POSTROUTING -s ${cidr} -d ${DESKTOP_IP}/32 -o wg0 -m comment --comment uah-route:${ROUTE_OWNER} -j MASQUERADE" || true
  done

  if [[ "${ALLOW_LEGACY_BROAD_RULE_CLEANUP:-false}" == "true" ]]; then
    # Optional cleanup for rules from old script versions.
    docker exec "$VPN_CONTAINER" sh -lc "iptables -D FORWARD -i eth0 -o wg0 -p tcp -d ${DESKTOP_IP}/32 --dport ${DESKTOP_PORT} -j ACCEPT" || true
    docker exec "$VPN_CONTAINER" sh -lc "iptables -D FORWARD -i wg0 -o eth0 -p tcp -s ${DESKTOP_IP}/32 --sport ${DESKTOP_PORT} -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT" || true
  fi
fi

echo "Removing host route (if present)"
if should_preserve_route; then
  echo "Preserving host route for sibling environment."
else
  sudo ip route del "${DESKTOP_IP}/32" 2>/dev/null || true
fi

echo "Rollback complete."
