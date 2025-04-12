from app import app, db
from sqlalchemy import text

with app.app_context():
    db.session.execute(text("ALTER TABLE etudiants ADD COLUMN year VARCHAR(50) NULL"))
    db.session.execute(text("ALTER TABLE etudiants ADD COLUMN Departement VARCHAR(100) NULL")) 
    db.session.execute(text("ALTER TABLE etudiants ADD COLUMN subject VARCHAR(100) NULL"))
    db.session.commit()
    print("Database schema updated successfully")
