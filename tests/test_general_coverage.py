import pytest
from app.models import User, UserRole, Enrollment, Subject, AssignedClass, EnrollmentStatus, TimetableSettings, TimetableEntry, Attendance, Branch
from flask import url_for
from datetime import datetime, date, time, timezone

class TestGeneralCoverage:

    @pytest.fixture(autouse=True)
    def setup_data(self, db):
        # Create users
        self.teacher = User(name="Teacher Two", email="teacher2@test.com", role=UserRole.TEACHER)
        self.teacher.set_password("password")

        self.student = User(name="Student Two", email="student2@test.com", role=UserRole.STUDENT, enrollment_number="S100", semester=2, branch=Branch.CSE)
        self.student.set_password("password")

        self.admin = User(name="Admin Two", email="admin2@test.com", role=UserRole.ADMIN)
        self.admin.set_password("password")

        # Create subject
        self.subject = Subject(name="Adv Math", code="M-202", semester=2, branch="CSE")
        db.session.add_all([self.teacher, self.student, self.admin, self.subject])
        db.session.commit()

        # Assign Class
        self.assigned_class = AssignedClass(
            teacher_id=self.teacher.id,
            subject_id=self.subject.id,
            section="A"
        )
        db.session.add(self.assigned_class)
        db.session.commit()

        # Timetable Settings
        self.settings = TimetableSettings(
            start_time=time(9,0),
            end_time=time(17,0),
            lunch_duration=60,
            periods=7,
            working_days="Monday,Tuesday,Wednesday,Thursday,Friday"
        )
        db.session.add(self.settings)
        db.session.commit()

    # --- Student Views (Coverage/Smoke Tests) ---
    def test_student_dashboard_access(self, client):
        client.post('/auth/login', data={'email': 'student2@test.com', 'password': 'password'})
        response = client.get('/student/dashboard')
        assert response.status_code == 200
        assert b"Dashboard" in response.data

    def test_unauthorized_dashboard_access(self, client):
        response = client.get('/student/dashboard', follow_redirects=True)
        assert response.status_code == 200
        assert b"Login" in response.data or b"Please log in" in response.data

    def test_attendance_view_generic(self, client, db):
        client.post('/auth/login', data={'email': 'student2@test.com', 'password': 'password'})
        db.session.add(Attendance(user_id=self.student.id, subject_id=self.subject.id, date=date.today(), status='present'))
        db.session.commit()
        
        response = client.get('/attendance')
        assert response.status_code == 200
        assert b"Adv Math" in response.data

    # --- Teacher Views (Coverage) ---
    def test_teacher_dashboard_stats(self, client, db):
        client.post('/auth/login', data={'email': 'teacher2@test.com', 'password': 'password'})
        # Case 1: No enrollments
        resp = client.get('/teacher/dashboard')
        assert resp.status_code == 200
        assert b"1" in resp.data # 1 Active Class

        # Case 2: Enrollment exists
        enrollment = Enrollment(student_id=self.student.id, class_id=self.assigned_class.id, status=EnrollmentStatus.PENDING)
        db.session.add(enrollment)
        db.session.commit()
        
        resp = client.get('/teacher/dashboard')
        assert resp.status_code == 200

    def test_teacher_schedule_rendering(self, client, db):
        client.post('/auth/login', data={'email': 'teacher2@test.com', 'password': 'password'})
        entry = TimetableEntry(
            day="Monday", period_number=1, assigned_class_id=self.assigned_class.id,
            start_time=time(9,0), end_time=time(10,0), semester=2, branch="CSE"
        )
        db.session.add(entry)
        db.session.commit()

        # Subject is Sem 2 (Even)
        resp = client.get('/teacher/schedule?group=even')
        assert resp.status_code == 200
        assert b"M-202" in resp.data

    def test_teacher_actions_edit_download(self, client, db):
        client.post('/auth/login', data={'email': 'teacher2@test.com', 'password': 'password'})
        # Edit
        resp = client.post(f'/teacher/class/{self.assigned_class.id}/edit', data={'section': 'B'}, follow_redirects=True)
        assert resp.status_code == 200

        db.session.refresh(self.assigned_class)
        assert self.assigned_class.section == 'B'
        
        # Download (CSV)
        enr = Enrollment(student_id=self.student.id, class_id=self.assigned_class.id, status=EnrollmentStatus.APPROVED)
        db.session.add(enr)
        db.session.commit()
        
        resp = client.get(f'/teacher/class/{self.assigned_class.id}/download')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/csv'

    def test_404_not_found(self, client):
        """Test custom 404 error page"""
        response = client.get('/non/existent/page/123987')
        assert response.status_code == 404
        assert b"404" in response.data or b"Not Found" in response.data

    # --- Admin Views (Coverage) ---
    def test_admin_timetable_view_get(self, client, db):
        client.post('/auth/login', data={'email': 'admin2@test.com', 'password': 'password'})
        resp = client.get('/admin/timetable')
        assert resp.status_code == 200
        assert b"Settings" in resp.data

    def test_admin_timetable_reset(self, client, db):
        client.post('/auth/login', data={'email': 'admin2@test.com', 'password': 'password'})
        entry = TimetableEntry(
            day="Monday", period_number=1, assigned_class_id=self.assigned_class.id,
            start_time=time(9,0), end_time=time(10,0), semester=2, branch="CSE"
        )
        db.session.add(entry)
        db.session.commit()
        
        resp = client.post('/admin/timetable', data={'action': 'reset'}, follow_redirects=True)
        assert resp.status_code == 200
        assert TimetableEntry.query.count() == 0

