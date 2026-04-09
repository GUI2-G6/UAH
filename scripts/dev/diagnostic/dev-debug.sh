#!/bin/bash
# UAH Dev Interactive Debug Console

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
COMPOSE="docker compose --env-file $ROOT_DIR/.env -f $ROOT_DIR/docker-compose.yml"
BACKEND_INTERNAL_URL="${BACKEND_INTERNAL_URL:-http://localhost:8000}"
BACKEND_INTERNAL_URL="${BACKEND_INTERNAL_URL%/}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

header() {
  clear
  echo -e "${BOLD}${CYAN}"
  echo "  ██╗   ██╗ █████╗ ██╗  ██╗    ██████╗ ███████╗██╗   ██╗"
  echo "  ██║   ██║██╔══██╗██║  ██║    ██╔══██╗██╔════╝██║   ██║"
  echo "  ██║   ██║███████║███████║    ██║  ██║█████╗  ██║   ██║"
  echo "  ██║   ██║██╔══██║██╔══██║    ██║  ██║██╔══╝  ╚██╗ ██╔╝"
  echo "  ╚██████╔╝██║  ██║██║  ██║    ██████╔╝███████╗ ╚████╔╝ "
  echo "   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═════╝ ╚══════╝  ╚═══╝  "
  echo -e "${NC}${BOLD}                   Dev Debug Console${NC}"
  echo -e "${CYAN}  ──────────────────────────────────────────────────────${NC}"
  echo ""
}

press_enter() {
  echo ""
  echo -e "${YELLOW}  Press Enter to continue...${NC}"
  read -r
}

menu_connectivity() {
  while true; do
    header
    echo -e "${BOLD}  [1] Connectivity & Health${NC}"
    echo ""
    echo "    1) Full connectivity check"
    echo "    2) Backend health"
    echo "    3) Backend → Redis"
    echo "    4) Backend → Database"
    echo "    5) VPN → Desktop ping"
    echo "    6) Cert status"
    echo "    7) Container status"
    echo "    8) Active env settings"
    echo "    9) WireGuard status"
    echo ""
    echo "    0) ← Back"
    echo ""
    read -rp "  Choice: " choice
    case $choice in
      1)
        header
        echo -e "${BOLD}  Full Connectivity Check${NC}\n"
        echo -e "${CYAN}  → Container Status${NC}"
        $COMPOSE ps
        echo ""
        echo -e "${CYAN}  → Backend Health${NC}"
        docker exec uah-dev-backend python3 -c "
import httpx
try:
    r = httpx.get('${BACKEND_INTERNAL_URL}/api/', timeout=5)
    print('  ✓ STATUS:', r.status_code)
except Exception as e:
    print('  ✗ FAILED:', type(e).__name__, str(e))
" 2>/dev/null
        echo ""
        echo -e "${CYAN}  → Backend → Redis${NC}"
        docker exec uah-dev-backend python3 -c "
import redis, os
try:
    c = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://uah-redis:6379/0'))
    print('  ✓ PING:', c.ping())
except Exception as e:
    print('  ✗ FAILED:', type(e).__name__, str(e))
" 2>/dev/null
        echo ""
        echo -e "${CYAN}  → Backend → Database${NC}"
        docker exec uah-dev-db psql -U uah -d uah_dev -c \
          "SELECT current_database(), now();" 2>&1 | sed 's/^/  /'
        echo ""
        echo -e "${CYAN}  → VPN → Desktop${NC}"
        docker exec uah-dev-vpn ping -c 2 10.8.0.8 2>/dev/null | sed 's/^/  /' || echo "  ✗ PING FAILED"
        press_enter ;;
      2)
        header
        echo -e "${BOLD}  Backend Health${NC}\n"
        docker exec uah-dev-backend python3 -c "
import httpx
try:
    r = httpx.get('${BACKEND_INTERNAL_URL}/api/', timeout=5)
    print('  STATUS:', r.status_code)
    print('  BODY:', r.text[:200])
except Exception as e:
    print('  ✗ FAILED:', type(e).__name__, str(e))
" 2>/dev/null
        press_enter ;;
      3)
        header
        echo -e "${BOLD}  Backend → Redis${NC}\n"
        docker exec uah-dev-backend python3 -c "
import redis, os
try:
    c = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://uah-redis:6379/0'))
    print('  ✓ PING:', c.ping())
    info = c.info('memory')
    print('  ✓ MEMORY:', info['used_memory_human'])
except Exception as e:
    print('  ✗ FAILED:', type(e).__name__, str(e))
" 2>/dev/null
        press_enter ;;
      4)
        header
        echo -e "${BOLD}  Backend → Database${NC}\n"
        docker exec uah-dev-db psql -U uah -d uah_dev -c \
          "SELECT current_database(), inet_server_addr(), now();" 2>&1 | sed 's/^/  /'
        press_enter ;;
      5)
        header
        echo -e "${BOLD}  VPN Container → Desktop Ping${NC}\n"
        docker exec uah-dev-vpn ping -c 4 10.8.0.8 2>/dev/null | sed 's/^/  /' || echo "  ✗ PING FAILED"
        press_enter ;;
      6)
        header
        echo -e "${BOLD}  Cert Status${NC}\n"
        echo -e "${CYAN}  Volume cert:${NC}"
        openssl x509 -in "$ROOT_DIR/volumes/certs/dev/tls.crt" -noout -dates -subject 2>/dev/null | sed 's/^/  /'
        echo ""
        echo -e "${CYAN}  Live LE cert:${NC}"
        sudo openssl x509 -in /etc/letsencrypt/live/dev.uahapp.com/fullchain.pem \
          -noout -dates -subject 2>/dev/null | sed 's/^/  /'
        echo ""
        echo -e "${CYAN}  Match check:${NC}"
        VOL=$(md5sum "$ROOT_DIR/volumes/certs/dev/tls.crt" 2>/dev/null | cut -d' ' -f1)
        LIVE=$(sudo md5sum /etc/letsencrypt/live/dev.uahapp.com/fullchain.pem 2>/dev/null | cut -d' ' -f1)
        if [[ "$VOL" == "$LIVE" ]]; then
          echo -e "  ${GREEN}✓ Certs match${NC}"
        else
          echo -e "  ${RED}✗ Certs DO NOT match — run dev-start.sh to sync${NC}"
        fi
        press_enter ;;
      7)
        header
        echo -e "${BOLD}  Container Status${NC}\n"
        $COMPOSE ps
        press_enter ;;
      8)
        header
        echo -e "${BOLD}  Active Env Settings${NC}\n"
        docker exec uah-dev-backend python3 -c "
from app.core.config import settings
print('  POSTGRES_HOST:     ', settings.POSTGRES_HOST)
print('  POSTGRES_DB:       ', settings.POSTGRES_DB)
print('  USE_LOCAL_PIPELINE:', settings.USE_LOCAL_PIPELINE)
print('  REDIS_ENABLED:     ', settings.REDIS_ENABLED)
print('  REDIS_URL:         ', settings.REDIS_URL)
print('  ZAI_API_KEY set:   ', bool(settings.ZAI_API_KEY))
" 2>/dev/null
        press_enter ;;
      9)
        header
        echo -e "${BOLD}  WireGuard Status${NC}\n"
        docker exec uah-dev-vpn wg show 2>/dev/null | sed 's/^/  /' || echo "  ✗ wg not available"
        press_enter ;;
      0) return ;;
    esac
  done
}

menu_users() {
  while true; do
    header
    echo -e "${BOLD}  [2] User Management${NC}"
    echo ""
    echo "    1) List all users"
    echo "    2) Reset user password"
    echo "    3) Show user by username"
    echo "    4) Activate/deactivate user"
    echo ""
    echo "    0) ← Back"
    echo ""
    read -rp "  Choice: " choice
    case $choice in
      1)
        header
        echo -e "${BOLD}  All Users${NC}\n"
        docker exec uah-dev-db psql -U uah -d uah_dev -c "
          SELECT id, username, email, first_name, is_active, created_at
          FROM users ORDER BY id;
        " | sed 's/^/  /'
        press_enter ;;
      2)
        header
        echo -e "${BOLD}  Reset User Password${NC}\n"
        read -rp "  Username: " uname
        read -rsp "  New password: " upass
        echo ""
        if [[ -n "$uname" && -n "$upass" ]]; then
          cat > /tmp/uah_pw_reset.py << PYEOF
import sys
sys.path.insert(0, '/app')
from app.core.security import hash_password, verify_password
import psycopg2, os
h = hash_password(os.environ['PW'])
conn = psycopg2.connect(
    host=os.environ['PGHOST'], dbname=os.environ['PGDB'],
    user=os.environ['PGUSER'], password=os.environ['PGPASS']
)
cur = conn.cursor()
cur.execute("UPDATE users SET hashed_password=%s WHERE username=%s RETURNING username, email", (h, os.environ['USERNAME']))
conn.commit()
row = cur.fetchone()
if row:
    print(f"  ✓ Password reset for {row[0]} ({row[1]})")
    print(f"  ✓ Verify: {verify_password(os.environ['PW'], h)}")
else:
    print(f"  ✗ User not found: {os.environ['USERNAME']}")
cur.close()
conn.close()
PYEOF
          docker cp /tmp/uah_pw_reset.py uah-dev-backend:/tmp/uah_pw_reset.py
          PGPASS=$(grep POSTGRES_PASSWORD "$ROOT_DIR/.env" | cut -d= -f2)
          PGHOST=$(grep POSTGRES_HOST "$ROOT_DIR/.env" | cut -d= -f2)
          PGDB=$(grep POSTGRES_DB "$ROOT_DIR/.env" | cut -d= -f2)
          PGUSER=$(grep POSTGRES_USER "$ROOT_DIR/.env" | cut -d= -f2)
          docker exec \
            -e PW="$upass" -e USERNAME="$uname" \
            -e PGHOST="$PGHOST" -e PGDB="$PGDB" \
            -e PGUSER="$PGUSER" -e PGPASS="$PGPASS" \
            uah-dev-backend python3 /tmp/uah_pw_reset.py 2>/dev/null
        fi
        press_enter ;;
      3)
        header
        echo -e "${BOLD}  User Lookup${NC}\n"
        read -rp "  Username: " uname
        docker exec uah-dev-db psql -U uah -d uah_dev -c "
          SELECT id, username, email, first_name, last_name, is_active,
                 email_verified, created_at, updated_at
          FROM users WHERE username='$uname';
        " | sed 's/^/  /'
        press_enter ;;
      4)
        header
        echo -e "${BOLD}  Toggle User Active${NC}\n"
        read -rp "  Username: " uname
        read -rp "  Active? (true/false): " active
        docker exec uah-dev-db psql -U uah -d uah_dev -c "
          UPDATE users SET is_active=$active WHERE username='$uname'
          RETURNING username, is_active;
        " | sed 's/^/  /'
        press_enter ;;
      0) return ;;
    esac
  done
}

menu_database() {
  while true; do
    header
    echo -e "${BOLD}  [3] Database${NC}"
    echo ""
    echo "    1) DB isolation check"
    echo "    2) User count"
    echo "    3) Resume count"
    echo "    4) Parse job stats"
    echo "    5) Recent parse jobs"
    echo "    6) Clear stuck jobs"
    echo "    7) Raw SQL"
    echo "    8) DB size"
    echo ""
    echo "    0) ← Back"
    echo ""
    read -rp "  Choice: " choice
    case $choice in
      1)
        header
        echo -e "${BOLD}  DB Isolation Check${NC}\n"
        docker exec uah-dev-db psql -U uah -d uah_dev -c \
          "SELECT current_database(), inet_server_addr(), version();" | sed 's/^/  /'
        press_enter ;;
      2)
        header
        echo -e "${BOLD}  User Count${NC}\n"
        docker exec uah-dev-db psql -U uah -d uah_dev -c \
          "SELECT COUNT(*) as total_users FROM users;" | sed 's/^/  /'
        press_enter ;;
      3)
        header
        echo -e "${BOLD}  Resume Count${NC}\n"
        docker exec uah-dev-db psql -U uah -d uah_dev -c \
          "SELECT COUNT(*) as total_resumes FROM resumes;" | sed 's/^/  /'
        press_enter ;;
      4)
        header
        echo -e "${BOLD}  Parse Job Stats${NC}\n"
        docker exec uah-dev-db psql -U uah -d uah_dev -c "
          SELECT method, status, COUNT(*) as count
          FROM parse_jobs GROUP BY method, status ORDER BY method, status;
        " | sed 's/^/  /'
        press_enter ;;
      5)
        header
        echo -e "${BOLD}  Recent Parse Jobs (last 20)${NC}\n"
        docker exec uah-dev-db psql -U uah -d uah_dev -c "
          SELECT id, user_id, method, status, error_code,
                 LEFT(error_message,40) as error_msg, updated_at
          FROM parse_jobs ORDER BY updated_at DESC LIMIT 20;
        " | sed 's/^/  /'
        press_enter ;;
      6)
        header
        echo -e "${BOLD}  Clear Stuck Jobs${NC}\n"
        docker exec uah-dev-db psql -U uah -d uah_dev -c "
          UPDATE parse_jobs SET status='failed', error_message='Cleared by admin', updated_at=now()
          WHERE status IN ('queued','parsing','validating')
          RETURNING id, status, updated_at;
        " | sed 's/^/  /'
        press_enter ;;
      7)
        header
        echo -e "${BOLD}  Raw SQL${NC}\n"
        read -rp "  SQL> " sql_query
        if [[ -n "$sql_query" ]]; then
          docker exec uah-dev-db psql -U uah -d uah_dev -c "$sql_query" | sed 's/^/  /'
        fi
        press_enter ;;
      8)
        header
        echo -e "${BOLD}  Database Size${NC}\n"
        docker exec uah-dev-db psql -U uah -d uah_dev -c "
          SELECT pg_size_pretty(pg_database_size(current_database())) as db_size;
        " | sed 's/^/  /'
        press_enter ;;
      0) return ;;
    esac
  done
}

menu_logs() {
  while true; do
    header
    echo -e "${BOLD}  [4] Logs${NC}"
    echo ""
    echo "    1) Backend logs (filtered)"
    echo "    2) Backend logs (raw)"
    echo "    3) Backend errors only"
    echo "    4) Frontend/nginx logs"
    echo "    5) Follow backend live"
    echo ""
    echo "    0) ← Back"
    echo ""
    read -rp "  Choice: " choice
    case $choice in
      1)
        header
        echo -e "${BOLD}  Backend Logs (filtered)${NC}\n"
        $COMPOSE logs --tail=50 backend 2>&1 \
          | grep -v "sqlalchemy" | grep -v "SELECT" | grep -v "FROM " \
          | grep -v "WHERE " | grep -v "LIMIT " | grep -v "cached since" \
          | sed 's/^/  /'
        press_enter ;;
      2)
        header
        echo -e "${BOLD}  Backend Logs (raw)${NC}\n"
        $COMPOSE logs --tail=50 backend 2>&1 | sed 's/^/  /'
        press_enter ;;
      3)
        header
        echo -e "${BOLD}  Backend Errors Only${NC}\n"
        $COMPOSE logs --tail=100 backend 2>&1 \
          | grep -iE "error|exception|failed|traceback|critical" \
          | sed 's/^/  /'
        press_enter ;;
      4)
        header
        echo -e "${BOLD}  Frontend/Nginx Logs${NC}\n"
        docker exec uah-dev-frontend cat /var/log/nginx/access.log 2>/dev/null | tail -20 | sed 's/^/  /'
        echo ""
        docker exec uah-dev-frontend cat /var/log/nginx/error.log 2>/dev/null | tail -20 | sed 's/^/  /'
        press_enter ;;
      5)
        header
        echo -e "${BOLD}  Live Backend Logs${NC} ${YELLOW}(Ctrl+C to exit)${NC}\n"
        $COMPOSE logs -f backend 2>&1 \
          | grep -v "sqlalchemy" | grep -v "SELECT" | grep -v "FROM " \
          | grep -v "WHERE " | grep -v "LIMIT " | grep -v "cached since"
        press_enter ;;
      0) return ;;
    esac
  done
}

while true; do
  header
  BACKEND_UP=$(docker ps --format '{{.Names}}' | grep -c uah-dev-backend || true)
  if [[ "$BACKEND_UP" -gt 0 ]]; then
    echo -e "  Status: ${GREEN}● ONLINE${NC}"
  else
    echo -e "  Status: ${RED}● OFFLINE${NC}"
  fi
  echo ""
  echo -e "  ${BOLD}Main Menu${NC}"
  echo ""
  echo "    1) Connectivity & Health"
  echo "    2) User Management"
  echo "    3) Database"
  echo "    4) Logs"
  echo ""
  echo "    0) Exit"
  echo ""
  read -rp "  Choice: " main_choice
  case $main_choice in
    1) menu_connectivity ;;
    2) menu_users ;;
    3) menu_database ;;
    4) menu_logs ;;
    0) echo ""; exit 0 ;;
    *) ;;
  esac
done