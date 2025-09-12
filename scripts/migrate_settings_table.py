#!/usr/bin/env python3
"""
Migration script to add missing columns to existing settings table.
This script adds created_at, updated_at, created_user_id, updated_user_id, valid_from, valid_to, and row_checksum columns.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

def check_column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    """Check if a column exists in the specified table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def add_column_if_not_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str, column_definition: str) -> bool:
    """Add a column to the table if it doesn't already exist."""
    if not check_column_exists(cursor, table_name, column_name):
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
            print(f"✅ Added column '{column_name}' to {table_name}")
            return True
        except sqlite3.Error as e:
            print(f"❌ Error adding column '{column_name}' to {table_name}: {e}")
            return False
    else:
        print(f"ℹ️  Column '{column_name}' already exists in {table_name}")
        return True

def migrate_settings_table(db_path: str) -> bool:
    """
    Migrate the settings table to add missing columns.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        bool: True if migration was successful, False otherwise
    """
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if settings table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if not cursor.fetchone():
            print("ℹ️  Settings table does not exist. Migration not needed.")
            conn.close()
            return True
        
        print("🔄 Starting settings table migration...")
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Define SQLite-specific column types (this script is for SQLite only)
        # For PostgreSQL, a separate migration script would be needed
        columns_to_add = [
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
            ("created_user_id", "TEXT DEFAULT 'a287befc-0570-4eb3-a5d7-46653054cf0f'"),
            ("updated_user_id", "TEXT DEFAULT 'a287befc-0570-4eb3-a5d7-46653054cf0f'"),
            ("row_checksum", "TEXT DEFAULT ''")
        ]
        
        success = True
        for column_name, column_definition in columns_to_add:
            if not add_column_if_not_exists(cursor, "settings", column_name, column_definition):
                success = False
                break
        
        if success:
            # Update existing rows to set timestamps to current time if they are NULL
            current_time = datetime.now().isoformat()
            
            cursor.execute("""
                UPDATE settings 
                SET created_at = ?, 
                    updated_at = ?,
                    valid_from = ?
                WHERE created_at IS NULL OR updated_at IS NULL OR valid_from IS NULL
            """, (current_time, current_time, current_time))
            
            updated_rows = cursor.rowcount
            if updated_rows > 0:
                print(f"✅ Updated {updated_rows} existing rows with timestamp values")
            
            # Commit the transaction
            cursor.execute("COMMIT")
            print("✅ Settings table migration completed successfully!")
            
        else:
            cursor.execute("ROLLBACK")
            print("❌ Migration failed, rolled back changes")
            
        conn.close()
        return success
        
    except sqlite3.Error as e:
        print(f"❌ Database error during migration: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during migration: {e}")
        return False

def main():
    """Main function to run the migration."""
    if len(sys.argv) != 2:
        print("Usage: python migrate_settings_table.py <database_path>")
        print("Example: python migrate_settings_table.py typing_trainer.db")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    # Check if database file exists
    if not Path(db_path).exists():
        print(f"❌ Database file '{db_path}' does not exist")
        sys.exit(1)
    
    print(f"🔍 Migrating database: {db_path}")
    
    # Run the migration
    if migrate_settings_table(db_path):
        print("🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("💥 Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
