import pytest
import os
from unittest.mock import patch

# Set env FIRST before importing app (though app import might be cached, create_app is a function) 
# But python imports are top level. `from app import create_app` runs app/__init__.py.
# Fortunately create_app logic is inside the function.

# We must ensure create_app uses our config.
# Since create_app reads os.getenv directly, we patch it or set os.environ.

from app import create_app
from app.models import db, User, Subject, AssignedClass, TimetableSettings, TimetableEntry, UserRole, Branch
from app.timetable_generator import TimetableGenerator
from datetime import time

class TestTimetableEngine:
    
    @pytest.fixture
    def app(self):
        # Patch os.getenv/environ to force sqlite memory
        old_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        
        try:
            app = create_app()
            app.config['TESTING'] = True
            # Re-enforce just in case
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
            
            with app.app_context():
                # db.create_all is called in create_app, so tables exist.
                yield app
                db.session.remove()
                db.drop_all()
        finally:
            if old_url:
                os.environ['DATABASE_URL'] = old_url
            else:
                del os.environ['DATABASE_URL']

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @pytest.fixture
    def setup_data(self, app):
        """
        Setup complex scenario:
        - 2 Branches: AIML, CSE
        - 2 Semesters: 1 (Odd), 2 (Even), 3 (Odd)
        - 1 Shared Teacher (teaches across branches and semesters)
        """
        with app.app_context():
            settings = TimetableSettings(
                start_time=time(9, 0),
                end_time=time(12, 0), # 180 mins
                periods=3,            # 60 min periods
                lunch_duration=0,
                working_days="Mon,Tue",
                max_class_duration=60,
                min_class_duration=40,
                active_semester_type='odd'
            )
            # Ensure no duplicates if seed ran
            if TimetableSettings.query.count() > 0:
                TimetableSettings.query.delete()
            db.session.add(settings)

            teacher = User(name="Prof. Shared", email="shared@test.com", role=UserRole.TEACHER)
            teacher.set_password("password")
            db.session.add(teacher)

            # Subjects
            # Credits = 2, so they should appear 2 times in the 2-day schedule (Mon, Tue)
            s1 = Subject(name="Math I", code="AIML-101", semester=1, branch="AIML", credits=2)
            s2 = Subject(name="Math I CSE", code="CSE-101", semester=1, branch="CSE", credits=2)
            s3 = Subject(name="Math III", code="AIML-301", semester=3, branch="AIML", credits=1)
            # Even semester subject - should NOT be scheduled if mode is 'odd'
            s4 = Subject(name="Math II", code="AIML-201", semester=2, branch="AIML", credits=2)
            
            db.session.add_all([s1, s2, s3, s4])
            db.session.flush()

            ac1 = AssignedClass(teacher_id=teacher.id, subject_id=s1.id)
            ac2 = AssignedClass(teacher_id=teacher.id, subject_id=s2.id)
            ac3 = AssignedClass(teacher_id=teacher.id, subject_id=s3.id)
            ac4 = AssignedClass(teacher_id=teacher.id, subject_id=s4.id)
            db.session.add_all([ac1, ac2, ac3, ac4])
            db.session.commit()
            return settings

    def test_day_parsing_bug_fix(self, app):
        """Test that comma separated days are parsed correctly"""
        with app.app_context():
            settings = TimetableSettings()
            gen = TimetableGenerator(db, settings)
            
            # Comma format
            days = gen._parse_days("Mon, Tue, Wed")
            assert days == ['Monday', 'Tuesday', 'Wednesday']
            
            # Full name fallback
            days = gen._parse_days("Monday, Tuesday")
            assert days == ['Monday', 'Tuesday']
            
            # MTWTF format
            days = gen._parse_days("MTWTF")
            assert days == ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    def test_respects_active_semester_type(self, app, setup_data):
        """Test that ONLY odd semesters are generated when active_semester_type='odd'"""
        with app.app_context():
            settings = TimetableSettings.query.first()
            assert settings.active_semester_type == 'odd'
            
            gen = TimetableGenerator(db, settings)
            success = gen.generate_schedule()
            
            assert success is True, f"Generation failed: {gen.errors}"
            
            entries = TimetableEntry.query.all()
            semesters = set(e.semester for e in entries)
            
            assert 1 in semesters
            assert 3 in semesters
            assert 2 not in semesters # Should be excluded
            
            # Switch to EVEN
            settings.active_semester_type = 'even'
            db.session.commit()
            
            gen = TimetableGenerator(db, settings)
            success = gen.generate_schedule()
            assert success is True
            
            entries = TimetableEntry.query.all()
            semesters = set(e.semester for e in entries)
            # We expect 2 to be there now, and (sem%2=0) parity implies sem 2 is key.
            # Generator filters for sem 2 assigned classes.
            # Old odd entries might remain unless we manually cleaned them, 
            # OR implemented a 'clean other' logic. 
            # In my implementation, I only clear entries matching current parity.
            # So ODD entries would persist.
            # But we assert that 2 IN semesters.
            assert 2 in semesters

    def test_credits_constraint_is_minimum(self, app, setup_data):
        """Test that subjects appear AT LEAST as many times as their credits (Filling logic)"""
        with app.app_context():
            settings = TimetableSettings.query.first()
            gen = TimetableGenerator(db, settings)
            gen.generate_schedule()
            
            # AIML-101 has 2 credits
            subject = Subject.query.filter_by(code="AIML-101").first()
            assigned = AssignedClass.query.filter_by(subject_id=subject.id).first()
            
            count = TimetableEntry.query.filter_by(assigned_class_id=assigned.id).count()
            assert count >= 2, f"Expected at least 2 slots for AIML-101, got {count}"

            # AIML-301 has 1 credit
            subject3 = Subject.query.filter_by(code="AIML-301").first()
            assigned3 = AssignedClass.query.filter_by(subject_id=subject3.id).first()
            
            count3 = TimetableEntry.query.filter_by(assigned_class_id=assigned3.id).count()
            assert count3 >= 1, f"Expected at least 1 slot for AIML-301, got {count3}"


    def test_teacher_conflict_avoidance(self, app, setup_data):
        """
        Shared teacher teaches different subjects (AIML-101, CSE-101).
        They cannot be in two places at once.
        """
        with app.app_context():
            gen = TimetableGenerator(db, TimetableSettings.query.first())
            gen.generate_schedule()
            
            teacher = User.query.filter_by(email="shared@test.com").first()
            
            # Get all entries for this teacher
            # Join via AssignedClass
            entries = TimetableEntry.query.join(AssignedClass).filter(AssignedClass.teacher_id == teacher.id).all()
            
            # Check for dupes in (day, period)
            slots = []
            for e in entries:
                slots.append((e.day, e.period_number))
            
            assert len(slots) == len(set(slots)), f"Teacher has collision! {slots}"

    def test_timetable_fills_majority_slots(self, app, setup_data):
        """
        Test that the generator fills empty slots beyond the minimum credits 
        if possible (Maximize utilization).
        Scenario: 
        - 2 Days * 3 Periods = 6 Slots total per cohort.
        - Subject 1 (2 credits), Subject 2 (2 credits). Total Min = 4.
        - We expect the generator to fill the remaining 2 slots (Total 6).
        """
        with app.app_context():
            settings = TimetableSettings.query.first()
            # Ensure settings allow filling (enough teacher availability)
            # Shared teacher has 4 hours of classes (2+2) across 2 subjects in ONE branch for this test?
            # In setup_data we have AIML-101 (2), CSE-101 (2), AIML-301 (1).
            # Let's focus on AIML Sem 1. Only AIML-101 (2 credits). Sem 1 has 6 slots.
            # If we only have 1 subject with 2 credits, it can at most expand to fill the week?
            # Or does it need more subjects?
            # Let's add another subject to AIML Sem 1 to make it interesting.
            
            s_new = Subject(name="Physics", code="AIML-102", semester=1, branch="AIML", credits=1)
            db.session.add(s_new)
            
            # Need a teacher for this. Let's use a new one to avoid conflicts.
            t_new = User(name="Prof. Physics", email="phys@test.com", role=UserRole.TEACHER)
            t_new.set_password("p")
            db.session.add(t_new)
            
            db.session.flush()
            
            ac_new = AssignedClass(teacher_id=t_new.id, subject_id=s_new.id)
            db.session.add(ac_new)
            db.session.commit()
            
            # Now AIML Sem 1 has:
            # - Math I (2 credits)
            # - Physics (1 credit)
            # Total Min = 3. Total Slots = 6.
            # We expect utilization > 3. Ideally 6.
            
            gen = TimetableGenerator(db, settings)
            gen.generate_schedule()
            
            # Check AIML Sem 1
            entries = TimetableEntry.query.filter_by(branch="AIML", semester=1).all()
            count = len(entries)
            
            assert count > 3, f"Timetable too sparse! Got {count} entries, expected > 3 (min credits)."
            assert count >= 5, f"Expected near-full utilization (5 or 6). Got {count}."
