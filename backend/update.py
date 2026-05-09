import sqlite3
conn = sqlite3.connect('tracelink.sqlite3')
# Demote the old default admin
conn.execute("UPDATE users SET role='operator' WHERE email='admin@tracelink.local'")
# Ensure harshjain0621 is the sole admin
conn.execute("UPDATE users SET role='admin' WHERE email='harshjain0621@gmail.com'")
conn.commit()
rows = conn.execute("SELECT email, role FROM users").fetchall()
for r in rows:
    print(r)
conn.close()
