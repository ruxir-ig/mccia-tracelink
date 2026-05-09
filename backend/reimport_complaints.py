import sqlite3
from app.api.import_routes import validate_csv_content
from app.pipeline import process_domain_import
from app.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Re-import complaints
with open('../defect_complaints.csv', 'r') as f:
    content = f.read()
valid_rows, errors = validate_csv_content(content, 'complaints')
print(f"Complaints: {len(valid_rows)} valid, {len(errors)} errors")
conn.execute("DELETE FROM complaints")
stats = process_domain_import(conn, 'complaints', valid_rows)
conn.commit()

# Verify
rows = conn.execute("SELECT complaint_id, root_cause_identified, financial_impact_inr, affected_order_ids FROM complaints").fetchall()
for r in rows:
    print(dict(r))

conn.close()
