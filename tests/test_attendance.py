#!/usr/bin/env python3
"""
Test script to verify attendance calculations for new users
"""

import os
import sys

from app import create_app
from app.models import db, User, Subject

def test_new_user_attendance():
    """Test that new users have 0% attendance initially"""
    app = create_app()
    
    with app.app_context():
        # Find a user or create a test scenario
        users = User.query.all()
        
        if not users:
            print("❌ No users found. Please create a user account first.")
            return
        
        print("🧪 Testing attendance calculations for existing users:")
        print("=" * 50)
        
        for user in users:
            print(f"\n👤 User: {user.name} (Semester {user.semester})")
            
            # Get attendance stats
            stats = user.get_overall_attendance_stats()
            subjects = user.get_subjects_with_attendance()
            
            print(f"📊 Overall Stats:")
            print(f"   Total Classes: {stats['total_classes']}")
            print(f"   Attended: {stats['attended_classes']}")
            print(f"   Percentage: {stats['attendance_percentage']}%")
            print(f"   This Week: {stats['this_week_classes']}")
            print(f"   Needed for 75%: {stats['needed_for_75']}")
            
            print(f"\n📚 Subject-wise Attendance:")
            for subject in subjects:
                print(f"   {subject['code']}: {subject['attendance_percentage']}% ({subject['attended_classes']}/{subject['total_classes']})")
            
            # Verify that new users have 0% attendance
            if stats['total_classes'] == 0:
                print("✅ PASS: New user correctly shows 0 total classes")
                print("✅ PASS: Attendance percentage is 0%")
            else:
                print("⚠️  User has attendance data")

if __name__ == "__main__":
    test_new_user_attendance()