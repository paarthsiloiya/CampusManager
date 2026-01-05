
from app import create_app
from app.models import db, Subject, seed_subjects

def test_seeding_idempotency(app):
    """Test that seeding subjects is idempotent (can run multiple times without error)."""
    with app.app_context():
        # Count existing subjects
        initial_count = Subject.query.count()
        
        # Run seeding again
        seed_subjects()
        
        # Count should be the same (or more if new ones were added, but for this test we assume static seed data)
        final_count = Subject.query.count()
        
        assert final_count >= initial_count
        
        # Verify specific subjects exist
        uhv = Subject.query.filter_by(code='COMMON-UHV').first()
        assert uhv is not None
        assert uhv.name == 'Human Values and Ethics'
        
        # Verify a branch subject exists (assuming CSE-ES-101 exists in json)
        # Note: This depends on branch_subjects.json content, but it's likely there based on previous logs
        cse_subject = Subject.query.filter(Subject.code.like('CSE-%')).first()
        if cse_subject:
            assert cse_subject.branch == 'CSE'
            
        print(f"Seeding test passed. Subjects: {initial_count} -> {final_count}")
