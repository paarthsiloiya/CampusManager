import json
import os

def fix_subject_codes():
    file_path = os.path.join('data', 'branch_subjects.json')
    with open(file_path, 'r') as f:
        data = json.load(f)

    changed_count = 0
    
    for branch, branch_data in data['branches'].items():
        if 'semesters' not in branch_data:
            continue
            
        for sem, subjects in branch_data['semesters'].items():
            for subject in subjects:
                if subject['name'] == "Applied Mathematics II" and subject['code'] == "BS-111":
                    print(f"Fixing {branch} Sem {sem}: {subject['name']} (BS-111 -> BS-112)")
                    subject['code'] = "BS-112"
                    changed_count += 1

    if changed_count > 0:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Successfully updated {changed_count} subjects.")
    else:
        print("No subjects needed fixing.")

if __name__ == "__main__":
    fix_subject_codes()
