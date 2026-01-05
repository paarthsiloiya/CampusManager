#!/usr/bin/env python3
"""
Test Account Creation Script
Creates 8 test accounts fo        print("🔑 Test Account Credentials:")
        print("=" * 40)
        for i in range(1, 9):
            email = f"sem{i}test@gmail.com"
            user = User.query.filter_by(email=email).first()
            if user:
                print(f"Semester {i}:")
                print(f"  📧 Email: {email}")
                print(f"  🔒 Password: 12345678")
                print(f"  👤 Name: {user.name}")
                print(f"  🎓 Branch: {user.branch.value if user.branch else 'Unknown'}")
                print()ifferent semesters
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, User, Branch
from werkzeug.security import generate_password_hash

def create_test_accounts():
    """Create 8 test accounts for all semesters"""
    
    app = create_app()
    
    with app.app_context():
        print("🧪 Student Management System - Test Account Creator")
        print("=" * 55)
        
        # Check current users
        existing_users = User.query.all()
        print(f"\n📊 Current users in database: {len(existing_users)}")
        
        if existing_users:
            print("\n👥 Existing users:")
            for user in existing_users:
                print(f"   - {user.name} ({user.email}) - Semester {user.semester}")
        
        print("\n🔄 Creating test accounts...")
        
        created_count = 0
        skipped_count = 0
        
        # Available branches to cycle through
        branches = [Branch.AIML, Branch.AIDS, Branch.CST, Branch.CSE]
        
        for i in range(1, 9):  # Semesters 1-8
            name = f"Sem {i} Test"
            email = f"sem{i}test@gmail.com"
            phone = "9971959945"
            semester = i
            branch = branches[(i-1) % len(branches)]  # Cycle through branches
            password = "12345678"
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            
            if existing_user:
                print(f"   ⚠️  Skipping Semester {i}: User with email {email} already exists")
                skipped_count += 1
                continue
            
            # Create new user
            try:
                new_user = User(
                    name=name,
                    email=email,
                    phone=phone,
                    semester=semester,
                    branch=branch,
                    password_hash=generate_password_hash(password)
                )
                
                db.session.add(new_user)
                db.session.commit()
                
                print(f"   ✅ Created: {name} ({email}) - Semester {semester} - {branch.value}")
                created_count += 1
                
            except Exception as e:
                print(f"   ❌ Error creating user for Semester {i}: {str(e)}")
                db.session.rollback()
        
        print(f"\n🎉 Account creation completed!")
        print(f"   📊 Created: {created_count} new accounts")
        print(f"   ⚠️  Skipped: {skipped_count} existing accounts")
        
        # Display final summary
        all_users = User.query.all()
        print(f"\n📊 Total users in database: {len(all_users)}")
        
        print("\n🔑 Test Account Credentials:")
        print("=" * 40)
        for i in range(1, 9):
            email = f"sem{i}test@gmail.com"
            user = User.query.filter_by(email=email).first()
            if user:
                print(f"Semester {i}:")
                print(f"  📧 Email: {email}")
                print(f"  🔒 Password: 12345678")
                print(f"  👤 Name: {user.name}")
                print()
        
        print("💡 You can now log in with any of these accounts to test different semesters!")

if __name__ == "__main__":
    create_test_accounts()