# UAH — Unified Application Hub

> **DEV Environment Documentation**
> All commands assume you are SSH'd into the server at  `/srv/uah/environments/dev` on proxmox

---

## Architecture

```
                    VPN Clients
                        │
                   ┌────▼────┐
                   │ WireGuard│  (10.8.0.1)
                   │ wg-easy  │
                   └────┬────┘
                        │ network_mode: container
                   ┌────▼────────┐
                   │  Frontend   │  Nginx :80
                   │  (Vue 3)    │
                   └────┬────────┘
                        │ proxy_pass /api/
                   ┌────▼────────┐
                   │  Backend    │  Uvicorn :8000
                   │  (FastAPI)  │
                   └────┬────────┘
                        │ service name "db"
                   ┌────▼────────┐
                   │  Database   │  Postgres :5432
                   │  (Postgres) │
                   └─────────────┘
```

| Service | Container | Exposed Ports | Network |
|---------|-----------|---------------|---------|
| db | uah-dev-db | None | uah-infra |
| backend | uah-dev-backend | None | uah-infra |
| frontend | uah-dev-frontend | 80 (via VPN only) | Shares VPN container |
| vpn | uah-dev-vpn | 51820/udp | uah-infra |

**Access:** `http://dev.uahapp.com` — requires VPN connection.

---

## File Structure

```
/srv/uah/environments/dev/
├── .env                          # Environment variables (secrets, DB creds)
├── docker-compose.yml            # Service definitions
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # FastAPI entry point
│       ├── api/routes.py         # API route handlers
│       ├── core/config.py        # Centralized settings from env vars
│       ├── db/session.py         # SQLAlchemy engine + session factory
│       ├── db/base.py            # Declarative Base for models
│       └── models/__init__.py    # Import all models here
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf                # Nginx config (proxy + SPA fallback)
│   ├── package.json
│   └── src/
│       ├── App.vue               # Root component (backend status check)
│       └── main.js               # Vue app mount
├── volumes/postgres/             # Persistent DB data (DO NOT DELETE)
└── logs/
```

---

## Quick Start

```bash
# Build and start all services
docker compose up -d --build
```

---

## Service-Specific Commands

### Rebuild a single service (does NOT affect others)

```bash
# Backend only — use after changing Python code or requirements.txt
docker compose up -d --build backend

# Frontend only — use after changing Vue code, nginx.conf, or package.json
docker compose up -d --build frontend

# Database — rarely needed, only if changing Postgres version
docker compose up -d --build db
```

### Restart without rebuilding

```bash
# Restart one service (keeps existing image)
docker compose restart backend
docker compose restart frontend
docker compose restart db
```

### Stop a single service

```bash
# Stop one service without removing it
docker compose stop backend

# Start it back
docker compose start backend
```

### Stop everything (preserves data)

```bash
docker compose down
```

> **Warning:** `docker compose down -v` will **delete the Postgres volume**. Never use `-v` unless you intend to wipe the database.

---

## Checking Status

```bash
# See all running containers and their health
docker compose ps

# View last 50 lines of logs for a service
docker compose logs backend --tail 50
docker compose logs frontend --tail 50
docker compose logs db --tail 50

# Follow logs in real-time (Ctrl+C to stop)
docker compose logs -f backend
```

---

## Testing Endpoints

The backend container uses `python:3.12-slim` (no curl). Use these methods:

```bash
# Test backend health
docker exec uah-dev-backend python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"

# Test API status
docker exec uah-dev-backend python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/status').read().decode())"

# Test frontend + proxy (curl is available in the nginx container)
docker exec uah-dev-frontend curl -s http://localhost/
docker exec uah-dev-frontend curl -s http://localhost/api/status
docker exec uah-dev-frontend curl -s http://localhost/docs | head -20
```

---

## Accessing Dev Tools (VPN Required)

| URL | Description |
|-----|-------------|
| `http://dev.uahapp.com` | Frontend app |
| `http://dev.uahapp.com/status` | System status page (full diagnostics) |
| `http://dev.uahapp.com/api/status` | API status check (JSON) |
| `http://dev.uahapp.com/api/diagnostics` | Full diagnostics payload (JSON) |
| `http://dev.uahapp.com/docs` | Swagger UI (auto-generated) |
| `http://dev.uahapp.com/redoc` | ReDoc (alternative API docs) |
| `http://dev.uahapp.com/openapi.json` | Raw OpenAPI spec |

---

## Database Access

```bash
# Open a psql shell inside the DB container
docker exec -it uah-dev-db psql -U uah -d uah_dev

# Run a quick query
docker exec uah-dev-db psql -U uah -d uah_dev -c "\dt"

# Check if DB is accepting connections
docker exec uah-dev-db pg_isready -U uah -d uah_dev
```

---

## Common Workflows

### I changed backend Python code

```bash
# Uvicorn has --reload enabled and the backend/ directory is volume-mounted.
# Changes to .py files are picked up automatically — no rebuild needed.
# Just check the logs:
docker compose logs -f backend
```

### I changed requirements.txt

```bash
# Must rebuild to install new packages
docker compose up -d --build backend
```

### I changed frontend Vue/JS code

```bash
# Frontend must be rebuilt (Vite builds static assets into the Nginx image)
docker compose up -d --build frontend
```

### I changed nginx.conf

```bash
# Must rebuild frontend since nginx.conf is baked into the image
docker compose up -d --build frontend
```

### I need to wipe the database and start fresh

```bash
docker compose down
sudo rm -rf ./volumes/postgres/*
docker compose up -d --build
```

---

## What NOT to Touch

| Item | Reason |
|------|--------|
| `/srv/uah/infrastructure/` | VPN and tunnel configs — managed separately |
| `uah-dev-vpn` container | Frontend depends on its network namespace |
| `uah-infra` Docker network | Shared across infrastructure and app services |
| Cloudflare tunnel config | Managed outside this repo |
| Port `51820/udp` | WireGuard VPN — do not change |

---

## Environment Variables

All secrets live in `.env` at the project root. Docker Compose reads it automatically.

| Variable | Used By | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | db, backend | Database username |
| `POSTGRES_PASSWORD` | db, backend | Database password |
| `POSTGRES_DB` | db, backend | Database name |
| `POSTGRES_PORT` | backend | Database port (default: 5432) |
| `COMPOSE_PROJECT_NAME` | docker compose | Project namespace |
| `ENV` | reference | Current environment |
| `DEV_DOMAIN` | reference | Domain for dev access |

> **Never commit `.env` to git.** It contains credentials.
