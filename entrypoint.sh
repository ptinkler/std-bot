#!/bin/sh
set -e

DB_PATH="${DB_PATH:-/data/polls.db}"

# Legacy DB: has tables but no alembic_version — stamp before upgrading
if [ -f "$DB_PATH" ]; then
    python - <<'EOF'
import sqlite3, os, subprocess
db = os.getenv('DB_PATH', '/data/polls.db')
conn = sqlite3.connect(db)
has_version = conn.execute(
    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='alembic_version'"
).fetchone()[0]
conn.close()
if not has_version:
    print("Legacy DB: stamping 7c2503d73cf3 before upgrade")
    subprocess.run([".venv/bin/alembic", "stamp", "7c2503d73cf3"], check=True)
EOF
fi

.venv/bin/alembic upgrade head
exec .venv/bin/python src/main.py
