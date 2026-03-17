import pytest
from app.models import (
    User, UserRole, Subject, AssignedClass, Enrollment, EnrollmentStatus,
    Attendance, TimetableEntry, TimetableSettings, Query, Branch, db
)
from datetime import date, time, datetime, timezone, timedelta


class TestAdminKPIDashboard:

    @pytest.fixture(autouse=True)
    def setup(self, db, client):
        # Create admin
        self.admin = User(name="Admin", email="admin@test.com", role=UserRole.ADMIN)
        self.admin.set_password("password")

        # Create teachers
        self.teacher1 = User(name="Teacher CSE", email="teacher_cse@test.com", role=UserRole.TEACHER, branch=Branch.CSE)
        self.teacher1.set_password("password")
        self.teacher2 = User(name="Teacher AIDS", email="teacher_aids@test.com", role=UserRole.TEACHER, branch=Branch.AIDS)
        self.teacher2.set_password("password")

        # Create students
        self.student1 = User(name="Student CSE", email="student_cse@test.com", role=UserRole.STUDENT, branch=Branch.CSE, semester=1)
        self.student1.set_password("password")
        self.student2 = User(name="Student AIDS", email="student_aids@test.com", role=UserRole.STUDENT, branch=Branch.AIDS, semester=1)
        self.student2.set_password("password")

        db.session.add_all([self.admin, self.teacher1, self.teacher2, self.student1, self.student2])
        db.session.commit()

        # Subjects
        self.subject_cse = Subject(name="Data Structures", code="CSE-201", semester=1, branch="CSE")
        self.subject_aids = Subject(name="Data Science", code="AIDS-201", semester=1, branch="AIDS")
        db.session.add_all([self.subject_cse, self.subject_aids])
        db.session.commit()

        # Assigned Classes
        self.class_cse = AssignedClass(teacher_id=self.teacher1.id, subject_id=self.subject_cse.id, section='A')
        self.class_aids = AssignedClass(teacher_id=self.teacher2.id, subject_id=self.subject_aids.id, section='A')
        db.session.add_all([self.class_cse, self.class_aids])
        db.session.commit()

        # Enrollments
        self.enrollment1 = Enrollment(student_id=self.student1.id, class_id=self.class_cse.id, status=EnrollmentStatus.APPROVED)
        self.enrollment2 = Enrollment(student_id=self.student2.id, class_id=self.class_aids.id, status=EnrollmentStatus.APPROVED)
        db.session.add_all([self.enrollment1, self.enrollment2])
        db.session.commit()

        # Attendance records
        today = date.today()
        self.att1 = Attendance(user_id=self.student1.id, subject_id=self.subject_cse.id, date=today, status='present')
        self.att2 = Attendance(user_id=self.student1.id, subject_id=self.subject_cse.id, date=today - timedelta(days=1), status='present')
        self.att3 = Attendance(user_id=self.student1.id, subject_id=self.subject_cse.id, date=today - timedelta(days=2), status='absent')
        self.att4 = Attendance(user_id=self.student2.id, subject_id=self.subject_aids.id, date=today, status='present')
        db.session.add_all([self.att1, self.att2, self.att3, self.att4])
        db.session.commit()

        # Timetable settings and entries
        self.settings = TimetableSettings(
            active_semester_type='odd',
            start_time=time(9, 0), end_time=time(17, 0),
            lunch_duration=60, periods=8
        )
        db.session.add(self.settings)

        self.entry1 = TimetableEntry(
            assigned_class=self.class_cse, day="Monday", period_number=1,
            start_time=time(9, 0), end_time=time(10, 0), semester=1, branch="CSE"
        )
        db.session.add(self.entry1)
        db.session.commit()

    def login_admin(self, client):
        return client.post('/auth/login', data={'email': 'admin@test.com', 'password': 'password'}, follow_redirects=True)

    def login_student(self, client):
        return client.post('/auth/login', data={'email': 'student_cse@test.com', 'password': 'password'}, follow_redirects=True)

    # --- Unit Tests: Dashboard Access ---

    def test_kpi_dashboard_loads(self, client):
        """Test KPI dashboard loads successfully for admin"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        assert b"Admin Dashboard" in response.data

    def test_kpi_dashboard_access_denied_for_non_admin(self, client):
        """Test non-admin users cannot access the KPI dashboard"""
        self.login_student(client)
        response = client.get('/admin/dashboard')
        assert response.status_code == 302  # redirect

    def test_kpi_dashboard_requires_login(self, client):
        """Test KPI dashboard requires authentication"""
        response = client.get('/admin/dashboard')
        assert response.status_code == 302

    # --- Unit Tests: KPI Data ---

    def test_kpi_displays_total_users(self, client):
        """Test KPI dashboard displays total user count"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"Total Users" in response.data

    def test_kpi_displays_students_count(self, client):
        """Test KPI dashboard displays students count"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"Students" in response.data

    def test_kpi_displays_teachers_count(self, client):
        """Test KPI dashboard displays teachers count"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"Teachers" in response.data

    def test_kpi_displays_attendance_rate(self, client):
        """Test KPI dashboard displays attendance rate"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"Attendance Rate" in response.data

    def test_kpi_displays_active_classes(self, client):
        """Test KPI dashboard displays active classes count"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"Active Classes" in response.data

    def test_kpi_displays_subjects(self, client):
        """Test KPI dashboard displays subjects count"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"Subjects" in response.data

    def test_kpi_displays_enrollments(self, client):
        """Test KPI dashboard displays enrollment count"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"Enrollments" in response.data

    def test_kpi_displays_department_performance(self, client):
        """Test KPI dashboard displays department performance table"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"Department Performance" in response.data

    def test_kpi_displays_chart_sections(self, client):
        """Test KPI dashboard displays chart sections"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"Department Distribution" in response.data
        assert b"Attendance Trend" in response.data
        assert b"User Role Distribution" in response.data

    def test_kpi_displays_app_usage_summary(self, client):
        """Test KPI dashboard displays app usage summary"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"App Usage Summary" in response.data
        assert b"Total Attendance Records" in response.data
        assert b"Timetable Entries" in response.data

    # --- Unit Tests: Filters ---

    def test_kpi_filter_by_branch(self, client):
        """Test KPI dashboard filters by branch"""
        self.login_admin(client)
        response = client.get('/admin/dashboard?branch=CSE')
        assert response.status_code == 200
        assert b"Admin Dashboard" in response.data

    def test_kpi_filter_by_period_7days(self, client):
        """Test KPI dashboard filters by 7-day period"""
        self.login_admin(client)
        response = client.get('/admin/dashboard?period=7days')
        assert response.status_code == 200

    def test_kpi_filter_by_period_30days(self, client):
        """Test KPI dashboard filters by 30-day period"""
        self.login_admin(client)
        response = client.get('/admin/dashboard?period=30days')
        assert response.status_code == 200

    def test_kpi_filter_by_period_90days(self, client):
        """Test KPI dashboard filters by 90-day period"""
        self.login_admin(client)
        response = client.get('/admin/dashboard?period=90days')
        assert response.status_code == 200

    def test_kpi_filter_by_user_type_student(self, client):
        """Test KPI dashboard filters by student user type"""
        self.login_admin(client)
        response = client.get('/admin/dashboard?user_type=STUDENT')
        assert response.status_code == 200

    def test_kpi_filter_by_user_type_teacher(self, client):
        """Test KPI dashboard filters by teacher user type"""
        self.login_admin(client)
        response = client.get('/admin/dashboard?user_type=TEACHER')
        assert response.status_code == 200

    def test_kpi_filter_combined(self, client):
        """Test KPI dashboard handles combined filters"""
        self.login_admin(client)
        response = client.get('/admin/dashboard?branch=CSE&period=7days&user_type=STUDENT')
        assert response.status_code == 200

    def test_kpi_filter_invalid_user_type(self, client):
        """Test KPI dashboard handles invalid user type filter gracefully"""
        self.login_admin(client)
        response = client.get('/admin/dashboard?user_type=INVALID')
        assert response.status_code == 200

    def test_kpi_filter_invalid_branch(self, client):
        """Test KPI dashboard handles invalid branch filter gracefully"""
        self.login_admin(client)
        response = client.get('/admin/dashboard?branch=NONEXISTENT')
        assert response.status_code == 200

    # --- Unit Tests: Manage Users ---

    def test_manage_users_loads(self, client):
        """Test manage users page loads successfully for admin"""
        self.login_admin(client)
        response = client.get('/admin/manage_users')
        assert response.status_code == 200
        assert b"User Management" in response.data or b"Manage Users" in response.data

    def test_manage_users_access_denied_for_non_admin(self, client):
        """Test non-admin users cannot access manage users"""
        self.login_student(client)
        response = client.get('/admin/manage_users')
        assert response.status_code == 302

    def test_manage_users_search(self, client):
        """Test manage users search functionality"""
        self.login_admin(client)
        response = client.get('/admin/manage_users?search=Teacher')
        assert response.status_code == 200

    def test_manage_users_lists_users(self, client):
        """Test manage users page lists all users"""
        self.login_admin(client)
        response = client.get('/admin/manage_users')
        assert response.status_code == 200
        # Should contain user names
        assert b"Admin" in response.data
        assert b"Teacher CSE" in response.data or b"teacher_cse" in response.data

    # --- Integration Tests ---

    def test_admin_login_redirects_to_kpi_dashboard(self, client):
        """Test admin login redirects to the KPI dashboard"""
        response = client.post('/auth/login', data={
            'email': 'admin@test.com', 'password': 'password'
        })
        assert response.status_code == 302
        assert '/admin/dashboard' in response.headers.get('Location', '')

    def test_sidebar_has_dashboard_and_manage_users(self, client):
        """Test sidebar contains both Dashboard and Manage Users links"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"Manage Users" in response.data
        assert b"Dashboard" in response.data

    def test_add_user_back_link_goes_to_manage_users(self, client):
        """Test add user page back link points to manage users"""
        self.login_admin(client)
        response = client.get('/admin/add_user')
        assert b"manage_users" in response.data or b"Back to Manage Users" in response.data

    def test_edit_user_back_link_goes_to_manage_users(self, client):
        """Test edit user page back link points to manage users"""
        self.login_admin(client)
        response = client.get(f'/admin/edit_user/{self.student1.id}')
        assert b"manage_users" in response.data or b"Back to Manage Users" in response.data

    def test_edit_user_redirect_to_manage_users(self, client, db):
        """Test editing a user redirects to manage users"""
        self.login_admin(client)
        data = {'name': 'Updated Student', 'phone': '9876543210', 'semester': '2', 'branch': 'CSE'}
        response = client.post(f'/admin/edit_user/{self.student1.id}', data=data)
        assert response.status_code == 302
        assert 'manage_users' in response.headers.get('Location', '')

    def test_delete_user_redirect_to_manage_users(self, client, db):
        """Test deleting a user redirects to manage users"""
        self.login_admin(client)
        # Create a user to delete
        user_to_delete = User(name="ToDelete", email="del@test.com", role=UserRole.STUDENT)
        user_to_delete.set_password("pass")
        db.session.add(user_to_delete)
        db.session.commit()

        response = client.post(f'/admin/delete_user/{user_to_delete.id}')
        assert response.status_code == 302
        assert 'manage_users' in response.headers.get('Location', '')

    def test_add_user_error_redirects_to_manage_users(self, client):
        """Test add user with missing fields redirects to manage users"""
        self.login_admin(client)
        # Missing required fields
        data = {'name': 'Incomplete', 'email': '', 'role': '', 'password': ''}
        response = client.post('/admin/add_user', data=data)
        assert response.status_code == 302
        assert 'manage_users' in response.headers.get('Location', '')

    def test_kpi_no_attendance_data(self, client, db):
        """Test KPI dashboard handles empty attendance data"""
        # Delete all attendance records
        Attendance.query.delete()
        db.session.commit()

        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        assert b"N/A" in response.data

    def test_kpi_department_stats_show_correct_branches(self, client):
        """Test department stats section shows CSE and ME"""
        self.login_admin(client)
        response = client.get('/admin/dashboard')
        assert b"CSE" in response.data
        assert b"AIDS" in response.data

    def test_manage_users_page_is_separate_from_dashboard(self, client):
        """Test that dashboard and manage_users are separate pages"""
        self.login_admin(client)
        dashboard_response = client.get('/admin/dashboard')
        manage_response = client.get('/admin/manage_users')

        assert dashboard_response.status_code == 200
        assert manage_response.status_code == 200
        # Dashboard has KPI content, manage_users has user management
        assert b"Admin Dashboard" in dashboard_response.data
        assert b"Admin Dashboard" not in manage_response.data
        assert b"User Management" in manage_response.data
