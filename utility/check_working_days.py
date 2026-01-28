import os, sys
# ensure project root is on sys.path (same approach as other utility scripts)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from sqlalchemy import inspect, text
from app.models import db

def main():
    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        cols = insp.get_columns('timetable_settings')
        print('Columns (name, type):')
        for c in cols:
            print(' -', c['name'], str(c['type']))

        print('\ninformation_schema for working_days:')
        res = db.session.execute(text("SELECT character_maximum_length, data_type FROM information_schema.columns WHERE table_name='timetable_settings' AND column_name='working_days'"))
        for row in res:
            print(' ->', row)

if __name__ == '__main__':
    main()
