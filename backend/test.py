import sqlite3
from app.db import DB_PATH
conn = sqlite3.connect(DB_PATH)
c = conn.execute("SELECT batch_id, production_date FROM production_batches WHERE input_lot_ref = 'LOT-2024-088' AND machine_id = 'MC-04'").fetchall()
print(c)
