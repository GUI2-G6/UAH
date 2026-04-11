#!/bin/bash
# Usage: bash scripts/dev/diagnostic/reset-user-password.sh <email> <new_password>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ENV_FILE="${UAH_ENV_FILE:-$ROOT_DIR/.env}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-uah-dev-backend}"

USER_EMAIL="${1:?Usage: reset-user-password.sh <email> <password>}"
PASSWORD="${2:?Usage: reset-user-password.sh <email> <password>}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Env file not found: $ENV_FILE" >&2
    exit 1
fi

read_env_var() {
    local key="$1"
    grep -E "^${key}=" "$ENV_FILE" | tail -n1 | cut -d= -f2-
}

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
cur.execute("UPDATE users SET hashed_password=%s WHERE lower(email)=lower(%s) RETURNING email", (h, os.environ['USER_EMAIL']))
conn.commit()
row = cur.fetchone()
if row:
    print(f"✓ Password reset for {row[0]}")
    print(f"✓ Verify: {verify_password(os.environ['PW'], h)}")
else:
    print(f"✗ User '{os.environ['USER_EMAIL']}' not found")
cur.close()
conn.close()
PYEOF

docker cp /tmp/uah_pw_reset.py uah-dev-backend:/tmp/uah_pw_reset.py
PGPASS="$(read_env_var POSTGRES_PASSWORD)"
PGHOST="$(read_env_var POSTGRES_HOST)"
PGDB="$(read_env_var POSTGRES_DB)"
PGUSER="$(read_env_var POSTGRES_USER)"

docker exec \
  -e PW="$PASSWORD" \
  -e USER_EMAIL="$USER_EMAIL" \
  -e PGHOST="$PGHOST" \
  -e PGDB="$PGDB" \
  -e PGUSER="$PGUSER" \
  -e PGPASS="$PGPASS" \
    "$BACKEND_CONTAINER" python3 /tmp/uah_pw_reset.py 2>/dev/null
