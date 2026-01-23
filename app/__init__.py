import os
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv

def create_app():
    # Load environment variables from .env file
    load_dotenv()
    
    app = Flask(__name__)
    # Application metadata
    app.config['APP_NAME'] = 'CampusManager'
    
    # Load secret key from environment with fallback
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secret_key_for_development')
    
    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///student_management.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    from .models import db, User
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/auth')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Seed subjects if they don't exist
        from .models import seed_subjects
        seed_subjects()
    
    return app