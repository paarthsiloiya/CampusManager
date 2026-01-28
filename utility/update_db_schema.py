#!/usr/bin/env python3
"""
Database Schema Update Tool

This script handles database schema migrations and updates without losing data.
It checks for missing columns, tables, or other schema changes and applies them.

Usage:
    python utility/update_db_schema.py
"""

import os
import sys
from sqlalchemy import text, inspect

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db

def check_and_add_column(connection, table_name, column_name, column_type):
    """
    Checks if a column exists in a table, and adds it if it doesn't.
    """
    inspector = inspect(connection)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    
    if column_name in columns:
        print(f"  ✅ Column '{column_name}' already exists in '{table_name}'.")
        return False
    else:
        print(f"  ➕ Adding column '{column_name}' to '{table_name}'...")
        try:
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
            print(f"     Successfully added.")
            return True
        except Exception as e:
            print(f"     ❌ Error adding column: {e}")
            return False

def run_migrations():
    """
    Define all schema updates here.
    """
    app = create_app()
    with app.app_context():
        print("🔧 Checking database schema for required updates...")
        
        with db.engine.connect() as connection:
            # Migration 1: Add Google Classroom link
            change_made = check_and_add_column(
                connection, 
                'assigned_classes', 
                'google_classroom_link', 
                'VARCHAR(255)'
            )
            
            # Migration 2: Add Location
            change_made_2 = check_and_add_column(
                connection, 
                'assigned_classes', 
                'location', 
                'VARCHAR(100)'
            )

            if change_made or change_made_2:
                connection.commit()
                print("💾 Changes committed to database.")
            else:
                print("✨ Database schema columns are up to date.")

            # Migration 3: Ensure timetable_settings.working_days has sufficient length
            try:
                cols = [c['name'] for c in inspect(connection).get_columns('timetable_settings')]
                if 'working_days' in cols:
                    print("  🔁 Ensuring 'working_days' column type/length is VARCHAR(255)...")
                    try:
                        # PostgreSQL syntax
                        connection.execute(text("ALTER TABLE timetable_settings ALTER COLUMN working_days TYPE VARCHAR(255)"))
                        print("     ✅ Altered 'working_days' to VARCHAR(255).")
                    except Exception as e:
                        # Some DBs (e.g., SQLite) won't support ALTER TYPE; attempt a generic ALTER
                        try:
                            connection.execute(text("ALTER TABLE timetable_settings ALTER COLUMN working_days TYPE TEXT"))
                            print("     ✅ Altered 'working_days' to TEXT as fallback.")
                        except Exception as e2:
                            print(f"     ⚠️ Could not alter column type (DB may not support ALTER COLUMN): {e2}")
                else:
                    print("  ℹ️ 'working_days' column not present; skipping type check.")
            except Exception as e:
                print(f"  ⚠️ Failed to inspect 'timetable_settings' columns: {e}")
        
        # Ensure new tables are created
        print("🔧 Checking for new tables...")
        db.create_all()
        print("✅ Tables synced.")

if __name__ == "__main__":
    run_migrations()
