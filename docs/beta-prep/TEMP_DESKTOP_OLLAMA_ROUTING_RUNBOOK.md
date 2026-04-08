# Temporary Desktop Ollama Routing Runbook

## Purpose
Provide a scoped, reversible temporary route so the backend container can reach desktop Ollama at `10.8.0.8:11434` through the existing `uah-dev-vpn` WireGuard container.

This does **not** replace permanent infrastructure routing. It is an operational bridge while desktop-first local OCR/LLM is being validated.

## What This Changes
- Adds a host route: `10.8.0.8/32` -> `uah-dev-vpn` container IP on the Docker bridge.
- Adds VPN-container forwarding rule only for TCP `11434` to desktop `10.8.0.8`.
- Adds scoped NAT rule for backend source CIDR -> desktop `10.8.0.8`.
- Defaults to least-privilege source scope using backend container IP (`/32`) when available.

## Security Scope
- Destination restricted to a single desktop IP: `10.8.0.8/32`
- Port restricted to Ollama API port: `11434/tcp`
- Rules are easy to roll back with one script

## Prerequisites
- SSH access to VM host where Docker Compose services run
- Running containers: `uah-dev-vpn`, `uah-dev-backend`
- Desktop peer online in WireGuard (recent handshake)

## Apply
Run from repo root on the VM host:

```bash
chmod +x scripts/network/*.sh
./scripts/network/apply_desktop_ollama_temp_route.sh
```

Optional overrides:

```bash
DESKTOP_IP=10.8.0.8 DESKTOP_PORT=11434 VPN_CONTAINER=uah-dev-vpn ./scripts/network/apply_desktop_ollama_temp_route.sh
```

## Verify Connectivity

```bash
./scripts/network/check_desktop_ollama_temp_route.sh
```

Expected:
- `ip route get 10.8.0.8` shows next-hop via VPN container IP on Docker bridge
- host curl to `/api/tags` returns JSON
- backend container request to `/api/tags` returns status `200` (uses Python stdlib, no `requests` dependency)

## Application Validation
After connectivity passes:

```bash
# Ensure flags point to desktop Ollama endpoint
# USE_LOCAL_PIPELINE=true
# LOCAL_OCR_URL=http://10.8.0.8:11434
# LOCAL_LLM_URL=http://10.8.0.8:11434
# REDIS_ENABLED=true

docker compose up -d --build backend

docker compose logs backend --tail 120
```

Then run UI/API resume smoke tests and check queue status endpoint:

```bash
# Example endpoint
curl -s http://dev.uahapp.com/api/resume/queue/status
```

## Rollback

```bash
./scripts/network/rollback_desktop_ollama_temp_route.sh
```

This removes the host route and temporary iptables rules from the VPN container.

## Notes
- This workaround may not survive host/container restart; re-run apply script if needed.
- If `sysctl` is read-only in the VPN container but forwarding is already enabled, apply script continues safely.
- Permanent solution should move route ownership to host/network infra rather than app runtime.
