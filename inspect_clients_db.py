import sqlite3, os
p='clients.db'
if not os.path.exists(p):
    print('clients.db not found')
else:
    conn=sqlite3.connect(p)
    c=conn.cursor()
    c.execute("PRAGMA table_info(jobs)")
    cols=c.fetchall()
    print('columns:')
    for col in cols:
        print(col)
    c.execute('SELECT * FROM jobs LIMIT 5')
    rows=c.fetchall()
    print('\nrows:')
    for r in rows:
        print(r)
    conn.close()
