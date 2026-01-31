# Utility Scripts Guide

This directory contains helper scripts for managing the Student Management System.

**Important:** These scripts should generally be run using the `docker compose exec` command to ensure they have access to the correct database environment.

## Quick Reference

| Task | Command | Description |
|------|---------|-------------|
| **Setup Project** | `python utility/setup_data.py` | Creates teachers and assigns classes from `data/branch_subjects.json`. |
| **Reset Database** | `python utility/reset_db.py` | **DANGER**: Drops all tables and recreates them. Wipes data. |
| **Create Admin** | `python utility/create_admin.py` | Create a new superuser manualy. |
| **Add Sample Data** | `python utility/add_sample_data.py` | Populates DB with fake students/attendance for testing. |

---

## How to Run Scripts

Since the project uses Docker, the database is inside a container and not directly accessible via `localhost` unless mapped, and even then, Python needs the correct drivers and credentials.

### The Recommended Way (Docker)

Run scripts *inside* the running application container. This guarantees the environment is identical to production.

1. **Ensure app is running**:
   ```bash
   docker compose up -d
   ```

2. **Execute the script**:
   ```bash
   # Syntax: docker compose exec <service_name> python <script_path>
   
   # Example: Reset Database
   docker compose exec admin-server python utility/reset_db.py
   
   # Example: Setup Initial Data
   docker compose exec admin-server python utility/setup_data.py
   ```

### The Local Way (Development Only)

If you have a local Python environment set up with `venv`, you can run scripts locally, but you must ensure the `DATABASE_URL` matches your local setup.

**Note:** If using the Docker database from your host machine, the host is usually `localhost` (mapped port), not `db`.

1. **Set Environment Variable (PowerShell)**:
   ```powershell
   # Point to the mapped port (usually 5433 or 5432)
   $env:DATABASE_URL="postgresql+psycopg2://campus_user:welcome_to_campus@localhost:5433/campus_db"
   ```

2. **Run Script**:
   ```powershell
   python utility/check_working_days.py
   ```

---

## Script Details

### `setup_data.py`
This is your **primary initialization script**. 
- It reads data from `data/branch_subjects.json`.
- It creates or updates `Subject` entries in the database.
- It creates Teacher accounts defined in the script.
- It links Teachers to Subjects (`AssignedClass`).

### `reset_db.py`
**Use with caution.** 
- Connects to the database.
- Drops all tables defined in SQLAlchemy models.
- Re-creates empty tables.
- Useful when you change `models.py` significantly and migrations are too complex.

### `db_check.py`
Diagnoses connection issues. It attempts to connect to the DB and print current user/session info.

### `create_test_accounts.py` / `add_sample_data.py`
Helpers for generating dummy data for students, attendance, and marks to visualize the dashboard.
