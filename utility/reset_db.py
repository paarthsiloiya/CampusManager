#!/usr/bin/env python3
"""
Database Reset Script for Student Management System

This script provides functionality to:
1. Reset (drop and recreate) all database tables
2. Clear all user data while keeping the database structure
3. Re-seed the database with sample subjects

Usage:
    python reset_db.py              # Reset entire database and re-seed
    python reset_db.py --clear-only # Clear data but keep tables
    python reset_db.py --help       # Show help message

WARNING: This will permanently delete all data in the database!
"""

import os
import sys
import argparse
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, User, Subject, Attendance, Marks, AttendanceSummary, reset_database, seed_subjects

def confirm_action(action_description):
    """Ask user for confirmation before performing destructive actions"""
    print(f"\n⚠️  WARNING: {action_description}")
    print("This action cannot be undone!")
    
    response = input("\nType 'YES' to confirm (case-sensitive): ")
    if response != 'YES':
        print("❌ Action cancelled.")
        return False
    return True

def reset_entire_database():
    """Reset the entire database - drop all tables and recreate them"""
    print("🔄 Resetting entire database...")
    
    if not confirm_action("This will DELETE ALL DATA and recreate the database"):
        return False
    
    try:
        # Drop all tables
        db.drop_all()
        print("✅ All tables dropped successfully")
        
        # Create all tables
        db.create_all()
        print("✅ All tables created successfully")
        
        # Seed with sample subjects
        seed_subjects()
        print("✅ Database seeded with sample subjects")
        
        print("\n🎉 Database reset completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during database reset: {str(e)}")
        return False

def clear_user_data():
    """Clear all user data but keep the database structure intact"""
    print("🧹 Clearing user data...")
    
    if not confirm_action("This will DELETE ALL USER DATA but keep the database structure"):
        return False
    
    try:
        # Delete user data in order (due to foreign key constraints)
        db.session.query(Attendance).delete()
        db.session.query(Marks).delete()
        db.session.query(AttendanceSummary).delete()
        db.session.query(User).delete()
        
        # Commit the changes
        db.session.commit()
        
        print("✅ All user data cleared successfully")
        print("✅ Database structure preserved")
        print("✅ Subject data preserved")
        
        print("\n🎉 User data cleanup completed successfully!")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error during data cleanup: {str(e)}")
        return False

def show_database_stats():
    """Show current database statistics"""
    try:
        user_count = db.session.query(User).count()
        subject_count = db.session.query(Subject).count()
        attendance_count = db.session.query(Attendance).count()
        marks_count = db.session.query(Marks).count()
        
        print("\n📊 Current Database Statistics:")
        print(f"   👥 Users: {user_count}")
        print(f"   📚 Subjects: {subject_count}")
        print(f"   📋 Attendance Records: {attendance_count}")
        print(f"   📊 Marks Records: {marks_count}")
        
        if user_count > 0:
            print("\n👥 Users in database:")
            users = db.session.query(User).all()
            for user in users:
                print(f"   - {user.name} ({user.email}) - Semester {user.semester}")
        
    except Exception as e:
        print(f"❌ Error reading database stats: {str(e)}")

def main():
    """Main function to handle command line arguments and execute appropriate actions"""
    parser = argparse.ArgumentParser(
        description="Reset or clear the Student Management System database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python reset_db.py                 Reset entire database
  python reset_db.py --clear-only    Clear user data only
  python reset_db.py --stats         Show database statistics
        """
    )
    
    parser.add_argument(
        '--clear-only', 
        action='store_true',
        help='Clear user data only, preserve database structure and subjects'
    )
    
    parser.add_argument(
        '--stats', 
        action='store_true',
        help='Show current database statistics without making changes'
    )
    
    args = parser.parse_args()
    
    # Create Flask app and set up database context
    app = create_app()
    
    with app.app_context():
        print("🚀 Student Management System - Database Reset Tool")
        print("=" * 50)
        
        # Show current stats first
        show_database_stats()
        
        if args.stats:
            # Only show stats, don't make changes
            print("\n✅ Statistics displayed. No changes made.")
            return
        
        if args.clear_only:
            # Clear user data only
            success = clear_user_data()
        else:
            # Reset entire database
            success = reset_entire_database()
        
        # Show final stats
        if success:
            print("\n" + "=" * 50)
            show_database_stats()

if __name__ == "__main__":
    main()