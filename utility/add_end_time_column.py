from app import create_app
from app.models import db
import sqlite3

app = create_app()

def add_end_time_column():
    # Since SQLite doesn't support generic ALTER TABLE flexibly with SQLAlchemy easily without migration tool,
    # we will use raw SQL to add the column if it doesn't exist.
    
    with app.app_context():
        # Check if column exists
        insp = db.inspect(db.engine)
        columns = [c['name'] for c in insp.get_columns('timetable_settings')]
        
        if 'end_time' not in columns:
            print("Adding end_time column to timetable_settings...")
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE timetable_settings ADD COLUMN end_time TIME"))
                # Note: TIME type in SQLite is usually TEXT/VARCHAR. 
                # Flask-SQLAlchemy handles conversion. Default was 16:30 per model but for existing rows it will be NULL unless we set it.
                
                # Update existing rows to have default 16:30
                conn.execute(db.text("UPDATE timetable_settings SET end_time = '16:30:00' WHERE end_time IS NULL"))
                conn.commit()
            print("Column added.")
        else:
            print("Column end_time already exists.")

if __name__ == '__main__':
    add_end_time_column()
