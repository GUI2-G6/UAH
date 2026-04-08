#!/usr/bin/env bash
set -euo pipefail

DESKTOP_IP="${DESKTOP_IP:-10.8.0.8}"
DESKTOP_PORT="${DESKTOP_PORT:-11434}"
VPN_CONTAINER="${VPN_CONTAINER:-uah-dev-vpn}"

if ! docker ps --format '{{.Names}}' | grep -Fxq "$VPN_CONTAINER"; then
  echo "VPN container '$VPN_CONTAINER' is not running. Continuing with host route cleanup only."
else
  NETWORK_NAME="${NETWORK_NAME:-$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{printf "%s\n" $k}}{{end}}' "$VPN_CONTAINER" | head -n1)}"
  SOURCE_CIDR="${SOURCE_CIDR:-$(docker network inspect "$NETWORK_NAME" -f '{{(index .IPAM.Config 0).Subnet}}')}"

  echo "Removing scoped iptables rules inside ${VPN_CONTAINER}"
  docker exec "$VPN_CONTAINER" sh -lc "iptables -D FORWARD -i eth0 -o wg0 -p tcp -d ${DESKTOP_IP}/32 --dport ${DESKTOP_PORT} -j ACCEPT" || true
  docker exec "$VPN_CONTAINER" sh -lc "iptables -D FORWARD -i wg0 -o eth0 -p tcp -s ${DESKTOP_IP}/32 --sport ${DESKTOP_PORT} -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT" || true
  docker exec "$VPN_CONTAINER" sh -lc "iptables -t nat -D POSTROUTING -s ${SOURCE_CIDR} -d ${DESKTOP_IP}/32 -o wg0 -j MASQUERADE" || true
fi

echo "Removing host route (if present)"
sudo ip route del "${DESKTOP_IP}/32" 2>/dev/null || true

echo "Rollback complete."
