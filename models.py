from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Enseignant(db.Model):
    ID_EN = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nom_EN = db.Column(db.String(50), nullable=False)  # Changed back to match database schema
    Prenom_EN = db.Column(db.String(50), nullable=False)  # Changed back to match database schema
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
    enseignant = db.relationship('Enseignant', backref='schedules')

class FAQ(db.Model):
    ID_FAQ = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Question = db.Column(db.Text, nullable=False)
    Reponse = db.Column(db.Text, nullable=False)
    nb_demander = db.Column(db.Integer, default=0)
    ID_EN = db.Column(db.Integer, db.ForeignKey('enseignant.ID_EN'), nullable=True)
    enseignant = db.relationship('Enseignant', backref='faqs')

class Notification(db.Model):
    ID_Notif = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Contexte = db.Column(db.Text, nullable=False)
    ID_EN = db.Column(db.Integer, db.ForeignKey('enseignant.ID_EN'), nullable=True)
    enseignant = db.relationship('Enseignant', backref='notifications')

class Document(db.Model):
    ID_Doc = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nom_Doc = db.Column(db.String(100), nullable=False)
    taille_Doc = db.Column(db.Float, nullable=False)
    ID_EN = db.Column(db.Integer, db.ForeignKey('enseignant.ID_EN'), nullable=True)
    enseignant = db.relationship('Enseignant', backref='documents')

class Etudiants(db.Model):
    Matricule_ET = db.Column(db.String(20), primary_key=True, unique=True)
    Nom_ET_complet = db.Column(db.String(100), nullable=False)
    Moyen = db.Column(db.Float)
    Note_TP = db.Column(db.Float)
    Note_CC = db.Column(db.Float)
    Note_CF = db.Column(db.Float)
    ID_EN = db.Column(db.Integer, db.ForeignKey('enseignant.ID_EN'), nullable=True)
    enseignant = db.relationship('Enseignant', backref='etudiants')

def init_db(app):
    from sqlalchemy import create_engine
    from sqlalchemy_utils import database_exists, create_database
    
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    if not database_exists(engine.url):
        create_database(engine.url)
    db.init_app(app)
    with app.app_context():
        db.create_all()
