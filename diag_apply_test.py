import sqlite3, requests, os, sys
base='http://127.0.0.1:5000'
print('Checking server /api/jobs...')
try:
    r = requests.get(base + '/api/jobs', timeout=5)
    print('/api/jobs status', r.status_code)
except Exception as e:
    print('Error reaching server:', e)
    sys.exit(0)

# List jobs from DB
print('\nReading jobs from clients.db...')
if not os.path.exists('clients.db'):
    print('clients.db not found')
else:
    conn = sqlite3.connect('clients.db')
    c = conn.cursor()
    c.execute('SELECT id, title FROM jobs ORDER BY id')
    rows = c.fetchall()
    if not rows:
        print('No jobs found in DB')
        conn.close()
    else:
        for r in rows:
            print('job', r[0], r[1])
        job_id = rows[-1][0]
        conn.close()
        print('\nAttempting to POST an application to job id', job_id)
        # create a small temp resume file
        fname = 'temp_resume.txt'
        with open(fname, 'w', encoding='utf-8') as f:
            f.write('Resume content')
        files = {'resume': (fname, open(fname, 'rb'), 'text/plain')}
        data = {'name':'Diag Tester','email':'diag@example.com','cover_letter':'Testing upload'}
        try:
            resp = requests.post(f'{base}/api/jobs/{job_id}/apply', data=data, files=files, timeout=10)
            print('POST apply status', resp.status_code)
            try:
                print('Response JSON:', resp.json())
            except Exception:
                print('Response text:', resp.text)
        except Exception as e:
            print('Error posting application:', e)
        finally:
            try:
                files['resume'][1].close()
            except:
                pass
            try:
                os.remove(fname)
            except:
                pass

print('\nDone')
