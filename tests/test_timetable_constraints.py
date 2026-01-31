import pytest
from app.models import TimetableSettings, TimetableEntry, AssignedClass, Subject, User, UserRole
from app.timetable_generator import TimetableGenerator
from datetime import time

class TestTimetableConstraints:
    """
    Test validation logic and edge cases for TimetableGenerator.
    """
    
    @pytest.fixture
    def setup_base_db(self, db):
        """Create minimal valid assignments for validation to fail on other things"""
        # Essential: We need at least 1 class for the active semester type
        t = User(name="Teacher", email="t@t.com", role=UserRole.TEACHER)
        t.set_password('123')
        db.session.add(t)
        
        s = Subject(name="Valid Sub", code="SUB1", semester=1, branch="CSE") # Odd sem
        db.session.add(s)
        db.session.flush()
        
        ac = AssignedClass(teacher_id=t.id, subject_id=s.id)
        db.session.add(ac)
        db.session.commit()
    
    def test_impossible_time_configuration(self, db, setup_base_db):
        """Test configurations that result in 0 or negative period duration"""
        # Scenario: Start 9:00, End 9:30, Lunch 40
        # Total time 30 mins < Lunch 40 mins -> Avail -10 mins.
        
        settings = TimetableSettings(
            start_time=time(9, 0),
            end_time=time(9, 30),
            lunch_duration=40,
            periods=4,
            active_semester_type='odd'
        )
        
        gen = TimetableGenerator(db, settings)
        is_valid = gen.validate()
        
        assert is_valid is False
        assert any("Non-positive" in e for e in gen.errors) or any("Calculated period duration is non-positive" in e for e in gen.errors)

    def test_no_classes_validation(self, db):
        """Test validation fails if no classes are assigned"""
        # Do NOT use setup_base_db here.
        # Ensure clean state (db fixture drops all)
        
        settings = TimetableSettings(
            start_time=time(9, 0),
            end_time=time(17, 0),
            lunch_duration=60,
            periods=8,
            active_semester_type='odd'
        )
        
        gen = TimetableGenerator(db, settings)
        is_valid = gen.validate()
        
        assert is_valid is False
        assert any("No classes found" in e for e in gen.errors)

    def test_period_duration_too_short(self, db, setup_base_db):
        """Test warning/error when period duration < min_class_duration"""
        # Available: 4 hours (240 mins) - 60 lunch = 180 mins.
        # Periods: 10.
        # Duration = 18 mins.
        # Min Duration default is 40.
        
        settings = TimetableSettings(
            start_time=time(9, 0),
            end_time=time(13, 0),
            lunch_duration=60,
            periods=10,
            min_class_duration=40,
            active_semester_type='odd'
        )
        
        gen = TimetableGenerator(db, settings)
        # Validate might return True (soft warning) or False depending on implementation.
        # Implementation says: self.errors.append(...) but "We don't return False here necessarily"
        # Let's check if it appends an error/warning string.
        
        gen.validate()
        assert any("Period duration" in e for e in gen.errors)
        assert any("less than minimum" in e for e in gen.errors)

    def test_zero_periods(self, db, setup_base_db):
        """Test validation with 0 periods"""
        settings = TimetableSettings(periods=0, active_semester_type='odd')
        
        gen = TimetableGenerator(db, settings)
        assert gen.validate() is False
        assert any("non-positive" in e.lower() for e in gen.errors)

