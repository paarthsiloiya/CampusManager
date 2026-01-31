import pytest
from app.models import Marks, User, Subject, Attendance, AttendanceSummary

class TestModelEdgeCases:
    """
    Unit tests for Model methods, focusing on edge cases,
    boundary conditions, and logic verification.
    """

    def test_marks_grade_boundaries(self):
        """Test grade calculation at boundary values"""
        user_id = 1 # Dummy
        subject_id = 1 # Dummy
        
        # Helper to create marks
        def get_grade(obtained, max_m):
            m = Marks(obtained_marks=obtained, max_marks=max_m, user_id=user_id, subject_id=subject_id, assessment_type="Quiz", assessment_name="Q1")
            return m.grade

        # Test A+ (>= 90%)
        assert get_grade(90, 100) == 'A+'
        assert get_grade(100, 100) == 'A+'
        
        # Test A (>= 80% and < 90%)
        assert get_grade(80, 100) == 'A'
        assert get_grade(89.9, 100) == 'A'
        
        # Test F (< 40%)
        assert get_grade(39, 100) == 'F'
        assert get_grade(0, 100) == 'F'
        
        # Test Zero Max Marks (Should not crash, handle division by zero)
        m_zero = Marks(obtained_marks=0, max_marks=0, user_id=user_id, subject_id=subject_id, assessment_type="Quiz", assessment_name="Q1")
        assert m_zero.percentage == 0
        assert m_zero.grade == 'F'

    def test_attendance_summary_calculation(self):
        """Test attendance percentage calculation"""
        summary = AttendanceSummary(total_classes=10, classes_attended=8)
        assert summary.attendance_percentage == 80.0
        
        # Test Division by Zero
        summary_empty = AttendanceSummary(total_classes=0, classes_attended=0)
        assert summary_empty.attendance_percentage == 0

    def test_user_overall_attendance_zero_classes(self, db):
        """Test get_overall_attendance_stats with no attendance records"""
        user = User(name="Test Student", email="model_test@test.com", password_hash="hash")
        db.session.add(user)
        db.session.commit()
        
        stats = user.get_overall_attendance_stats()
        
        assert stats['total_classes'] == 0
        assert stats['attendance_percentage'] == 0
        assert stats['needed_for_75'] == 0

    def test_needed_for_75_calculation(self, db):
        """Test the logic that calculates how many classes are needed for 75%"""
        # We need to mock get_subjects_for_semester and get_attendance_for_subject
        # or actually create the data. Creating data is more robust integration/model test.
        
        user = User(name="Attendance Student", email="att_student@test.com", password_hash="hash", semester=1)
        subject = Subject(name="Math", code="M101", semester=1, branch="COMMON")
        db.session.add_all([user, subject])
        db.session.commit()
        
        # Case 1: 50% attendance (2 total, 1 attended). Needs more to reach 75%.
        # (1 + x) / (2 + x) = 0.75  => 1 + x = 1.5 + 0.75x => 0.25x = 0.5 => x = 2
        
        a1 = Attendance(user_id=user.id, subject_id=subject.id, date=datetime.now(), status='present')
        a2 = Attendance(user_id=user.id, subject_id=subject.id, date=datetime.now(), status='absent')
        db.session.add_all([a1, a2])
        db.session.commit()
        
        # Force refresh of stats
        stats = user.get_overall_attendance_stats()
        
        assert stats['total_classes'] == 2
        assert stats['attended_classes'] == 1
        assert stats['attendance_percentage'] == 50.0
        
        # Explanation: (1 attended + 2 needed) / (2 total + 2 needed) = 3/4 = 75%
        assert stats['needed_for_75'] == 2

from datetime import datetime
