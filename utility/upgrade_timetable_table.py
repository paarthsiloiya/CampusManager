from app import create_app
from app.models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Upgrading TimetableEntry table...")
    try:
        # Try to add the column (SQLite syntax)
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE timetable_entries ADD COLUMN branch VARCHAR(10) DEFAULT 'COMMON'"))
            conn.commit()
        print("Column 'branch' added successfully.")
    except Exception as e:
        print(f"Error adding column (might already exist): {e}")
        # If error, maybe recreate table?
        # db.metadata.tables['timetable_entries'].drop(db.engine)
        # db.create_all()
