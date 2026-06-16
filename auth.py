from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from app import db, mail
from app.models import User, DeliveryPartner
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__)

def send_welcome_email(user):
    msg = Message('Welcome to PharmaPlus!',
                  recipients=[user.email])
    msg.body = f"Hello {user.username},\n\nWelcome to our PharmaPlus portal! We are glad to have you with us.\n\nBest Regards,\nPharmaPlus Team"
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        flash(f'Note: Could not send welcome email due to configuration issues.', 'warning')
        return False

def send_welcome_sms(user):
    """
    Simulates sending an SMS to the user upon registration.
    In a real-world scenario, you would integrate Twilio or a similar SMS API here.
    """
    if user.phone_number:
        # For simulation: Print to console and return True
        print(f"--- SMS SENT ---")
        print(f"To: {user.phone_number}")
        print(f"Message: Hello {user.username}, welcome to PharmaPlus! Your account is now active.")
        print(f"----------------")
        return True
    return False

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        identifier = request.form.get('email') or request.form.get('phone')
        password = request.form.get('password')
        # We search for the user regardless of the role passed in form, 
        # then we use their actual role from the database.
        user = User.query.filter(
            ((User.email == identifier) | (User.phone_number == identifier) | (User.username == identifier))
        ).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            # Determine redirection based on the actual user role
            role = user.role
            next_page = request.args.get('next')
            if role == 'admin':
                return redirect(next_page or url_for('admin.dashboard'))
            elif role == 'delivery_partner':
                return redirect(next_page or url_for('delivery.dashboard'))
            return redirect(next_page or url_for('user.dashboard'))
        else:
            flash('Login Unsuccessful. Please check credentials', 'danger')
            
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        # Check if any of the identifiers already exist
        user_exists = User.query.filter(
            (User.email == email) | (User.username == username) | (User.phone_number == phone_number)
        ).first()
        
        if user_exists:
            if user_exists.email == email:
                flash('Email already registered.', 'danger')
            elif user_exists.username == username:
                flash('Username already taken.', 'danger')
            else:
                flash('Phone number already registered.', 'danger')
        else:
            try:
                new_user = User(username=username, email=email, phone_number=phone_number, role=role)
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.flush() # Get user id for relations
                
                if role == 'delivery_partner':
                    vehicle_number = request.form.get('vehicle_number')
                    if not vehicle_number:
                        raise ValueError("Vehicle number is required for delivery partners.")
                    new_partner = DeliveryPartner(user_id=new_user.id, vehicle_number=vehicle_number)
                    db.session.add(new_partner)
                    
                db.session.commit()
                
                if email:
                    send_welcome_email(new_user)
                
                if phone_number:
                    send_welcome_sms(new_user)
                
                flash(f'Account created successfully as {role.replace("_", " ").title()}! You can now login.', 'success')
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.session.rollback()
                print(f"Registration Error: {e}")
                flash(f'Error during registration: {str(e)}', 'danger')
            
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
