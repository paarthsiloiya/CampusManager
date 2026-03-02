import pytest
from app.models import User, UserRole, Query, QueryTag, Notification, Branch

class TestQuerySystem:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.student = User(name="Student", email="student@test.com", role=UserRole.STUDENT, semester=1, branch=Branch.CSE)
        self.student.set_password("password")
        
        self.admin = User(name="Admin", email="admin@test.com", role=UserRole.ADMIN)
        self.admin.set_password("password")

        db.session.add_all([self.student, self.admin])
        db.session.commit()

    def test_submit_query(self, client, auth, db):
        """Test submitting a query"""
        auth.login("student@test.com", "password")
        response = client.post('/query/submit', data={
            'title': 'Test Query',
            'tag': 'BUG',
            'description': 'This is a test bug report'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b"Query submitted successfully" in response.data
        
        query = Query.query.first()
        assert query.title == "Test Query"
        assert query.user_id == self.student.id
        assert query.tag == QueryTag.BUG

    def test_admin_view_queries(self, client, auth, db):
        """Test admin viewing queries"""
        # Create a query
        q = Query(user_id=self.student.id, title="Help", description="Desc", tag=QueryTag.ACCOUNT)
        db.session.add(q)
        db.session.commit()
        
        auth.login("admin@test.com", "password")
        response = client.get('/admin/queries')
        assert response.status_code == 200
        assert b"Help" in response.data
        assert b"ACCOUNT" in response.data

    def test_admin_resolve_query(self, client, auth, db):
        """Test resolving a query"""
        q = Query(user_id=self.student.id, title="Resolve Me", description="Desc", tag=QueryTag.FEATURE)
        db.session.add(q)
        db.session.commit()
        
        auth.login("admin@test.com", "password")
        response = client.post(f'/admin/query/{q.id}/resolve', data={
            'action': 'resolve',
            'response': 'Done'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b"resolved successfully" in response.data
        
        # Check query is gone
        assert Query.query.count() == 0
        
        # Check notification created
        notif = Notification.query.filter_by(user_id=self.student.id).first()
        assert notif is not None
        assert "resolved" in notif.message
        assert "Done" in notif.message

    def test_admin_dismiss_query(self, client, auth, db):
        """Test dismissing a query"""
        q = Query(user_id=self.student.id, title="Dismiss Me", description="Desc", tag=QueryTag.OTHER)
        db.session.add(q)
        db.session.commit()
        
        auth.login("admin@test.com", "password")
        response = client.post(f'/admin/query/{q.id}/resolve', data={
            'action': 'dismiss',
            'response': 'Not relevant'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b"dismissed" in response.data
        
        # Check query is gone
        assert Query.query.count() == 0

    def test_admin_filter_queries(self, client, auth, db):
        """Test filtering queries by tag and role"""
        auth.login("admin@test.com", "password")
        # Add queries
        q1 = Query(user_id=self.student.id, title="Bug1", description=".", tag=QueryTag.BUG)
        q2 = Query(user_id=self.student.id, title="Feature1", description=".", tag=QueryTag.FEATURE)
        db.session.add_all([q1, q2])
        db.session.commit()
        
        # Filter by Bug
        response = client.get('/admin/queries?tag=BUG')
        assert b"Bug1" in response.data
        assert b"Feature1" not in response.data
        
        # Filter by Student Role
        response = client.get('/admin/queries?role=STUDENT')
        assert b"Bug1" in response.data
        assert b"Feature1" in response.data