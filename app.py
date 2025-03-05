from flask import Flask, render_template, redirect, url_for, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, Enseignant, EmploiDuTemps, init_db
from flask_mail import Mail
from email.message import EmailMessage

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/assistprof'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

init_db(app)

# Configure Flask-Mail for Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Gmail SMTP server
app.config['MAIL_PORT'] = 587  # Port for TLS
app.config['MAIL_USERNAME'] = 'assistprof.djib@gmail.com'  # Replace with your Gmail address
app.config['MAIL_PASSWORD'] = 'jgfx ryzu muvn wbjj '  # Replace with your app password (not your Gmail password)
app.config['MAIL_USE_TLS'] = True  # Use TLS
app.config['MAIL_USE_SSL'] = False  # Don't use SSL
mail = Mail(app)

@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        matricule = request.form['matricule']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_enseignant = Enseignant(Nom_EN=nom, Prenom_EN=prenom, Matricule_EN=matricule, Email_EN=email, Mot_de_Passe=hashed_password)
        try:
            db.session.add(new_enseignant)
            db.session.commit()
            flash('Inscription réussie!', 'success')
            return redirect(url_for('connexion'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'inscription: {str(e)}', 'danger')

    return render_template('inscription.html')

@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        enseignant = Enseignant.query.filter_by(Email_EN=email).first()
        if enseignant and check_password_hash(enseignant.Mot_de_Passe, password):
            session['user_id'] = enseignant.ID_EN
            session['user_name'] = enseignant.Nom_EN
            return redirect(url_for('dashboard'))
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
    app.run(debug=True)