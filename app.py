import random
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from flask_mail import Mail, Message
from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, create_database
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import logging
import csv
import io
from dotenv import load_dotenv

# Load environment variables from .env file in development
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Verify email credentials are loaded correctly
email_username = os.environ.get('MAIL_USERNAME')
email_password = os.environ.get('MAIL_PASSWORD')
if not email_username or not email_password:
    logger.warning("Email credentials not found in environment variables! Check your .env file.")
else:
    logger.info(f"Email credentials loaded for: {email_username}")

# Import auth related functions
from auth import init_login_manager, login_route, logout_route, signup_route, verify_otp_route

# Create Flask app
app = Flask(__name__)

# Set the base directory for SQLite database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'assistprof.db')

# Configure database connection for SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'xxxxyyyyyzzzzz')

# Import db and models
from models import db, Enseignant, EmploiDuTemps, Etudiants, Document, Notification

# Initialize extensions with app
db.init_app(app)

# Create all database tables if they don't exist
with app.app_context():
    db.create_all()
    logger.info("Database tables created or verified successfully")

# Configure Flask-Mail for Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = email_username
app.config['MAIL_PASSWORD'] = email_password
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEFAULT_SENDER'] = email_username
app.config['MAIL_DEBUG'] = not os.environ.get('RENDER', False)  # Disable mail debug in production

# Initialize Mail after configuration
mail = Mail(app)

# Initialize Flask-Login
init_login_manager(app)

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'ppt', 'pptx', 'png', 'jpg', 'jpeg', 'gif', 'zip'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to format file size
def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    else:
        return f"{size_bytes/(1024*1024):.1f} MB"

# Route for landing/introduction page
@app.route('/')
def index():
    return render_template('index.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    result = login_route()
    
    # If login was successful and user is now authenticated
    if current_user.is_authenticated:
        # Send reminders after successful login
        send_schedule_reminder(current_user.ID_EN)
        
    return result

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    return signup_route(mail)

# OTP verification route
@app.route('/verify-otp/<int:user_id>', methods=['GET', 'POST'])
def verify_otp(user_id):
    return verify_otp_route(user_id)

# Logout route
@app.route('/logout')
def logout():
    return logout_route()

# Notification system
def check_today_schedule(user_id):
    """Check if there are any events scheduled for today and create notifications"""
    today = date.today()
    day_name = today.strftime("%A")  # Get the day name (Monday, Tuesday, etc.)
    
    # Get all events for today for the specific user
    today_events = EmploiDuTemps.query.filter_by(
        ID_EN=user_id,
        Jour=day_name
    ).all()
    
    notifications_created = 0
    
    for event in today_events:
        # Check if notification already exists for this event today
        existing_notification = Notification.query.filter_by(
            user_id=user_id,
            reference_id=event.ID_EMP,
            type='schedule',
            created_at=datetime.combine(today, datetime.min.time())
        ).first()
        
        if not existing_notification:
            # Create a new notification
            message = f"You have {event.Type_Cour} for {event.Fillier} with {event.Groupe} today from {event.Heure_debut.strftime('%H:%M')} to {event.Heure_fin.strftime('%H:%M')} in {event.Salle}."
            notification = Notification(
                user_id=user_id,
                title=f"Reminder: {event.Type_Cour} today",
                message=message,
                type='schedule',
                reference_id=event.ID_EMP,
                created_at=datetime.combine(today, datetime.min.time())
            )
            db.session.add(notification)
            notifications_created += 1
            
            # Send email notification
            try:
                msg = Message(
                    subject=f"Schedule Reminder: {event.Type_Cour} today",
                    recipients=[current_user.Email_EN],
                    body=message
                )
                mail.send(msg)
            except Exception as e:
                logger.error(f"Failed to send email notification: {str(e)}")
    
    if notifications_created > 0:
        db.session.commit()
    
    return notifications_created

# Function to send schedule reminders when user logs in
def send_schedule_reminder(user_id):
    """Sends email and creates browser notification with today's schedule"""
    try:
        # Get user info
        user = Enseignant.query.get(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found")
            return False
        
        today = date.today()
        day_name = today.strftime("%A")  # Get the day name (Monday, Tuesday, etc.)
        
        # Map English day names to French day names
        day_name_map = {
            'Monday': 'Lundi',
            'Tuesday': 'Mardi',
            'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi',
            'Friday': 'Vendredi',
            'Saturday': 'Samedi',
            'Sunday': 'Dimanche'
        }
        
        french_day = day_name_map.get(day_name, day_name)
        
        # Get all events for today for this user
        today_events = EmploiDuTemps.query.filter_by(
            ID_EN=user_id,
            Jour=day_name
        ).all()
        
        # If the day might be stored in French
        if not today_events:
            today_events = EmploiDuTemps.query.filter_by(
                ID_EN=user_id,
                Jour=french_day
            ).all()
        
        # If no events today, create a notification for no events
        if not today_events:
            logger.info(f"No events scheduled for user {user_id} on {day_name}")
            
            # Check if there's already a login reminder for today to avoid duplicates
            existing_reminder = Notification.query.filter(
                Notification.user_id == user_id,
                Notification.type == 'login_reminder',
                Notification.created_at >= datetime.combine(today, datetime.min.time()),
                Notification.created_at <= datetime.combine(today, datetime.max.time())
            ).first()
            
            if not existing_reminder:
                # Create a notification to inform no events today
                notification = Notification(
                    user_id=user_id,
                    title=f"Aucun cours aujourd'hui - {french_day}, {today.strftime('%d/%m/%Y')}",
                    message=f"Vous n'avez aucun cours programmé pour aujourd'hui ({french_day}).",
                    type='login_reminder',
                    is_read=False,
                    created_at=datetime.now()
                )
                db.session.add(notification)
                db.session.commit()
            
            return False
        
        # Sort events by start time
        today_events.sort(key=lambda x: x.Heure_debut)
        
        # Format message for email
        email_subject = f"Votre emploi du temps pour aujourd'hui ({french_day}, {today.strftime('%d/%m/%Y')})"
        email_body = f"Bonjour {user.Prenom_EN},\n\nVoici votre emploi du temps pour aujourd'hui ({french_day}, {today.strftime('%d/%m/%Y')}):\n\n"
        
        # Format message for notification
        notification_title = f"Emploi du temps - {french_day}, {today.strftime('%d/%m/%Y')}"
        notification_message = f"Votre emploi du temps pour aujourd'hui ({french_day}):\n\n"
        
        # Add each event to the messages
        for event in today_events:
            event_details = (
                f"• {event.Type_Cour} - {event.Fillier} ({event.Groupe})\n"
                f"  {event.Heure_debut.strftime('%H:%M')} - {event.Heure_fin.strftime('%H:%M')}\n"
                f"  Salle: {event.Salle}\n"
            )
            email_body += event_details + "\n"
            
            # Use a more compact format for notification
            notification_message += f"• {event.Heure_debut.strftime('%H:%M')} - {event.Heure_fin.strftime('%H:%M')} : {event.Type_Cour} {event.Fillier} ({event.Groupe})\n"
            notification_message += f"  Salle: {event.Salle}\n\n"
        
        email_body += "\nCeci est un rappel automatique de votre emploi du temps quotidien.\n\nAssistProf"
        
        # Send email notification
        try:
            msg = Message(
                subject=email_subject,
                recipients=[user.Email_EN],
                body=email_body
            )
            mail.send(msg)
            logger.info(f"Schedule reminder email sent successfully to {user.Email_EN}")
        except Exception as e:
            logger.error(f"Failed to send reminder email: {str(e)}")
        
        # Create browser notification
        # Check if there's already a login reminder for today to avoid duplicates
        existing_reminder = Notification.query.filter(
            Notification.user_id == user_id,
            Notification.type == 'login_reminder',
            Notification.created_at >= datetime.combine(today, datetime.min.time()),
            Notification.created_at <= datetime.combine(today, datetime.max.time())
        ).first()
        
        if not existing_reminder:
            notification = Notification(
                user_id=user_id,
                title=notification_title,
                message=notification_message,
                type='login_reminder',
                is_read=False,
                created_at=datetime.now()
            )
            db.session.add(notification)
            db.session.commit()
            logger.info(f"Schedule reminder notification created for user {user_id} with {len(today_events)} events")
            
        return True
    except Exception as e:
        logger.error(f"Error sending schedule reminder: {str(e)}")
        return False

# Dashboard route (protected)
@app.route('/dashboard')
@login_required
def dashboard():
    # Check for today's schedule and create notifications
    check_today_schedule(current_user.ID_EN)
    
    # Get unread notifications count for the navbar
    unread_count = Notification.query.filter_by(
        user_id=current_user.ID_EN,
        is_read=False
    ).count()
    
    # Check if we have today's login reminder notification
    today = date.today()
    login_reminder = Notification.query.filter(
        Notification.user_id == current_user.ID_EN,
        Notification.type == 'login_reminder',
        Notification.created_at >= datetime.combine(today, datetime.min.time()),
        Notification.created_at <= datetime.combine(today, datetime.max.time())
    ).first()
    
    # Get today's schedule for display on the dashboard
    day_name = today.strftime("%A")  # Get day name (Monday, Tuesday, etc.)
    
    # Map English day names to French day names
    day_name_map = {
        'Monday': 'Lundi',
        'Tuesday': 'Mardi',
        'Wednesday': 'Mercredi',
        'Thursday': 'Jeudi',
        'Friday': 'Vendredi',
        'Saturday': 'Samedi',
        'Sunday': 'Dimanche'
    }
    
    french_day = day_name_map.get(day_name, day_name)
    
    # Format date for display (e.g., "Lundi, 15 Jan 2024")
    today_display = f"{french_day}, {today.strftime('%d %b %Y')}"
    
    # Get all events for today for this user (try both English and French day names)
    today_events = EmploiDuTemps.query.filter_by(
        ID_EN=current_user.ID_EN,
        Jour=day_name
    ).all()
    
    # If the day might be stored in French
    if not today_events:
        today_events = EmploiDuTemps.query.filter_by(
            ID_EN=current_user.ID_EN,
            Jour=french_day
        ).all()
    
    # Sort events by start time
    today_events.sort(key=lambda x: x.Heure_debut)
    
    # Add CSS classes for styling based on event type
    for event in today_events:
        if event.Type_Cour == "Lecture":
            event.type_class = "bg-lecture"
        elif event.Type_Cour == "Lab":
            event.type_class = "bg-lab"
        elif event.Type_Cour == "Tutorial":
            event.type_class = "bg-tutorial"
        elif event.Type_Cour == "Exam":
            event.type_class = "bg-exam"
        elif event.Type_Cour == "Office Hours":
            event.type_class = "bg-office-hours"
        else:
            event.type_class = ""
    
    # Get student grade statistics for the pie chart
    students = Etudiants.query.filter_by(ID_EN=current_user.ID_EN).all()
    
    # Count students by grade category
    excellent_count = 0  # ≥ 16
    very_good_count = 0  # ≥ 14 and < 16
    good_count = 0       # ≥ 12 and < 14
    passing_count = 0    # ≥ 10 and < 12
    failing_count = 0    # < 10
    total_grade = 0
    grades_count = 0
    
    # Additional statistics
    total_students = len(students)
    departments_set = set()
    missing_tp_count = 0
    missing_cc_count = 0
    missing_cf_count = 0
    missing_projet_count = 0
    
    for student in students:
        # Add department to set if available
        if student.Departement:
            departments_set.add(student.Departement)
            
        # Check for missing grades
        if student.Note_TP is None:
            missing_tp_count += 1
        if student.Note_CC is None:
            missing_cc_count += 1
        if student.Note_CF is None:
            missing_cf_count += 1
        if student.Note_Projet is None:
            missing_projet_count += 1
            
        # Existing grade distribution logic
        if student.Moyen is not None:
            grades_count += 1
            total_grade += student.Moyen
            
            if student.Moyen >= 16:
                excellent_count += 1
            elif student.Moyen >= 14:
                very_good_count += 1
            elif student.Moyen >= 12:
                good_count += 1
            elif student.Moyen >= 10:
                passing_count += 1
            else:
                failing_count += 1
    
    # Count distinct departments
    distinct_departments = len(departments_set)
    
    # Calculate average grade if we have any grades
    average_grade = total_grade / grades_count if grades_count > 0 else 0
    
    # Group stats for easier summary
    average_count = good_count + passing_count + very_good_count
    
    return render_template('dashboard.html', 
                          unread_notifications=unread_count,
                          login_reminder=login_reminder,
                          today_events=today_events,
                          today_display=today_display,
                          excellent_count=excellent_count,
                          very_good_count=very_good_count,
                          good_count=good_count,
                          passing_count=passing_count,
                          failing_count=failing_count,
                          average_grade=average_grade,
                          grades_count=grades_count,
                          average_count=average_count,
                          total_students=total_students,
                          distinct_departments=distinct_departments,
                          missing_tp_count=missing_tp_count,
                          missing_cc_count=missing_cc_count,
                          missing_cf_count=missing_cf_count,
                          missing_projet_count=missing_projet_count)

# FAQ page route
@app.route('/faq')
def faq():
    # Define common FAQ questions and answers
    faq_data = [
        {
            "question": "Comment ajouter un étudiant?",
            "answer": "Pour ajouter un étudiant, allez à la page de notation, puis cliquez sur le bouton 'Ajouter un étudiant' et remplissez le formulaire avec les détails de l'étudiant."
        },
        {
            "question": "Comment importer plusieurs étudiants à la fois?",
            "answer": "Vous pouvez importer des étudiants en utilisant un fichier CSV. Sur la page de notation, cliquez sur 'Importer CSV' et téléchargez votre fichier. Assurez-vous que le CSV contient les colonnes: matricule, nom_complet, année, département, matière, note_tp, note_cc, note_cf, note_projet."
        },
        {
            "question": "Comment modifier mon emploi du temps?",
            "answer": "Allez à la page 'Emploi du temps', puis vous pouvez ajouter de nouveaux événements en cliquant sur 'Ajouter un cours'. Vous pouvez également modifier les événements existants en les faisant glisser vers un nouvel horaire ou en cliquant dessus pour les éditer."
        },
        {
            "question": "Comment calculer les moyennes?",
            "answer": "Les moyennes sont calculées automatiquement selon la formule suivante: 30% TP + 20% CC + 50% CF. Si un projet est inclus, la formule devient: 20% TP + 20% CC + 40% CF + 20% Projet."
        },
        {
            "question": "Comment télécharger ou partager des documents?",
            "answer": "Allez à la page 'Documents', puis cliquez sur 'Télécharger un document'. Vous pouvez ensuite remplir les détails du document et télécharger votre fichier. Pour partager, utilisez le lien généré après le téléchargement."
        },
        {
            "question": "Comment recevoir des rappels pour mes cours?",
            "answer": "Les rappels sont envoyés automatiquement chaque jour où vous avez des cours. Vous recevrez des notifications dans l'application et également par email si vous avez configuré votre adresse email."
        },
        {
            "question": "Comment réinitialiser mon mot de passe?",
            "answer": "Sur la page de connexion, cliquez sur 'Mot de passe oublié?' et suivez les instructions pour réinitialiser votre mot de passe. Un email avec des instructions sera envoyé à l'adresse associée à votre compte."
        },
        {
            "question": "Comment ajouter ou modifier des notes d'étudiants?",
            "answer": "Sur la page de notation, recherchez l'étudiant par son matricule ou son nom. Ensuite, cliquez sur l'icône d'édition à côté de son nom pour modifier ses notes. Les moyennes seront recalculées automatiquement."
        }
    ]
    
    # If user is logged in, get notification count
    unread_count = 0
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(
            user_id=current_user.ID_EN,
            is_read=False
        ).count()
    
    return render_template('faq.html', faq_data=faq_data, unread_notifications=unread_count)

# Grading route (protected)
@app.route('/grading')
@login_required
def grading():
    students = Etudiants.query.filter_by(ID_EN=current_user.ID_EN).all()
    return render_template('grading.html', students=students)

# Add student route
@app.route('/add-student', methods=['POST'])
@login_required
def add_student():
    try:
        # Get form data
        matricule = request.form.get('matricule')
        nom_complet = request.form.get('nom_complet')
        note_tp = request.form.get('note_tp') or None
        note_cc = request.form.get('note_cc') or None
        note_cf = request.form.get('note_cf') or None
        note_projet = request.form.get('note_projet') or None
        # Get new fields
        year = request.form.get('year') or None
        departement = request.form.get('departement') or None
        subject = request.form.get('subject') or None
        
        # Check if student with this matricule already exists
        existing_student = Etudiants.query.filter_by(Matricule_ET=matricule).first()
        if (existing_student):
            return jsonify({'status': 'error', 'message': 'Student with this matricule already exists'}), 400
        
        # Convert string values to float if they exist
        if (note_tp):
            note_tp = float(note_tp)
        if (note_cc):
            note_cc = float(note_cc)
        if (note_cf):
            note_cf = float(note_cf)
        if (note_projet):
            note_projet = float(note_projet)
        
        # Calculate average if all the required fields are available
        moyen = None
        if (all(x is not None for x in [note_tp, note_cc, note_cf])):
            # Calculate weighted average: 30% TP, 20% CC, 50% CF
            moyen = (note_tp * 0.3) + (note_cc * 0.2) + (note_cf * 0.5)
            if (note_projet):
                # If projet exists, adjust the calculation: 20% TP, 20% CC, 40% CF, 20% projet
                moyen = (note_tp * 0.2) + (note_cc * 0.2) + (note_cf * 0.4) + (note_projet * 0.2)
        
        # Create new student
        new_student = Etudiants(
            Matricule_ET=matricule,
            Nom_ET_complet=nom_complet,
            Note_TP=note_tp,
            Note_CC=note_cc,
            Note_CF=note_cf,
            Note_Projet=note_projet,
            Moyen=moyen,
            ID_EN=current_user.ID_EN,
            year=year,
            Departement=departement,
            subject=subject
        )
        
        # Add to database
        db.session.add(new_student)
        db.session.commit()
        
        # Return success response
        return jsonify({
            'status': 'success',
            'message': 'Student added successfully',
            'student': {
                'matricule': new_student.Matricule_ET,
                'nom_complet': new_student.Nom_ET_complet,
                'note_tp': new_student.Note_TP,
                'note_cc': new_student.Note_CC,
                'note_cf': new_student.Note_CF,
                'note_projet': new_student.Note_Projet,
                'moyen': new_student.Moyen
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Update student grades
@app.route('/update-grade/<matricule>', methods=['POST'])
@login_required
def update_grade(matricule):
    try:
        student = Etudiants.query.filter_by(Matricule_ET=matricule, ID_EN=current_user.ID_EN).first()
        if (not student):
            return jsonify({'status': 'error', 'message': 'Student not found'}), 404
        
        # Get form data
        note_tp = request.form.get('note_tp') 
        note_cc = request.form.get('note_cc')
        note_cf = request.form.get('note_cf')
        note_projet = request.form.get('note_projet')
        
        # Update student grades if provided
        if (note_tp):
            student.Note_TP = float(note_tp)
        if (note_cc):
            student.Note_CC = float(note_cc)
        if (note_cf):
            student.Note_CF = float(note_cf)
        if (note_projet):
            student.Note_Projet = float(note_projet)
        
        # Calculate new average
        if (all(x is not None for x in [student.Note_TP, student.Note_CC, student.Note_CF])):
            # Calculate weighted average: 30% TP, 20% CC, 50% CF
            student.Moyen = (student.Note_TP * 0.3) + (student.Note_CC * 0.2) + (student.Note_CF * 0.5)
            if (student.Note_Projet):
                # If projet exists, adjust the calculation: 20% TP, 20% CC, 40% CF, 20% projet
                student.Moyen = (student.Note_TP * 0.2) + (student.Note_CC * 0.2) + (student.Note_CF * 0.4) + (student.Note_Projet * 0.2)
        
        db.session.commit()
        
        # Return success response
        return jsonify({
            'status': 'success', 
            'message': 'Grades updated successfully',
            'moyen': student.Moyen
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Search students route
@app.route('/search-students', methods=['GET'])
@login_required
def search_students():
    query = request.args.get('query', '').strip()
    
    if (not query):
        students = Etudiants.query.filter_by(ID_EN=current_user.ID_EN).all()
    else:
        # Search by matricule or name
        students = Etudiants.query.filter(
            Etudiants.ID_EN == current_user.ID_EN,
            (Etudiants.Matricule_ET.like(f'%{query}%') | Etudiants.Nom_ET_complet.like(f'%{query}%'))
        ).all()
    
    return render_template('students_search.html', students=students, query=query)

# Delete student
@app.route('/delete-student/<matricule>', methods=['POST'])
@login_required
def delete_student(matricule):
    try:
        student = Etudiants.query.filter_by(Matricule_ET=matricule, ID_EN=current_user.ID_EN).first()
        if (not student):
            return jsonify({'status': 'error', 'message': 'Student not found'}), 404
        
        db.session.delete(student)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Student deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# DEBUG: Route to check session variables
@app.route('/check-session')
def check_session():
    if (not current_user.is_authenticated):
        return jsonify({
            'error': 'Not authenticated',
            'status': 401
        }), 401
    
    # Get all session data
    session_data = {key: session.get(key) for key in session}
    
    # Get user data from database
    user_data = {
        'id': current_user.ID_EN,
        'email': current_user.Email_EN,
        'name': f"{current_user.Prenom_EN} {current_user.Nom_EN}",
        'role': current_user.role,
        'is_admin': current_user.role.lower() == 'admin' if current_user.role else False
    }
    
    return jsonify({
        'session': session_data,
        'user': user_data,
        'status': 200
    })

# DEBUG: Route to set current user as admin (for testing)
@app.route('/set-admin')
@login_required
def set_admin():
    if (not current_user.is_authenticated):
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        # Set the user's role to admin in the database
        current_user.role = 'admin'
        db.session.commit()
        
        # Update the session
        session['user_role'] = 'admin'
        
        return jsonify({
            'message': 'User promoted to admin successfully',
            'new_role': current_user.role,
            'session_role': session.get('user_role')
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Add new route for student login
@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if (request.method == 'POST'):
        matricule = request.form.get('matricule')
        
        if (not matricule):
            flash('Matricule is required', 'danger')
            return render_template('student_login.html')
        
        # Find student by matricule
        student = Etudiants.query.filter_by(Matricule_ET=matricule).first()
        
        if (not student):
            flash('No student found with this matricule', 'danger')
            return render_template('student_login.html')
        
        # Store student info in session
        session['student_id'] = student.Matricule_ET
        session['student_name'] = student.Nom_ET_complet
        
        # Redirect to student dashboard
        return redirect(url_for('student_dashboard'))
    
    return render_template('student_login.html')

@app.route('/student-dashboard')
def student_dashboard():
    # Check if student is logged in
    if ('student_id' not in session):
        flash('Please login first', 'warning')
        return redirect(url_for('student_login'))
    
    # Get student info
    student = Etudiants.query.filter_by(Matricule_ET=session['student_id']).first()
    
    if (not student):
        session.pop('student_id', None)
        session.pop('student_name', None)
        flash('Student not found', 'danger')
        return redirect(url_for('student_login'))
    
    # Render student dashboard with grades
    return render_template('student_dashboard.html', student=student)

@app.route('/student-logout')
def student_logout():
    # Remove student info from session
    session.pop('student_id', None)
    session.pop('student_name', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('student_login'))

# Import students from CSV
@app.route('/import-students', methods=['POST'])
@login_required
def import_students():
    try:
        if ('csvFile' not in request.files):
            return jsonify({'status': 'error', 'message': 'No file part'}), 400
            
        file = request.files['csvFile']
        if (file.filename == ''):
            return jsonify({'status': 'error', 'message': 'No selected file'}), 400
            
        # Check if it's a CSV file
        if (not file.filename.endswith('.csv')):
            return jsonify({'status': 'error', 'message': 'File must be a CSV'}), 400
            
        # Process the CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        
        # Skip header row and identify column indices
        header = next(csv_input)
        header = [h.strip() for h in header]
        
        # Map expected column names to indices
        column_map = {}
        expected_headers = ['Matricule', 'Nom_ET_complet', 'year', 'Departement', 'subject', 
                          'Note_TP', 'Note_CC', 'Note_CF', 'Note_Projet', 'Moyen']
        
        for expected in expected_headers:
            if expected in header:
                column_map[expected] = header.index(expected)
            else:
                # For backward compatibility, try some common variations
                if expected == 'Matricule' and 'matricule' in header:
                    column_map[expected] = header.index('matricule')
                elif expected == 'Nom_ET_complet' and 'nom_complet' in header:
                    column_map[expected] = header.index('nom_complet')
                    
        # Make sure we at least have matricule and name
        if 'Matricule' not in column_map or 'Nom_ET_complet' not in column_map:
            return jsonify({
                'status': 'error', 
                'message': 'CSV must contain at least Matricule and Nom_ET_complet columns'
            }), 400
        
        imported_count = 0
        errors = []
        
        for row in csv_input:
            # Skip empty rows
            if (not any(row)):
                continue
                
            try:
                # Extract data from CSV using the column map
                # Default to None if column doesn't exist
                matricule = row[column_map['Matricule']].strip() if len(row) > column_map['Matricule'] else None
                nom_complet = row[column_map['Nom_ET_complet']].strip() if len(row) > column_map['Nom_ET_complet'] else None
                
                # Optional fields
                year = row[column_map.get('year', -1)].strip() if 'year' in column_map and len(row) > column_map['year'] else None
                departement = row[column_map.get('Departement', -1)].strip() if 'Departement' in column_map and len(row) > column_map['Departement'] else None
                subject = row[column_map.get('subject', -1)].strip() if 'subject' in column_map and len(row) > column_map['subject'] else None
                
                # Grade fields - convert to float if present and not empty
                try:
                    note_tp = float(row[column_map.get('Note_TP', -1)]) if 'Note_TP' in column_map and len(row) > column_map['Note_TP'] and row[column_map['Note_TP']].strip() else None
                except ValueError:
                    note_tp = None
                    
                try:
                    note_cc = float(row[column_map.get('Note_CC', -1)]) if 'Note_CC' in column_map and len(row) > column_map['Note_CC'] and row[column_map['Note_CC']].strip() else None
                except ValueError:
                    note_cc = None
                    
                try:
                    note_cf = float(row[column_map.get('Note_CF', -1)]) if 'Note_CF' in column_map and len(row) > column_map['Note_CF'] and row[column_map['Note_CF']].strip() else None
                except ValueError:
                    note_cf = None
                    
                try:
                    note_projet = float(row[column_map.get('Note_Projet', -1)]) if 'Note_Projet' in column_map and len(row) > column_map['Note_Projet'] and row[column_map['Note_Projet']].strip() else None
                except ValueError:
                    note_projet = None
                
                # Validate required data
                if (not matricule or not nom_complet):
                    errors.append(f"Row skipped: missing required data - {','.join(row)}")
                    continue
                
                # Check if student already exists
                existing_student = Etudiants.query.filter_by(Matricule_ET=matricule).first()
                if (existing_student):
                    # Update existing student
                    existing_student.Nom_ET_complet = nom_complet
                    
                    # Only update if the value is not None
                    if year is not None:
                        existing_student.year = year
                    if departement is not None:
                        existing_student.Departement = departement
                    if subject is not None:
                        existing_student.subject = subject
                    if note_tp is not None:
                        existing_student.Note_TP = note_tp
                    if note_cc is not None:
                        existing_student.Note_CC = note_cc
                    if note_cf is not None:
                        existing_student.Note_CF = note_cf
                    if note_projet is not None:
                        existing_student.Note_Projet = note_projet
                        
                    # Recalculate average
                    if (all(x is not None for x in [existing_student.Note_TP, existing_student.Note_CC, existing_student.Note_CF])):
                        existing_student.Moyen = (existing_student.Note_TP * 0.3) + (existing_student.Note_CC * 0.2) + (existing_student.Note_CF * 0.5)
                        if (existing_student.Note_Projet):
                            existing_student.Moyen = (existing_student.Note_TP * 0.2) + (existing_student.Note_CC * 0.2) + (existing_student.Note_CF * 0.4) + (existing_student.Note_Projet * 0.2)
                else:
                    # Create new student
                    # Calculate average if all required grades are present
                    moyen = None
                    if (all(x is not None for x in [note_tp, note_cc, note_cf])):
                        moyen = (note_tp * 0.3) + (note_cc * 0.2) + (note_cf * 0.5)
                        if (note_projet is not None):
                            moyen = (note_tp * 0.2) + (note_cc * 0.2) + (note_cf * 0.4) + (note_projet * 0.2)
                    
                    # Create new student record
                    new_student = Etudiants(
                        Matricule_ET=matricule,
                        Nom_ET_complet=nom_complet,
                        year=year,
                        Departement=departement,
                        subject=subject,
                        Note_TP=note_tp,
                        Note_CC=note_cc,
                        Note_CF=note_cf,
                        Note_Projet=note_projet,
                        Moyen=moyen,
                        ID_EN=current_user.ID_EN
                    )
                    db.session.add(new_student)
                
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Error processing row: {str(e)} - {','.join(row if row else ['Empty row'])}")
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully imported {imported_count} students',
            'imported': imported_count,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Document management route
@app.route('/documents')
@login_required
def documents():
    # Fetch all documents for the current user
    documents = Document.query.filter_by(user_id=current_user.ID_EN).all()
    
    # Add formatted size to each document
    for doc in documents:
        doc.size_formatted = format_file_size(doc.size)
    
    return render_template('documents.html', documents=documents)

# Upload document route
@app.route('/upload-document', methods=['POST'])
@login_required
def upload_document():
    try:
        if 'document' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part'}), 400
        
        file = request.files['document']
        
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            # Make sure user folder exists
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.ID_EN))
            os.makedirs(user_folder, exist_ok=True)
            
            # Get form data
            title = request.form.get('title')
            category = request.form.get('category')
            description = request.form.get('description', '')
            
            # Secure the filename and create path
            filename = secure_filename(file.filename)
            file_path = os.path.join(user_folder, filename)
            
            # Ensure unique filename by adding timestamp if file exists
            base, extension = os.path.splitext(filename)
            counter = 1
            while os.path.exists(file_path):
                filename = f"{base}_{counter}{extension}"
                file_path = os.path.join(user_folder, filename)
                counter += 1
            
            # Save the file
            file.save(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Create document record in database
            new_document = Document(
                title=title,
                filename=filename,
                filepath=file_path,
                category=category,
                description=description,
                size=file_size,
                upload_date=datetime.now(),
                user_id=current_user.ID_EN
            )
            
            db.session.add(new_document)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Document uploaded successfully',
                'document': {
                    'id': new_document.id,
                    'title': new_document.title,
                    'filename': new_document.filename,
                    'category': new_document.category,
                    'size': format_file_size(new_document.size),
                    'upload_date': new_document.upload_date.strftime('%Y-%m-%d')
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Download document route
@app.route('/download-document/<int:document_id>')
@login_required
def download_document(document_id):
    try:
        # Get document from database
        document = Document.query.filter_by(id=document_id, user_id=current_user.ID_EN).first()
        
        if not document:
            flash('Document not found or you do not have permission to download it', 'danger')
            return redirect(url_for('documents'))
        
        # Check if file exists
        if not os.path.exists(document.filepath):
            flash('Document file not found on server', 'danger')
            return redirect(url_for('documents'))
        
        # Return the file as an attachment
        from flask import send_file
        return send_file(document.filepath, as_attachment=True, download_name=document.filename)
    
    except Exception as e:
        flash(f'Error downloading document: {str(e)}', 'danger')
        return redirect(url_for('documents'))

# Delete document route
@app.route('/delete-document/<int:document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    try:
        document = Document.query.filter_by(id=document_id, user_id=current_user.ID_EN).first()
        
        if not document:
            return jsonify({'status': 'error', 'message': 'Document not found'}), 404
        
        # Delete the file from storage
        if os.path.exists(document.filepath):
            os.remove(document.filepath)
        
        # Delete record from database
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Document deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Search documents route
@app.route('/search-documents', methods=['GET'])
@login_required
def search_documents():
    query = request.args.get('query', '').strip()
    category = request.args.get('category', 'all')
    
    # Base query - get user's documents
    documents_query = Document.query.filter_by(user_id=current_user.ID_EN)
    
    # Apply category filter if not "all"
    if category != 'all':
        documents_query = documents_query.filter_by(category=category)
    
    # Apply search query if provided
    if query:
        documents_query = documents_query.filter(
            Document.title.ilike(f'%{query}%') | 
            Document.description.ilike(f'%{query}%') |
            Document.filename.ilike(f'%{query}%')
        )
    
    # Get results
    documents = documents_query.all()
    
    # Add formatted size
    for doc in documents:
        doc.size_formatted = format_file_size(doc.size)
    
    # Return to the main documents page with search results
    return render_template('documents.html', documents=documents, search_query=query, category=category)

# Schedule page route
@app.route('/schedule')
@login_required
def schedule():
    # Check for today's schedule and create notifications
    check_today_schedule(current_user.ID_EN)
    
    # Map English day names to French day names
    day_name_map = {
        'Monday': 'Lundi',
        'Tuesday': 'Mardi',
        'Wednesday': 'Mercredi',
        'Thursday': 'Jeudi',
        'Friday': 'Vendredi',
        'Saturday': 'Samedi',
        'Sunday': 'Dimanche'
    }
    
    # Get schedule events for the current user
    events = EmploiDuTemps.query.filter_by(ID_EN=current_user.ID_EN).all()
    
    # Extract hour and minute from Time objects and translate the day names
    for event in events:
        # Store hour and minute components separately
        event.start_hour = event.Heure_debut.hour
        event.start_minute = event.Heure_debut.minute
        event.end_hour = event.Heure_fin.hour
        event.end_minute = event.Heure_fin.minute
        
        # Translate day name from English to French if needed
        if event.Jour in day_name_map.keys():
            event.Jour = day_name_map[event.Jour]
        
        # Calculate duration in hours (can include fractional hours for half-hour slots)
        event.duration = (event.end_hour - event.start_hour) + (event.end_minute - event.start_minute) / 60.0
    
    # Get unread notifications count
    unread_count = Notification.query.filter_by(
        user_id=current_user.ID_EN,
        is_read=False
    ).count()
    
    return render_template('schedule.html', schedule=events, unread_notifications=unread_count)

# Add schedule event route
@app.route('/add-schedule-event', methods=['POST'])
@login_required
def add_schedule_event():
    try:
        # Get form data
        fillier = request.form.get('fillier')
        groupe = request.form.get('groupe')
        type_cour = request.form.get('type_cour')
        jour = request.form.get('jour')
        heure_debut = request.form.get('heure_debut')
        heure_fin = request.form.get('heure_fin')
        salle = request.form.get('salle')
        
        # Validate data
        if not all([fillier, groupe, type_cour, jour, heure_debut, heure_fin, salle]):
            return jsonify({'status': 'error', 'message': 'All fields are required'}), 400
            
        # Convert time strings to datetime.time objects
        from datetime import datetime
        h_debut = datetime.strptime(heure_debut, '%H:%M').time()
        h_fin = datetime.strptime(heure_fin, '%H:%M').time()
        
        if h_debut >= h_fin:
            return jsonify({'status': 'error', 'message': 'End time must be after start time'}), 400
            
        # Create new schedule event
        new_event = EmploiDuTemps(
            Jour=jour,
            Heure_debut=h_debut,
            Heure_fin=h_fin,
            Salle=salle,
            Fillier=fillier,
            Type_Cour=type_cour,
            Groupe=groupe,
            ID_EN=current_user.ID_EN
        )
        
        # Add to database
        db.session.add(new_event)
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'message': 'Event added successfully',
            'event_id': new_event.ID_EMP
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Update schedule event when dragged
@app.route('/update-schedule-event/<int:event_id>', methods=['POST'])
@login_required
def update_schedule_event(event_id):
    try:
        # Find the event
        event = EmploiDuTemps.query.filter_by(ID_EMP=event_id, ID_EN=current_user.ID_EN).first()
        
        if not event:
            return jsonify({'status': 'error', 'message': 'Événement non trouvé'}), 404
        
        # Get the new position data
        new_day = request.form.get('day')
        new_start_hour = int(request.form.get('start_hour'))
        new_start_minute = int(request.form.get('start_minute', 0))  # Default to 0 if not provided
        
        # Log received values for debugging
        app.logger.info(f"Updating event {event_id}: New day={new_day}, hour={new_start_hour}, minute={new_start_minute}")
        app.logger.info(f"Current event data: Day={event.Jour}, Start={event.Heure_debut}")
        
        # Calculate the event duration in hours
        old_duration_mins = (event.Heure_fin.hour - event.Heure_debut.hour) * 60 + (event.Heure_fin.minute - event.Heure_debut.minute)
        
        # Calculate new end time
        new_end_minutes = new_start_hour * 60 + new_start_minute + old_duration_mins
        new_end_hour = new_end_minutes // 60
        new_end_minute = new_end_minutes % 60
        
        # Convert to time objects
        from datetime import datetime, time
        new_start_time = time(hour=new_start_hour, minute=new_start_minute)
        new_end_time = time(hour=new_end_hour, minute=new_end_minute)
        
        # Update the event
        old_day = event.Jour
        event.Jour = new_day
        event.Heure_debut = new_start_time
        event.Heure_fin = new_end_time
        
        app.logger.info(f"Updated event: Day changed from {old_day} to {event.Jour}, Time from {event.Heure_debut} to {event.Heure_fin}")
        
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'message': 'Événement mis à jour avec succès',
            'event': {
                'id': event.ID_EMP,
                'day': event.Jour,
                'start_time': f"{event.Heure_debut.hour}:{event.Heure_debut.minute:02d}",
                'end_time': f"{event.Heure_fin.hour}:{event.Heure_fin.minute:02d}"
            }
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating event: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Delete schedule event
@app.route('/delete-schedule-event/<int:event_id>', methods=['POST'])
@login_required
def delete_schedule_event(event_id):
    try:
        # Find the event
        event = EmploiDuTemps.query.filter_by(ID_EMP=event_id, ID_EN=current_user.ID_EN).first()
        
        if not event:
            return jsonify({'status': 'error', 'message': 'Event not found'}), 404
            
        # Delete the event
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Event deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Add these new routes for notification handling
@app.route('/notifications')
@login_required
def view_notifications():
    # Get all notifications for current user, newest first
    notifications = Notification.query.filter_by(
        user_id=current_user.ID_EN
    ).order_by(Notification.created_at.desc()).all()
    
    return render_template('notifications.html', notifications=notifications)

@app.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.ID_EN
    ).first()
    
    if notification:
        notification.is_read = True
        db.session.commit()
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Notification not found'}), 404

@app.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    notifications = Notification.query.filter_by(
        user_id=current_user.ID_EN,
        is_read=False
    ).all()
    
    for notification in notifications:
        notification.is_read = True
    
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/get-notifications')
@login_required
def get_notifications():
    # Get the 5 most recent unread notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.ID_EN,
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    # Format notifications for JSON response
    result = []
    for notification in notifications:
        result.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.type,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_read': notification.is_read
        })
    
    # Get total count of unread notifications
    unread_count = Notification.query.filter_by(
        user_id=current_user.ID_EN,
        is_read=False
    ).count()
    
    return jsonify({
        'notifications': result,
        'unread_count': unread_count
    })

if __name__ == "__main__":
    # Create the database engine with the configured URI
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    
    # Create all tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created or verified successfully")
    
    # Create uploads directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Get port from environment variable for Render deployment
    port = int(os.environ.get('PORT', 5000))
    
    # Run app on all interfaces (0.0.0.0) and use the correct port
    # Disable debug mode when running on Render
    app.run(host='0.0.0.0', port=port, debug=not os.environ.get('RENDER', False))