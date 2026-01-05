#!/usr/bin/env python3
"""
Advanced Attendance Testing & Generation Script
Creates realistic attendance data for test accounts with various scenarios
"""

import sys
import os
import random
from datetime import datetime, date, timedelta

# Add the app directory to Python path for standalone execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, User, Subject, Attendance

class AttendanceGenerator:
    """Class to generate and manage attendance test data"""
    
    def __init__(self):
        self.app = create_app()
        self.scenarios = {
            'excellent': {'percentage': 95, 'description': 'Excellent student (95% attendance)'},
            'good': {'percentage': 85, 'description': 'Good student (85% attendance)'},
            'average': {'percentage': 75, 'description': 'Average student (75% attendance)'},
            'warning': {'percentage': 65, 'description': 'Warning zone (65% attendance)'},
            'poor': {'percentage': 45, 'description': 'Poor attendance (45% attendance)'},
            'mixed': {'percentage': 'random', 'description': 'Mixed attendance pattern'}
        }
    
    def get_user_by_email(self, email):
        """Get user by email address"""
        with self.app.app_context():
            return User.query.filter_by(email=email).first()
    
    def get_subjects_for_user(self, user):
        """Get all subjects for a user's semester and branch"""
        with self.app.app_context():
            return user.get_subjects_for_semester()
    
    def clear_attendance_for_user(self, user_email):
        """Clear all attendance records for a specific user"""
        with self.app.app_context():
            user = self.get_user_by_email(user_email)
            if not user:
                print(f"❌ User with email {user_email} not found")
                return False
            
            # Delete existing attendance records
            deleted_count = Attendance.query.filter_by(user_id=user.id).delete()
            db.session.commit()
            
            print(f"🗑️  Cleared {deleted_count} existing attendance records for {user.name}")
            return True
    
    def generate_attendance_dates(self, weeks_back=12, classes_per_week=3):
        """Generate realistic class dates (excluding weekends)"""
        dates = []
        current_date = date.today()
        
        for week in range(weeks_back):
            week_start = current_date - timedelta(weeks=week)
            
            # Add classes on weekdays only (Monday to Friday)
            for day in range(5):  # 0=Monday, 4=Friday
                class_date = week_start - timedelta(days=week_start.weekday()) + timedelta(days=day)
                
                # Randomly skip some days to make it realistic
                if random.random() < 0.7:  # 70% chance of having class
                    dates.append(class_date)
                
                if len(dates) >= classes_per_week * weeks_back:
                    break
        
        return sorted(dates)[:classes_per_week * weeks_back]
    
    def create_attendance_record(self, user, subject, class_date, status='present'):
        """Create a single attendance record"""
        # Check if record already exists
        existing = Attendance.query.filter_by(
            user_id=user.id,
            subject_id=subject.id,
            date=class_date
        ).first()
        
        if existing:
            return False
        
        attendance = Attendance(
            user_id=user.id,
            subject_id=subject.id,
            date=class_date,
            status=status,
            class_type='lecture',
            recorded_at=datetime.now()
        )
        
        db.session.add(attendance)
        return True
    
    def generate_attendance_for_scenario(self, user_email, scenario_name, weeks_back=12, classes_per_week=3):
        """Generate attendance based on predefined scenarios"""
        with self.app.app_context():
            user = self.get_user_by_email(user_email)
            if not user:
                print(f"❌ User with email {user_email} not found")
                return False
            
            if scenario_name not in self.scenarios:
                print(f"❌ Scenario '{scenario_name}' not found")
                print(f"Available scenarios: {list(self.scenarios.keys())}")
                return False
            
            scenario = self.scenarios[scenario_name]
            subjects = self.get_subjects_for_user(user)
            
            if not subjects:
                print(f"❌ No subjects found for {user.name} (Semester {user.semester}, {user.branch.value})")
                return False
            
            print(f"👤 Generating attendance for: {user.name}")
            print(f"📊 Scenario: {scenario['description']}")
            print(f"📚 Subjects: {len(subjects)} subjects")
            print(f"📅 Duration: {weeks_back} weeks, {classes_per_week} classes/week per subject")
            print("-" * 60)
            
            total_records = 0
            
            for subject in subjects:
                print(f"📖 Processing: {subject.name} ({subject.code})")
                
                # Generate class dates
                class_dates = self.generate_attendance_dates(weeks_back, classes_per_week)
                
                # Calculate attendance based on scenario
                if scenario['percentage'] == 'random':
                    # Mixed scenario: random attendance between 40-95%
                    target_percentage = random.randint(40, 95)
                else:
                    target_percentage = scenario['percentage']
                
                # Determine how many classes to attend
                total_classes = len(class_dates)
                classes_to_attend = int((target_percentage / 100) * total_classes)
                
                # Randomly select which classes to attend
                attend_dates = random.sample(class_dates, classes_to_attend)
                
                # Create attendance records
                subject_records = 0
                for class_date in class_dates:
                    status = 'present' if class_date in attend_dates else 'absent'
                    
                    if self.create_attendance_record(user, subject, class_date, status):
                        subject_records += 1
                
                actual_percentage = (classes_to_attend / total_classes * 100) if total_classes > 0 else 0
                print(f"   ✅ Created {subject_records} records | Target: {target_percentage}% | Actual: {actual_percentage:.1f}%")
                total_records += subject_records
            
            # Commit all changes and refresh the user object
            try:
                db.session.commit()
                # Refresh user to get updated data
                db.session.refresh(user)
                print(f"\n🎉 Successfully created {total_records} attendance records!")
                print("🔄 Refreshing database session...")
                return True
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error committing attendance records: {str(e)}")
                return False
    
    def verify_attendance_records(self, user_email):
        """Verify that attendance records exist in the database"""
        with self.app.app_context():
            user = self.get_user_by_email(user_email)
            if not user:
                return False
            
            total_records = Attendance.query.filter_by(user_id=user.id).count()
            print(f"🔍 Verification: Found {total_records} attendance records in database for {user.name}")
            
            if total_records > 0:
                # Show a sample of records
                sample_records = Attendance.query.filter_by(user_id=user.id).limit(3).all()
                print("📋 Sample records:")
                for record in sample_records:
                    print(f"   - {record.subject.name}: {record.status} on {record.date}")
            
            return total_records > 0
    def show_attendance_stats(self, user_email):
        """Display detailed attendance statistics for a user"""
        with self.app.app_context():
            user = self.get_user_by_email(user_email)
            if not user:
                print(f"❌ User with email {user_email} not found")
                return
            
            # First verify records exist
            self.verify_attendance_records(user_email)
            
            print(f"\n📊 ATTENDANCE STATISTICS FOR {user.name}")
            print("=" * 60)
            
            # Overall stats
            overall_stats = user.get_overall_attendance_stats()
            print(f"📈 Overall Attendance:")
            print(f"   Total Classes: {overall_stats['total_classes']}")
            print(f"   Attended: {overall_stats['attended_classes']}")
            print(f"   Percentage: {overall_stats['attendance_percentage']}%")
            print(f"   This Week: {overall_stats['this_week_classes']}")
            print(f"   Classes needed for 75%: {overall_stats['needed_for_75']}")
            
            # Subject-wise breakdown
            subjects_data = user.get_subjects_with_attendance()
            print(f"\n📚 Subject-wise Breakdown:")
            print("-" * 60)
            
            for subject in subjects_data:
                status_emoji = "🟢" if subject['status'] == 'good' else "🟡" if subject['status'] == 'warning' else "🔴"
                print(f"{status_emoji} {subject['name']}")
                print(f"   Code: {subject['code']}")
                print(f"   Attendance: {subject['attendance_percentage']}% ({subject['attended_classes']}/{subject['total_classes']})")
                print()
            
            # Debug: Check raw attendance data
            if overall_stats['total_classes'] == 0:
                print("\n🔧 DEBUG: Checking raw attendance records...")
                raw_count = Attendance.query.filter_by(user_id=user.id).count()
                print(f"   Raw attendance records in DB: {raw_count}")
                
                if raw_count > 0:
                    print("   This suggests an issue with the attendance calculation logic.")
                    # Show some sample records
                    samples = Attendance.query.filter_by(user_id=user.id).limit(5).all()
                    for sample in samples:
                        print(f"   Sample: Subject ID {sample.subject_id}, Status: {sample.status}, Date: {sample.date}")
    
    def create_sample_scenario(self):
        """Create a comprehensive test scenario with multiple attendance patterns"""
        test_users = [
            {'email': 'sem1test@gmail.com', 'scenario': 'excellent'},
            {'email': 'sem2test@gmail.com', 'scenario': 'good'},
            {'email': 'sem3test@gmail.com', 'scenario': 'average'},
            {'email': 'sem4test@gmail.com', 'scenario': 'warning'},
            {'email': 'sem5test@gmail.com', 'scenario': 'poor'},
            {'email': 'sem6test@gmail.com', 'scenario': 'mixed'}
        ]
        
        print("🎭 CREATING COMPREHENSIVE ATTENDANCE TEST SCENARIOS")
        print("=" * 60)
        
        successful_generations = 0
        
        for test_case in test_users:
            print(f"\n{'='*20} {test_case['email']} {'='*20}")
            
            # Clear existing attendance
            if self.clear_attendance_for_user(test_case['email']):
                # Generate new attendance
                if self.generate_attendance_for_scenario(
                    test_case['email'], 
                    test_case['scenario'],
                    weeks_back=10,
                    classes_per_week=4
                ):
                    successful_generations += 1
                    
                    # Show stats
                    self.show_attendance_stats(test_case['email'])
        
        print(f"\n🏆 SUMMARY: Successfully generated attendance for {successful_generations}/{len(test_users)} users")

def main():
    """Main function with interactive menu"""
    generator = AttendanceTestGenerator()
    
    while True:
        print("\n" + "="*60)
        print("🎯 ATTENDANCE TEST GENERATOR")
        print("="*60)
        print("1. Generate attendance for specific user")
        print("2. Show attendance stats for user")
        print("3. Clear attendance for user")
        print("4. Create comprehensive test scenarios (all test users)")
        print("5. Generate attendance for sem1test@gmail.com (default)")
        print("6. List available scenarios")
        print("7. Debug: Verify attendance records")
        print("8. Exit")
        print("-"*60)
        
        choice = input("Enter your choice (1-8): ").strip()
        
        if choice == '1':
            email = input("Enter user email: ").strip()
            if not email:
                email = 'sem1test@gmail.com'
            
            print("\nAvailable scenarios:")
            for name, info in generator.scenarios.items():
                print(f"  {name}: {info['description']}")
            
            scenario = input("Enter scenario name: ").strip()
            weeks = int(input("Enter weeks back (default 12): ") or 12)
            classes = int(input("Enter classes per week (default 3): ") or 3)
            
            generator.clear_attendance_for_user(email)
            if generator.generate_attendance_for_scenario(email, scenario, weeks, classes):
                generator.show_attendance_stats(email)
        
        elif choice == '2':
            email = input("Enter user email (default: sem1test@gmail.com): ").strip()
            if not email:
                email = 'sem1test@gmail.com'
            generator.show_attendance_stats(email)
        
        elif choice == '3':
            email = input("Enter user email: ").strip()
            if email:
                generator.clear_attendance_for_user(email)
        
        elif choice == '4':
            confirm = input("This will create attendance for all test users. Continue? (y/N): ").strip().lower()
            if confirm == 'y':
                generator.create_sample_scenario()
        
        elif choice == '5':
            print("Generating excellent attendance scenario for sem1test@gmail.com...")
            generator.clear_attendance_for_user('sem1test@gmail.com')
            if generator.generate_attendance_for_scenario('sem1test@gmail.com', 'excellent'):
                # Add a small delay to ensure database consistency
                import time
                time.sleep(1)
                generator.show_attendance_stats('sem1test@gmail.com')
        
        elif choice == '6':
            print("\n📋 Available Attendance Scenarios:")
            for name, info in generator.scenarios.items():
                print(f"  • {name}: {info['description']}")
        
        elif choice == '7':
            email = input("Enter user email (default: sem1test@gmail.com): ").strip()
            if not email:
                email = 'sem1test@gmail.com'
            generator.verify_attendance_records(email)
        
        elif choice == '8':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()