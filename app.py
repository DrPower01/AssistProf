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

@app.route('/add_student_page')
def add_student_page():
    return render_template('add_student.html')

@app.route('/add', methods=['POST'])
def add_student():
    nom = request.form['nom']
    cc = float(request.form['cc'])
    cf = float(request.form['cf'])
    tp = float(request.form['tp'])
    moyenne = float(request.form['moyenne'])
    id_en = session.get('user_id')  # Get enseignant ID from session

    new_student = Etudiants(
        Matricule_ET=str(random.randint(100000, 999999)),  # Generate a random matricule
        Nom_ET_complet=nom,
        Note_CC=cc,
        Note_CF=cf,
        Note_TP=tp,
        Moyen=moyenne,
        ID_EN=id_en  # Assign enseignant ID
    )
    db.session.add(new_student)
    db.session.commit()
    flash('Étudiant ajouté avec succès!', 'success')
    return redirect(url_for('notes'))

@app.route('/edit/<id>', methods=['POST'])
def edit_student(id):
    student = Etudiants.query.get(id)
    if student:
        student.Nom_ET_complet = request.form['nom']
        student.Note_CC = float(request.form['cc'])
        student.Note_CF = float(request.form['cf'])
        student.Note_TP = float(request.form['tp'])
        student.Moyen = float(request.form['moyenne'])
        db.session.commit()
        flash('Étudiant modifié avec succès!', 'success')
    else:
        flash('Étudiant introuvable!', 'danger')
    return redirect(url_for('notes'))

@app.route('/delete/<id>')
def delete_student(id):
    student = Etudiants.query.get(id)
    if student:
        db.session.delete(student)
        db.session.commit()
        flash('Étudiant supprimé avec succès!', 'success')
    else:
        flash('Étudiant introuvable!', 'danger')
    return redirect(url_for('notes'))

@app.route('/search_student', methods=['GET'])
def search_student():
    query = request.args.get('query', '')
    etudiants = Etudiants.query.filter(Etudiants.Nom_ET_complet.like(f"%{query}%")).all()
    return render_template('notes.html', etudiants=etudiants)

@app.route('/documents')
def documents():
    return render_template('documents.html', now=datetime.now())

@app.route('/edit_schedule/<int:id>', methods=['POST'])
def edit_schedule(id):
    if request.content_type == 'application/json':
        # Handle JSON request from fetch API
        data = request.get_json()
        schedule = EmploiDuTemps.query.get(id)
        
        if schedule:
            schedule.Jour = data.get('jour', schedule.Jour)
            schedule.Heure_debut = data.get('heure_debut', schedule.Heure_debut)
            schedule.Heure_fin = data.get('heure_fin', schedule.Heure_fin)
            schedule.Salle = data.get('salle', schedule.Salle)
            schedule.Fillier = data.get('filiere', schedule.Fillier)
            schedule.Type_Cour = data.get('type', schedule.Type_Cour)
            schedule.Groupe = data.get('groupe', schedule.Groupe)
            
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Schedule not found'})
    else:
        # Handle form submission
        schedule = EmploiDuTemps.query.get(id)
        if schedule:
            schedule.Jour = request.form['jour']
            schedule.Heure_debut = request.form['heure_debut']
            schedule.Heure_fin = request.form['heure_fin']
            schedule.Salle = request.form['salle']
            schedule.Fillier = request.form['filiere']
            schedule.Type_Cour = request.form['type']
            schedule.Groupe = request.form['groupe']
            db.session.commit()
            flash('Cours modifié avec succès!', 'success')
        else:
            flash('Cours introuvable!', 'danger')
        return redirect(url_for('schedule'))

@app.route('/delete_schedule/<int:id>', methods=['GET'])
def delete_schedule(id):
    schedule = EmploiDuTemps.query.get(id)
    if schedule:
        db.session.delete(schedule)
        db.session.commit()
        flash('Cours supprimé avec succès!', 'success')
    else:
        flash('Cours introuvable!', 'danger')
    return redirect(url_for('schedule'))

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