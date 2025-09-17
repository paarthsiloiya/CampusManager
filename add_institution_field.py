#!/usr/bin/env python3
"""
Database migration script to add institution field to existing users
Run this script to update your database schema with the new institution field.
"""

from app import create_app
from app.models import db, User

def migrate_add_institution():
    """Add institution field to existing users"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔍 Checking if migration is needed...")
            
            # Try to query institution column to see if it exists
            try:
                # This will fail if column doesn't exist
                db.session.execute(db.text('SELECT institution FROM users LIMIT 1'))
                print("✅ Institution column already exists!")
                return True
            except:
                print("📋 Institution column not found. Adding it now...")
                
                # Add the column using raw SQL with proper text() wrapper
                if 'sqlite' in str(db.engine.url):
                    # SQLite syntax
                    db.session.execute(db.text('ALTER TABLE users ADD COLUMN institution VARCHAR(200) DEFAULT "Delhi Technical Campus"'))
                else:
                    # PostgreSQL/MySQL syntax
                    db.session.execute(db.text("ALTER TABLE users ADD COLUMN institution VARCHAR(200) DEFAULT 'Delhi Technical Campus'"))
                
                db.session.commit()
                print("✅ Institution column added successfully!")
                
                # Update existing users to have the default institution
                users = User.query.all()
                for user in users:
                    user.institution = 'Delhi Technical Campus'
                
                db.session.commit()
                print(f"✅ Updated {len(users)} existing users with default institution")
                
            print("🎉 Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("🚀 Starting database migration to add institution field...")
    print("🔧 This will add the 'institution' column to the users table.")
    print()
    
    success = migrate_add_institution()
    
    if success:
        print()
        print("✅ Migration completed successfully!")
        print("🎯 You can now update institution names in the settings page.")
        print("📝 Institution field has been added to all existing users.")
    else:
        print()
        print("❌ Migration failed. Please check the error messages above.")
        print("💡 Try running the app first to make sure the database is created.")