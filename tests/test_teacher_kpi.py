import pytest
from datetime import date, timedelta
from app.models import (
    User, UserRole, Branch, Subject, AssignedClass,
    Enrollment, EnrollmentStatus, Attendance, Marks
)


class TestTeacherKPIDashboard:
    """Unit and integration tests for the Teacher KPI Dashboard feature."""

    @pytest.fixture
    def kpi_setup(self, db):
        """Create a full setup with teacher, students, classes, attendance, and marks."""
        teacher = User(name="KPI Teacher", email="kpi_teacher@test.com", role=UserRole.TEACHER, institution="DTC")
        teacher.set_password("password")

        student1 = User(name="Good Student", email="good@test.com", role=UserRole.STUDENT, semester=1, branch=Branch.CSE, institution="DTC")
        student1.set_password("password")

        student2 = User(name="At Risk Student", email="atrisk@test.com", role=UserRole.STUDENT, semester=1, branch=Branch.CSE, institution="DTC")
        student2.set_password("password")

        subject1 = Subject(name="Data Structures", code="CS201", semester=1, branch="CSE")
        subject2 = Subject(name="Algorithms", code="CS202", semester=1, branch="CSE")

        db.session.add_all([teacher, student1, student2, subject1, subject2])
        db.session.commit()

        assign1 = AssignedClass(teacher_id=teacher.id, subject_id=subject1.id, section="A")
        assign2 = AssignedClass(teacher_id=teacher.id, subject_id=subject2.id, section="A")
        db.session.add_all([assign1, assign2])
        db.session.commit()

        # Enroll both students in both classes
        for student in [student1, student2]:
            for assign in [assign1, assign2]:
                enroll = Enrollment(student_id=student.id, class_id=assign.id, status=EnrollmentStatus.APPROVED)
                db.session.add(enroll)
        db.session.commit()

        # Add attendance records over last 10 days
        today = date.today()
        for i in range(10):
            d = today - timedelta(days=i)
            # Good student: present for all
            db.session.add(Attendance(user_id=student1.id, subject_id=subject1.id, date=d, status='present'))
            db.session.add(Attendance(user_id=student1.id, subject_id=subject2.id, date=d, status='present'))
            # At risk student: present for 5 out of 10 in subject1, absent for all in subject2
            if i < 5:
                db.session.add(Attendance(user_id=student2.id, subject_id=subject1.id, date=d, status='present'))
            else:
                db.session.add(Attendance(user_id=student2.id, subject_id=subject1.id, date=d, status='absent'))
            db.session.add(Attendance(user_id=student2.id, subject_id=subject2.id, date=d, status='absent'))
        db.session.commit()

        # Add marks
        db.session.add(Marks(user_id=student1.id, subject_id=subject1.id, assessment_type='midterm', assessment_name='Midterm 1', max_marks=100, obtained_marks=85))
        db.session.add(Marks(user_id=student2.id, subject_id=subject1.id, assessment_type='midterm', assessment_name='Midterm 1', max_marks=100, obtained_marks=45))
        db.session.add(Marks(user_id=student1.id, subject_id=subject2.id, assessment_type='quiz', assessment_name='Quiz 1', max_marks=50, obtained_marks=40))
        db.session.commit()

        return {
            "teacher": teacher,
            "student1": student1,
            "student2": student2,
            "subject1": subject1,
            "subject2": subject2,
            "assign1": assign1,
            "assign2": assign2,
        }

    # ---- Unit Tests ----

    def test_kpi_page_loads(self, client, auth, kpi_setup):
        """Test that the KPI dashboard page loads successfully for a teacher."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"KPI Dashboard" in response.data

    def test_kpi_access_denied_for_student(self, client, auth, kpi_setup):
        """Test that students cannot access the KPI dashboard."""
        auth.login(kpi_setup["student1"].email, "password")
        response = client.get('/teacher/kpi', follow_redirects=True)
        assert response.status_code == 200
        assert b"KPI Dashboard" not in response.data

    def test_kpi_requires_login(self, client, kpi_setup):
        """Test that unauthenticated users are redirected from KPI dashboard."""
        response = client.get('/teacher/kpi', follow_redirects=True)
        assert response.status_code == 200
        assert b"KPI Dashboard" not in response.data

    def test_kpi_displays_attendance_rate(self, client, auth, kpi_setup):
        """Test that the KPI dashboard displays the attendance rate."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"Attendance Rate" in response.data

    def test_kpi_displays_enrolled_students_count(self, client, auth, kpi_setup):
        """Test that the KPI dashboard shows the total enrolled students."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"Enrolled Students" in response.data
        # We enrolled 2 students
        assert b">2<" in response.data

    def test_kpi_displays_avg_score(self, client, auth, kpi_setup):
        """Test that the KPI dashboard shows average score."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"Avg. Score" in response.data

    def test_kpi_displays_at_risk_section(self, client, auth, kpi_setup):
        """Test that the at-risk students section is present."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"Students At Risk" in response.data

    def test_kpi_identifies_at_risk_student(self, client, auth, kpi_setup):
        """Test that the student with low attendance is identified as at risk."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"At Risk Student" in response.data

    def test_kpi_shows_chart_sections(self, client, auth, kpi_setup):
        """Test that chart sections are present in the dashboard."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"Attendance Distribution" in response.data
        assert b"Attendance by Subject" in response.data
        assert b"Attendance Trend" in response.data
        assert b"Grade Distribution" in response.data

    def test_kpi_chart_data_in_page(self, client, auth, kpi_setup):
        """Test that chart data JSON is embedded in the page."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"kpi-chart-data" in response.data
        assert b"attendance_pie" in response.data
        assert b"class_bar" in response.data
        assert b"trend_line" in response.data
        assert b"grade_dist" in response.data

    def test_kpi_filter_by_class(self, client, auth, kpi_setup):
        """Test that filtering by a specific class works."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get(f'/teacher/kpi?class_id={kpi_setup["assign1"].id}')
        assert response.status_code == 200
        assert b"KPI Dashboard" in response.data
        # Should show Data Structures in the chart data
        assert b"Data Structures" in response.data

    def test_kpi_filter_by_period_7days(self, client, auth, kpi_setup):
        """Test that the 7-day period filter works."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi?period=7days')
        assert response.status_code == 200
        assert b"KPI Dashboard" in response.data

    def test_kpi_filter_by_period_30days(self, client, auth, kpi_setup):
        """Test that the 30-day period filter works."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi?period=30days')
        assert response.status_code == 200
        assert b"KPI Dashboard" in response.data

    def test_kpi_filter_by_period_90days(self, client, auth, kpi_setup):
        """Test that the 90-day period filter works."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi?period=90days')
        assert response.status_code == 200
        assert b"KPI Dashboard" in response.data

    def test_kpi_filter_combined(self, client, auth, kpi_setup):
        """Test that combining class and period filters works."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get(f'/teacher/kpi?class_id={kpi_setup["assign2"].id}&period=30days')
        assert response.status_code == 200
        assert b"Algorithms" in response.data

    # ---- Integration Tests ----

    def test_kpi_empty_state_no_classes(self, client, auth, db):
        """Test KPI dashboard renders correctly for a teacher with no classes."""
        teacher = User(name="Empty Teacher", email="empty@test.com", role=UserRole.TEACHER, institution="DTC")
        teacher.set_password("password")
        db.session.add(teacher)
        db.session.commit()

        auth.login("empty@test.com", "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"KPI Dashboard" in response.data
        assert b"All Students on Track" in response.data
        # No data states
        assert b"No attendance data available" in response.data

    def test_kpi_no_attendance_data(self, client, auth, db):
        """Test KPI dashboard with enrolled students but no attendance records."""
        teacher = User(name="NoAtt Teacher", email="noatt@test.com", role=UserRole.TEACHER, institution="DTC")
        teacher.set_password("password")
        student = User(name="NoAtt Student", email="noatts@test.com", role=UserRole.STUDENT, semester=1, branch=Branch.CSE, institution="DTC")
        student.set_password("password")
        subject = Subject(name="Physics", code="PHY101", semester=1, branch="CSE")
        db.session.add_all([teacher, student, subject])
        db.session.commit()

        assign = AssignedClass(teacher_id=teacher.id, subject_id=subject.id, section="A")
        db.session.add(assign)
        db.session.commit()

        enroll = Enrollment(student_id=student.id, class_id=assign.id, status=EnrollmentStatus.APPROVED)
        db.session.add(enroll)
        db.session.commit()

        auth.login("noatt@test.com", "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"N/A" in response.data
        assert b"No attendance data available" in response.data

    def test_kpi_with_late_records(self, client, auth, db):
        """Test KPI dashboard correctly counts late attendance records."""
        teacher = User(name="Late Teacher", email="late_t@test.com", role=UserRole.TEACHER, institution="DTC")
        teacher.set_password("password")
        student = User(name="Late Student", email="late_s@test.com", role=UserRole.STUDENT, semester=1, branch=Branch.CSE, institution="DTC")
        student.set_password("password")
        subject = Subject(name="Chemistry", code="CHM101", semester=1, branch="CSE")
        db.session.add_all([teacher, student, subject])
        db.session.commit()

        assign = AssignedClass(teacher_id=teacher.id, subject_id=subject.id, section="A")
        db.session.add(assign)
        db.session.commit()

        enroll = Enrollment(student_id=student.id, class_id=assign.id, status=EnrollmentStatus.APPROVED)
        db.session.add(enroll)
        db.session.commit()

        today = date.today()
        db.session.add(Attendance(user_id=student.id, subject_id=subject.id, date=today, status='late'))
        db.session.add(Attendance(user_id=student.id, subject_id=subject.id, date=today - timedelta(days=1), status='present'))
        db.session.commit()

        auth.login("late_t@test.com", "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"Late" in response.data

    def test_kpi_sidebar_has_link(self, client, auth, kpi_setup):
        """Test that the KPI Dashboard link exists in teacher sidebar navigation."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/dashboard')
        assert response.status_code == 200
        assert b"KPI Dashboard" in response.data
        assert b"/teacher/kpi" in response.data

    def test_kpi_invalid_class_filter_ignored(self, client, auth, kpi_setup):
        """Test that an invalid class_id filter is gracefully ignored."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi?class_id=99999')
        assert response.status_code == 200
        assert b"KPI Dashboard" in response.data

    def test_kpi_grade_distribution_data(self, client, auth, kpi_setup):
        """Test that grade distribution data is correctly computed and displayed."""
        auth.login(kpi_setup["teacher"].email, "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        # We have 3 marks: 85% (A), 45% (D), 80% (A)
        assert b"grade_dist" in response.data

    def test_kpi_multiple_teachers_isolated(self, client, auth, db):
        """Test that each teacher only sees their own class KPIs."""
        teacher1 = User(name="T1", email="t1_kpi@test.com", role=UserRole.TEACHER, institution="DTC")
        teacher1.set_password("password")
        teacher2 = User(name="T2", email="t2_kpi@test.com", role=UserRole.TEACHER, institution="DTC")
        teacher2.set_password("password")
        student = User(name="S1", email="s1_kpi@test.com", role=UserRole.STUDENT, semester=1, branch=Branch.CSE, institution="DTC")
        student.set_password("password")

        sub1 = Subject(name="English", code="ENG101", semester=1, branch="CSE")
        sub2 = Subject(name="Hindi", code="HIN101", semester=1, branch="CSE")

        db.session.add_all([teacher1, teacher2, student, sub1, sub2])
        db.session.commit()

        assign1 = AssignedClass(teacher_id=teacher1.id, subject_id=sub1.id, section="A")
        assign2 = AssignedClass(teacher_id=teacher2.id, subject_id=sub2.id, section="A")
        db.session.add_all([assign1, assign2])
        db.session.commit()

        enroll1 = Enrollment(student_id=student.id, class_id=assign1.id, status=EnrollmentStatus.APPROVED)
        enroll2 = Enrollment(student_id=student.id, class_id=assign2.id, status=EnrollmentStatus.APPROVED)
        db.session.add_all([enroll1, enroll2])
        db.session.commit()

        today = date.today()
        db.session.add(Attendance(user_id=student.id, subject_id=sub1.id, date=today, status='present'))
        db.session.add(Attendance(user_id=student.id, subject_id=sub2.id, date=today, status='absent'))
        db.session.commit()

        # Teacher1 should only see English data
        auth.login("t1_kpi@test.com", "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"English" in response.data
        assert b"Hindi" not in response.data

    def test_kpi_pending_enrollment_excluded(self, client, auth, db):
        """Test that students with pending enrollment status are excluded from KPI calculations."""
        teacher = User(name="Pend Teacher", email="pend_t@test.com", role=UserRole.TEACHER, institution="DTC")
        teacher.set_password("password")
        student = User(name="Pending Student", email="pend_s@test.com", role=UserRole.STUDENT, semester=1, branch=Branch.CSE, institution="DTC")
        student.set_password("password")
        subject = Subject(name="Biology", code="BIO101", semester=1, branch="CSE")
        db.session.add_all([teacher, student, subject])
        db.session.commit()

        assign = AssignedClass(teacher_id=teacher.id, subject_id=subject.id, section="A")
        db.session.add(assign)
        db.session.commit()

        # Enrollment is PENDING, not APPROVED
        enroll = Enrollment(student_id=student.id, class_id=assign.id, status=EnrollmentStatus.PENDING)
        db.session.add(enroll)
        db.session.commit()

        auth.login("pend_t@test.com", "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        # Should show 0 enrolled students since none are approved
        assert b">0<" in response.data

    def test_kpi_all_students_on_track(self, client, auth, db):
        """Test that when all students have good attendance, the 'All on Track' message shows."""
        teacher = User(name="Good Teacher", email="good_t@test.com", role=UserRole.TEACHER, institution="DTC")
        teacher.set_password("password")
        student = User(name="Star Student", email="star@test.com", role=UserRole.STUDENT, semester=1, branch=Branch.CSE, institution="DTC")
        student.set_password("password")
        subject = Subject(name="Music", code="MUS101", semester=1, branch="CSE")
        db.session.add_all([teacher, student, subject])
        db.session.commit()

        assign = AssignedClass(teacher_id=teacher.id, subject_id=subject.id, section="A")
        db.session.add(assign)
        db.session.commit()

        enroll = Enrollment(student_id=student.id, class_id=assign.id, status=EnrollmentStatus.APPROVED)
        db.session.add(enroll)
        db.session.commit()

        today = date.today()
        for i in range(10):
            db.session.add(Attendance(user_id=student.id, subject_id=subject.id, date=today - timedelta(days=i), status='present'))
        db.session.commit()

        auth.login("good_t@test.com", "password")
        response = client.get('/teacher/kpi')
        assert response.status_code == 200
        assert b"All Students on Track" in response.data
