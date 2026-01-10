
import pytest
from app import create_app
from app.models import db, User, Subject, AssignedClass, TimetableSettings, TimetableEntry, UserRole, Branch
from app.timetable_generator import TimetableGenerator
from datetime import time

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def setup_data(app):
    """
    Setup complex scenario:
    - 2 Branches: AIML, CSE
    - 2 Semesters: 1 (Odd), 2 (Even), 3 (Odd)
    - 1 Shared Teacher (teaches across branches and semesters)
    - 1 Settings object
    """
    with app.app_context():
        # Settings
        settings = TimetableSettings(
            start_time=time(9, 0),
            end_time=time(12, 0), # 3 Hours
            periods=3, # 1 hour per period (simplified)
            lunch_duration=0,
            working_days="Mon,Tue",
            max_class_duration=60,
            min_class_duration=40
        )
        db.session.add(settings)

        # Teacher
        teacher = User(name="Prof. Shared", email="shared@test.com", role=UserRole.TEACHER)
        teacher.set_password("password")
        db.session.add(teacher)
        
        # Subjects & Assignments
        
        # 1. AIML Sem 1 (Odd)
        s1 = Subject(name="Math I", code="AIML-101", semester=1, branch="AIML")
        db.session.add(s1)
        db.session.flush()
        ac1 = AssignedClass(teacher_id=teacher.id, subject_id=s1.id)
        db.session.add(ac1)
        
        # 2. CSE Sem 1 (Odd) - Collision Hazard with AIML Sem 1
        s2 = Subject(name="Math I CSE", code="CSE-101", semester=1, branch="CSE")
        db.session.add(s2)
        db.session.flush()
        ac2 = AssignedClass(teacher_id=teacher.id, subject_id=s2.id)
        db.session.add(ac2)
        
        # 3. AIML Sem 3 (Odd) - Collision Hazard with AIML Sem 1
        s3 = Subject(name="Math III", code="AIML-301", semester=3, branch="AIML")
        db.session.add(s3)
        db.session.flush()
        ac3 = AssignedClass(teacher_id=teacher.id, subject_id=s3.id)
        db.session.add(ac3)
        
        # 4. AIML Sem 2 (Even) - No Collision with Odd
        s4 = Subject(name="Math II", code="AIML-201", semester=2, branch="AIML")
        db.session.add(s4)
        db.session.flush()
        ac4 = AssignedClass(teacher_id=teacher.id, subject_id=s4.id)
        db.session.add(ac4)
        
        db.session.commit()
        return settings

def test_config_validation(app, setup_data):
    """Test 1: Generator validates configuration correctly"""
    with app.app_context():
        settings = TimetableSettings.query.first()
        
        # Invalid Case: Min > Max
        settings.min_class_duration = 70
        settings.max_class_duration = 60
        gen = TimetableGenerator(db, settings)
        assert gen.validate() == False
        assert "Minimum class duration cannot be greater than maximum" in gen.errors[0]
        
        # Valid Case
        settings.min_class_duration = 40
        gen = TimetableGenerator(db, settings)
        assert gen.validate() == True

def test_timetable_generation_success(app, setup_data):
    """Test 2: Can generate entries"""
    with app.app_context():
        settings = TimetableSettings.query.first()
        gen = TimetableGenerator(db, settings)
        
        success = gen.generate_schedule()
        assert success == True
        assert len(gen.generated_entries) > 0

def test_inter_branch_collision_avoidance(app, setup_data):
    """
    Test 3: Inter-Branch Collision (Odd Sem)
    Teacher 'Prof. Shared' teaches AIML-101 (Sem 1) and CSE-101 (Sem 1).
    These MUST NOT be scheduled at the same time (Day, Period).
    """
    with app.app_context():
        gen = TimetableGenerator(db, TimetableSettings.query.first())
        gen.generate_schedule()
        
        entries = TimetableEntry.query.all()
        
        # Get entries for the teacher
        # We need to join with AssignedClass to filter by teacher
        teacher = User.query.filter_by(email="shared@test.com").first()
        teacher_entries = [e for e in entries if e.assigned_class.teacher_id == teacher.id]
        
        # Check odd semester entries only for this test
        odd_entries = [e for e in teacher_entries if e.semester % 2 != 0]
        
        # Collect slots: (Day, Period)
        slots = []
        for e in odd_entries:
            slot = (e.day, e.period_number)
            slots.append(slot)
            
        # If slots contains duplicates, it means collision occurred
        # e.g. Mon P1 for AIML and Mon P1 for CSE
        unique_slots = set(slots)
        
        assert len(slots) == len(unique_slots), f"Collision detected for Shared Teacher in Odd Semesters! Slots: {slots}"

def test_inter_sem_collision_avoidance(app, setup_data):
    """
    Test 4: Inter-Semester Collision (Odd Sem)
    Teacher teaches Sem 1 and Sem 3.
    These share the 'Odd' busy map, so they MUST NOT overlap.
    """
    with app.app_context():
        gen = TimetableGenerator(db, TimetableSettings.query.first())
        gen.generate_schedule()
        
        teacher = User.query.filter_by(email="shared@test.com").first()
        entries = TimetableEntry.query.join(AssignedClass).filter(AssignedClass.teacher_id == teacher.id).all()
        
        odd_entries = [e for e in entries if e.semester % 2 != 0]
        
        # Check if Sem 1 and Sem 3 entries overlap
        slots = [(e.day, e.period_number) for e in odd_entries]
        unique_slots = set(slots)
        
        assert len(slots) == len(unique_slots), "Collision between Sem 1 and Sem 3 for same teacher!"

def test_odd_even_independence(app, setup_data):
    """
    Test 5: Odd vs Even Independence.
    Teacher teaches Sem 1 (Odd) and Sem 2 (Even).
    Current logic treats them as SEPARATE domains.
    So they ARE allowed to have the same (Day, Period).
    
    If this behavior is intended (different shifts/terms), this test PASSES if overlaps exist or don't exist 
    (strictly speaking, they are independent, so overlaps are irrelevant).
    
    But to verify implementation, we check that constraints don't cross over.
    We check that busy_map of Odd didn't block Even.
    """
    with app.app_context():
        gen = TimetableGenerator(db, TimetableSettings.query.first())
        gen.generate_schedule()
        
        teacher = User.query.filter_by(email="shared@test.com").first()
        entries = TimetableEntry.query.join(AssignedClass).filter(AssignedClass.teacher_id == teacher.id).all()
        
        odd_entries = [e for e in entries if e.semester % 2 != 0]
        even_entries = [e for e in entries if e.semester % 2 == 0]
        
        assert len(odd_entries) > 0, "Should have scheduled Odd classes"
        assert len(even_entries) > 0, "Should have scheduled Even classes"
        
        # We don't assert collision or non-collision here because random chance might separate them anyway.
        # But we verify that both got scheduled successfully, implying no "total blocking".

def test_lunch_break_logic(app):
    """Test 6: Lunch break calculation/insertion logic in Generator (implicitly via period times)"""
    with app.app_context():
        settings = TimetableSettings(
            start_time=time(10, 0),
            end_time=time(13, 0), # 180 mins
            lunch_duration=60,    # Lunch: 60 mins. Available for class: 120 mins.
            periods=2,            # 60 mins per period
            working_days="Mon",
        )
        db.session.add(settings)
        # Add basic class
        s = Subject(name="Test", code="T-1", semester=1)
        db.session.add(s)
        t = User(name="T", email="t@t.com", role=UserRole.TEACHER)
        t.set_password("password") # Fix: Set password to avoid IntegrityError
        db.session.add(t)
        db.session.flush()
        ac = AssignedClass(teacher_id=t.id, subject_id=s.id)
        db.session.add(ac)
        db.session.commit()
        
        gen = TimetableGenerator(db, settings)
        gen.generate_schedule()
        
        entries = TimetableEntry.query.order_by(TimetableEntry.period_number).all()
        assert len(entries) > 0
        
        # Period 1 start: 10:00. End: 11:00.
        # Lunch after period: 2 // 2 = 1.
        # So Lunch is after Period 1.
        # Period 2 start should be: 10:00 + 60(P1) + 60(Lunch) = 12:00.
        
        p1 = next((e for e in entries if e.period_number == 1), None)
        p2 = next((e for e in entries if e.period_number == 2), None)
        
        if p1 and p2:
            assert p1.start_time == time(10, 0)
            assert p2.start_time == time(12, 0)

