#!/usr/bin/env bash
set -euo pipefail

# Scoped route/NAT for dev backend -> desktop Ollama over WireGuard.
# Runs on host, not inside a container namespace.

DESKTOP_IP="${DESKTOP_IP:-10.8.0.8}"
DESKTOP_PORT="${DESKTOP_PORT:-11434}"
VPN_CONTAINER="${VPN_CONTAINER:-uah-dev-vpn}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-uah-dev-backend}"
ROUTE_OWNER="${ROUTE_OWNER:-dev}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd docker
require_cmd ip

if ! docker ps --format '{{.Names}}' | grep -Fxq "$VPN_CONTAINER"; then
  echo "VPN container '$VPN_CONTAINER' is not running." >&2
  exit 1
fi

NETWORK_NAME="${NETWORK_NAME:-$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{printf "%s\n" $k}}{{end}}' "$VPN_CONTAINER" | head -n1)}"
if [[ -z "$NETWORK_NAME" ]]; then
  echo "Unable to determine Docker network for $VPN_CONTAINER" >&2
  exit 1
fi

VPN_IP="${VPN_IP:-$(docker inspect -f "{{with index .NetworkSettings.Networks \"$NETWORK_NAME\"}}{{.IPAddress}}{{end}}" "$VPN_CONTAINER")}" 
if [[ -z "$VPN_IP" ]]; then
  echo "Unable to determine VPN container IP on network $NETWORK_NAME" >&2
  exit 1
fi

SOURCE_CIDR="${SOURCE_CIDR:-}"

BACKEND_IP=""
if docker ps --format '{{.Names}}' | grep -Fxq "$BACKEND_CONTAINER"; then
  BACKEND_IP="$(docker inspect -f "{{with index .NetworkSettings.Networks \"$NETWORK_NAME\"}}{{.IPAddress}}{{end}}" "$BACKEND_CONTAINER" 2>/dev/null || true)"
fi

if [[ -z "${SOURCE_CIDR:-}" ]]; then
  if [[ -n "$BACKEND_IP" ]]; then
    SOURCE_CIDR="${BACKEND_IP}/32"
  else
    SOURCE_CIDR="$(docker network inspect "$NETWORK_NAME" -f '{{(index .IPAM.Config 0).Subnet}}')"
  fi
fi

if [[ -z "$SOURCE_CIDR" ]]; then
  echo "Unable to determine source CIDR for rules on network $NETWORK_NAME" >&2
  exit 1
fi

BRIDGE_IF="${BRIDGE_IF:-$(docker network inspect "$NETWORK_NAME" -f '{{index .Options "com.docker.network.bridge.name"}}')}"
if [[ -z "$BRIDGE_IF" || "$BRIDGE_IF" == "<no value>" ]]; then
  NET_ID_SHORT="$(docker network inspect "$NETWORK_NAME" -f '{{.Id}}' | cut -c1-12)"
  BRIDGE_IF="br-${NET_ID_SHORT}"
fi

if ! ip link show "$BRIDGE_IF" >/dev/null 2>&1; then
  echo "Bridge interface '$BRIDGE_IF' was not found. Set BRIDGE_IF explicitly." >&2
  exit 1
fi

echo "Applying host route: ${DESKTOP_IP}/32 via ${VPN_IP} dev ${BRIDGE_IF}"
sudo ip route replace "${DESKTOP_IP}/32" via "$VPN_IP" dev "$BRIDGE_IF"

echo "Ensuring forwarding is enabled in VPN container namespace"
current_forward="$(docker exec "$VPN_CONTAINER" sh -lc 'cat /proc/sys/net/ipv4/ip_forward 2>/dev/null || echo 0')"
if [[ "$current_forward" != "1" ]]; then
  if ! docker exec "$VPN_CONTAINER" sh -lc 'sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1'; then
    after_forward="$(docker exec "$VPN_CONTAINER" sh -lc 'cat /proc/sys/net/ipv4/ip_forward 2>/dev/null || echo 0')"
    if [[ "$after_forward" != "1" ]]; then
      echo "Could not enable net.ipv4.ip_forward in $VPN_CONTAINER (read-only sysctl)" >&2
      echo "Set container capability/sysctl for IP forwarding, then retry." >&2
      exit 1
    fi
    echo "Forwarding appears enabled despite sysctl warning; continuing."
  fi
fi

echo "Applying scoped iptables rules inside ${VPN_CONTAINER}"
docker exec "$VPN_CONTAINER" sh -lc "iptables -C FORWARD -i eth0 -o wg0 -p tcp -s ${SOURCE_CIDR} -d ${DESKTOP_IP}/32 --dport ${DESKTOP_PORT} -m comment --comment uah-route:${ROUTE_OWNER} -j ACCEPT 2>/dev/null || iptables -A FORWARD -i eth0 -o wg0 -p tcp -s ${SOURCE_CIDR} -d ${DESKTOP_IP}/32 --dport ${DESKTOP_PORT} -m comment --comment uah-route:${ROUTE_OWNER} -j ACCEPT"
docker exec "$VPN_CONTAINER" sh -lc "iptables -C FORWARD -i wg0 -o eth0 -p tcp -s ${DESKTOP_IP}/32 --sport ${DESKTOP_PORT} -d ${SOURCE_CIDR} -m conntrack --ctstate ESTABLISHED,RELATED -m comment --comment uah-route:${ROUTE_OWNER} -j ACCEPT 2>/dev/null || iptables -A FORWARD -i wg0 -o eth0 -p tcp -s ${DESKTOP_IP}/32 --sport ${DESKTOP_PORT} -d ${SOURCE_CIDR} -m conntrack --ctstate ESTABLISHED,RELATED -m comment --comment uah-route:${ROUTE_OWNER} -j ACCEPT"
docker exec "$VPN_CONTAINER" sh -lc "iptables -t nat -C POSTROUTING -s ${SOURCE_CIDR} -d ${DESKTOP_IP}/32 -o wg0 -m comment --comment uah-route:${ROUTE_OWNER} -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -s ${SOURCE_CIDR} -d ${DESKTOP_IP}/32 -o wg0 -m comment --comment uah-route:${ROUTE_OWNER} -j MASQUERADE"

echo "Done. Route + scoped NAT/forward rules are active."
echo "Source scope: ${SOURCE_CIDR}"
echo "Route owner: ${ROUTE_OWNER}"
