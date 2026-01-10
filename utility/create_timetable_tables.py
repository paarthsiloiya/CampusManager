from app import create_app
from app.models import db, TimetableSettings, TimetableEntry

app = create_app()

with app.app_context():
    print("Creating timetable tables...")
    try:
        TimetableSettings.__table__.create(db.engine)
        print("Created timetable_settings table")
    except Exception as e:
        print(f"Error creating timetable_settings: {e}")

    try:
        TimetableEntry.__table__.create(db.engine)
        print("Created timetable_entries table")
    except Exception as e:
        print(f"Error creating timetable_entries: {e}")
    
    print("Done.")
