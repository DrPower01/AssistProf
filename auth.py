from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import random
from models import db, Enseignant
import logging
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return Enseignant.query.get(int(user_id))
    
    return login_manager

def login_route():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = Enseignant.query.filter_by(Email_EN=email).first()
        
        if user and check_password_hash(user.Mot_de_Passe, password):
            if not user.verified:
                flash('Please verify your email first.')
                return redirect(url_for('verify_otp', user_id=user.ID_EN))
            
            login_user(user)
            # Set session variables with user info
            session['user_name'] = f"{user.Prenom_EN} {user.Nom_EN}"
            session['user_role'] = user.role  # Store the exact role from the database
            
            # Debug log
            logger.info(f"User {user.Email_EN} logged in with role: {user.role}")
            logger.info(f"Session data set: user_name={session.get('user_name')}, user_role={session.get('user_role')}")
            
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.')
    
    return render_template('login.html')

def signup_route(mail):
    if request.method == 'POST':
        try:
            nom = request.form.get('nom')
            prenom = request.form.get('prenom')
            email = request.form.get('email')
            password = request.form.get('password')
            
            # Validate input fields
            if not all([nom, prenom, email, password]):
                flash('All fields are required')
                return redirect(url_for('signup'))
            
            existing_user = Enseignant.query.filter_by(Email_EN=email).first()
            if existing_user:
                flash('Email already exists.')
                return redirect(url_for('signup'))
            
            # Generate OTP
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # Create user
            hashed_password = generate_password_hash(password)
            new_user = Enseignant(
                Nom_EN=nom,
                Prenom_EN=prenom,
                Email_EN=email,
                Mot_de_Passe=hashed_password,
                otp=otp,
                verified=False  # Ensure the user starts unverified
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            # Store OTP in session to verify later
            session['otp'] = otp
            
            email_sent = False
            # Send OTP email
            try:
                from flask_mail import Message
                msg = Message('Email Verification', recipients=[email])
                msg.body = f'Your verification code is: {otp}'
                mail.send(msg)
                flash('Please check your email for verification code.')
                email_sent = True
            except Exception as e:
                logger.error(f"Email send error: {e}")
                session['email_error'] = str(e)
                flash('Could not send verification email. Please check the verification page for more information.')
            
            # Redirect to verification page with user ID
            return redirect(url_for('verify_otp', user_id=new_user.ID_EN))
        except Exception as e:
            # Roll back the session
            db.session.rollback()
            
            # Log the error with details
            logger.error(f"Signup error: {str(e)}")
            
            # Show a user-friendly error message
            flash(f'An error occurred during signup: {str(e)}. Please try again.')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

def verify_otp_route(user_id):
    """Handle OTP verification"""
    user = Enseignant.query.get(user_id)
    
    if not user:
        flash('Invalid user. Please try signing up again.', 'danger')
        return redirect(url_for('signup'))
    
    # Fix attribute name inconsistency - check if the attribute is verified or is_verified
    if hasattr(user, 'verified') and user.verified:
        flash('Account already verified. Please log in.', 'info')
        return redirect(url_for('login'))
    elif hasattr(user, 'is_verified') and user.is_verified:
        flash('Account already verified. Please log in.', 'info')
        return redirect(url_for('login'))
    
    # Handle email errors
    email_error = session.get('email_error')
    display_otp = None
    
    # If there was an email error, provide OTP for user
    if email_error:
        display_otp = session.get('otp')
    
    if request.method == 'POST':
        submitted_otp = request.form.get('otp')
        stored_otp = session.get('otp')
        
        # Compare with both session OTP and user's stored OTP
        if submitted_otp == stored_otp or submitted_otp == user.otp:
            # OTP matches, verify the user
            if hasattr(user, 'verified'):
                user.verified = True
            elif hasattr(user, 'is_verified'):
                user.is_verified = True
                
            db.session.commit()
            
            # Clear OTP from session
            session.pop('otp', None)
            session.pop('email_error', None)
            session.pop('display_otp', None)
            
            flash('Account verified successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid verification code. Please try again.', 'danger')
    
    # Pass error info and optional OTP to template
    return render_template('verify_otp.html', user_id=user_id, email_error=email_error, display_otp=display_otp)

def logout_route():
    logout_user()
    session.clear()
    return redirect(url_for('index'))

def forgot_password_route(mail):
    """Handle forgot password request"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Email is required', 'danger')
            return render_template('forgot_password.html')
        
        # Check if user exists with this email
        user = Enseignant.query.filter_by(Email_EN=email).first()
        if not user:
            # Don't reveal if email exists or not (security best practice)
            flash('Si votre email existe dans notre système, un code de vérification sera envoyé.', 'info')
            return render_template('forgot_password.html')
        
        # Generate a 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store OTP in database
        user.otp = otp
        user.otp_expires_at = datetime.now() + timedelta(minutes=15)  # OTP valid for 15 minutes
        db.session.commit()
        
        # Store user_id in session for the reset page
        session['reset_user_id'] = user.ID_EN
        
        # Send OTP via email
        try:
            from flask_mail import Message
            subject = "Réinitialisation de mot de passe - AssistProf"
            body = f"""Bonjour {user.Prenom_EN},

Vous avez demandé la réinitialisation de votre mot de passe.

Votre code de vérification est: {otp}

Ce code expire dans 15 minutes.

Si vous n'avez pas demandé cette réinitialisation, veuillez ignorer cet email.

Cordialement,
L'équipe AssistProf
"""
            msg = Message(subject, recipients=[email])
            msg.body = body
            mail.send(msg)
            
            flash('Un code de vérification a été envoyé à votre adresse email.', 'success')
            return redirect(url_for('reset_password', user_id=user.ID_EN))
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            flash('Une erreur est survenue lors de l\'envoi de l\'email. Veuillez réessayer plus tard.', 'danger')
    
    return render_template('forgot_password.html')

def reset_password_route(user_id):
    """Handle password reset with OTP verification"""
    # Check if user exists
    user = Enseignant.query.get(user_id)
    if not user:
        flash('Utilisateur non trouvé', 'danger')
        return redirect(url_for('login'))
    
    # Check if user_id in session matches the requested user_id (security check)
    if session.get('reset_user_id') != user.ID_EN:
        flash('Session invalide, veuillez recommencer le processus', 'danger')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        otp = request.form.get('otp')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not all([otp, password, confirm_password]):
            flash('Tous les champs sont obligatoires', 'danger')
            return render_template('reset_password.html', user_id=user_id)
        
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas', 'danger')
            return render_template('reset_password.html', user_id=user_id)
        
        # Check if OTP is valid and not expired
        if user.otp != otp:
            flash('Code de vérification invalide', 'danger')
            return render_template('reset_password.html', user_id=user_id)
        
        if user.otp_expires_at and user.otp_expires_at < datetime.now():
            flash('Le code de vérification a expiré. Veuillez recommencer le processus.', 'danger')
            return redirect(url_for('forgot_password'))
        
        # Reset password
        user.Mot_de_Passe = generate_password_hash(password)
        
        # Clear OTP data
        user.otp = None
        user.otp_expires_at = None
        
        db.session.commit()
        
        # Clear session data
        session.pop('reset_user_id', None)
        
        flash('Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', user_id=user_id)
