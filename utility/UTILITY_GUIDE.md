# 🛠️ Utility Scripts Guide

This guide explains the purpose and usage of the helper scripts located in the `utility/` folder. These scripts are designed to help with development, testing, and database management.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Database Management](#database-management)
3. [User Management](#user-management)
4. [Data Generation](#data-generation)
5. [Migration Tools](#migration-tools)

---

## 🎯 Overview

The `utility/` folder contains the following scripts:

| Script | Purpose |
|--------|---------|
| `reset_db.py` | Completely resets the database (drops tables, reseeds subjects) |
| `create_admin.py` | Creates a default admin user |
| `create_test_accounts.py` | Creates test student accounts for all semesters |
| `add_sample_data.py` | Populates the database with realistic attendance and marks data |
| `add_institution_field.py` | Migration script to add the 'institution' field to existing users |
| `sync_subjects.py` | Forces synchronization between `branch_subjects.json` and the database subjects table |
| `fix_subject_codes.py` | Resolves data collisions (e.g. duplicate codes) in `branch_subjects.json` |
| `debug_subject_sync.py` | Detailed comparison report between JSON source and Database records |
| `upgrade_timetable_table.py` | Schema migration to enable branch-aware timetables (adds column) |

---

## 🗃️ Database Management

### `reset_db.py`

**Purpose:**  
This is the "nuclear option" for the database. It drops all tables and recreates them from scratch. It also reseeds the initial subject data from `data/branch_subjects.json`.

**Usage:**
```bash
# Full reset (requires confirmation)
python utility/reset_db.py

# Clear user data only (keeps subjects and structure)
python utility/reset_db.py --clear-only

# View database statistics
python utility/reset_db.py --stats
```

**When to use:**
- When you want to start fresh.
- After modifying the database schema (models).
- After updating `branch_subjects.json`.

---

## 👥 User Management

### `create_admin.py`

**Purpose:**  
Creates a default administrator account if one doesn't already exist.

**Usage:**
```bash
python utility/create_admin.py
```

**Default Credentials:**
- **Email:** `admin@example.com`
- **Password:** `admin123`

### `create_test_accounts.py`

**Purpose:**  
Generates a set of student accounts, one for each semester (1-8), rotating through different branches (AIML, AIDS, CST, CSE).

**Usage:**
```bash
python utility/create_test_accounts.py
```

**Generated Accounts:**
- **Emails:** `sem1test@gmail.com` to `sem8test@gmail.com`
- **Password:** `12345678` (for all accounts)

---

## 📝 Data Generation

### `add_sample_data.py`

**Purpose:**  
Fills the database with realistic-looking data for demonstration and testing. It generates attendance records (present/absent/late) and marks for the test users.

**Usage:**
```bash
# Add data for all users
python utility/add_sample_data.py

# Add data for a specific user ID
python utility/add_sample_data.py --user-id 1
```

**When to use:**
- After running `create_test_accounts.py` to give the students some history.
- Before demonstrating the application to show off the charts and analytics.

---

## 🔄 Migration Tools

### `add_institution_field.py`

**Purpose:**  
A one-time migration script used to add the `institution` column to the `user` table for existing databases that were created before this field was introduced.

**Usage:**
```bash
python utility/add_institution_field.py
```

**Note:**  
If you have just run `reset_db.py`, you do **not** need to run this, as the new table structure will already include the field. Use this only if you have an old database you want to preserve.

### `sync_subjects.py`
**Purpose:**
Updates the database to match `data/branch_subjects.json`. It adds new subjects and updates existing ones (credits, names) if changed.

### `fix_subject_codes.py`
**Purpose:**
Fixes specific known data errors in the JSON source file, such as duplicate subject codes across semesters.

### `debug_subject_sync.py`
**Purpose:**
A diagnostic tool that prints out mismatches between the JSON file and the SQLite database. Use this to verify data integrity after a sync.

### `upgrade_timetable_table.py`
**Purpose:**
Adds the `branch` column to the `timetable_entries` table. Essential for upgrading older databases to support the new branch-specific timetable feature.
