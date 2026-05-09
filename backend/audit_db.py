import sqlite3
from app.db import DB_PATH
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print([t[0] for t in tables])
for t in tables:
    try:
        n = conn.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
        print(t[0], n)
    except: pass

# check dispatch_batches schema
print("\n--- dispatch_batches ---")
try:
    rows = conn.execute("SELECT * FROM dispatch_batches LIMIT 3").fetchall()
    for r in rows:
        print(dict(r))
except Exception as e:
    print("ERROR:", e)

# check complaints schema
print("\n--- complaints sample ---")
try:
    rows = conn.execute("SELECT * FROM complaints LIMIT 3").fetchall()
    for r in rows:
        print(dict(r))
except Exception as e:
    print("ERROR:", e)
