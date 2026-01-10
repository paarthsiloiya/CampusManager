import pytest
import io
from app.models import User, UserRole, TimetableEntry, TimetableSettings, AssignedClass, Subject, Branch, db
from app.excel_export import generate_timetable_excel
from flask import url_for
from datetime import time, datetime

class TestTimetableExport:
    
    @pytest.fixture(autouse=True)
    def setup(self, db, client):
        # Create admin
        self.admin = User(name="Admin", email="admin@test.com", role=UserRole.ADMIN)
        self.admin.set_password("password")
        
        # Create teacher
        self.teacher = User(name="Teacher", email="teacher@test.com", role=UserRole.TEACHER)
        self.teacher.set_password("password")
        
        # Create subjects and assigned class
        self.subject1 = Subject(name="Math", code="CSE-101", semester=1, branch="CSE")
        self.subject2 = Subject(name="Physics", code="ME-101", semester=1, branch="ME")
        
        self.assigned1 = AssignedClass(teacher=self.teacher, subject=self.subject1)
        self.assigned2 = AssignedClass(teacher=self.teacher, subject=self.subject2)
        
        db.session.add_all([self.admin, self.teacher, self.subject1, self.subject2, self.assigned1, self.assigned2])
        db.session.commit()
        
        # Create Timetable Settings
        self.settings = TimetableSettings(
            start_time=time(9, 0),
            end_time=time(17, 0),
            lunch_duration=60,
            periods=8
        )
        db.session.add(self.settings)
        
        # Create Timetable Entries
        self.entry1 = TimetableEntry(
            assigned_class=self.assigned1,
            day="Monday",
            period_number=1,
            start_time=time(9, 0),
            end_time=time(10, 0),
            semester=1,
            branch="CSE"
        )
        self.entry2 = TimetableEntry(
            assigned_class=self.assigned2,
            day="Tuesday",
            period_number=2,
            start_time=time(10, 0),
            end_time=time(11, 0),
            semester=1,
            branch="ME"
        )
        db.session.add_all([self.entry1, self.entry2])
        db.session.commit()

    def login_admin(self, client):
        return client.post('/auth/login', data={'email': 'admin@test.com', 'password': 'password'}, follow_redirects=True)

    def test_excel_generator_function(self):
        """Test the generate_timetable_excel function directly"""
        entries_by_branch = {
            "CSE": [self.entry1],
            "ME": [self.entry2]
        }
        
        excel_io = generate_timetable_excel(entries_by_branch)
        assert isinstance(excel_io, io.BytesIO)
        
        # Verify it's a valid zip file (Excel files are zip files)
        from zipfile import ZipFile, is_zipfile
        assert is_zipfile(excel_io)
        
        with ZipFile(excel_io) as zf:
            # Check if sheets exists (worksheets are usually xl/worksheets/sheetX.xml)
            files = zf.namelist()
            # We expect at least sheet1 and sheet2 (or named sheets)
            # The structure of xlsx includes xl/worksheets/sheet1.xml
            assert any('xl/worksheets/sheet' in f for f in files)

    def test_download_timetable_excel_all_branches(self, client):
        """Test downloading Excel for all branches"""
        self.login_admin(client)
        response = client.get('/admin/timetable/download?format=excel&branch=all')
        
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'timetable_export_all.xlsx' in response.headers['Content-Disposition']

    def test_download_timetable_excel_single_branch(self, client):
        """Test downloading Excel for a single branch"""
        self.login_admin(client)
        response = client.get('/admin/timetable/download?format=excel&branch=CSE')
        
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'timetable_export_CSE.xlsx' in response.headers['Content-Disposition']

    def test_download_timetable_pdf_all_branches(self, client):
        """Test PDF (print view) for all branches"""
        self.login_admin(client)
        response = client.get('/admin/timetable/download?format=pdf&branch=all')
        
        assert response.status_code == 200
        # The header/button might have been removed or hidden, so we check for the core data content
        assert b"CSE" in response.data
        assert b"ME" in response.data
        assert b"Semester 1" in response.data

    def test_download_timetable_pdf_single_branch(self, client):
        """Test PDF (print view) for single branch"""
        self.login_admin(client)
        response = client.get('/admin/timetable/download?format=pdf&branch=CSE')
        
        assert response.status_code == 200
        assert b"CSE" in response.data
        # With single branch, we might ensure ME is NOT shown if logic separates them strictly
        # But 'all_timetables' logic in view might handle it.
        # Let's verify structure.
        
        # Based on implementation, if we query filter by branch=CSE, we shouldn't see 'ME' if logic is correct
        assert b"Physics" not in response.data
        assert b"Math" in response.data

    def test_download_no_data(self, client):
        """Test handling of empty data"""
        self.login_admin(client)
        response = client.get('/admin/timetable/download?format=excel&branch=Civil') # Non-existent branch
        
        # It should redirect back to timetable view with a flash message
        assert response.status_code == 302
        assert '/admin/timetable' in response.headers['Location']
