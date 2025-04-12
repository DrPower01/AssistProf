from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import random
from models import db, Enseignant
import logging

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
                otp=otp
            )
            
            db.session.add(new_user)
            db.session.commit()
            
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
                # Store the OTP in session for display on the verification page
                session['display_otp'] = otp
                session['email_error'] = str(e)
                flash(f'Could not send verification email. Please use this verification code instead: {otp}')
            
            # Redirect to verification page
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
    
    if user.is_verified:
        flash('Account already verified. Please log in.', 'info')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        submitted_otp = request.form.get('otp')
        stored_otp = session.get('otp')
        
        if submitted_otp == stored_otp:
            # OTP matches, verify the user
            user.is_verified = True
            db.session.commit()
            
            # Clear OTP from session
            session.pop('otp', None)
            
            flash('Account verified successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid verification code. Please try again.', 'danger')
    
    # Don't show OTP for debugging anymore
    return render_template('verify_otp.html', user_id=user_id)

def logout_route():
    logout_user()
    session.clear()
    return redirect(url_for('index'))
