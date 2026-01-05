from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from .models import db, User, Branch, UserRole
from datetime import datetime

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        if current_user.role == UserRole.ADMIN:
            return redirect(url_for('views.admin_dashboard'))
        elif current_user.role == UserRole.TEACHER:
            return redirect(url_for('views.teacher_dashboard'))
        else:
            return redirect(url_for('views.student_dashboard'))
    
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember-me') == 'on'
        
        # Validate input
        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return redirect(url_for('auth.login'))
        
        # Find user in database
        user = User.query.filter_by(email=email.lower().strip()).first()
        
        # Check if user exists and password is correct
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.name}!', 'success')
            
            # Redirect to next page if specified, otherwise dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            if user.role == UserRole.ADMIN:
                return redirect(url_for('views.admin_dashboard'))
            elif user.role == UserRole.TEACHER:
                return redirect(url_for('views.teacher_dashboard'))
            else:
                return redirect(url_for('views.student_dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            return redirect(url_for('auth.login'))
    
    # GET request - show login form
    return render_template('Auth/login.html')

@auth.route('/signin', methods=['GET', 'POST'])
def signin():
    flash('Student registration is disabled. Please contact your administrator.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    name = current_user.name
    logout_user()
    flash(f'You have been logged out successfully. Goodbye, {name}!', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/profile')
@login_required
def profile():
    """User profile page - placeholder for future implementation"""
    return render_template('Student/profile.html')  # You can create this template later