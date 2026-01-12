
import pytest
from datetime import datetime, time, timezone, timedelta
from unittest.mock import patch
from app.models import User, UserRole, Branch, Subject, AssignedClass, TimetableEntry, db

# --- Helpers ---
def t(hour, minute):
    return time(hour, minute)

# Custom Mock wrapping real datetime
class MockDatetime(datetime):
    _mock_utc_now = None
    
    @classmethod
    def now(cls, tz=None):
        if cls._mock_utc_now:
            if tz:
                return cls._mock_utc_now.astimezone(tz)
            return cls._mock_utc_now.replace(tzinfo=None) # Naive if no tz
        return super().now(tz)

# --- Tests ---

def test_student_dashboard_active_class_collision(client, auth, app):
    """
    Test that student dashboard shows the correct active class even when
    another branch has a class at the same time.
    """
    with app.app_context():
        # 1. Setup Data
        
        # Student: AIML
        student = User(
            name="AIML Student", 
            email="aiml@test.com", 
            role=UserRole.STUDENT, 
            semester=1, 
            branch=Branch.AIML
        )
        student.set_password("password")
        
        # Teacher
        teacher = User(
            name="Prof. Teacher", 
            email="teacher@test.com", 
            role=UserRole.TEACHER
        )
        teacher.set_password("password")
        
        db.session.add(student)
        db.session.add(teacher)
        db.session.commit()
        
        # Subjects: One for AIML, One for CSE (Conflict)
        subj_aiml = Subject(
            name="AIML Subject", 
            code="AIML-101", 
            semester=1, 
            branch="AIML"
        )
        subj_cse = Subject(
            name="CSE Subject",
            code="CSE-101",
            semester=1,
            branch="CSE"
        )
        db.session.add(subj_aiml)
        db.session.add(subj_cse)
        db.session.commit()
        
        # Assigned Classes
        cls_aiml = AssignedClass(subject_id=subj_aiml.id, teacher_id=teacher.id)
        cls_cse = AssignedClass(subject_id=subj_cse.id, teacher_id=teacher.id)
        db.session.add(cls_aiml)
        db.session.add(cls_cse)
        db.session.commit()
        
        # Timetable Entries: Both on Monday 10:00 - 11:00
        # NOTE: 2024-01-01 is a Monday
        entry_aiml = TimetableEntry(
            assigned_class_id=cls_aiml.id,
            day="Monday",
            start_time=t(10, 0),
            end_time=t(11, 0),
            semester=1,
            branch="AIML", 
            period_number=1
        )
        entry_cse = TimetableEntry(
            assigned_class_id=cls_cse.id,
            day="Monday",
            start_time=t(10, 0),
            end_time=t(11, 0),
            semester=1,
            branch="CSE",
            period_number=1
        )
        db.session.add(entry_aiml)
        db.session.add(entry_cse)
        db.session.commit()

        # Login
        auth.login("aiml@test.com", "password")

    # 2. Test during class time (10:30 AM IST = 5:00 AM UTC)
    mock_utc_now = datetime(2024, 1, 1, 5, 0, 0, tzinfo=timezone.utc)
    MockDatetime._mock_utc_now = mock_utc_now
    
    with patch('app.views.datetime', MockDatetime):
        response = client.get('/student/dashboard')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Verify AIML class is active
        assert "Active Class" in html
        assert "AIML Subject" in html
        assert "AIML-101" in html
        
        # Verify CSE class is NOT active/shown
        assert "CSE Subject" not in html
        assert "CSE-101" not in html

    # 3. Test outside class time (12:00 PM IST = 6:30 AM UTC)
    mock_utc_now = datetime(2024, 1, 1, 6, 30, 0, tzinfo=timezone.utc)
    MockDatetime._mock_utc_now = mock_utc_now
    
    with patch('app.views.datetime', MockDatetime):
        response = client.get('/student/dashboard')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Verify no active class
        assert "No active class right now" in html

def test_teacher_class_details_active_button(client, auth, app):
    """
    Test that teacher class details page shows 'Take Attendance' button
    only when class is active.
    """
    with app.app_context():
        # Setup Teacher & Class
        teacher = User(
            name="Prof. Tester", 
            email="tester@test.com", 
            role=UserRole.TEACHER
        )
        teacher.set_password("password")
        db.session.add(teacher)
        db.session.commit() # get teacher.id

        subject = Subject(name="Test Subject", code="TEST-101", semester=1)
        db.session.add(subject)
        db.session.commit()

        assigned_class = AssignedClass(subject_id=subject.id, teacher_id=teacher.id)
        db.session.add(assigned_class)
        db.session.commit()

        # Timetable: Monday 10:00 - 11:00
        entry = TimetableEntry(
            assigned_class_id=assigned_class.id,
            day="Monday",
            start_time=t(10, 0),
            end_time=t(11, 0),
            semester=1,
            branch="COMMON",
            period_number=1
        )
        db.session.add(entry)
        db.session.commit()
        
        cls_id = assigned_class.id
        
        # Login
        auth.login("tester@test.com", "password")

    # 1. Test During Class (10:30 AM IST = 5:00 AM UTC Mon)
    mock_utc_now = datetime(2024, 1, 1, 5, 0, 0, tzinfo=timezone.utc)
    MockDatetime._mock_utc_now = mock_utc_now
    
    with patch('app.views.datetime', MockDatetime):
        response = client.get(f'/teacher/class/{cls_id}')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        assert "Class Active" in html
        assert "Take Attendance Now" in html
        assert "LIVE" in html

    # 2. Test Outside Class (12:00 PM IST)
    mock_utc_now = datetime(2024, 1, 1, 6, 30, 0, tzinfo=timezone.utc)
    MockDatetime._mock_utc_now = mock_utc_now
    
    with patch('app.views.datetime', MockDatetime):
        response = client.get(f'/teacher/class/{cls_id}')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        assert "Class Active" not in html
        assert "Take Attendance Now" not in html
        
    # 3. Test Wrong Day (Tuesday same time)
    # Jan 2, 2024 is Tuesday
    mock_utc_now = datetime(2024, 1, 2, 5, 0, 0, tzinfo=timezone.utc)
    MockDatetime._mock_utc_now = mock_utc_now
    
    with patch('app.views.datetime', MockDatetime):
        response = client.get(f'/teacher/class/{cls_id}')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert "Class Active" not in html
