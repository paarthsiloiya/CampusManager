import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, User, UserRole

app = create_app()

with app.app_context():
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            name='Admin User',
            email='admin@example.com',
            role=UserRole.ADMIN,
            is_password_changed=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: admin@example.com / admin123")
    else:
        print("Admin user already exists")