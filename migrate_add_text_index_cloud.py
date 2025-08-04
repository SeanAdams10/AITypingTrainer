#!/usr/bin/env python3
"""
Database migration script to add text_index column to session_keystrokes table (CLOUD VERSION).

This script:
1. Adds a nullable text_index column to session_keystrokes table
2. Populates the column using ROW_NUMBER() partitioned by session_id, ordered by keystroke_time ASC
3. Makes the column NOT NULL after population

Usage:
    python migrate_add_text_index_cloud.py
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path before any project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from db.database_manager import ConnectionType, DatabaseManager

def migrate_add_text_index_cloud():
    """Add text_index column to session_keystrokes table and populate it (CLOUD VERSION)."""
    
    print("=== Adding text_index column to session_keystrokes table (CLOUD) ===")
    print("Connecting to cloud database...")
    
    try:
        # Connect to the cloud database
        db_manager = DatabaseManager(connection_type=ConnectionType.CLOUD)
        print("✓ Connected to cloud database successfully")
        
        # Check if text_index column already exists
        print("Checking if text_index column exists...")
        
        # For PostgreSQL, check column existence
        column_exists_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = 'session_keystrokes' 
            AND column_name = 'text_index'
        """
        
        result = db_manager.fetchone(column_exists_query, (db_manager.SCHEMA_NAME,))
        
        if result:
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
            add_column_query = """
                ALTER TABLE session_keystrokes 
                ADD COLUMN text_index INTEGER
            """
            db_manager.execute(add_column_query)
            print("✓ Added text_index column (nullable)")
        
        # Step 2: Populate the column using ROW_NUMBER()
        print("Populating text_index values using ROW_NUMBER()...")
        
        # PostgreSQL supports ROW_NUMBER() window function
        update_query = """
            UPDATE session_keystrokes 
            SET text_index = subquery.row_num - 1
            FROM (
                SELECT keystroke_id, 
                       ROW_NUMBER() OVER (
                           PARTITION BY session_id 
                           ORDER BY keystroke_time ASC, keystroke_id ASC
                       ) as row_num
                FROM session_keystrokes
            ) AS subquery
            WHERE session_keystrokes.keystroke_id = subquery.keystroke_id
        """
        
        cursor = db_manager.execute(update_query)
        total_updated = cursor.rowcount
        print(f"✓ Populated text_index for {total_updated} keystrokes")
        
        # Step 3: Handle any remaining NULL values (set to 0)
        null_update_query = "UPDATE session_keystrokes SET text_index = 0 WHERE text_index IS NULL"
        cursor = db_manager.execute(null_update_query)
        null_updated = cursor.rowcount
        if null_updated > 0:
            print(f"✓ Set {null_updated} NULL text_index values to 0")
        
        # Step 4: Make the column NOT NULL
        print("Making text_index column NOT NULL...")
        
        alter_not_null_query = """
            ALTER TABLE session_keystrokes 
            ALTER COLUMN text_index SET NOT NULL
        """
        db_manager.execute(alter_not_null_query)
        print("✓ Set text_index column to NOT NULL")
        
        print("\n✅ Migration completed successfully!")
        
        # Verify the migration
        count_query = "SELECT COUNT(*) as total_count FROM session_keystrokes"
        result = db_manager.fetchone(count_query)
        total_count = result["total_count"] if result else 0
        
        non_null_query = "SELECT COUNT(*) as non_null_count FROM session_keystrokes WHERE text_index IS NOT NULL"
        result = db_manager.fetchone(non_null_query)
        non_null_count = result["non_null_count"] if result else 0
        
        print(f"Verification: {non_null_count}/{total_count} keystrokes have text_index values")
        
        if total_count > 0:
            range_query = "SELECT MIN(text_index) as min_val, MAX(text_index) as max_val FROM session_keystrokes"
            result = db_manager.fetchone(range_query)
            if result:
                min_val = result["min_val"]
                max_val = result["max_val"]
                print(f"text_index range: {min_val} to {max_val}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'db_manager' in locals():
            db_manager.close()

if __name__ == "__main__":
    migrate_add_text_index_cloud()
