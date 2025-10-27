# new animated signup
# Extend Flask backend to support search functionality
from flask import Flask, request, jsonify, render_template, redirect, url_for,session
import sqlite3
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import random
import smtplib
from email.message import EmailMessage
app = Flask(__name__)

@app.route("/")
@app.route("/landing")
def landing():
    return render_template('landing.html')

@app.route("/index")
def index():
    # Check if user is logged in and has completed profile
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and not user.profile_completed:
            # Redirect to additional info page if profile is not completed
            return redirect('/additional-info')
    return render_template('index.html')

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

@app.route('/addJob')
def addJob():
    return render_template('addJob.html')
@app.route('/account')
def account():
    return render_template('account.html')

def init_db():
    conn = sqlite3.connect('clients.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
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
    conn.commit()
    conn.close()


@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    query = request.args.get('q', '').strip()
    conn = sqlite3.connect('clients.db')
    c = conn.cursor()
    if query:
        c.execute('''SELECT * FROM jobs WHERE 
                        title LIKE ? OR 
                        company_email LIKE ? OR 
                        location LIKE ? OR 
                        salary LIKE ? OR 
                        duration LIKE ? OR 
                        experience LIKE ? OR 
                        job_type LIKE ? OR 
                        description LIKE ?''',
                  tuple([f"%{query}%"] * 8))
    else:
        c.execute('SELECT * FROM jobs')
    jobs = [dict(id=row[0], title=row[1], company_email=row[2], location=row[3],
                 salary=row[4], duration=row[5], experience=row[6], 
                 job_type=row[7], description=row[8])
            for row in c.fetchall()]
    conn.close()
    return jsonify(jobs)

@app.route('/api/jobs', methods=['POST'])
def add_job():
    data = request.get_json()
    conn = sqlite3.connect('clients.db')
    c = conn.cursor()
    c.execute('''INSERT INTO jobs (title, company_email, location, salary, duration, experience, job_type, description)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (data['title'], data.get('company_email', ''), data['location'],
               data.get('salary', ''), data.get('duration', ''), data.get('experience', ''),
               data['job_type'], data['description']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'}), 201



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
    role = db.Column(db.String(150), nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    profile_completed = db.Column(db.Boolean, default=False, nullable=False)
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
    
    # Store user ID in session after successful signup
    session['user_id'] = new_user.id

    return jsonify({'message': 'Signup successful', 'redirect': '/additional-info'})

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
        'role': user.role or '',
        'phone': user.phone or '',
        'date_of_birth': user.date_of_birth.strftime('%Y-%m-%d') if user.date_of_birth else '',
        'gender': user.gender or '',
        'location': user.location or '',
        'profile_completed': user.profile_completed,
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
    date_of_birth = data.get('date_of_birth')
    gender = data.get('gender')
    location = data.get('location')
    
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
    
    if role:
        user.role = role
    if phone:
        user.phone = phone
    if date_of_birth:
        try:
            user.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    if gender:
        user.gender = gender
    if location:
        user.location = location
    
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

# New route for the additional info page
@app.route('/additional-info')
def additional_info():
    if 'user_id' not in session:
        return redirect('/login_page')
    
    # Check if user has already completed their profile
    user = User.query.get(session['user_id'])
    if user and user.profile_completed:
        return redirect('/index')  # Redirect to main page if already completed
    
    return render_template('additional_info.html')

# New route to handle additional info submission
@app.route('/api/complete-profile', methods=['POST'])
def complete_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    phone = data.get('phone')
    date_of_birth = data.get('date_of_birth')
    gender = data.get('gender')
    location = data.get('location')
    
    # Update user information
    if phone:
        user.phone = phone
    if date_of_birth:
        try:
            dob_date = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            # Check if user is at least 13 years old
            today = datetime.now().date()
            age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
            if age < 13:
                return jsonify({'error': 'You must be at least 13 years old to use this service'}), 400
            user.date_of_birth = dob_date
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    if gender:
        user.gender = gender
    if location:
        user.location = location
    
    # Mark profile as completed
    user.profile_completed = True
    
    db.session.commit()
    
    return jsonify({'message': 'Profile completed successfully'})

# Route to skip additional info
@app.route('/api/skip-profile', methods=['POST'])
def skip_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Mark profile as completed even if skipped
    user.profile_completed = True
    db.session.commit()
    
    return jsonify({'message': 'Profile setup skipped successfully'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)


