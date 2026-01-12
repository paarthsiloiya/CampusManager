# 🧪 Testing Guide - Student Management System

## 📋 Table of Contents
1. [Automated Testing](#automated-testing)
2. [Coverage Analysis](#coverage-analysis)
3. [Test Environment Utilities](#test-environment-utilities)

---

## 🤖 Automated Testing

The project uses `pytest` for automated unit and integration testing. The test suite has been consolidated into feature-focused modules to maintain organization and ease of use.

### Test Architecture (in `tests/` directory)

We have organized the test suite into 6 core "Feature Suites" containing **75 tests** (Coverage: ~80%):

#### 1. `test_auth_models.py` (Foundation & Security)
*   **Authentication**: Login success/failure, Logout, Session cleanup.
*   **Models**: User creation, Password hashing verification (including empty string checks), String representation.
*   **Security**: RBAC (Role-Based Access Control) ensuring Students/Teachers cannot access Admin routes.
*   **Edge Cases**: Duplicate email registration prevention, Enum handling (string vs Enum object).

#### 2. `test_student_features.py` (Student Experience)
*   **Dashboard**: Verifies access to attendance stats and upcoming classes.
*   **Academics**: Curriculum view, Calendar event loading, Subject filtering.
*   **Class Actions**: Joining classes (including prevention of duplicate joins), Viewing attendance history.
*   **Profile**: Updating personal details (Phone, DOB), Changing passwords (with validation).
*   **Account**: Account deletion flow and confirmation security.

#### 3. `test_teacher_features.py` (Teacher Tools)
*   **Class Management**: Dashboard "Live Class" detection, Editing class details (Sections), Viewing assigned classes (Active/Past semester filter).
*   **Attendance**: Marking attendance (Lecture vs Lab handling), Preventing unauthorized modifications.
*   **Enrollments**: Viewing enrollment requests, Approving/Rejecting students.
*   **Security**: Ensuring teachers cannot edit or view reports for classes they don't own.

#### 4. `test_admin_features.py` (System Administration)
*   **User Management**: Adding Users with detailed profiles (Branch, DOB, Institution), Editing Users, Deleting Users (with self-delete protection).
*   **Timetables**: Generating timetables (algorithm integration), Exporting to Excel/PDF.
*   **System Settings**: Toggling Semester types (Odd/Even), managing global constraints.
*   **Assignments**: Assigning teachers to subjects, Deleting assignments.

#### 5. `test_timetable_engine.py` (Core Logic)
*   **Algorithm**: Validates the genetic/heuristic algorithm for schedule generation.
*   **Constraints**: Checks collision avoidance (Teacher double-booking, Student overlapping classes).
*   **Optimization**: Verifies lunch break placement and load distribution.

#### 6. `test_general_coverage.py` (Health Checks)
*   **Route Availability**: Iterates through all registered Flask routes to ensure no 500 errors.
*   **Static Assets**: Verifies critical templates and static files are reachable.

#### 7. `test_active_class_dashboard.py` (Real-Time Logic)
*   **Student Dashboard**: Verifies "Active Class" widget correctly identifies classes based on current time (IST/UTC conversion) and Branch (handling collisions between streams like AIML/CSE).
*   **Teacher Actions**: Verifies "Take Attendance" button only appears during scheduled class hours.

### Running Tests

Run **all tests** from the project root:

```bash
pytest
```

Run a specific feature suite (e.g., Teacher features):
```bash
pytest tests/test_teacher_features.py
```

Run with verbose output to see individual test names:
```bash
pytest -v
```

---

## 📈 Coverage Analysis

We aim for at least **70% code coverage** to ensure system reliability.

### Generating Reports

Run tests with coverage tracking:
```bash
coverage run -m pytest
```

View the coverage report in the terminal:
```bash
coverage report -m
```

Generate a detailed HTML report (opens in `htmlcov/index.html`):
```bash
coverage html
```

---

## 🛠️ Test Environment Utilities

Several utility scripts are provided to set up the environment for manual testing or demonstration.

### Database Management
**`utility/reset_db.py`**
- **Reset Database**: `python utility/reset_db.py` (Drops and recreates all tables)
- **Clear Data Only**: `python utility/reset_db.py --clear-only` (Removes users/data, keeps schema)
- **Check Stats**: `python utility/reset_db.py --stats`

### Test Accounts
**`utility/create_test_accounts.py`**
Creates 8 standard test accounts (one per semester) with password `12345678`.
```bash
python utility/create_test_accounts.py
```

### Data Generation
**`utility/add_sample_data.py`**
Populates the database with basic sample data.

**`utility/generate_realistic_attendance.py`** (Previously `test_attendance_generator.py`)
A powerful interactive script to generate realistic, historical attendance patterns (Excellent, Good, Poor scenarios) for testing analytics.
```bash
python utility/generate_realistic_attendance.py
```
*(Follow the on-screen menu instructions)*

**`utility/check_calendar.py`**
Quick utility to verify calendar event loading logic.
