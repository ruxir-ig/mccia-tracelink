import sqlite3
from app.db import DB_PATH
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
print('Complaints matching LOT-2024-088:')
c = conn.execute("SELECT root_cause_identified, financial_impact_inr FROM complaints WHERE root_cause_identified LIKE '%LOT-2024-088%'").fetchall()
print([dict(x) for x in c])

print('Affected dispatch batches for LOT-2024-088:')
rows = conn.execute("""
SELECT d.*, db.batch_id, q.pass_fail, q.inspection_date
FROM dispatch_batches db
JOIN dispatch_orders d ON d.order_id = db.order_id
LEFT JOIN qc_inspections q ON q.batch_id = db.batch_id
JOIN production_batches p ON p.batch_id = db.batch_id
WHERE p.input_lot_ref = 'LOT-2024-088'
""").fetchall()
print([dict(x) for x in rows])
