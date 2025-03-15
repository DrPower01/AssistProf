from flask import render_template, request, redirect, url_for, flash, session
from app import app, db, mail, generate_otp
from models import Enseignant, EmploiDuTemps
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
import random

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
                session['user_name'] = enseignant.Nom_EN
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
        return render_template('dashboard.html', user_name=session['user_name'], user_id=user_id)
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
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('notes.html', now=datetime.now())
    return redirect(url_for('dashboard'))

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
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin.html', current_user=current_user)
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
    
    return render_template('schedule.html', 
                          user_name=session['user_name'],
                          teacher=teacher,
                          schedules=schedules)

@app.route('/schedule/<int:teacher_id>')
def teacher_schedule(teacher_id):
    teacher = Enseignant.query.get_or_404(teacher_id)
    schedules = EmploiDuTemps.query.filter_by(ID_EN=teacher_id).all()
    return render_template('schedule.html', teacher=teacher, schedules=schedules)

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

# Other Routes
@app.route('/')
def index():
    return redirect(url_for('connexion'))

# For compatibility with older code
@app.route('/login', methods=['GET', 'POST'])
def login():
    return redirect(url_for('connexion'))
