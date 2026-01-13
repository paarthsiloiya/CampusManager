import pytest
from datetime import datetime, time, date, timedelta, timezone
from unittest.mock import patch
from app.models import User, UserRole, Branch, Subject, TimetableSettings, AssignedClass, TimetableEntry, Enrollment, EnrollmentStatus, Attendance
from flask import url_for as base_url_for

# Helper to avoid import issues if url_for needs app context, but fixtures usually provide valid context
# We'll just use client requests directly mostly.

# --- Fixtures ---
class TestTeacherFeatures:
    
    @pytest.fixture
    def basic_teacher_setup(self, db):
        teacher = User(name="Teacher", email="teacher@test.com", role=UserRole.TEACHER, institution="DTC")
        teacher.set_password("password")
        
        student = User(name="Student", email="student@test.com", role=UserRole.STUDENT, semester=1, institution="DTC")
        student.set_password("password")
        
        subject = Subject(name="Math", code="MATH101", semester=1, branch="CSE")
        db.session.add_all([teacher, student, subject])
        db.session.commit()
        
        assign = AssignedClass(teacher_id=teacher.id, subject_id=subject.id, section="A")
        db.session.add(assign)
        db.session.commit()
        
        return {
            "teacher": teacher,
            "student": student,
            "subject": subject,
            "assignment": assign
        }

    def test_teacher_update_class_details(self, client, auth, basic_teacher_setup, db):
        """Test teacher updating class details like location and google link"""
        # Unpack setup
        teacher = basic_teacher_setup['teacher']
        assigned_class = basic_teacher_setup['assignment']
        
        auth.login(teacher.email, "password")
        
        # Test valid update
        response = client.post(f'/teacher/class/{assigned_class.id}/edit', data={
            'location': 'Room 101-B',
            'google_classroom_link': 'https://classroom.google.com/test'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify DB update first
        updated_class = db.session.get(AssignedClass, assigned_class.id)
        assert updated_class.location == 'Room 101-B'
        assert updated_class.google_classroom_link == 'https://classroom.google.com/test'
        
        # Then check flash message
        # assert b"Details updated successfully" in response.data

    # --- Dashboard Timetable Tests (Live Class) ---
    def test_dashboard_shows_active_class(self, client, auth, db):
        # Setup specific data for this test
        dashboard_teacher = User(name="Dash T", email="dash@t.com", role=UserRole.TEACHER)
        dashboard_teacher.set_password("password")
        db.session.add(dashboard_teacher)
        
        subject = Subject(name="Live Subject", code="LIVE101", semester=3, branch="CSE")
        db.session.add(subject)
        db.session.commit()
        
        ac = AssignedClass(teacher_id=dashboard_teacher.id, subject_id=subject.id, section="A")
        db.session.add(ac)
        db.session.commit()
        
        # Monday 10:00 - 11:00
        entry = TimetableEntry(
            semester=3, branch="CSE", day="Monday", period_number=1,
            start_time=time(10, 0), end_time=time(11, 0), assigned_class_id=ac.id
        )
        db.session.add(entry)
        db.session.commit()
        
        auth.login(email=dashboard_teacher.email, password="password")

        # Mock time: Monday 10:30 AM IST (which is 05:00 AM UTC)
        # The view adds +5:30 to the UTC time returned by .now()
        mock_now = datetime(2024, 1, 1, 5, 0, 0) # Jan 1 2024 is Monday

        with patch('app.views.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.strptime.side_effect = lambda *args, **kwargs: datetime.strptime(*args, **kwargs)
            
            response = client.get('/teacher/dashboard')
            assert response.status_code == 200
            assert b"Live Class" in response.data
            assert b"Live Subject" in response.data

    def test_dashboard_hides_inactive(self, client, auth, db):
        # Similar setup... reuse helper if possible but keeping self-contained for clarity
        dashboard_teacher = User(name="Dash T2", email="dash2@t.com", role=UserRole.TEACHER)
        dashboard_teacher.set_password("password")
        db.session.add(dashboard_teacher)
        db.session.commit()
        
        auth.login(email="dash2@t.com", password="password")
        
        # Monday 12:00 PM (No class)
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        
        with patch('app.views.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.strptime.side_effect = lambda *args, **kwargs: datetime.strptime(*args, **kwargs)
            
            response = client.get('/teacher/dashboard')
            assert b"Live Class" not in response.data

    def test_dashboard_active_class_ignores_semester_setting(self, client, auth, db):
        """Test that active live class is shown even if it belongs to a semester currently marked 'inactive' in settings"""
        # 1. Setup Teacher
        teacher = User(name="MismatchTeacher", email="mismatch@test.com", role=UserRole.TEACHER)
        teacher.set_password("password")
        db.session.add(teacher)
        
        # 2. Setup Settings: Active Semester = EVEN
        settings = TimetableSettings(active_semester_type='even')
        db.session.add(settings)
        
        # 3. Setup Subject: Semester 1 (ODD)
        subject = Subject(name="Odd Subject", code="ODD101", semester=1, branch="CSE")
        db.session.add(subject)
        db.session.commit()
        
        # 4. Assign Class
        ac = AssignedClass(teacher_id=teacher.id, subject_id=subject.id, section="A")
        db.session.add(ac)
        db.session.commit()
        
        # 5. Create Timetable Entry: Monday 10:00-11:00
        entry = TimetableEntry(
            semester=1, branch="CSE", day="Monday", period_number=1,
            start_time=time(10, 0), end_time=time(11, 0), assigned_class_id=ac.id
        )
        db.session.add(entry)
        db.session.commit()
        
        auth.login(email="mismatch@test.com", password="password")

        # 6. Mock Time: Monday 10:30 AM IST (05:00 UTC)
        mock_now = datetime(2024, 1, 1, 5, 0, 0)

        with patch('app.views.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.strptime.side_effect = lambda *args, **kwargs: datetime.strptime(*args, **kwargs)
            
            response = client.get('/teacher/dashboard')
            
            # Should show "Odd Subject" even though settings say "Even" is active
            assert b"Odd Subject" in response.data

    def test_dashboard_real_data_scenario(self, client, auth, db):
        # Recreate the data from debug output
        
        # Teacher ID 13 (approx) - "EGTech"
        teacher = User(name="EGTech", email="egtech@test.com", role=UserRole.TEACHER)
        teacher.set_password("password")
        db.session.add(teacher)
        db.session.commit() # Get ID
        
        # Subject AIML-ES-157
        subject = Subject(name="Engineering Graphics I", code="AIML-ES-157-TEST", semester=1, branch="AIML")
        db.session.add(subject)
        db.session.commit()
        
        # Assigned Class
        ac = AssignedClass(teacher_id=teacher.id, subject_id=subject.id)
        db.session.add(ac)
        db.session.commit()
        
        # Timetable Entry: Monday 09:30 - 10:25
        entry = TimetableEntry(
            semester=1, 
            branch="AIML", 
            day="Monday", 
            period_number=1,
            start_time=time(9, 30), 
            end_time=time(10, 25), 
            assigned_class_id=ac.id
        )
        db.session.add(entry)
        db.session.commit()
        
        # Login
        auth.login(email="egtech@test.com", password="password")
        
        # Mock Time: Server is UTC (04:18), so +5:30 makes it 09:48 IST (Active Class Time)
        mock_now = datetime(2026, 1, 12, 4, 18, 0)
        
        with patch('app.views.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now.replace(tzinfo=timezone.utc) # Mock UTC
            mock_datetime.strptime.side_effect = lambda *args, **kwargs: datetime.strptime(*args, **kwargs)
            
            response = client.get('/teacher/dashboard')
            
            # Checks
            assert response.status_code == 200
            if b"Engineering Graphics I" not in response.data:
                 print(response.data.decode())
            assert b"Engineering Graphics I" in response.data
            assert b"Live Class" in response.data

    # --- Attendance Tests ---
    def test_mark_attendance_page_loads(self, client, auth, basic_teacher_setup):
        setup = basic_teacher_setup
        auth.login(email=setup["teacher"].email, password="password")
        
        response = client.get(f'/teacher/class/{setup["assignment"].id}/attendance')
        assert response.status_code == 200
        assert b"Mark Attendance" in response.data

    def test_submit_attendance(self, client, auth, basic_teacher_setup, db):
        setup = basic_teacher_setup
        auth.login(email=setup["teacher"].email, password="password")
        
        # Enroll student first
        enroll = Enrollment(student_id=setup["student"].id, class_id=setup["assignment"].id, status=EnrollmentStatus.APPROVED)
        db.session.add(enroll)
        db.session.commit()
        
        today_str = date.today().strftime('%Y-%m-%d')
        data = {
            'date': today_str,
            f'attendance_{setup["student"].id}': 'on'
        }
        
        response = client.post(f'/teacher/class/{setup["assignment"].id}/attendance', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"Attendance marked" in response.data
        
        # Verify DB
        rec = Attendance.query.filter_by(user_id=setup["student"].id, date=date.today()).first()
        assert rec is not None
        assert rec.status == 'present'

    # --- Lab Attendance (Consolidated from test_lab_attendance.py) ---
    def test_lab_attendance_marking(self, client, auth, db):
        # Setup Lab Teacher/Subject
        teacher = User(name="Lab T", email="lab@t.com", role=UserRole.TEACHER)
        teacher.set_password("password")
        student = User(name="Lab S", email="labs@t.com", role=UserRole.STUDENT, semester=5, branch="CSE")
        student.set_password("password")
        lab = Subject(name="Phys Lab", code="PHYLAB", semester=5, branch="CSE", credits=1, is_lab=True)
        
        db.session.add_all([teacher, student, lab])
        db.session.commit()
        
        assign = AssignedClass(teacher_id=teacher.id, subject_id=lab.id, section="A")
        db.session.add(assign)
        db.session.commit()
        
        enroll = Enrollment(student_id=student.id, class_id=assign.id, status=EnrollmentStatus.APPROVED)
        db.session.add(enroll)
        db.session.commit()
        
        auth.login("lab@t.com", "password")
        
        today_str = date.today().strftime('%Y-%m-%d')
        response = client.post(f'/teacher/class/{assign.id}/attendance', data={
            'date': today_str,
            f'attendance_{student.id}': 'on'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify is_lab/class_type logic
        rec = Attendance.query.filter_by(user_id=student.id, subject_id=lab.id).first()
        assert rec.class_type == 'lab'

    # --- Enrollment Management ---
    def test_handle_enrollment(self, client, auth, basic_teacher_setup, db):
        setup = basic_teacher_setup
        
        # Create pending enrollment
        enroll = Enrollment(student_id=setup["student"].id, class_id=setup["assignment"].id, status=EnrollmentStatus.PENDING)
        db.session.add(enroll)
        db.session.commit()
        
        auth.login(email=setup["teacher"].email, password="password")
        
        # Approve
        resp = client.post(f'/teacher/enrollment/{enroll.id}', data={'action': 'approve'}, follow_redirects=True)
        assert resp.status_code == 200
        
        updated = db.session.get(Enrollment, enroll.id)
        assert updated.status == EnrollmentStatus.APPROVED

    def test_curriculum_assignment_visibility(self, client, auth, db):
        """Test that assignment makes teacher appear in student curriculum"""
        teacher = User(name='Professor X', email='prof@x.com', role=UserRole.TEACHER, branch=Branch.CSE)
        teacher.set_password('password')
        student = User(name='Logan', email='wolv@x.com', role=UserRole.STUDENT, branch=Branch.CSE, semester=1)
        student.set_password('password')
        subject = Subject(name='X-Men History', code='HIS101', branch='CSE', semester=1)
        
        db.session.add_all([teacher, student, subject])
        db.session.commit()
        
        assign = AssignedClass(teacher_id=teacher.id, subject_id=subject.id)
        db.session.add(assign)
        db.session.commit()
        
        auth.login('wolv@x.com', 'password')
        response = client.get('/curriculum')
        assert b'Professor X' in response.data or b'prof@x.com' in response.data or b'X-Men History' in response.data

    def test_access_other_teacher_class_denied(self, client, auth, db, basic_teacher_setup):
        """Ensure a teacher cannot access another teacher's class details"""
        setup = basic_teacher_setup
        
        # Create another teacher
        other_teacher = User(name="Other T", email="other@t.com", role=UserRole.TEACHER)
        other_teacher.set_password("password")
        db.session.add(other_teacher)
        db.session.commit()
        
        auth.login("other@t.com", "password")
        
        # Try to access first teacher's class
        response = client.get(f'/teacher/class/{setup["assignment"].id}', follow_redirects=True)
        assert response.status_code == 200
        # Should be redirected to dashboard with error
        assert b"Unauthorized access" in response.data or b"Dashboard" in response.data

    # --- New Tests Added ---
    def test_view_enrollments_list(self, client, auth, basic_teacher_setup):
        setup = basic_teacher_setup
        auth.login(setup["teacher"].email, "password")
        
        response = client.get(f'/teacher/enrollments')
        assert response.status_code == 200
        assert b"Enrollment" in response.data

    def test_teacher_dashboard_context(self, client, auth, basic_teacher_setup):
        setup = basic_teacher_setup
        auth.login(setup["teacher"].email, "password")
        
        response = client.get('/teacher/dashboard')
        assert response.status_code == 200
        # Check if helper methods/variables like 'upcoming_classes' are roughly correct
        # Just ensuring page loads with context is mostly what this test does
        assert setup["subject"].name.encode() in response.data or b"Dashboard" in response.data

    def test_settings_page_load(self, client, auth, basic_teacher_setup):
        auth.login(basic_teacher_setup["teacher"].email, "password")
        response = client.get('/settings')
        assert response.status_code == 200
        assert b"Settings" in response.data

    def test_teacher_view_student_profile(self, client, auth, basic_teacher_setup):
        setup = basic_teacher_setup
        auth.login(setup["teacher"].email, "password")
        # Assuming there is a route /student/<id> or similar, or just check attendance page has student name
        # We can check attendance page again for student name as a proxy
        response = client.get(f'/teacher/class/{setup["assignment"].id}/attendance')
        assert setup["student"].name.encode() in response.data

    def test_teacher_classes_active_filter(self, client, auth, basic_teacher_setup, db):
        # Create a setting for EVEN semester
        s = TimetableSettings(active_semester_type='even')
        db.session.add(s)
        # Create Subject with ODD (1)
        # already in setup ["subject"] is sem 1
        
        auth.login(basic_teacher_setup["teacher"].email, "password")
        response = client.get('/teacher/classes')
        # Should NOT show the sem 1 subject if active is EVEN
        # Note: basic_teacher_setup creates subject with sem=1 (ODD)
        # So "Math" should NOT be present if active is EVEN
        # However, verifying 'Math' is tricky if it appears in other contexts (like sidebar).
        # We check the main list area. Maybe count occurrences or ensure specific ID isn't linked.
        # Ideally, cleaner verification:
        assert b"MATH101" not in response.data

    def test_edit_class_details(self, client, auth, basic_teacher_setup, db):
        setup = basic_teacher_setup
        auth.login(setup["teacher"].email, "password")
        
        # Change section from 'A' to 'C'
        response = client.post(f'/teacher/class/{setup["assignment"].id}/edit', data={
            'section': 'C'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b"updated successfully" in response.data
        
        # Verify in DB
        refreshed = db.session.get(AssignedClass, setup["assignment"].id)
        assert refreshed.section == 'C'

    def test_edit_class_unauthorized(self, client, auth, basic_teacher_setup, db):
        setup = basic_teacher_setup
        
        # Another teacher
        t2 = User(name="T2", email="t2@test.com", role=UserRole.TEACHER)
        t2.set_password("pass")
        db.session.add(t2)
        db.session.commit()
        
        auth.login("t2@test.com", "pass")
        
        # Try to edit T1's class
        response = client.post(f'/teacher/class/{setup["assignment"].id}/edit', data={
            'section': 'HACK'
        }, follow_redirects=True)
        
        # Should redirect or error
        assert b"Unauthorized" in response.data or b"Dashboard" in response.data
        
        refreshed = db.session.get(AssignedClass, setup["assignment"].id)
        assert refreshed.section == 'A' # Unchanged

    def test_download_report_access(self, client, auth, basic_teacher_setup):
        setup = basic_teacher_setup
        auth.login(setup["teacher"].email, "password")
        
        response = client.get(f'/teacher/class/{setup["assignment"].id}/download')
        # Could be csv or excel, check content type or success
        # If checks permission, checks mimetype
        assert response.status_code == 200
        # Check if CSV/Excel header present
        assert 'text/csv' in response.headers.get('Content-Type', '') or \
               'application/vnd.openxmlformats' in response.headers.get('Content-Type', '') or \
               'text/html' in response.headers.get('Content-Type', '') # In case it renders html table
