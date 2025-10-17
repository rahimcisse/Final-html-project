import sqlite3
import os
DB='applications.db'
if not os.path.exists(DB):
    print('applications.db not found, creating new DB')
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    applicant_name TEXT NOT NULL,
                    applicant_email TEXT NOT NULL,
                    cover_letter TEXT,
                    resume_text TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()

conn=sqlite3.connect(DB)
c=conn.cursor()
# helper to check column
c.execute("PRAGMA table_info(applications)")
cols=[r[1] for r in c.fetchall()]
print('Existing columns:', cols)
if 'resume_path' not in cols:
    try:
        c.execute("ALTER TABLE applications ADD COLUMN resume_path TEXT")
        print('Added column resume_path')
    except Exception as e:
        print('Failed to add resume_path:', e)
if 'client_id' not in cols:
    try:
        c.execute("ALTER TABLE applications ADD COLUMN client_id INTEGER")
        print('Added column client_id')
    except Exception as e:
        print('Failed to add client_id:', e)
conn.commit()
conn.close()
print('Migration complete')
