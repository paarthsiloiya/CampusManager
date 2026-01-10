from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone, time
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
import enum

db = SQLAlchemy()

class Branch(enum.Enum):
    """Enum for available branches"""
    AIML = "AIML"  # Artificial Intelligence & Machine Learning
    AIDS = "AIDS"  # Artificial Intelligence & Data Science
    CST = "CST"   # Computer Science & Technology
    CSE = "CSE"   # Computer Science & Engineering

class UserRole(enum.Enum):
    """Enum for user roles"""
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    ADMIN = "ADMIN"

class EnrollmentStatus(enum.Enum):
    """Enum for enrollment status"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class User(UserMixin, db.Model):
    """User model for storing basic student information and authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information (collected at signup)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    semester = db.Column(db.Integer, nullable=True)
    branch = db.Column(db.Enum(Branch), nullable=True)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_password_changed = db.Column(db.Boolean, default=False)
    
    # Authentication
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Additional profile information
    enrollment_number = db.Column(db.String(50), unique=True, nullable=True)
    department = db.Column(db.String(100), nullable=True)
    institution = db.Column(db.String(200), nullable=True, default='Delhi Technical Campus')
    year_of_admission = db.Column(db.Integer, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    attendance_records = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')
    marks = db.relationship('Marks', backref='student', lazy=True, cascade='all, delete-orphan')
    
    # Teacher specific relationships
    assigned_classes = db.relationship('AssignedClass', backref='teacher', lazy=True, cascade='all, delete-orphan')

    # Student specific relationships
    enrollments = db.relationship('Enrollment', backref='student', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_subjects_for_semester(self):
        """Get all subjects for the user's current semester and branch"""
        branch_code = self.branch.value if self.branch else 'CSE'
        
        # Get branch-specific subjects and common subjects
        return Subject.query.filter(
            Subject.semester == self.semester,
            db.or_(
                Subject.branch == branch_code,
                Subject.branch == 'COMMON'
            )
        ).all()
    
    def get_attendance_for_subject(self, subject_id):
        """Get attendance statistics for a specific subject"""
        total_classes = Attendance.query.filter_by(
            user_id=self.id, 
            subject_id=subject_id
        ).count()
        
        attended_classes = Attendance.query.filter_by(
            user_id=self.id, 
            subject_id=subject_id,
            status='present'
        ).count()
        
        if total_classes == 0:
            return {
                'total_classes': 0,
                'attended_classes': 0,
                'attendance_percentage': 0,
                'status': 'no_data'
            }
        
        attendance_percentage = (attended_classes / total_classes) * 100
        
        return {
            'total_classes': total_classes,
            'attended_classes': attended_classes,
            'attendance_percentage': round(attendance_percentage, 1),
            'status': 'good' if attendance_percentage >= 75 else 'warning' if attendance_percentage >= 60 else 'danger'
        }
    
    def get_overall_attendance_stats(self):
        """Get overall attendance statistics for the user"""
        subjects = self.get_subjects_for_semester()
        
        total_classes_all = 0
        attended_classes_all = 0
        
        for subject in subjects:
            attendance_data = self.get_attendance_for_subject(subject.id)
            total_classes_all += attendance_data['total_classes']
            attended_classes_all += attendance_data['attended_classes']
        
        if total_classes_all == 0:
            return {
                'total_classes': 0,
                'attended_classes': 0,
                'attendance_percentage': 0,
                'this_week_classes': 0,
                'needed_for_75': 0
            }
        
        attendance_percentage = (attended_classes_all / total_classes_all) * 100
        
        # Calculate classes needed for 75% attendance
        if attendance_percentage < 75:
            # Formula: (current_attended + x) / (current_total + x) = 0.75
            # Solving for x: x = (0.75 * current_total - current_attended) / 0.25
            needed_for_75 = max(0, int((0.75 * total_classes_all - attended_classes_all) / 0.25))
        else:
            needed_for_75 = 0
        
        # Calculate this week's classes (last 7 days)
        from datetime import date, timedelta
        week_ago = date.today() - timedelta(days=7)
        this_week_classes = Attendance.query.filter(
            Attendance.user_id == self.id,
            Attendance.date >= week_ago
        ).count()
        
        return {
            'total_classes': total_classes_all,
            'attended_classes': attended_classes_all,
            'attendance_percentage': round(attendance_percentage, 1),
            'this_week_classes': this_week_classes,
            'needed_for_75': needed_for_75
        }
    
    def get_subjects_with_attendance(self):
        """Get subjects with their attendance data for the dashboard"""
        subjects = self.get_subjects_for_semester()
        subjects_data = []
        
        for subject in subjects:
            attendance_data = self.get_attendance_for_subject(subject.id)
            
            subjects_data.append({
                'id': subject.id,
                'name': subject.name,
                'code': subject.code,
                'faculty': 'Faculty Name',  # You can add faculty field to Subject model
                'icon': f'static/icons/{subject.code.lower()}.png',  # Map to your icons
                'attendance_percentage': attendance_data['attendance_percentage'],
                'total_classes': attendance_data['total_classes'],
                'attended_classes': attendance_data['attended_classes'],
                'status': attendance_data['status']
            })
        
        return subjects_data
    
    def __repr__(self):
        return f'<User {self.name} ({self.email}) - Semester {self.semester} - {self.branch.value if self.branch else "No Branch"}>'

class Subject(db.Model):
    """Model for storing subject information"""
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)  # Increased length for branch prefix
    semester = db.Column(db.Integer, nullable=False)
    credits = db.Column(db.Integer, default=3)
    branch = db.Column(db.String(10), nullable=False, default='COMMON')  # Branch-specific or COMMON
    
    # Relationships
    attendance_records = db.relationship('Attendance', backref='subject', lazy=True)
    marks = db.relationship('Marks', backref='subject', lazy=True)
    assigned_classes = db.relationship('AssignedClass', backref='subject', lazy=True)
    
    def __repr__(self):
        return f'<Subject {self.branch}-{self.code}: {self.name}>'

class AssignedClass(db.Model):
    """Model for linking a teacher to a subject (Class Assignment)"""
    __tablename__ = 'assigned_classes'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    
    # Can add things like 'section' (A, B, C) or 'group' here if multiple teachers teach same subject
    section = db.Column(db.String(10), nullable=True) 
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='assigned_class', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AssignedClass {self.subject.code} - Teacher: {self.teacher.name}>'

class Enrollment(db.Model):
    """Model for student enrollment in an assigned class"""
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('assigned_classes.id'), nullable=False)
    
    status = db.Column(db.Enum(EnrollmentStatus), default=EnrollmentStatus.PENDING, nullable=False)
    request_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    response_date = db.Column(db.DateTime, nullable=True)
    
    class Meta:
        unique_together = ('student_id', 'class_id')
        
    @property
    def is_approved(self):
        return self.status == EnrollmentStatus.APPROVED

    def __repr__(self):
        return f'<Enrollment {self.student.name} -> {self.assigned_class.subject.code}: {self.status.value}>'

class Attendance(db.Model):
    """Model for tracking student attendance per subject"""
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    
    # Attendance Details
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # 'present', 'absent', 'late'
    class_type = db.Column(db.String(20), default='lecture')  # 'lecture', 'lab', 'tutorial'
    
    # Additional information
    remarks = db.Column(db.Text, nullable=True)
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Attendance {self.student.name} - {self.subject.code} on {self.date}: {self.status}>'

class Marks(db.Model):
    """Model for storing student marks/grades per subject"""
    __tablename__ = 'marks'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    
    # Assessment Details
    assessment_type = db.Column(db.String(50), nullable=False)  # 'midterm', 'final', 'assignment', 'quiz', 'practical'
    assessment_name = db.Column(db.String(100), nullable=False)
    max_marks = db.Column(db.Float, nullable=False)
    obtained_marks = db.Column(db.Float, nullable=False)
    
    # Additional information
    assessment_date = db.Column(db.Date, nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    @property
    def percentage(self):
        """Calculate percentage"""
        if self.max_marks > 0:
            return (self.obtained_marks / self.max_marks) * 100
        return 0
    
    @property
    def grade(self):
        """Calculate grade based on percentage"""
        percentage = self.percentage
        if percentage >= 90:
            return 'A+'
        elif percentage >= 80:
            return 'A'
        elif percentage >= 70:
            return 'B+'
        elif percentage >= 60:
            return 'B'
        elif percentage >= 50:
            return 'C'
        elif percentage >= 40:
            return 'D'
        else:
            return 'F'
    
    def __repr__(self):
        return f'<Marks {self.student.name} - {self.subject.code}: {self.obtained_marks}/{self.max_marks}>'

class AttendanceSummary(db.Model):
    """Model for storing calculated attendance summaries per student per subject"""
    __tablename__ = 'attendance_summary'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    
    # Summary Data
    total_classes = db.Column(db.Integer, default=0)
    classes_attended = db.Column(db.Integer, default=0)
    classes_missed = db.Column(db.Integer, default=0)
    
    # Calculated fields
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    student = db.relationship('User', backref='attendance_summaries')
    subject = db.relationship('Subject', backref='attendance_summaries')
    
    @property
    def attendance_percentage(self):
        """Calculate attendance percentage"""
        if self.total_classes > 0:
            return (self.classes_attended / self.total_classes) * 100
        return 0
    
    def __repr__(self):
        return f'<AttendanceSummary {self.student.name} - {self.subject.code}: {self.attendance_percentage:.1f}%>'

class TimetableSettings(db.Model):
    """Model for storing timetable configuration"""
    __tablename__ = 'timetable_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Time, nullable=False, default=time(9, 30))
    end_time = db.Column(db.Time, nullable=False, default=time(16, 30))
    lunch_duration = db.Column(db.Integer, nullable=False, default=30) # in minutes
    min_class_duration = db.Column(db.Integer, nullable=False, default=40) # in minutes
    max_class_duration = db.Column(db.Integer, nullable=False, default=50) # in minutes
    periods = db.Column(db.Integer, nullable=False, default=8)
    working_days = db.Column(db.String(20), nullable=False, default="MTWTF")
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class TimetableEntry(db.Model):
    """Model for storing generated timetable entries"""
    __tablename__ = 'timetable_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    semester = db.Column(db.Integer, nullable=False)
    branch = db.Column(db.String(10), nullable=False, default='COMMON') # Added branch column
    day = db.Column(db.String(10), nullable=False) # Mon, Tue, Wed, Thu, Fri
    period_number = db.Column(db.Integer, nullable=False) # 1-based index
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    assigned_class_id = db.Column(db.Integer, db.ForeignKey('assigned_classes.id'), nullable=False)
    
    assigned_class = db.relationship('AssignedClass', backref='timetable_entries')
    
    def __repr__(self):
        return f'<TimetableEntry Sem{self.semester} {self.day} P{self.period_number}: {self.assigned_class.subject.code}>'

# Database utility functions
def create_tables():
    """Create all database tables"""
    db.create_all()

def drop_tables():
    """Drop all database tables"""
    db.drop_all()

def reset_database():
    """Reset the entire database"""
    drop_tables()
    create_tables()

def seed_subjects():
    """
    Seed and sync the database with branch-specific subjects from JSON data.
    This function:
    1. Creates new subjects found in JSON.
    2. Updates existing subjects if JSON data changed (matching by Code OR Name+Branch).
    3. Removes subjects from DB that are no longer in the JSON (orphans).
    4. Aggressively cleans up dependent data (Attendance, etc.) for orphans.
    """
    import json
    import os
    
    try:
        # First check if we can query the subjects table (if it has the branch column)
        test_query = Subject.query.first()
    except Exception:
        return
    
    # Load branch-specific subjects from JSON
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'branch_subjects.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        return
    
    subjects_created = 0
    subjects_updated = 0
    active_subject_ids = set()
    
    # Iterate through branches and their semesters
    for branch_code, branch_data in data.get('branches', {}).items():
        for semester_num, subjects_list in branch_data.get('semesters', {}).items():
            semester_int = int(semester_num)
            
            for subject_data in subjects_list:
                # Skip empty objects or objects missing required fields
                if not subject_data or not isinstance(subject_data, dict):
                    continue
                
                # Check if required fields exist and are not empty
                if not subject_data.get('name') or not subject_data.get('code'):
                    continue
                
                # Skip subjects with generic or invalid codes
                if subject_data['code'] in ['Test', '1', '']:
                    continue
                
                # Desired new state
                tgt_code = f"{branch_code}-{subject_data['code']}"
                tgt_name = subject_data['name']
                tgt_credits = subject_data.get('credits', -1)
                
                # Strategy:
                # 1. Try to find by EXACT Code (Preferred)
                existing = Subject.query.filter_by(code=tgt_code).first()
                
                # 2. If not found, try to find by Name + Branch + Semester (Rename/Recode Case)
                if not existing:
                    existing = Subject.query.filter_by(
                        name=tgt_name,
                        branch=branch_code, 
                        semester=semester_int
                    ).first()
                
                if not existing:
                    # Create New
                    new_subject = Subject(
                        name=tgt_name,
                        code=tgt_code,
                        semester=semester_int,
                        credits=tgt_credits,
                        branch=branch_code
                    )
                    db.session.add(new_subject)
                    db.session.flush() # Get ID
                    active_subject_ids.add(new_subject.id)
                    subjects_created += 1
                else:
                    # Update Existing
                    active_subject_ids.add(existing.id)
                    changed = False
                    
                    if existing.code != tgt_code: # Critical: Updating Code
                        existing.code = tgt_code
                        changed = True
                    if existing.name != tgt_name:
                        existing.name = tgt_name
                        changed = True
                    if existing.semester != semester_int:
                        existing.semester = semester_int
                        changed = True
                    if existing.credits != tgt_credits:
                        existing.credits = tgt_credits
                        changed = True
                    if existing.branch != branch_code:
                        existing.branch = branch_code
                        changed = True
                        
                    if changed:
                        print(f"DEBUG: Updating {existing.code}")
                        subjects_updated += 1
    
    # Common subjects block removed to prevent duplicates with branch-specific subjects
    # The JSON file should now contain all subjects for all branches.
    
    # Commit additions and updates
    try:
        db.session.commit()
    except Exception as e:
        print(f"Commit Error: {e}")
        db.session.rollback()
        return

    # Cleanup Orphaned Subjects
    # If the user previously had duplicate subjects due to code changes, 
    # the above logic might have "claimed" one of them (the one matching name/branch).
    # The "other" one (the one with old code that didn't match name/branch or was skipped)
    # will not be in active_subject_ids.
    
    try:
        all_subjects = Subject.query.all()
        subjects_deleted = 0
        
        for subj in all_subjects:
            if subj.id not in active_subject_ids:
                print(f"🗑️ Deleting orphan subject: {subj.code} ({subj.name})")
                try:
                    # 1. Delete Assigned Classes (and cascade Enrollments)
                    AssignedClass.query.filter_by(subject_id=subj.id).delete()
                    
                    # 2. Delete Attendance Summary
                    AttendanceSummary.query.filter_by(subject_id=subj.id).delete()
                    
                    # 3. Delete Attendance
                    Attendance.query.filter_by(subject_id=subj.id).delete()
                    
                    # 4. Delete Marks
                    Marks.query.filter_by(subject_id=subj.id).delete()
                    
                    # 5. Delete the Subject itself
                    db.session.delete(subj)
                    
                    # Commit per deletion to keep transaction log small and safe
                    db.session.commit()
                    subjects_deleted += 1
                except Exception as e:
                    print(f"❌ Failed to delete orphan {subj.code}: {e}")
                    db.session.rollback()
                    continue
        
        if subjects_deleted > 0 or subjects_updated > 0:
            print(f"Subject Sync: Created {subjects_created}, Updated {subjects_updated}, Deleted {subjects_deleted}")
            
    except Exception as e:
        print(f"❌ Sync Error: {e}")
        db.session.rollback()