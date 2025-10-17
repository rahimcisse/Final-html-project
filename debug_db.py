import sqlite3

def debug_databases():
    print("=== DEBUG: Checking databases ===")
    
    # Check jobs.db (now integrated into clients.db)
    print("\n--- JOBS (from clients.db) ---")
    conn = sqlite3.connect('clients.db')
    c = conn.cursor()
    c.execute('SELECT * FROM jobs')
    jobs = c.fetchall()
    conn.close()
    
    for job in jobs:
        print(f"Job ID: {job[0]}, Title: {job[1]}, Posted by user: {job[12] if len(job) > 12 else 'NULL'}")
    
    # Check applications.db
    print("\n--- APPLICATIONS.DB ---")
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT * FROM applications')
    apps = c.fetchall()
    conn.close()
    
    for app in apps:
        print(f"App ID: {app[0]}, Job ID: {app[1]}, Applicant: {app[2]}, Client ID: {app[8] if len(app) > 8 else 'NULL'}")
    
    # Check clients.db
    print("\n--- CLIENTS.DB ---")
    conn = sqlite3.connect('clients.db')
    c = conn.cursor()
    c.execute('SELECT * FROM jobs')
    clients = c.fetchall()
    conn.close()
    
    for client in clients:
        print(f"Client Job ID: {client[0]}, Title: {client[1]}")
    
    print("\n=== END DEBUG ===")

if __name__ == "__main__":
    debug_databases()