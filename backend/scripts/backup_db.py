"""Dump the POS-MOBILE SQLite tables to a timestamped JSON file.

Used by the `backup` service in docker-compose.yml:
    docker compose --profile backup run --rm backup

DB_PATH and BACKUP_DIR may be overridden through the environment
(defaults: /data/pos_mobile.db and /backup).
"""
import sqlite3, json, datetime, os
from contextlib import closing

DB_PATH = os.environ.get("DB_PATH", "/data/pos_mobile.db")
BACKUP_DIR = os.environ.get("BACKUP_DIR", "/backup")

tables = ["products","sales","sale_items","purchases","purchase_items",
          "debts","debt_payments","expenses","stock_movements",
          "hold_bills","settings","category_mappings"]
data = {}
# mode=ro: fail if the DB is missing instead of silently creating an empty one
with closing(sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)) as conn:
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    for t in tables:
        cursor.execute(f"SELECT * FROM {t}")
        data[t] = [dict(row) for row in cursor.fetchall()]
ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
with open(f"{BACKUP_DIR}/pos_mobile_backup_{ts}.json", "w", encoding="utf-8") as f:
    json.dump({"timestamp": ts, "version": "1.0.0", "data": data}, f, ensure_ascii=False, indent=2)
print(f"Backup saved to {BACKUP_DIR}/pos_mobile_backup_{ts}.json")
