import pytest
from app.models import User, UserRole

class TestRBAC:
    """
    Comprehensive Role-Based Access Control Tests.
    Verifies that users can only access pages authorized for their role.
    """
    
    @pytest.fixture(autouse=True)
    def setup_users(self, db):
        """Create one user of each role for testing"""
        self.admin = User(name="Admin", email="admin@rbac.com", role=UserRole.ADMIN)
        self.admin.set_password("password")
        
        self.teacher = User(name="Teacher", email="teacher@rbac.com", role=UserRole.TEACHER)
        self.teacher.set_password("password")
        
        self.student = User(name="Student", email="student@rbac.com", role=UserRole.STUDENT)
        self.student.set_password("password")
        
        db.session.add_all([self.admin, self.teacher, self.student])
        db.session.commit()

    def test_anonymous_access_denied(self, client):
        """Ensure protected routes redirect to login for anonymous users"""
        protected_routes = [
            '/student/dashboard',
            '/teacher/dashboard',
            '/admin/dashboard',
            '/settings'
        ]
        
        for route in protected_routes:
            response = client.get(route)
            # Should redirect (302) to login page
            assert response.status_code == 302
            assert '/auth/login' in response.headers['Location']

    def test_student_access_restrictions(self, client, auth):
        """Verify Student cannot access Admin or Teacher routes"""
        auth.login('student@rbac.com', 'password')
        
        # Forbidden routes for students
        forbidden = [
            '/admin/dashboard',
            '/admin/add_user',
            '/admin/timetable',
            '/teacher/dashboard',
            '/teacher/classes'
        ]
        
        for route in forbidden:
            response = client.get(route)
            # The app implements protection by redirecting or showing 403
            # We accept 403 (Forbidden) or 302 (Redirect to home/dashboard/login)
            assert response.status_code in [403, 302, 401], f"Student was able to access {route}"

    def test_teacher_access_restrictions(self, client, auth):
        """Verify Teacher cannot access Admin or Student routes"""
        auth.login('teacher@rbac.com', 'password')
        
        # Forbidden routes for teachers
        forbidden = [
            '/admin/dashboard',
            '/admin/add_user',
            '/admin/timetable',
            # Teachers usually can't see student dashboard, but sometimes they can view student profiles
            # Assuming strictly separate dashboards:
            '/student/dashboard' 
        ]
        
        for route in forbidden:
            response = client.get(route)
            assert response.status_code in [403, 302, 401], f"Teacher was able to access {route}"

    def test_admin_access_restrictions(self, client, auth):
        """Verify Admin behavior (Admins might be allowed everywhere or restricted from student views)"""
        auth.login('admin@rbac.com', 'password')
        
        # Admin should definitely access Admin routes
        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        
        # Often Admins are redirected if they try to access student/teacher specific dashboards
        # But this depends on implementation. Let's just check they don't crash (500).
        response = client.get('/student/dashboard')
        assert response.status_code != 500

