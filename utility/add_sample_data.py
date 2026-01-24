#!/usr/bin/env python3
"""
Sample Data Generator for Student Management System

This script adds sample attendance and marks data for testing purposes.
It's useful for demonstrating the system with realistic data.

Usage:
    python add_sample_data.py              # Add sample data for all users
    python add_sample_data.py --user-id 1  # Add sample data for specific user
    python add_sample_data.py --help       # Show help message
"""

import os
import sys
import argparse
from datetime import date, timedelta
import random

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, User, Subject, Attendance, Marks

def add_sample_attendance(user_id, days_back=30):
    """Add sample attendance data for a user"""
    user = db.session.get(User, user_id)
    if not user:
        print(f"❌ User with ID {user_id} not found")
        return False
    
    subjects = user.get_subjects_for_semester()
    if not subjects:
        print(f"❌ No subjects found for user {user.name} in semester {user.semester}")
        return False
    
    print(f"📊 Adding sample attendance for {user.name} (Semester {user.semester})")
    
    # Generate attendance for last N days
    start_date = date.today() - timedelta(days=days_back)
    
    added_count = 0
    for subject in subjects:
        # Generate random attendance pattern (70-95% attendance)
        attendance_rate = random.uniform(0.7, 0.95)
        
        for i in range(days_back):
            current_date = start_date + timedelta(days=i)
            
            # Skip weekends (assuming classes are Monday-Friday)
            if current_date.weekday() >= 5:
                continue
            
            # Random chance of having class on this day (60% chance)
            if random.random() < 0.6:
                # Determine attendance status based on attendance rate
                if random.random() < attendance_rate:
                    status = 'present'
                else:
                    status = 'absent'
                
                # Check if attendance already exists
                existing = Attendance.query.filter_by(
                    user_id=user_id,
                    subject_id=subject.id,
                    date=current_date
                ).first()
                
                if not existing:
                    attendance = Attendance(
                        user_id=user_id,
                        subject_id=subject.id,
                        date=current_date,
                        status=status,
                        class_type='lecture'
                    )
                    db.session.add(attendance)
                    added_count += 1
    
    try:
        db.session.commit()
        print(f"✅ Added {added_count} attendance records for {user.name}")
        
        # Show updated statistics
        stats = user.get_overall_attendance_stats()
        print(f"📈 Updated stats: {stats['attended_classes']}/{stats['total_classes']} = {stats['attendance_percentage']}%")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error adding attendance data: {str(e)}")
        return False

def add_sample_marks(user_id):
    """Add sample marks data for a user"""
    user = db.session.get(User, user_id)
    if not user:
        print(f"❌ User with ID {user_id} not found")
        return False
    
    subjects = user.get_subjects_for_semester()
    if not subjects:
        print(f"❌ No subjects found for user {user.name}")
        return False
    
    print(f"📊 Adding sample marks for {user.name}")
    
    assessment_types = [
        ('Quiz 1', 'quiz', 10),
        ('Assignment 1', 'assignment', 25),
        ('Midterm Exam', 'midterm', 50),
        ('Quiz 2', 'quiz', 10),
        ('Assignment 2', 'assignment', 25),
        ('Final Exam', 'final', 100)
    ]
    
    added_count = 0
    for subject in subjects:
        for assessment_name, assessment_type, max_marks in assessment_types:
            # Generate random marks (60-95% of max marks)
            obtained_marks = random.uniform(0.6, 0.95) * max_marks
            obtained_marks = round(obtained_marks, 1)
            
            # Check if marks already exist
            existing = Marks.query.filter_by(
                user_id=user_id,
                subject_id=subject.id,
                assessment_name=assessment_name
            ).first()
            
            if not existing:
                marks = Marks(
                    user_id=user_id,
                    subject_id=subject.id,
                    assessment_type=assessment_type,
                    assessment_name=assessment_name,
                    max_marks=max_marks,
                    obtained_marks=obtained_marks,
                    assessment_date=date.today() - timedelta(days=random.randint(1, 60))
                )
                db.session.add(marks)
                added_count += 1
    
    try:
        db.session.commit()
        print(f"✅ Added {added_count} marks records for {user.name}")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error adding marks data: {str(e)}")
        return False

def list_users():
    """List all users in the database"""
    users = User.query.all()
    if not users:
        print("❌ No users found in database")
        return
    
    print("\n👥 Users in database:")
    for user in users:
        print(f"   ID: {user.id} | {user.name} ({user.email}) | Semester {user.semester}")

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(
        description="Add sample attendance and marks data for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--user-id',
        type=int,
        help='Add sample data for specific user ID only'
    )
    
    parser.add_argument(
        '--list-users',
        action='store_true',
        help='List all users and their IDs'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days back to generate attendance data (default: 30)'
    )
    
    parser.add_argument(
        '--attendance-only',
        action='store_true',
        help='Add only attendance data, skip marks'
    )
    
    parser.add_argument(
        '--marks-only',
        action='store_true',
        help='Add only marks data, skip attendance'
    )
    
    args = parser.parse_args()
    
    # Create Flask app and set up database context
    app = create_app()
    
    with app.app_context():
        print("🚀 Student Management System - Sample Data Generator")
        print("=" * 55)
        
        if args.list_users:
            list_users()
            return
        
        if args.user_id:
            # Add data for specific user
            user = db.session.get(User, args.user_id)
            if not user:
                print(f"❌ User with ID {args.user_id} not found")
                list_users()
                return
            
            success = True
            if not args.marks_only:
                success &= add_sample_attendance(args.user_id, args.days)
            
            if not args.attendance_only:
                success &= add_sample_marks(args.user_id)
            
            if success:
                print(f"\n🎉 Sample data added successfully for {user.name}!")
        else:
            # Add data for all users
            users = User.query.all()
            if not users:
                print("❌ No users found in database")
                print("💡 Create a user account first by signing up through the web interface")
                return
            
            print(f"📊 Adding sample data for {len(users)} users...")
            
            for user in users:
                print(f"\n👤 Processing {user.name}...")
                
                if not args.marks_only:
                    add_sample_attendance(user.id, args.days)
                
                if not args.attendance_only:
                    add_sample_marks(user.id)
            
            print(f"\n🎉 Sample data generation completed for all users!")

if __name__ == "__main__":
    main()