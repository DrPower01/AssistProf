from datetime import datetime, timedelta
from flask import Flask
from flask_mail import Mail, Message
from sqlalchemy import and_
import threading
import time

# Create Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/assistprof'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

# Import db and models
from models import db, Enseignant, EmploiDuTemps

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

def send_notification_email(mail, recipient, subject, body):
    """Send an email notification to a recipient."""
    msg = Message(
        subject=subject,
        recipients=[recipient],
        body=body,
        sender='assistprof.djib@gmail.com'
    )
    mail.send(msg)

def check_upcoming_classes(app, mail, db, Enseignant, EmploiDuTemps):
    """
    Check for upcoming classes and send notifications to teachers
    30 minutes before their scheduled courses.
    """
    with app.app_context():
        while True:
            now = datetime.now()
            # Calculate time 30 minutes from now
            upcoming_time = now + timedelta(minutes=30)
            
            current_day = now.strftime('%A').lower()
            current_time = now.strftime('%H:%M')
            
            # Find classes that start within the next 30 minutes
            upcoming_classes = EmploiDuTemps.query.filter(
                and_(
                    EmploiDuTemps.jour == current_day,
                    EmploiDuTemps.heure_debut >= current_time,
                    EmploiDuTemps.heure_debut <= upcoming_time.strftime('%H:%M')
                )
            ).all()
            
            # Send notifications for each upcoming class
            for course in upcoming_classes:
                teacher = Enseignant.query.get(course.id_enseignant)
                if teacher and teacher.email:
                    # Get course type (default to "Cours" if not specified)
                    course_type = getattr(course, 'type_cours', 'Cours')
                    
                    subject = f"Rappel: {course_type} de {course.nom_cours} dans 30 minutes"
                    body = f"""
Bonjour {teacher.nom} {teacher.prenom},

Nous vous rappelons que vous avez un {course_type} de {course.nom_cours} aujourd'hui à {course.heure_debut}.
Salle: {course.salle}
Classe: {course.classe}

AssistProf
"""
                    send_notification_email(mail, teacher.email, subject, body)
            
            # Check every minute
            time.sleep(60)

def start_notification_service(app, mail, db, Enseignant, EmploiDuTemps):
    """Start the notification service in a background thread."""
    notification_thread = threading.Thread(
        target=check_upcoming_classes,
        args=(app, mail, db, Enseignant, EmploiDuTemps),
        daemon=True
    )
    notification_thread.start()
    return notification_thread
