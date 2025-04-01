import random
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_mail import Mail, Message
from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, create_database
from flask_login import LoginManager, login_required, current_user
from werkzeug.utils import secure_filename
import os

# Create Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/assistprof'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'xxxxyyyyyzzzzz'

# Import db and models
from models import db, Enseignant, EmploiDuTemps, Etudiants  # Include Etudiants model

# Initialize extensions with app
db.init_app(app)
mail = Mail(app)

# Configure Flask-Mail for Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'assistprof.djib@gmail.com'
app.config['MAIL_PASSWORD'] = 'jgfx ryzu muvn wbjj '
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

def generate_otp():
    return random.randint(100000, 999999)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('documents'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('documents'))
    
    if file:
        filename = secure_filename(file.filename)
        upload_path = os.path.join('uploads', filename)
        file.save(upload_path)
        flash('File uploaded successfully', 'success')
        # Optionally, save file metadata to the database here
        return redirect(url_for('documents'))

# Import routes - after app, db, and models are initialized
from routes import *

if __name__ == "__main__":
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    # Create the database if it doesn't exist
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE DATABASE IF NOT EXISTS assistprof"))
    except Exception as e:
        print(f"Database creation error: {e}")
    
    # Create all tables
    with app.app_context():
        db.create_all()
    
    app.run(debug=True)