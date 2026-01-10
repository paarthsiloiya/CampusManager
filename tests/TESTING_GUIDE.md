# 🧪 Testing Guide - Student Management System

## 📋 Table of Contents
1. [Automated Testing](#automated-testing)
2. [Coverage Analysis](#coverage-analysis)
3. [Test Environment Utilities](#test-environment-utilities)

---

## 🤖 Automated Testing

The project uses `pytest` for automated unit and integration testing. The test suite covers models, authentication, views, and security.

### Key Test Files (in `tests/` directory)

| File | Purpose |
|------|---------|
| `test_models.py` | Unit tests for data models (User, Attendance, Grades) |
| `test_auth.py` | Integration tests for login, logout, and access control |
| `test_views.py` | General view accessibility and dashboard tests |
| `test_security.py` | Security verification (RBAC, CSRF) |
| `test_student_views.py` | Student specific workflows (Curriculum, Join Class) |
| `test_admin_teacher_views.py` | Admin and Teacher operations |
| `test_account_management.py` | Account lifecycle tests |
| `test_timetable_full.py` | Extensive coverage of Timetable Generator (collisions, constraints, parity logic) |
| `test_timetable_export.py` | Unit and integration tests for Timetable Export (Excel/PDF) |
| `test_views_coverage.py` | Additional coverage for Timetable views, Teacher schedule rendering, and Student dashboards |

### Running Tests

Run all tests from the project root:

```bash
pytest
```

Run specific test files:
```bash
pytest tests/test_models.py
```

Run with verbose output:
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
**`utility/add_sample_data.py`** & **`test_attendance_generator.py`**
Populate the database with realistic attendance and grade data for testing scenarios.
```bash
python utility/add_sample_data.py
# or
python test_attendance_generator.py
```
