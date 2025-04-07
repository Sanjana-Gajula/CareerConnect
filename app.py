from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os

from models import db, User, Job
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
mail = Mail(app)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        role = request.form['role']

        if User.query.filter_by(email=email).first():
            flash('User already exists')
            return redirect(url_for('register'))

        if password != confirm:
            flash('Passwords do not match')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()
        flash('Registered successfully!')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Invalid credentials')
            return redirect(url_for('login'))

        session['user_id'] = user.id
        session['role'] = user.role
        flash('Logged in successfully!')
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    jobs = Job.query.all()
    return render_template('dashboard.html', jobs=jobs)

@app.route('/add_job', methods=['GET', 'POST'])
def add_job():
    if 'user_id' not in session or session['role'] != 'employer':
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        location = request.form['location']
        role = request.form['role']
        salary = request.form['salary']
        description = request.form['description']

        job = Job(title=title, location=location, role=role, salary=salary, description=description)
        db.session.add(job)
        db.session.commit()
        flash('Job added successfully!')
        notify_users(job)
        return redirect(url_for('dashboard'))

    return render_template('add_job.html')

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        if 'resume' in request.files:
            resume = request.files['resume']
            filename = secure_filename(resume.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume.save(filepath)
            user.resume = filename
            db.session.commit()
            flash('Application submitted successfully!')
            return redirect(url_for('dashboard'))

    return render_template('apply.html', job=Job.query.get(job_id))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.profile = request.form['profile']
        db.session.commit()
        flash('Profile updated successfully!')

    return render_template('profile.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out')
    return redirect(url_for('index'))

# Helper to notify matching users

def notify_users(job):
    seekers = User.query.filter_by(role='jobseeker').all()
    for seeker in seekers:
        if seeker.profile and job.role.lower() in seeker.profile.lower():
            msg = Message('New Job Match Found', sender=app.config['MAIL_USERNAME'], recipients=[seeker.email])
            msg.body = f"Hi {seeker.username},\n\nA new job matching your profile has been posted: {job.title} in {job.location}.\n\nCheck it out at CareerConnect."
            mail.send(msg)

if __name__ == '__main__':
    app.run(debug=True)
