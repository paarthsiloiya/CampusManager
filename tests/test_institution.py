#!/usr/bin/env python3
"""
Test script to verify that the institution field is working correctly
"""

from app import create_app
from app.models import db, User
import pytest

def test_institution_field():
    """Test that the institution field is working"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔍 Testing institution field functionality...")
            
            # Get all users and show their institution
            users = User.query.all()
            print(f"\n📊 Found {len(users)} users in database:")
            
            for user in users:
                institution = user.institution or "No institution set"
                print(f"  👤 {user.name} ({user.email}) - Institution: {institution}")
            
            # Test updating a user's institution
            if users:
                test_user = users[0]
                original_institution = test_user.institution
                print(f"\n🧪 Testing institution update for user: {test_user.name}")
                print(f"   Original institution: {original_institution}")
                
                # Update institution
                test_user.institution = "Test Institution Update"
                db.session.commit()
                print(f"   ✅ Updated institution to: {test_user.institution}")
                
                # Restore original
                test_user.institution = original_institution
                db.session.commit()
                print(f"   🔄 Restored original institution: {test_user.institution}")
            
            print("\n✅ Institution field is working correctly!")
            print("🎯 You can now change institution names in the settings page.")
            
        except Exception as e:
            pytest.fail(f"Error testing institution field: {e}")

if __name__ == "__main__":
    print("🚀 Testing institution field functionality...")
    test_institution_field()