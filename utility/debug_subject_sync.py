import json
import os
from app import create_app
from app.models import db, Subject

app = create_app()

def compare_json_db():
    print("Starting comparison between JSON and Database...")
    
    # Load JSON
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'branch_subjects.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        print("Error: branch_subjects.json not found.")
        return

    with app.app_context():
        # Get all subjects from DB
        db_subjects = Subject.query.all()
        # Create a lookup map: (Branch, Semester, Code) -> Subject
        db_map = {}
        for s in db_subjects:
            # Code in DB is "{Branch}-{Code}" usually, but let's check how it's stored.
            # detailed check.
            # The seed function constructs code as f"{branch_code}-{subject_data['code']}"
            db_map[s.code] = s
            # Also map by name for fuzzy check? 
            # No, strict code check first.
        
        print(f"Total subjects in Database: {len(db_subjects)}")
        
        missing_count = 0
        mismatch_count = 0
        total_json_subjects = 0

        for branch_code, branch_data in data.get('branches', {}).items():
            for semester_num, subjects_list in branch_data.get('semesters', {}).items():
                semester_int = int(semester_num)
                
                for subject_data in subjects_list:
                    if not subject_data or not isinstance(subject_data, dict):
                        continue
                        
                    name = subject_data.get('name')
                    code = subject_data.get('code')
                    
                    if not name or not code or code in ['Test', '1', '']:
                        continue

                    total_json_subjects += 1
                    
                    # Expected DB Code
                    # The seed function does: tgt_code = f"{branch_code}-{subject_data['code']}"
                    expected_code = f"{branch_code}-{code}"
                    
                    if expected_code not in db_map:
                        print(f"MISSING in DB: Branch={branch_code}, Sem={semester_num}, Code={expected_code}, Name={name}")
                        missing_count += 1
                        
                        # Check if it exists with raw code (maybe legacy?)
                        raw_match = Subject.query.filter_by(code=code, branch=branch_code).first()
                        if raw_match:
                             print(f"  -> Found with raw code '{code}' instead of '{expected_code}'")
                    else:
                        # Optional: Check name match
                        db_subj = db_map[expected_code]
                        if db_subj.name != name:
                            print(f"MISMATCH Name: {expected_code} | JSON: '{name}' vs DB: '{db_subj.name}'")
                            mismatch_count += 1
                            
        print("-" * 30)
        print(f"Comparison Complete.")
        print(f"Total JSON Subjects checked: {total_json_subjects}")
        print(f"Missing in DB: {missing_count}")
        print(f"Name Mismatches: {mismatch_count}")

if __name__ == '__main__':
    compare_json_db()
