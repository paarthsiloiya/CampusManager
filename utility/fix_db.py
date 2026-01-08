import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, User, UserRole, seed_subjects

def fix_database():
    app = create_app()
    with app.app_context():
        print("Dropping old tables...")
        db.drop_all()
        print("Creating database tables...")
        db.create_all()
        
        print("Seeding subjects...")
        try:
            seed_subjects()
        except Exception as e:
            print(f"Error seeding subjects: {e}")
        
        print("Creating users...")
        # Admin
        if not User.query.filter_by(email='admin@example.com').first():
            admin = User(
                name='Admin User',
                email='admin@example.com',
                role=UserRole.ADMIN,
                is_password_changed=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print("Created Admin: admin@example.com / admin123")
        else:
            print("Admin user already exists.")

        # Teacher
        if not User.query.filter_by(email='teacher@example.com').first():
            teacher = User(
                name='John Teacher',
                email='teacher@example.com',
                role=UserRole.TEACHER,
                department='CSE',
                is_password_changed=True
            )
            teacher.set_password('teacher123')
            db.session.add(teacher)
            print("Created Teacher: teacher@example.com / teacher123")
        else:
            print("Teacher user already exists.")

        db.session.commit()
        print("Database initialized successfully.")

if __name__ == "__main__":
    fix_database()
