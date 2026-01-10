import sys
import os

# Add the project root to the path so we can import app modules
start_path = os.getcwd()
sys.path.append(start_path)

from app import create_app
from app.models import db, User, UserRole, Subject, AssignedClass
from werkzeug.security import generate_password_hash

# ==========================================
# CONFIGURATION SECTION
# Edit this section to define your teachers and their subjects
# ==========================================

TEACHERS_DATA = [
    {
        "name": "Rachna",
        "email": "rachna@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            {"code": "ES-101", "branch": "CSE"},
            {"code": "ES-101", "branch": "CST"},
            {"code": "ES-102", "branch": "AIML"},
            {"code": "ES-102", "branch": "AIDS"},
            #Labs
            {"code": "ES-153", "branch": "CSE"},
            {"code": "ES-153", "branch": "CST"},
            {"code": "ES-154", "branch": "AIML"},
            {"code": "ES-154", "branch": "AIDS"},
        ]
    },
    {
        "name": "Neeta",
        "email": "neeta@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            {"code": "BS-103", "branch": "AIML"},
            {"code": "BS-103", "branch": "AIDS"},
            {"code": "BS-104", "branch": "CSE"},
            {"code": "BS-104", "branch": "CST"},
            #Labs
            {"code": "BS-155", "branch": "AIML"},
            {"code": "BS-155", "branch": "AIDS"},
            {"code": "BS-156", "branch": "CSE"},
            {"code": "BS-156", "branch": "CST"}
        ]
    },
    {
        "name": "Asha",
        "email": "asha@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            {"code": "BS-105", "branch": "AIML"},
            {"code": "BS-105", "branch": "AIDS"},
            {"code": "BS-106", "branch": "CSE"},
            {"code": "BS-106", "branch": "CST"},
            #Labs
            {"code": "BS-151", "branch": "AIML"},
            {"code": "BS-151", "branch": "AIDS"},
            {"code": "BS-152", "branch": "CSE"},
            {"code": "BS-152", "branch": "CST"}
        ]
    },
    {
        "name": "Indolia",
        "email": "indolia@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            {"code": "BS-105", "branch": "CSE"},
            {"code": "BS-105", "branch": "CST"},
            {"code": "BS-106", "branch": "AIML"},
            {"code": "BS-106", "branch": "AIDS"},
            #Labs
            {"code": "BS-151", "branch": "CSE"},
            {"code": "BS-151", "branch": "CST"},
            {"code": "BS-152", "branch": "AIML"},
            {"code": "BS-152", "branch": "AIDS"}
        ]
    },
    {
        "name": "Satvaveer",
        "email": "satvaveer@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            {"code": "ES-107", "branch": "AIML"},
            {"code": "ES-107", "branch": "AIDS"},
            {"code": "ES-108", "branch": "CSE"},
            {"code": "ES-108", "branch": "CST"},
            #Labs
            {"code": "ES-159", "branch": "AIML"},
            {"code": "ES-159", "branch": "AIDS"},
            {"code": "ES-159", "branch": "CSE"},
            {"code": "ES-159", "branch": "CST"},
            {"code": "ES-160", "branch": "AIML"},
            {"code": "ES-160", "branch": "AIDS"},
            {"code": "ES-160", "branch": "CSE"},
            {"code": "ES-160", "branch": "CST"}
        ]
    },
    {
        "name": "Mahak",
        "email": "mahak@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            {"code": "ES-107", "branch": "CSE"},
            {"code": "ES-107", "branch": "CST"},
            {"code": "ES-108", "branch": "AIML"},
            {"code": "ES-108", "branch": "AIDS"}
        ]
    },
    {
        "name": "Alka",
        "email": "alka@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            {"code": "BS-109", "branch": "CSE"},
            {"code": "BS-109", "branch": "CST"},
            {"code": "BS-110", "branch": "AIML"},
            {"code": "BS-110", "branch": "AIDS"},
            #Labs
            {"code": "BS-161", "branch": "CSE"},
            {"code": "BS-161", "branch": "CST"},
            {"code": "BS-162", "branch": "AIML"},
            {"code": "BS-162", "branch": "AIDS"}
        ]
    },
    {
        "name": "Devesh",
        "email": "devesh@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            {"code": "BS-111", "branch": "AIML"},
            {"code": "BS-111", "branch": "AIDS"},
            {"code": "BS-111", "branch": "CSE"},
            {"code": "BS-111", "branch": "CST"},
            {"code": "BS-112", "branch": "AIML"},
            {"code": "BS-112", "branch": "AIDS"},
            {"code": "BS-112", "branch": "CSE"},
            {"code": "BS-112", "branch": "CST"}
        ]
    },
    {
        "name": "UHV",
        "email": "uhv@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            {"code": "HS-117", "branch": "AIML"},
            {"code": "HS-117", "branch": "AIDS"},
            {"code": "HS-113", "branch": "CSE"},
            {"code": "HS-113", "branch": "CST"},
            {"code": "HS-118", "branch": "AIML"},
            {"code": "HS-118", "branch": "AIDS"},
            {"code": "HS-114", "branch": "CSE"},
            {"code": "HS-114", "branch": "CST"}
        ]
    },
    {
        "name": "DG",
        "email": "dg@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            {"code": "HS-115", "branch": "AIML"},
            {"code": "HS-115", "branch": "AIDS"},
            {"code": "HS-116", "branch": "CSE"},
            {"code": "HS-116", "branch": "CST"}

        ]
    },
    {
        "name": "Dhaka",
        "email": "dhaka@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            {"code": "ES-119", "branch": "AIML"},
            {"code": "ES-119", "branch": "AIDS"},
            {"code": "ES-119", "branch": "CSE"},
            {"code": "ES-119", "branch": "CST"},
            {"code": "ES-114", "branch": "AIML"},
            {"code": "ES-114", "branch": "AIDS"},
            {"code": "ES-114", "branch": "CSE"},
            {"code": "ES-114", "branch": "CST"},
            ##Labs
            {"code": "ES-157", "branch": "CSE"},
            {"code": "ES-157", "branch": "CST"},
            {"code": "ES-158", "branch": "CSE"},
            {"code": "ES-158", "branch": "CST"}
        ]
    },
    {
        "name": "EGTech",
        "email": "egtech@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            ##Labs
            {"code": "ES-157", "branch": "AIML"},
            {"code": "ES-157", "branch": "AIDS"},
            {"code": "ES-158", "branch": "AIML"},
            {"code": "ES-158", "branch": "AIDS"}
        ]
    },
    {
        "name": "chand",
        "email": "chand@college.edu",
        "password": "123456",
        "phone": "9876543210",
        "subjects": [
            ##Labs
            {"code": "ES-164", "branch": "AIML"},
            {"code": "ES-164", "branch": "AIDS"},
            {"code": "ES-164", "branch": "CSE"},
            {"code": "ES-164", "branch": "CST"}
        ]
    }
]

# ==========================================
# SCRIPT LOGIC
# ==========================================

def setup_data():
    # Force use of the instance database to ensure we modify the correct data
    db_path = os.path.join(os.getcwd(), 'instance', 'student_management.db')
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    
    app = create_app()
    with app.app_context():
        print(f"🚀 Starting Setup Script (DB: {db_path})...")
        
        # --- PHASE 1: PRE-VALIDATION ---
        print("\n🔍 Validating all subjects first...")
        all_valid = True
        missing_subjects = []

        for teacher_data in TEACHERS_DATA:
            for subj_info in teacher_data['subjects']:
                raw_code = subj_info['code']
                branch = subj_info.get('branch', 'COMMON')
                
                # Check exact code
                subject = Subject.query.filter_by(code=raw_code).first()
                
                # Check prefixed code
                if not subject and branch != 'COMMON':
                    prefixed_code = f"{branch}-{raw_code}"
                    subject = Subject.query.filter_by(code=prefixed_code).first()
                
                if not subject:
                    error_msg = f"Teacher: {teacher_data['name']} -> Subject: '{raw_code}' (Prefix attempt: '{branch}-{raw_code}') NOT FOUND"
                    missing_subjects.append(error_msg)
                    all_valid = False

        if not all_valid:
            print("\n❌ VALIDATION FAILED! The following subjects do not exist in the database:")
            for msg in missing_subjects:
                print(f"   - {msg}")
            print("\n⛔ Operation aborted. No teachers or assignments were added.")
            return

        print("✅ Validation Successful. All subjects found.")

        # --- PHASE 2: EXECUTION ---
        for teacher_data in TEACHERS_DATA:
            print(f"\nProcessing Teacher: {teacher_data['name']} ({teacher_data['email']})")
            
            # 1. Create or Get Teacher
            teacher = User.query.filter_by(email=teacher_data['email']).first()
            
            if not teacher:
                try:
                    teacher = User(
                        name=teacher_data['name'],
                        email=teacher_data['email'],
                        phone=teacher_data.get('phone', ''),
                        role=UserRole.TEACHER,
                        password_hash=generate_password_hash(teacher_data.get('password', 'password123')),
                        department="B.Tech" 
                    )
                    db.session.add(teacher)
                    db.session.commit()
                    print(f"   ✅ Created new teacher account.")
                except Exception as e:
                    print(f"   ❌ Error creating teacher: {e}")
                    db.session.rollback()
                    continue
            else:
                print(f"   ℹ️  Teacher account already exists.")
                if teacher.role != UserRole.TEACHER:
                    teacher.role = UserRole.TEACHER
                    db.session.commit()
                    print(f"   ⚠️  Updated role to TEACHER.")

            # 2. Process Assignments
            for subj_info in teacher_data['subjects']:
                raw_code = subj_info['code']
                branch = subj_info.get('branch', 'COMMON')
                
                # Validation: Subject MUST exist
                # Strategy 1: Check exact code (e.g. "AIML-ES-101")
                subject = Subject.query.filter_by(code=raw_code).first()
                
                # Strategy 2: Check prefixed code (e.g. "AIML" + "-" + "ES-101")
                if not subject and branch != 'COMMON':
                    prefixed_code = f"{branch}-{raw_code}"
                    subject = Subject.query.filter_by(code=prefixed_code).first()
                
                if not subject:
                    print(f"   ❌ ERROR: Subject '{raw_code}' (or '{branch}-{raw_code}') not found! Skipping assignment.")
                    continue
                
                # Optional: Verify branch matches if strictness is desired
                if subject.branch != branch and subject.branch != "COMMON":
                     print(f"   ⚠️  Warning: Subject '{subject.code}' belongs to {subject.branch}, but input specified {branch}.")
                
                # 3. Assign Class
                existing_assignment = AssignedClass.query.filter_by(
                    teacher_id=teacher.id,
                    subject_id=subject.id
                ).first()
                
                if not existing_assignment:
                    try:
                        assignment = AssignedClass(
                            teacher_id=teacher.id,
                            subject_id=subject.id
                        )
                        db.session.add(assignment)
                        db.session.commit()
                        print(f"   🔗 Assigned {teacher.name} to {subject.code} ({subject.name})")
                    except Exception as e:
                        print(f"   ❌ Error assigning class: {e}")
                        db.session.rollback()
                else:
                    print(f"   ℹ️  Already assigned to {subject.code}")

        print("\n✨ Setup Completed!")

if __name__ == "__main__":
    setup_data()
