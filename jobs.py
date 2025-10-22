# new animated signup
# Extend Flask backend to support search functionality
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
import sqlite3
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_cors import CORS
import random
import smtplib
from email.message import EmailMessage
import os
app = Flask(__name__)

@app.route("/")
@app.route("/landing")
def landing():
    return render_template('landing.html')

@app.route("/index")
def index():
    return render_template('index.html')

# Client Dashboard route
@app.route('/client-dashboard')
def client_dashboard():
    if 'user_id' not in session:
        return redirect('/login_page')
    return render_template('client_dashboard.html')

@app.route("/clients")
def clients():
    return render_template('Clients-Browse-Page.html')



@app.route('/browse')
def browse():
    return render_template('Job-Browse-Page.html')



@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/how_it_works')
def how_it_works():
    return render_template('how_it_works.html')

@app.route('/addworker')
def addworker():
    return render_template('addJob.html')

@app.route('/addClient')
def addClient():
    return render_template('addClient.html')

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/account')
def account():
    return render_template('account.html')

@app.route('/debug')
def debug_page():
    return render_template('debug.html')

def init_workers_db():
    conn = sqlite3.connect('workers.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    location TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    description TEXT
                )''')
    conn.commit()
    conn.close()

init_workers_db()

@app.route('/api/workers', methods=['GET'])
def get_workers():
    query = request.args.get('q', '').strip()
    conn = sqlite3.connect('workers.db')
    c = conn.cursor()
    if query:
        c.execute('''SELECT * FROM workers WHERE 
                        title LIKE ? OR 
                        location LIKE ? OR 
                        job_type LIKE ? OR 
                        description LIKE ?''',
                  tuple([f"%{query}%"] * 4))
    else:
        c.execute('SELECT * FROM workers')
    workers = [dict(id=row[0], title=row[1], location=row[2],
                 job_type=row[3], description=row[4])
            for row in c.fetchall()]
    conn.close()
    return jsonify(workers)

@app.route('/api/workers', methods=['POST'])
def add_worker():
    data = request.get_json()
    conn = sqlite3.connect('workers.db')
    c = conn.cursor()
    c.execute('''INSERT INTO workers (title, location, job_type, description)
                 VALUES (?, ?, ?, ? )''',
              (data['title'], data['location'],
               data['job_type'], data['description']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'}), 201

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    query = request.args.get('q', '').strip()
    user_id = session.get('user_id')
    
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    
    # Get all active (non-deleted) jobs
    if query:
        database.execute('''SELECT * FROM jobs WHERE 
                        (title LIKE ? OR 
                        location LIKE ? OR 
                        job_type LIKE ? OR 
                        description LIKE ? OR 
                        company_email LIKE ? OR 
                        salary LIKE ? OR 
                        duration LIKE ? OR 
                        experience LIKE ?) AND 
                        (deleted IS NULL OR deleted = 0)''',
                  tuple([f"%{query}%"] * 8))
    else:
        database.execute('SELECT * FROM jobs WHERE deleted IS NULL OR deleted = 0')
    
    active_jobs = database.fetchall()
    
    # If user is logged in, also get deleted jobs they have applied to
    user_applied_deleted_jobs = []
    if user_id:
        # Get job IDs the user has applied to
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        c.execute('SELECT DISTINCT job_id FROM applications WHERE user_id = ?', (user_id,))
        applied_job_ids = [row[0] for row in c.fetchall()]
        conn.close()
        
        if applied_job_ids:
            # Get deleted jobs from the applied list
            placeholders = ','.join(['?'] * len(applied_job_ids))
            if query:
                database.execute(f'''SELECT * FROM jobs WHERE 
                                id IN ({placeholders}) AND deleted = 1 AND
                                (title LIKE ? OR 
                                location LIKE ? OR 
                                job_type LIKE ? OR 
                                description LIKE ? OR 
                                company_email LIKE ? OR 
                                salary LIKE ? OR 
                                duration LIKE ? OR 
                                experience LIKE ?)''',
                          applied_job_ids + [f"%{query}%"] * 8)
            else:
                database.execute(f'SELECT * FROM jobs WHERE id IN ({placeholders}) AND deleted = 1', applied_job_ids)
            
            user_applied_deleted_jobs = database.fetchall()
    
    mydatabase.close()
    
    # Combine active jobs and user's applied deleted jobs
    all_jobs = active_jobs + user_applied_deleted_jobs
    
    jobs = []
    for row in all_jobs:
        job = dict(id=row[0], title=row[1], company_email=row[2], location=row[3], 
                  salary=row[4], duration=row[5], experience=row[6], 
                  job_type=row[7], description=row[8])
        # Add optional company fields safely
        try:
            job['company_name'] = row[9] if len(row) > 9 else ''
            job['company_description'] = row[10] if len(row) > 10 else ''
            job['company_website'] = row[11] if len(row) > 11 else ''
            job['posted_by_user_id'] = row[12] if len(row) > 12 else None
            job['deleted'] = row[13] if len(row) > 13 else 0
        except Exception:
            job['company_name'] = ''
            job['company_description'] = ''
            job['company_website'] = ''
            job['posted_by_user_id'] = None
            job['deleted'] = 0
        
        # Add status information
        if job['deleted'] == 1:
            job['status'] = 'unavailable'
            job['status_message'] = 'This job is no longer available'
        else:
            job['status'] = 'available'
            job['status_message'] = 'Open for applications'
        
        jobs.append(job)
    
    return jsonify(jobs)

@app.route('/api/jobs', methods=['POST'])
def add_job():
    data = request.get_json()
    user_id = session.get('user_id')  # Get logged-in user
    
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    database.execute('''INSERT INTO jobs (title, company_email, location, salary, duration, experience, job_type, description, company_name, company_description, company_website, posted_by_user_id)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (data['title'], data.get('company_email', ''), data['location'], 
               data.get('salary', ''), data.get('duration', ''), data.get('experience', ''),
               data['job_type'], data['description'],
               data.get('company_name', ''), data.get('company_description', ''), 
               data.get('company_website', ''), user_id))
    mydatabase.commit()
    mydatabase.close()
    return jsonify({'status': 'success'}), 201


# GET job details by id
@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    database.execute('SELECT * FROM jobs WHERE id = ? AND (deleted IS NULL OR deleted = 0)', (job_id,))
    row = database.fetchone()
    mydatabase.close()
    if not row:
        return jsonify({'error': 'Job not found'}), 404
    
    # Map columns: id, title, company_email, location, salary, duration, experience, job_type, description, then optional company fields
    job = dict(id=row[0], title=row[1], company_email=row[2], location=row[3], 
              salary=row[4], duration=row[5], experience=row[6], job_type=row[7], description=row[8])
    
    # Add optional company fields safely
    try:
        job['company_name'] = row[9] if len(row) > 9 else ''
        job['company_description'] = row[10] if len(row) > 10 else ''
        job['company_website'] = row[11] if len(row) > 11 else ''
        job['posted_by_user_id'] = row[12] if len(row) > 12 else None
    except Exception:
        job['company_name'] = ''
        job['company_description'] = ''
        job['company_website'] = ''
        job['posted_by_user_id'] = None

    return jsonify(job)


# Applications DB init
def init_applications_db():
    try:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS applications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id INTEGER NOT NULL,
                        applicant_name TEXT NOT NULL,
                        applicant_email TEXT NOT NULL,
                        cover_letter TEXT,
                        resume_text TEXT,
                        resume_path TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')
        conn.commit()
        conn.close()
        print("Applications table initialized successfully")
        
        # ensure client_id column exists for client-posting applications
        try:
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('ALTER TABLE applications ADD COLUMN client_id INTEGER')
            conn.commit()
            print("Client_id column added successfully")
        except Exception as e:
            # column probably already exists
            print(f"Client_id column may already exist: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
        
        # Add user_id column to track which user applied
        try:
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('ALTER TABLE applications ADD COLUMN user_id INTEGER')
            conn.commit()
            print("User_id column added successfully")
        except Exception as e:
            # column probably already exists
            print(f"User_id column may already exist: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        print(f"Error initializing applications database: {e}")

init_applications_db()


# Endpoint to submit application for a job
@app.route('/api/jobs/<int:job_id>/apply', methods=['POST'])
def apply_job(job_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Must be logged in to apply'}), 401
    
    # Check if user has already applied to this job
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT id FROM applications WHERE job_id = ? AND user_id = ?', (job_id, user_id))
    existing_application = c.fetchone()
    conn.close()
    
    if existing_application:
        return jsonify({'error': 'You have already applied to this job'}), 400
    
    # Support JSON or multipart/form-data with file upload
    name = None
    email = None
    cover_letter = ''
    resume_text = ''
    resume_path = None

    if request.content_type and request.content_type.startswith('application/json'):
        data = request.get_json() or {}
        name = data.get('name')
        email = data.get('email')
        cover_letter = data.get('cover_letter', '')
        resume_text = data.get('resume', '')
    else:
        # multipart/form-data
        name = request.form.get('name')
        email = request.form.get('email')
        cover_letter = request.form.get('cover_letter', '')
        # handle file
        file = request.files.get('resume')
        if file and file.filename:
            filename = secure_filename(file.filename)
            # ensure upload folder exists
            upload_folder = os.path.join(os.getcwd(), 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            save_path = os.path.join(upload_folder, f"{int(datetime.utcnow().timestamp())}_{filename}")
            file.save(save_path)
            # store relative path to serve
            resume_path = os.path.basename(save_path)

    if not name or not email:
        return jsonify({'error': 'Name and email are required'}), 400

    # Check job exists and is not deleted
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    database.execute('SELECT id FROM jobs WHERE id = ? AND (deleted IS NULL OR deleted = 0)', (job_id,))
    if not database.fetchone():
        mydatabase.close()
        return jsonify({'error': 'Job not found or no longer available'}), 404
    mydatabase.close()

    # Save application with user_id
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('''INSERT INTO applications (job_id, applicant_name, applicant_email, cover_letter, resume_text, resume_path, user_id)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''', (job_id, name, email, cover_letter, resume_text, resume_path, user_id))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Application submitted successfully'})


# Check if current user has already applied to a job
@app.route('/api/jobs/<int:job_id>/check-application', methods=['GET'])
def check_user_application(job_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'applied': False, 'message': 'Not logged in'})
    
    # Check if user has already applied to this job
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT id FROM applications WHERE job_id = ? AND user_id = ?', (job_id, user_id))
    existing_application = c.fetchone()
    conn.close()
    
    return jsonify({
        'applied': existing_application is not None,
        'message': 'Already applied' if existing_application else 'Can apply'
    })


# Delete application for a specific job by the logged-in user
@app.route('/api/jobs/<int:job_id>/application', methods=['DELETE'])
def delete_application(job_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Must be logged in'}), 401
    
    # Check if user has an application for this job
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT id FROM applications WHERE job_id = ? AND user_id = ?', (job_id, user_id))
    application = c.fetchone()
    
    if not application:
        conn.close()
        return jsonify({'error': 'Application not found'}), 404
    
    # Delete the application
    c.execute('DELETE FROM applications WHERE job_id = ? AND user_id = ?', (job_id, user_id))
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': 'Application deleted successfully',
        'job_id': job_id
    })


# Get all jobs that the current user has applied to (including deleted ones)
@app.route('/api/my-applications', methods=['GET'])
def get_my_applications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Get all job IDs that the user has applied to
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT job_id, created_at FROM applications WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    applied_jobs = c.fetchall()
    conn.close()
    
    if not applied_jobs:
        return jsonify([])
    
    # Get job details for all applied jobs (including deleted ones)
    job_ids = [str(job[0]) for job in applied_jobs]
    placeholders = ','.join(['?'] * len(job_ids))
    
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    database.execute(f'SELECT * FROM jobs WHERE id IN ({placeholders})', job_ids)
    jobs_data = database.fetchall()
    mydatabase.close()
    
    # Create a lookup for application dates
    application_dates = {job[0]: job[1] for job in applied_jobs}
    
    jobs = []
    for row in jobs_data:
        job = dict(id=row[0], title=row[1], company_email=row[2], location=row[3], 
                  salary=row[4], duration=row[5], experience=row[6], 
                  job_type=row[7], description=row[8])
        
        # Add optional company fields safely
        try:
            job['company_name'] = row[9] if len(row) > 9 else ''
            job['company_description'] = row[10] if len(row) > 10 else ''
            job['company_website'] = row[11] if len(row) > 11 else ''
            job['posted_by_user_id'] = row[12] if len(row) > 12 else None
            job['deleted'] = row[13] if len(row) > 13 else 0
        except Exception:
            job['company_name'] = ''
            job['company_description'] = ''
            job['company_website'] = ''
            job['posted_by_user_id'] = None
            job['deleted'] = 0
        
        # Add application status information
        job['applied_at'] = application_dates.get(job['id'], '')
        job['status'] = 'unavailable' if job['deleted'] == 1 else 'available'
        job['already_applied'] = True
        
        jobs.append(job)
    
    return jsonify(jobs)


@app.route('/api/jobs/<int:job_id>/applications', methods=['GET'])
def list_applications(job_id):
    # Return all applications for a given job
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT id, applicant_name, applicant_email, cover_letter, resume_path, created_at FROM applications WHERE job_id = ? ORDER BY created_at DESC', (job_id,))
    rows = c.fetchall()
    conn.close()
    apps = []
    for r in rows:
        apps.append({
            'id': r[0],
            'applicant_name': r[1],
            'applicant_email': r[2],
            'cover_letter': r[3],
            'resume_path': r[4],
            'created_at': r[5]
        })
    return jsonify(apps)

# New route: Get jobs posted by the logged-in user
@app.route('/api/my-jobs', methods=['GET'])
def get_my_jobs():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    database.execute('SELECT * FROM jobs WHERE posted_by_user_id = ? AND (deleted IS NULL OR deleted = 0) ORDER BY id DESC', (user_id,))
    rows = database.fetchall()
    mydatabase.close()
    
    jobs = []
    for row in rows:
        job = {
            'id': row[0],
            'title': row[1],
            'company_email': row[2],
            'location': row[3],
            'salary': row[4],
            'duration': row[5],
            'experience': row[6],
            'job_type': row[7],
            'description': row[8]
        }
        # Add optional company fields safely
        try:
            job['company_name'] = row[9] if len(row) > 9 else ''
            job['company_description'] = row[10] if len(row) > 10 else ''
            job['company_website'] = row[11] if len(row) > 11 else ''
        except Exception:
            job['company_name'] = ''
            job['company_description'] = ''
            job['company_website'] = ''
        jobs.append(job)
    
    return jsonify(jobs)

# Enhanced route: Get applications for jobs posted by logged-in user with authorization
@app.route('/api/my-jobs/<int:job_id>/applications', methods=['GET'])
def get_my_job_applications(job_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    # First check if this job belongs to the logged-in user and is not deleted
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    database.execute('SELECT id, title FROM jobs WHERE id = ? AND posted_by_user_id = ? AND (deleted IS NULL OR deleted = 0)', (job_id, user_id))
    job = database.fetchone()
    mydatabase.close()
    
    if not job:
        return jsonify({'error': 'Job not found or not authorized'}), 404
    
    # Get applications for this job
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT id, applicant_name, applicant_email, cover_letter, resume_path, created_at FROM applications WHERE job_id = ? ORDER BY created_at DESC', (job_id,))
    rows = c.fetchall()
    conn.close()
    
    applications = []
    for r in rows:
        applications.append({
            'id': r[0],
            'applicant_name': r[1],
            'applicant_email': r[2],
            'cover_letter': r[3],
            'resume_path': r[4],
            'created_at': r[5]
        })
    
    return jsonify({
        'job_title': job[1],
        'job_id': job_id,
        'applications': applications
    })

# Delete job and all its applications
@app.route('/api/my-jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    # First check if this job belongs to the logged-in user
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    database.execute('SELECT id, title, deleted FROM jobs WHERE id = ? AND posted_by_user_id = ?', (job_id, user_id))
    job = database.fetchone()
    
    if not job:
        mydatabase.close()
        return jsonify({'error': 'Job not found or not authorized'}), 404
    
    # Check if job is already deleted
    if job[2] == 1:  # deleted column value
        mydatabase.close()
        return jsonify({'error': 'Job is already deleted'}), 400
    
    job_title = job[1]
    
    # Count applications for this job (for information purposes)
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM applications WHERE job_id = ?', (job_id,))
    applications_count = c.fetchone()[0]
    conn.close()
    
    # Mark the job as deleted instead of actually deleting it
    database.execute('UPDATE jobs SET deleted = 1 WHERE id = ?', (job_id,))
    mydatabase.commit()
    mydatabase.close()
    
    return jsonify({
        'message': f'Job "{job_title}" has been marked as deleted. {applications_count} applications are preserved.',
        'deleted_job_id': job_id,
        'applications_count': applications_count,
        'note': 'Job data and applications are preserved in the database but hidden from public view'
    })


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    upload_folder = os.path.join(os.getcwd(), 'uploads')
    return send_from_directory(upload_folder, filename, as_attachment=True)


@app.route('/applications')
def applications_page():
    # Simple employer-facing page to view applications
    if 'user_id' not in session:
        # allow access for now; in real app restrict to employers
        pass
    return render_template('applications.html')

@app.route('/my-applications')
def my_applications_page():
    # Page for job seekers to view their application history
    if 'user_id' not in session:
        return redirect('/login_page')
    return render_template('my_applications.html')


def init_db2():
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()

    database.execute('''CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company_email TEXT NOT NULL,
                    location TEXT NOT NULL,
                    salary TEXT NOT NULL,
                    duration TEXT NOT NULL,
                    experience TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    description TEXT
                )''')
    mydatabase.commit()
    
    # Add missing fields from jobs.db if they don't exist (safe ALTER TABLE)
    try:
        database.execute("ALTER TABLE jobs ADD COLUMN company_name TEXT")
    except Exception:
        pass
    try:
        database.execute("ALTER TABLE jobs ADD COLUMN company_description TEXT")
    except Exception:
        pass
    try:
        database.execute("ALTER TABLE jobs ADD COLUMN company_website TEXT")
    except Exception:
        pass
    try:
        database.execute("ALTER TABLE jobs ADD COLUMN posted_by_user_id INTEGER")
    except Exception:
        pass
    try:
        database.execute("ALTER TABLE jobs ADD COLUMN deleted INTEGER DEFAULT 0")
    except Exception:
        pass
    
    mydatabase.commit()
    mydatabase.close()
init_db2()

# Note: /api/clients GET functionality is handled by /api/jobs GET endpoint
# Note: /api/clients/<id> GET functionality is handled by /api/jobs/<id> GET endpoint
# Note: /api/clients/<id>/apply POST functionality is handled by /api/jobs/<id>/apply POST endpoint
# All use the same clients.db database, so no duplication needed

# Removed client-specific applications route since we use unified database now
# Use /api/jobs/<job_id>/applications instead

# Note: /api/clients POST functionality is handled by /api/jobs POST endpoint
# Both use the same clients.db database, so no duplication needed

CORS(app)  # Enable CORS for frontend access

# Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iconnect_users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    role = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Routes
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    role = data.get('role')
    password = data.get('password')

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    new_user = User(name=name, email=email, role=role, created_at=datetime.utcnow())
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Signup successful'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        session['user_id'] = user.id  # Store user ID in session
        return jsonify({'message': 'Login successful'})
    else:
        return jsonify({'error': 'Invalid email or password'}), 401
    
app.config['SECRET_KEY'] = '12345678'
@app.route('/get_user', methods=['GET'])
def get_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'full_name': user.name,
        'email': user.email,
        'role': user.role,

        # 'phone': user.phone,
        'created_at': user.created_at.strftime('%B %d, %Y')  # Format the date
    })

@app.route('/update_password', methods=['POST'])
def update_password():
    # Get user from session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    # Validate input
    if not all([current_password, new_password, confirm_password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Password validation
    if new_password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400
    
    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    # Verify current password
    if not user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    # Update password (Werkzeug handles hashing automatically)
    user.set_password(new_password)  # Uses generate_password_hash internally
    db.session.commit()
    
    return jsonify({'message': 'Password updated successfully'}), 200

EMAIL_ADDRESS = 'abdulrahimmogtaricisse@gmail.com'
EMAIL_PASSWORD = 'nshb szsc saaa tzio'


@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    session['otp'] = otp
    session['email'] = email

    try:
        msg = EmailMessage()
        msg['Subject'] = "OTPVerification - ICONNECT"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg.set_content(f"Thank you for signing up! To verify your email address and complete the sign-up process, please enter the following one-time password (OTP) on our website: {otp}")

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        return jsonify({'message': 'OTP sent successfully'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    entered_otp = data.get('otp')

    if entered_otp == session.get('otp'):
        return jsonify({'message': 'OTP verified successfully'})
    else:
        return jsonify({'error': 'Invalid OTP'}), 400

@app.route('/get_profile', methods=['GET'])
def get_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'full_name': user.name,
        'email': user.email,
        'role': user.role,
        'phone': user.phone if hasattr(user, 'phone') else '',
        'created_at': user.created_at.strftime('%B %d, %Y')
    })
@app.route('/update_profile', methods=['POST'])
def update_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    full_name = data.get('full_name')
    email = data.get('email')
    role = data.get('role')
    phone = data.get('phone')
    
    # Validate input
    if not full_name or not email:
        return jsonify({'error': 'Name and email are required'}), 400
    
    # Check if email is already taken by another user
    existing_user = User.query.filter(User.email == email, User.id != user_id).first()
    if existing_user:
        return jsonify({'error': 'Email already in use'}), 400
    
    # Update user information
    user.name = full_name
    user.email = email
    
    user.role = role
    if phone:
        user.phone = phone
    
    db.session.commit()
    
    return jsonify({'message': 'Profile updated successfully'})

# New route to update profile details
@app.route('/api/update_profile_details', methods=['POST'])
def update_profile_details():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    phone = data.get('phone')
    gender = data.get('gender')
    location = data.get('location')
    
    # Update user information
    user.phone = phone
    user.gender = gender
    user.location = location
    
    db.session.commit()
    
    return jsonify({'message': 'Profile details updated successfully'})

# New route for the details page
@app.route('/details')
def details():
    if 'user_id' not in session:
        return redirect('/login_page')
    return render_template('details.html')


# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login_page')
    return render_template('dashboard.html')



# Debug routes to check data
@app.route('/debug/jobs')
def debug_jobs():
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    database.execute('SELECT * FROM jobs')
    jobs = database.fetchall()
    mydatabase.close()
    return jsonify([{
        'id': job[0], 
        'title': job[1], 
        'posted_by_user_id': job[12] if len(job) > 12 else 'NULL',
        'deleted': job[13] if len(job) > 13 else 'NULL',
        'status': 'DELETED' if (len(job) > 13 and job[13] == 1) else 'ACTIVE',
        'all_fields': job
    } for job in jobs])

@app.route('/debug/applications')
def debug_applications():
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT * FROM applications')
    apps = c.fetchall()
    conn.close()
    return jsonify([{
        'id': app[0],
        'job_id': app[1],
        'applicant_name': app[2],
        'applicant_email': app[3],
        'user_id': app[8] if len(app) > 8 else 'NULL',
        'all_fields': app
    } for app in apps])

@app.route('/debug/my-data')
def debug_my_data():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Get my jobs (including deleted ones for debug purposes)
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    database.execute('SELECT * FROM jobs WHERE posted_by_user_id = ?', (user_id,))
    my_jobs = database.fetchall()
    mydatabase.close()
    
    # Get all applications for my jobs
    job_ids = [job[0] for job in my_jobs]
    apps_data = []
    if job_ids:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        placeholders = ','.join(['?'] * len(job_ids))
        c.execute(f'SELECT * FROM applications WHERE job_id IN ({placeholders})', job_ids)
        apps_data = c.fetchall()
        conn.close()
    
    return jsonify({
        'user_id': user_id,
        'my_jobs': [{
            'id': job[0], 
            'title': job[1], 
            'posted_by_user_id': job[12] if len(job) > 12 else 'NULL',
            'deleted': job[13] if len(job) > 13 else 'NULL',
            'status': 'DELETED' if (len(job) > 13 and job[13] == 1) else 'ACTIVE'
        } for job in my_jobs],
        'applications_for_my_jobs': [{'id': app[0], 'job_id': app[1], 'applicant_name': app[2]} for app in apps_data]
    })

# Debug route to view only deleted jobs
@app.route('/debug/deleted-jobs')
def debug_deleted_jobs():
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    database.execute('SELECT * FROM jobs WHERE deleted = 1')
    jobs = database.fetchall()
    mydatabase.close()
    return jsonify([{
        'id': job[0], 
        'title': job[1], 
        'company_email': job[2],
        'location': job[3],
        'posted_by_user_id': job[12] if len(job) > 12 else 'NULL',
        'deleted': job[13] if len(job) > 13 else 'NULL',
        'status': 'DELETED'
    } for job in jobs])

# Migration route to fix existing jobs without posted_by_user_id
@app.route('/migrate/fix-job-ownership')
def migrate_job_ownership():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    mydatabase = sqlite3.connect('clients.db')
    database = mydatabase.cursor()
    
    # Get jobs with NULL posted_by_user_id
    database.execute('SELECT id, title FROM jobs WHERE posted_by_user_id IS NULL OR posted_by_user_id = ""')
    orphan_jobs = database.fetchall()
    
    if orphan_jobs:
        # Update all orphan jobs to belong to current user (for testing)
        job_ids = [job[0] for job in orphan_jobs]
        placeholders = ','.join(['?'] * len(job_ids))
        database.execute(f'UPDATE jobs SET posted_by_user_id = ? WHERE id IN ({placeholders})', [user_id] + job_ids)
        mydatabase.commit()
    
    mydatabase.close()
    
    return jsonify({
        'message': f'Updated {len(orphan_jobs)} orphan jobs to belong to user {user_id}',
        'updated_jobs': [{'id': job[0], 'title': job[1]} for job in orphan_jobs]
    })

# Fix applications route - migrate client applications to job applications
@app.route('/migrate/fix-applications')
def migrate_applications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    
    # Get applications with job_id = 0 (client applications)
    c.execute('SELECT id, client_id, applicant_name FROM applications WHERE job_id = 0')
    client_apps = c.fetchall()
    
    updated_apps = []
    for app in client_apps:
        app_id, client_id, applicant_name = app
        
        # Try to find corresponding job in clients.db
        # Look for jobs that might correspond to this client
        job_conn = sqlite3.connect('clients.db')
        job_c = job_conn.cursor()
        job_c.execute('SELECT id FROM jobs WHERE id = ?', (client_id,))
        corresponding_job = job_c.fetchone()
        job_conn.close()
        
        if corresponding_job:
            # Update the application to use the job_id instead of client_id
            c.execute('UPDATE applications SET job_id = ?, client_id = NULL WHERE id = ?', 
                     (corresponding_job[0], app_id))
            updated_apps.append({
                'app_id': app_id,
                'applicant': applicant_name,
                'old_client_id': client_id,
                'new_job_id': corresponding_job[0]
            })
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': f'Updated {len(updated_apps)} applications to use job IDs',
        'updated_applications': updated_apps
    })

def init_db3():
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            userType TEXT,
            category TEXT,
            subject TEXT,
            message TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db3()

@app.route('/help', methods=['GET'])
def help_page():
    return render_template('help.html')




def send_email(subject, body, to_email):
    # Configure your SMTP server and credentials
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_user = EMAIL_ADDRESS      # Replace with your email
    smtp_password = EMAIL_PASSWORD     # Use an app password, not your main password

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

@app.route('/submit_message', methods=['POST'])
def submit_message():
    data = request.json
    # ...save to database as before...

    # Prepare email content
    subject = f"New Contact Message from {data['name']}"
    body = f"""
    Name: {data['name']}
    Email: {data['email']}
    User Type: {data['userType']}
    Category: {data['category']}
    Subject: {data['subject']}
    Message: {data['message']}
    """
    send_email(subject, body, EMAIL_ADDRESS)  # Replace with your email

    return jsonify({'status': 'success'})

# ...existing code...

import string
from email.mime.text import MIMEText
# Store OTPs in memory for demo (use a DB or cache in production)
otp_store = {}

@app.route('/send-forgot-otp', methods=['POST'])
def send_forgot_otp():
    data = request.get_json()
    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'error': 'Email not registered'}), 404

    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    otp_store[email] = otp

    try:
        msg = EmailMessage()
        msg['Subject'] = "Password Reset OTP - ICONNECT"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg.set_content(f"Your password reset OTP is: {otp}")

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        return jsonify({'message': 'OTP sent successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    new_password = data.get('newPassword')

    if not all([email, otp, new_password]):
        return jsonify({'error': 'Missing fields'}), 400

    if otp_store.get(email) != otp:
        return jsonify({'error': 'Invalid OTP'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.set_password(new_password)
    db.session.commit()
    otp_store.pop(email, None)
    return jsonify({'message': 'Password reset successful'})



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)


