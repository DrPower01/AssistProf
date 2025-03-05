import random
from flask import Flask, render_template, redirect, url_for, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/assistprof'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'
db = SQLAlchemy(app)

# Configure Flask-Mail for Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Gmail SMTP server
app.config['MAIL_PORT'] = 587  # Port for TLS
app.config['MAIL_USERNAME'] = 'assistprof.djib@gmail.com'  # Replace with your Gmail address
app.config['MAIL_PASSWORD'] = 'jgfx ryzu muvn wbjj'  # Replace with your app password (not your Gmail password)
app.config['MAIL_USE_TLS'] = True  # Use TLS
app.config['MAIL_USE_SSL'] = False  # Don't use SSL
mail = Mail(app)

class Enseignant(db.Model):
    ID_EN = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nom_EN = db.Column(db.String(50), nullable=False)
    Prenom_EN = db.Column(db.String(50), nullable=False)
    Matricule_EN = db.Column(db.String(20), unique=True, nullable=False)
    Email_EN = db.Column(db.String(100), unique=True, nullable=False)
    Mot_de_Passe = db.Column(db.String(255), nullable=False)
    otp_token = db.Column(db.String(6), nullable=True)
    verified = db.Column(db.Boolean, default=False)

class EmploiDuTemps(db.Model):
    ID_EMP = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Jour = db.Column(db.String(20), nullable=False)
    Heure_debut = db.Column(db.Time, nullable=False)
    Heure_fin = db.Column(db.Time, nullable=False)
    Salle = db.Column(db.String(50), nullable=False)
    Fillier = db.Column(db.String(50), nullable=False)
    Type_Cour = db.Column(db.String(20), nullable=False)
    Groupe = db.Column(db.String(20), nullable=False)
    ID_EN = db.Column(db.Integer, db.ForeignKey('enseignant.ID_EN'), nullable=True)

def generate_otp():
    return random.randint(100000, 999999)

@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        matricule = request.form['matricule']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        # Generate OTP and store registration data in session
        otp = str(random.randint(100000, 999999))
        session['registration_data'] = {
            'nom': nom,
            'prenom': prenom,
            'matricule': matricule,
            'email': email,
            'password': password
        }
        session['otp'] = otp

        # Send OTP to user's email
        msg = Message('OTP Verification', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f'Your OTP is: {otp}'
        mail.send(msg)

        return redirect(url_for('verify_otp'))
    return render_template('inscription.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    # Redirect if no registration data present
    if 'registration_data' not in session or 'otp' not in session:
        return redirect(url_for('inscription'))
    error = None
    if request.method == 'POST':
        if request.form['otp'] == session['otp']:
            data = session['registration_data']
            # Create the user in the database
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
            # Clear registration data from session
            session.pop('registration_data', None)
            session.pop('otp', None)
            flash('OTP verified successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid OTP'
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
                flash('Please verify your email before logging in.', 'warning')
        else:
            flash('Email ou mot de passe incorrect', 'danger')
    return render_template('connexion.html')

@app.route('/dashboard')
def dashboard():
    if 'user_name' in session:
        return render_template('dashboard.html', user_name=session['user_name'])
    else:
        return redirect(url_for('connexion'))

@app.route('/schedule')
def schedule():
    if 'user_name' in session:
        return render_template('schedule.html', user_name=session['user_name'])
    else:
        return redirect(url_for('connexion'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('connexion'))

@app.route('/')
def index():
    return redirect(url_for('connexion'))

if __name__ == '__main__':
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    if not database_exists(engine.url):
        create_database(engine.url)
    with app.app_context():
        db.create_all()
    app.run(debug=True)