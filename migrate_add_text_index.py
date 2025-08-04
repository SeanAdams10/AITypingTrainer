#!/usr/bin/env python3
"""
Database migration script to add text_index column to session_keystrokes table.

This script:
1. Adds a nullable text_index column to session_keystrokes table
2. Populates the column using ROW_NUMBER() partitioned by session_id, ordered by keystroke_time ASC
3. Makes the column NOT NULL after population

Usage:
    python migrate_add_text_index.py
"""

import os
import sqlite3
import sys
from pathlib import Path

def get_database_path():
    """Get the path to the typing_data.db database."""
    # Get the project root directory
    project_root = Path(__file__).parent
    db_path = project_root / "typing_data.db"
    
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        print("Please ensure you're running this script from the project root directory.")
        sys.exit(1)
    
    return str(db_path)

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in the specified table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col[1] == column_name for col in columns)

def migrate_add_text_index():
    """Add text_index column to session_keystrokes table and populate it."""
    db_path = get_database_path()
    
    print(f"Connecting to database: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if text_index column already exists
        if check_column_exists(cursor, 'session_keystrokes', 'text_index'):
            print("text_index column already exists in session_keystrokes table.")
            response = input("Do you want to repopulate the values? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                return
            else:
                print("Repopulating text_index values...")
        else:
            print("Adding text_index column to session_keystrokes table...")
            
            # Step 1: Add the column as nullable
            cursor.execute("""
                ALTER TABLE session_keystrokes 
                ADD COLUMN text_index INTEGER
            """)
            print("✓ Added text_index column (nullable)")
        
        # Step 2: Populate the column using ROW_NUMBER()
        print("Populating text_index values using ROW_NUMBER()...")
        
        # SQLite doesn't support ROW_NUMBER() in older versions, so we'll use a different approach
        # First, get all sessions
        cursor.execute("SELECT DISTINCT session_id FROM session_keystrokes WHERE session_id IS NOT NULL")
        sessions = cursor.fetchall()
        
        total_updated = 0
        
        for (session_id,) in sessions:
            print(f"Processing session: {session_id}")
            
            # Get all keystrokes for this session ordered by keystroke_time
            cursor.execute("""
                SELECT keystroke_id, keystroke_time 
                FROM session_keystrokes 
                WHERE session_id = ? 
                ORDER BY keystroke_time ASC, keystroke_id ASC
            """, (session_id,))
            
            keystrokes = cursor.fetchall()
            
            # Update each keystroke with its text_index (0-based)
            for index, (keystroke_id, keystroke_time) in enumerate(keystrokes):
                cursor.execute("""
                    UPDATE session_keystrokes 
                    SET text_index = ? 
                    WHERE keystroke_id = ?
                """, (index, keystroke_id))
                total_updated += 1
        
        print(f"✓ Populated text_index for {total_updated} keystrokes")
        
        # Step 3: Handle any remaining NULL values (set to 0)
        cursor.execute("UPDATE session_keystrokes SET text_index = 0 WHERE text_index IS NULL")
        null_updated = cursor.rowcount
        if null_updated > 0:
            print(f"✓ Set {null_updated} NULL text_index values to 0")
        
        # Step 4: Check if we need to make the column NOT NULL
        # SQLite doesn't support ALTER COLUMN to add NOT NULL constraint
        # We'll need to recreate the table
        print("Making text_index column NOT NULL...")
        
        # Get the current table schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='session_keystrokes'")
        create_sql = cursor.fetchone()[0]
        
        if 'text_index INTEGER NOT NULL' not in create_sql:
            # Create new table with NOT NULL constraint
            cursor.execute("""
                CREATE TABLE session_keystrokes_new (
                    session_id TEXT,
                    keystroke_id TEXT PRIMARY KEY,
                    keystroke_time TEXT,
                    keystroke_char TEXT,
                    expected_char TEXT,
                    is_error INTEGER,
                    time_since_previous INTEGER,
                    text_index INTEGER NOT NULL
                )
            """)
            
            # Copy data to new table
            cursor.execute("""
                INSERT INTO session_keystrokes_new 
                SELECT session_id, keystroke_id, keystroke_time, keystroke_char, 
                       expected_char, is_error, time_since_previous, text_index
                FROM session_keystrokes
            """)
            
            # Drop old table and rename new table
            cursor.execute("DROP TABLE session_keystrokes")
            cursor.execute("ALTER TABLE session_keystrokes_new RENAME TO session_keystrokes")
            
            print("✓ Recreated table with NOT NULL constraint on text_index")
        else:
            print("✓ text_index column already has NOT NULL constraint")
        
        # Commit the changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM session_keystrokes")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM session_keystrokes WHERE text_index IS NOT NULL")
        non_null_count = cursor.fetchone()[0]
        
        print(f"Verification: {non_null_count}/{total_count} keystrokes have text_index values")
        
        if total_count > 0:
            cursor.execute("SELECT MIN(text_index), MAX(text_index) FROM session_keystrokes")
            min_val, max_val = cursor.fetchone()
            print(f"text_index range: {min_val} to {max_val}")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== Adding text_index column to session_keystrokes table ===")
    migrate_add_text_index()
