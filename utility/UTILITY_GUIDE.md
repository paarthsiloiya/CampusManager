# 🛠️ Utility Scripts Guide

This guide explains the purpose and usage of the helper scripts located in the `utility/` folder. These scripts are designed to help with development, testing, and database management.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Database Management](#database-management)
3. [User & Data Setup](#user--data-setup)
4. [Data Synchronization](#data-synchronization)

---

## 🎯 Overview

The `utility/` folder contains the following core scripts:

| Script | Purpose |
|--------|---------|
| `setup_data.py` | **Primary Setup Tool**: Configures teachers, subjects, and class assignments. |
| `reset_db.py` | Completely resets the database (drops tables, reseeds subjects). |
| `sync_subjects.py` | Forces synchronization between `branch_subjects.json` and the database. |
| `create_admin.py` | Creates a default admin user. |
| `create_test_accounts.py` | Creates test student accounts for all semesters. |
| `add_sample_data.py` | Populates the database with realistic attendance and marks data. |

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
- After updating `branch_subjects.json` significantly.

---

## 👥 User & Data Setup

### `setup_data.py`

**Purpose:**  
The main configuration script for the application. You should edit this file to define your real-world faculty members and their subject assignments.

**Features:**
- Validates that all subjects exist in the database before running.
- Creates Teacher accounts if they don't exist.
- Assigns subjects to teachers (creating `AssignedClass` records).
- Prevents duplicate assignments.

**Usage:**
1. Open `utility/setup_data.py`.
2. Edit the `TEACHERS_DATA` list with your faculty details.
3. Run:
```bash
python utility/setup_data.py
```

### `create_admin.py`

**Purpose:**  
Creates a default administrator account if one doesn't already exist.

**Usage:**
```bash
python utility/create_admin.py
```
**Credentials:** `admin@example.com` / `admin123`

### `create_test_accounts.py`

**Purpose:**  
Generates a set of student accounts, one for each semester (1-8), rotating through different branches.

**Usage:**
```bash
python utility/create_test_accounts.py
```
**Credentials:** `semXtest@gmail.com` / `12345678`

### `add_sample_data.py`

**Purpose:**  
Fills the database with realistic-looking attendance and marks data for demonstration.

**Usage:**
```bash
python utility/add_sample_data.py
```

---

## 🔄 Data Synchronization

### `sync_subjects.py`

**Purpose:**  
Refreshes the database subject list from the source file `data/branch_subjects.json`.

**When to use:**
- If you have manually edited `data/branch_subjects.json` (e.g., added new subjects, fixed codes, or changed credits).
- Run this **before** running `setup_data.py` if you have added new subjects ensuring they are available for assignment.

**Usage:**
```bash
python utility/sync_subjects.py
```
