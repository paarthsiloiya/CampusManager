# Branch-Aware Curriculum Management Guide

This guide explains how to manage the branch-aware curriculum system, including adding new branches, semesters, and subjects.

## 🎓 System Overview

The system now uses a **branch-aware architecture** where:
- Each branch (AIML, AIDS, CST, CSE) has its own curriculum
- Subjects are stored in `data/branch_subjects.json`
- Database creates branch-prefixed subject codes (e.g., `AIML-ES-101`)
- Students only see subjects relevant to their branch

## 📁 File Structure

```
data/
├── branch_subjects.json    # Master curriculum data (branch-specific)
└── semesters.json         # Legacy file (deprecated - use branch_subjects.json)
```

## 🏢 Adding a New Branch

### Step 1: Update the Database Model

Add the new branch to the `Branch` enum in `app/models.py`:

```python
class Branch(enum.Enum):
    AIML = "AIML"  # Artificial Intelligence & Machine Learning
    AIDS = "AIDS"  # Artificial Intelligence & Data Science
    CST = "CST"    # Computer Science & Technology
    CSE = "CSE"    # Computer Science & Engineering
    IOT = "IOT"    # Internet of Things (NEW BRANCH)
```

### Step 2: Update Registration Form

Add the new branch option in `app/templates/Auth/signin.html`:

```html
<select id="branch" name="branch" required class="...">
    <option value="">Select your branch</option>
    <option value="AIML">AIML - Artificial Intelligence & Machine Learning</option>
    <option value="AIDS">AIDS - Artificial Intelligence & Data Science</option>
    <option value="CST">CST - Computer Science & Technology</option>
    <option value="CSE">CSE - Computer Science & Engineering</option>
    <option value="IOT">IOT - Internet of Things</option> <!-- NEW -->
</select>
```

### Step 3: Update Profile Settings

Add the branch option in the dashboard profile settings in `app/templates/Student/student_dashboard.html`:

```html
<select id="branch" class="border p-2 w-full ml-2">
    <option value="AIML" {% if student.branch == 'AIML' %}selected{% endif %}>AIML - AI & Machine Learning</option>
    <option value="AIDS" {% if student.branch == 'AIDS' %}selected{% endif %}>AIDS - AI & Data Science</option>
    <option value="CST" {% if student.branch == 'CST' %}selected{% endif %}>CST - Computer Science & Technology</option>
    <option value="CSE" {% if student.branch == 'CSE' %}selected{% endif %}>CSE - Computer Science & Engineering</option>
    <option value="IOT" {% if student.branch == 'IOT' %}selected{% endif %}>IOT - Internet of Things</option> <!-- NEW -->
</select>
```

### Step 4: Update Form Validation

Update the validation in `app/auth.py`:

```python
if not branch or branch not in ['AIML', 'AIDS', 'CST', 'CSE', 'IOT']:
    errors.append('Please select a valid branch.')
```

### Step 5: Add Branch Curriculum

Add the new branch structure to `data/branch_subjects.json`:

```json
{
  "branches": {
    "IOT": {
      "name": "Internet of Things",
      "semesters": {
        "1": [
          {
            "name": "Programming Fundamentals",
            "faculty": "Dr. IoT Expert",
            "icon": "https://img.icons8.com/pulsar-line/96/code.png",
            "code": "ES-101",
            "credits": 3
          },
          {
            "name": "Electronics Basics",
            "faculty": "Prof. Hardware",
            "icon": "https://img.icons8.com/pulsar-line/96/electrical.png",
            "code": "IOT-101",
            "credits": 4
          }
        ]
      }
    }
  }
}
```

## 📚 Adding New Subjects to Existing Branch

### Method 1: Add to Existing Semester

Edit `data/branch_subjects.json` and add the subject to the appropriate semester:

```json
{
  "branches": {
    "AIML": {
      "semesters": {
        "3": [
          {
            "name": "Deep Learning Fundamentals",
            "faculty": "Dr. Neural Networks",
            "icon": "https://img.icons8.com/pastel-glyph/64/intelligent-person.png",
            "code": "DL-301",
            "credits": 4
          }
        ]
      }
    }
  }
}
```

### Method 2: Add New Semester

Add a new semester with subjects:

```json
{
  "branches": {
    "AIML": {
      "semesters": {
        "4": [
          {
            "name": "Computer Vision",
            "faculty": "Dr. Vision Expert",
            "icon": "https://img.icons8.com/pulsar-line/96/camera.png",
            "code": "CV-401",
            "credits": 4
          },
          {
            "name": "Natural Language Processing",
            "faculty": "Dr. Language AI",
            "icon": "https://img.icons8.com/pulsar-line/96/talk-male.png",
            "code": "NLP-401",
            "credits": 3
          }
        ]
      }
    }
  }
}
```

## 🔄 Database Operations

### Reset Database After Changes

After making changes to branches or subjects, reset the database:

```bash
python utility/reset_db.py
```

This will:
1. Drop all existing tables
2. Recreate tables with new schema
3. Seed branch-specific subjects from JSON
4. Create unique codes like `AIML-ES-101`, `CSE-BS-111`

### Create Test Accounts

Generate test accounts for all branches:

```bash
python utility/create_test_accounts.py
```

## 🎨 Available Icons

Use these icon URLs for subjects:

```json
{
  "Programming": "https://img.icons8.com/pulsar-line/96/code.png",
  "AI/ML": "https://img.icons8.com/pastel-glyph/64/intelligent-person.png",
  "Mathematics": "https://img.icons8.com/pulsar-line/96/tangent.png",
  "Physics": "https://img.icons8.com/pulsar-line/96/physics.png",
  "Chemistry": "https://img.icons8.com/pulsar-line/96/acid-flask.png",
  "Database": "https://img.icons8.com/pulsar-line/96/database.png",
  "Networks": "https://img.icons8.com/pulsar-line/96/network.png",
  "Electronics": "https://img.icons8.com/pulsar-line/96/electrical.png",
  "Graphics": "https://img.icons8.com/pulsar-line/96/3d-modeling.png",
  "Security": "https://img.icons8.com/pulsar-line/96/security-lock.png",
  "Mobile": "https://img.icons8.com/pulsar-line/96/mobile-phone.png",
  "Cloud": "https://img.icons8.com/pulsar-line/96/cloud.png",
  "Blockchain": "https://img.icons8.com/pulsar-line/96/blockchain.png",
  "Communication": "https://img.icons8.com/pulsar-line/96/talk-male.png",
  "Statistics": "https://img.icons8.com/pulsar-line/96/statistics.png",
  "Management": "https://img.icons8.com/pulsar-line/96/management.png",
  "Ethics": "https://img.icons8.com/pulsar-line/96/volunteering.png",
  "Default": "https://img.icons8.com/ios/96/book--v1.png"
}
```

## 🔧 System Behavior

### Automatic Features

1. **Branch Filtering**: Students only see subjects for their branch
2. **Subject Codes**: Automatically prefixed with branch (e.g., `AIML-ML-301`)
3. **Icon Mapping**: JSON icons automatically display in dashboard
4. **Faculty Info**: JSON faculty names show in subject cards

### Database Structure

```
Subject Table:
├── id (Primary Key)
├── name (Subject Name)
├── code (Branch-prefixed: "AIML-ES-101")
├── semester (1-8)
├── credits (Credit hours)
└── branch (AIML/AIDS/CST/CSE/etc.)
```

## 📋 Branch-Specific Examples

### AIML (AI & Machine Learning)
- Focus: Artificial Intelligence, Machine Learning, Neural Networks
- Unique Subjects: ML Basics, Deep Learning, Computer Vision, NLP
- Math Heavy: Linear Algebra, Statistics, Probability

### AIDS (AI & Data Science)  
- Focus: Data Analysis, Big Data, AI for Data
- Unique Subjects: Data Mining, Data Visualization, Big Data Analytics
- Statistics Heavy: Advanced Statistics, Data Modeling

### CST (Computer Science & Technology)
- Focus: Software Development, Systems, Technology
- Unique Subjects: Software Engineering, System Design, DevOps
- Tech Heavy: Cloud Computing, Microservices

### CSE (Computer Science & Engineering)
- Focus: Traditional CS with Engineering Foundation
- Unique Subjects: Computer Architecture, VLSI, Embedded Systems
- Engineering Heavy: Digital Logic, Computer Organization

## 🚀 Quick Commands

```bash
# Reset database after JSON changes
python utility/reset_db.py

# Create test accounts for all branches
python utility/create_test_accounts.py

# Start development server
python main.py

# Test specific branch login
# Use: sem1test@gmail.com (AIML), sem2test@gmail.com (AIDS), etc.
```

## ⚠️ Important Notes

1. **JSON First**: Always update `branch_subjects.json` first, then reset database
2. **Unique Codes**: Each branch-subject combination gets unique database code
3. **Case Sensitive**: Branch codes are case-sensitive (AIML, not aiml)
4. **Credits**: Ensure credit values match university requirements
5. **Faculty Names**: Keep faculty names consistent across subjects

The system automatically handles all the complexity - you just need to update the JSON file! 🎯