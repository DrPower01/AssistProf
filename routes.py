from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app, db, mail, generate_otp
from models import Enseignant, EmploiDuTemps, Etudiants
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
import random
from openpyxl import Workbook  # Import openpyxl for exporting to XLSX

# Authentication Routes
@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        matricule = request.form['matricule']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        # Générer OTP et stocker les données d'inscription dans la session
        otp = str(random.randint(100000, 999999))
        session['registration_data'] = {
            'nom': nom,
            'prenom': prenom,
            'matricule': matricule,
            'email': email,
            'password': password
        }
        session['otp'] = otp

        # Envoyer OTP à l'email de l'utilisateur
        msg = Message('OTP Verification', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f'Your OTP is: {otp}'
        try:
            mail.send(msg)
            flash('OTP envoyé à votre adresse email.', 'success')
        except Exception as e:
            flash(f'Erreur lors de l\'envoi de l\'email: {str(e)}', 'danger')
            app.logger.error(f'Erreur lors de l\'envoi de l\'email: {str(e)}')
            return redirect(url_for('inscription'))

        return redirect(url_for('verify_otp'))
    return render_template('inscription.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    # Rediriger si aucune donnée d'inscription présente
    if 'registration_data' not in session or 'otp' not in session:
        return redirect(url_for('inscription'))
    error = None
    if request.method == 'POST':
        if request.form['otp'] == session['otp']:
            data = session['registration_data']
            # Créer l'utilisateur dans la base de données
            new_enseignant = Enseignant(
                Nom_EN=data['nom'],
                Prenom_EN=data['prenom'],
                Matricule_EN=data['matricule'],
                Email_EN=data['email'],
                Mot_de_Passe=data['password'],
                verified=True
            )
            db.session.add(new_enseignant)
            db.session.commit()
            # Effacer les données d'inscription de la session
            session.pop('registration_data', None)
            session.pop('otp', None)
            flash('OTP vérifié avec succès!', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = 'OTP invalide'
    return render_template('verify_otp.html', error=error)

@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        enseignant = Enseignant.query.filter_by(Email_EN=email).first()
        if enseignant and check_password_hash(enseignant.Mot_de_Passe, password):
            if enseignant.verified:
                session['user_id'] = enseignant.ID_EN
                session['user_name'] = f"{enseignant.Prenom_EN} {enseignant.Nom_EN}"
                # Store user role if available, otherwise use a default
                session['user_role'] = enseignant.role if hasattr(enseignant, 'role') else "Professor"
                return redirect(url_for('dashboard'))
            else:
                flash('Veuillez vérifier votre email avant de vous connecter.', 'warning')
        else:
            flash('Email ou mot de passe incorrect', 'danger')
    return render_template('connexion.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('connexion'))

# Dashboard Routes
@app.route('/dashboard')
def dashboard():
    if 'user_name' in session:
        user_id = session['user_id']
        # Fetch the current user from database
        current_user = Enseignant.query.get(user_id)
        
        # Debug: Print current user attributes to console
        app.logger.debug(f"User attributes: {vars(current_user)}")
        
        # Set is_admin to True for testing or determine from user object
        # Option 1: Force admin status for testing
        is_admin = True
        
        # Option 2: Check all possible admin field names (uncomment one of these)
        # if hasattr(current_user, 'Role') and current_user.Role == 'admin':
        #     is_admin = True
        # elif hasattr(current_user, 'admin_status') and current_user.admin_status:
        #     is_admin = True
        # elif hasattr(current_user, 'Admin_Status') and current_user.Admin_Status:
        #     is_admin = True
        # elif hasattr(current_user, 'is_admin') and current_user.is_admin:
        #     is_admin = True
        
        # Debug: Log the is_admin status
        app.logger.debug(f"Admin status for user {user_id}: {is_admin}")
        
        return render_template('dashboard.html', user_name=session['user_name'], 
                              user_id=user_id, is_admin=is_admin)
    else:
        return redirect(url_for('connexion'))

@app.route('/overview')
def overview():
    # If it's an AJAX request, return only the content for the tab
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('overview.html')
    # Otherwise redirect to dashboard with overview tab active
    return redirect(url_for('dashboard'))

@app.route('/notes')
def notes():
    user_id = session.get('user_id')  # Get the logged-in user's ID
    if not user_id:
        flash('Vous devez être connecté pour voir vos étudiants.', 'danger')
        return redirect(url_for('connexion'))  # Redirect to login if not logged in

    etudiants = Etudiants.query.filter_by(ID_EN=user_id).all()  # Filter students by enseignant ID
    return render_template('notes.html', etudiants=etudiants)

@app.route('/documents')
def documents():
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('documents.html', now=datetime.now())
    return redirect(url_for('dashboard'))

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('connexion'))
    
    # Get the current user data
    user_id = session['user_id']
    current_user = Enseignant.query.get(user_id)
    
    # Get the total number of users (teachers)
    total_users = Enseignant.query.count()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin.html', current_user=current_user, total_users=total_users)
    return redirect(url_for('dashboard'))

# Schedule Routes
@app.route('/schedule')
def schedule():
    if 'user_id' not in session:
        return redirect(url_for('connexion'))
    
    # Get the current user data for the schedule
    user_id = session['user_id']
    teacher = Enseignant.query.get_or_404(user_id)
    schedules = EmploiDuTemps.query.filter_by(ID_EN=user_id).all()
    
    # Format time values for JavaScript
    for schedule in schedules:
        if hasattr(schedule, 'Heure_debut') and schedule.Heure_debut:
            # Format time as string in HH:MM format
            schedule.Heure_debut = schedule.Heure_debut.strftime('%H:%M')
        
        if hasattr(schedule, 'Heure_fin') and schedule.Heure_fin:
            schedule.Heure_fin = schedule.Heure_fin.strftime('%H:%M')
    
    return render_template('schedule.html', 
                          user_name=session['user_name'],
                          teacher=teacher,
                          schedules=schedules,
                          now=datetime.now())  # Pass the current date

@app.route('/teacher_schedule/<int:teacher_id>')
def teacher_schedule(teacher_id):
    teacher = Enseignant.query.get_or_404(teacher_id)
    schedules = EmploiDuTemps.query.filter_by(ID_EN=teacher_id).all()
    
    # Format time values for JavaScript
    for schedule in schedules:
        if hasattr(schedule, 'Heure_debut') and schedule.Heure_debut:
            schedule.Heure_debut = schedule.Heure_debut.strftime('%H:%M')
        
        if hasattr(schedule, 'Heure_fin') and schedule.Heure_fin:
            schedule.Heure_fin = schedule.Heure_fin.strftime('%H:%M')
    
    return render_template('schedule.html', teacher=teacher, schedules=schedules, now=datetime.now())

@app.route('/add_schedule', methods=['GET', 'POST'])
def add_schedule():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Get form data
        jour = request.form['jour']
        heure_debut = request.form['heure_debut']
        heure_fin = request.form['heure_fin']
        salle = request.form['salle']
        fillier = request.form['fillier']
        type_cour = request.form['type_cour']
        groupe = request.form['groupe']
        id_en = session['user_id']  # Current logged-in teacher
        
        # Create new schedule
        new_schedule = EmploiDuTemps(
            Jour=jour,
            Heure_debut=heure_debut,
            Heure_fin=heure_fin,
            Salle=salle,
            Fillier=fillier,
            Type_Cour=type_cour,
            Groupe=groupe,
            ID_EN=id_en
        )
        
        try:
            db.session.add(new_schedule)
            db.session.commit()
            flash('Schedule added successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding schedule: {str(e)}', 'danger')
    
    # For GET request, just show the form
    return render_template('add_schedule.html', user_name=session.get('user_name', ''))

@app.route('/schedules')
def all_schedules():
    schedules = EmploiDuTemps.query.all()
    return render_template('all_schedules.html', schedules=schedules)

# API endpoints for the admin interface
@app.route('/api/enseignants')
def api_enseignants():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get all teachers
    enseignants = Enseignant.query.all()
    
    # Convert to list of dicts
    enseignants_data = []
    for enseignant in enseignants:
        enseignants_data.append({
            'ID_EN': enseignant.ID_EN,
            'Nom_EN': enseignant.Nom_EN,
            'Prenom_EN': enseignant.Prenom_EN,
            'Matricule_EN': enseignant.Matricule_EN,
            'Email_EN': enseignant.Email_EN,
            'verified': enseignant.verified,
            'role': enseignant.role
        })
    
    return jsonify(enseignants_data)

@app.route('/api/etudiants')
def api_etudiants():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get all students
    etudiants = Etudiants.query.all()
    
    # Convert to list of dicts
    etudiants_data = []
    for etudiant in etudiants:
        # Get teacher name if assigned
        enseignant_nom = None
        if etudiant.ID_EN:
            enseignant = Enseignant.query.get(etudiant.ID_EN)
            if enseignant:
                enseignant_nom = f"{enseignant.Prenom_EN} {enseignant.Nom_EN}"
        
        etudiants_data.append({
            'Matricule_ET': etudiant.Matricule_ET,
            'Nom_ET_complet': etudiant.Nom_ET_complet,
            'Moyen': etudiant.Moyen,
            'Note_TP': etudiant.Note_TP,
            'Note_CC': etudiant.Note_CC,
            'Note_CF': etudiant.Note_CF,
            'ID_EN': etudiant.ID_EN,
            'enseignant_nom': enseignant_nom
        })
    
    return jsonify(etudiants_data)

@app.route('/search_results', methods=['GET'])
def search_results():
    user_id = session.get('user_id')  # Get the logged-in user's ID
    if not user_id:
        flash('Vous devez être connecté pour effectuer une recherche.', 'danger')
        return redirect(url_for('connexion'))  # Redirect to login if not logged in

    query = request.args.get('query', '').strip()  # Get the search query
    if not query:
        flash('Veuillez entrer un nom ou un matricule pour rechercher.', 'warning')
        return redirect(url_for('notes'))

    # Search for students by name or matricule belonging to the logged-in user
    etudiants = Etudiants.query.filter(
        (Etudiants.ID_EN == user_id) & 
        ((Etudiants.Nom_ET_complet.like(f"%{query}%")) | (Etudiants.Matricule_ET.like(f"%{query}%")))
    ).all()

    return render_template('search_results.html', etudiants=etudiants, query=query)

@app.route('/export_students', methods=['GET'])
def export_students():
    user_id = session.get('user_id')  # Get the logged-in user's ID
    if not user_id:
        flash('Vous devez être connecté pour exporter vos étudiants.', 'danger')
        return redirect(url_for('connexion'))  # Redirect to login if not logged in

    etudiants = Etudiants.query.filter_by(ID_EN=user_id).all()  # Get students for the logged-in user

    # Create an XLSX workbook and sheet
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Étudiants'

    # Write the header row
    headers = ['Matricule', 'Nom', 'CC', 'CF', 'TP', 'Moyenne']
    sheet.append(headers)

    # Write student data
    for etudiant in etudiants:
        sheet.append([
            etudiant.Matricule_ET,
            etudiant.Nom_ET_complet,
            etudiant.Note_CC,
            etudiant.Note_CF,
            etudiant.Note_TP,
            etudiant.Moyen
        ])

    # Save the workbook to a response
    response = app.response_class()
    response.headers['Content-Disposition'] = 'attachment; filename=etudiants.xlsx'
    response.mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    workbook.save(response.stream)
    return response

# Function to send class reminder emails
def send_schedule_reminder(enseignant, schedule):
    try:
        if not enseignant.Email_EN:
            app.logger.warning(f"No email for teacher ID {enseignant.ID_EN}")
            return False
            
        msg = Message(
            subject='Rappel de cours - AssistProf', 
            sender=app.config['MAIL_USERNAME'], 
            recipients=[enseignant.Email_EN]
        )
        
        # Format time values for email
        debut = schedule.Heure_debut
        fin = schedule.Heure_fin
        if isinstance(debut, str):
            debut_str = debut
            fin_str = fin
        else:
            debut_str = debut.strftime('%H:%M') if debut else "N/A"
            fin_str = fin.strftime('%H:%M') if fin else "N/A"
        
        msg.html = f'''
        <h3>Rappel de cours</h3>
        <p>Bonjour {enseignant.Prenom_EN} {enseignant.Nom_EN},</p>
        <p>Vous avez un cours qui commence bientôt:</p>
        <ul>
            <li><strong>Jour:</strong> {schedule.Jour}</li>
            <li><strong>Horaire:</strong> {debut_str} - {fin_str}</li>
            <li><strong>Salle:</strong> {schedule.Salle}</li>
            <li><strong>Filière:</strong> {schedule.Fillier}</li>
            <li><strong>Type de cours:</strong> {schedule.Type_Cour}</li>
            <li><strong>Groupe:</strong> {schedule.Groupe}</li>
        </ul>
        <p>Bonne journée!</p>
        <p>L'équipe AssistProf</p>
        '''
        
        mail.send(msg)
        app.logger.info(f"Reminder email sent to {enseignant.Email_EN}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send reminder email: {str(e)}")
        return False

@app.route('/api/check_upcoming_schedules', methods=['GET'])
def check_upcoming_schedules():
    """Check for upcoming classes and send notifications."""
    # Security check - this can be enhanced with API tokens
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    now = datetime.now()
    current_day = now.strftime("%A")
    
    # Convert day names to French for comparison
    day_mapping = {
        'Monday': 'Lundi',
        'Tuesday': 'Mardi',
        'Wednesday': 'Mercredi',
        'Thursday': 'Jeudi',
        'Friday': 'Vendredi',
        'Saturday': 'Samedi',
        'Sunday': 'Dimanche'
    }
    
    french_day = day_mapping.get(current_day, current_day)
    current_time = now.strftime('%H:%M')
    
    # Get upcoming schedules for the user
    upcoming_schedules = EmploiDuTemps.query.filter_by(
        ID_EN=user_id, 
        Jour=french_day
    ).all()
    
    notifications_sent = []
    
    # For testing/debugging purposes
    app.logger.info(f"Checking schedules for user {user_id} on {french_day} at {current_time}")
    
    # Check each schedule
    for schedule in upcoming_schedules:
        # Format time values
        debut_time = schedule.Heure_debut
        if isinstance(debut_time, str):
            # If it's already a string in HH:MM format
            debut_str = debut_time
        else:
            # If it's a time object
            debut_str = debut_time.strftime('%H:%M') if debut_time else "00:00"
        
        # Calculate time difference (assuming debut_str is in HH:MM format)
        debut_hour, debut_min = map(int, debut_str.split(':'))
        debut_datetime = now.replace(hour=debut_hour, minute=debut_min, second=0, microsecond=0)
        
        # Calculate time difference in minutes
        time_diff = (debut_datetime - now).total_seconds() / 60
        
        # Send notification if class is starting in 15-20 minutes
        if 15 <= time_diff <= 20:
            teacher = Enseignant.query.get(user_id)
            if teacher:
                if send_schedule_reminder(teacher, schedule):
                    notifications_sent.append({
                        'schedule_id': schedule.ID_EMP if hasattr(schedule, 'ID_EMP') else 'unknown',
                        'start_time': debut_str,
                        'status': 'sent'
                    })
                else:
                    notifications_sent.append({
                        'schedule_id': schedule.ID_EMP if hasattr(schedule, 'ID_EMP') else 'unknown',
                        'start_time': debut_str,
                        'status': 'failed'
                    })
    
    return jsonify({
        'checked_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        'day': french_day, 
        'notifications': notifications_sent
    })

# Other Routes
@app.route('/')
def index():
    return redirect(url_for('connexion'))

# For compatibility with older code
@app.route('/login', methods=['GET', 'POST'])
def login():
    return redirect(url_for('connexion'))
