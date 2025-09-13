#!/usr/bin/env python3
"""
Migration script to update the settings table to the new schema.

This script:
1. Examines the current settings table structure
2. Checks for valid user IDs in the users table
3. Backs up existing data
4. Adds missing columns with appropriate default values
5. Migrates existing data to the new format
"""

import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Any, Optional
import hashlib
import json
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database_manager import DatabaseManager, ConnectionType
from helpers.debug_util import DebugUtil

def get_current_table_structure(cursor: sqlite3.Cursor, table_name: str) -> List[Tuple]:
    """Get the current structure of a table."""
    cursor.execute(f'PRAGMA table_info({table_name})')
    return cursor.fetchall()

def get_sample_users(use_cloud: bool = True, limit: int = 10) -> List[Tuple]:
    """Get sample users from the users table."""
    connection_type = ConnectionType.CLOUD if use_cloud else ConnectionType.LOCAL
    debug_util = DebugUtil()
    
    try:
        db_manager = DatabaseManager(
            db_path=None,
            connection_type=connection_type,
            debug_util=debug_util
        )
        
        cursor = db_manager.connection.cursor()
        cursor.execute('SELECT user_id, first_name, last_name, email FROM users LIMIT ?', (limit,))
        result = cursor.fetchall()
        db_manager.close()
        return result
    except Exception:
        return []

def get_first_user_id(use_cloud: bool = True) -> Optional[str]:
    """Get the first user ID from the users table."""
    connection_type = ConnectionType.CLOUD if use_cloud else ConnectionType.LOCAL
    debug_util = DebugUtil()
    
    try:
        db_manager = DatabaseManager(
            db_path=None,
            connection_type=connection_type,
            debug_util=debug_util
        )
        
        cursor = db_manager.connection.cursor()
        cursor.execute('SELECT user_id FROM users LIMIT 1')
        result = cursor.fetchone()
        db_manager.close()
        return result[0] if result else None
    except Exception:
        return None

def calculate_setting_checksum(setting_type_id: str, setting_value: str, related_entity_id: str) -> str:
    """Calculate SHA-256 checksum of business columns for a setting."""
    business_data = "|".join([setting_type_id, setting_value, related_entity_id])
    return hashlib.sha256(business_data.encode("utf-8")).hexdigest()

def backup_existing_settings(cursor: sqlite3.Cursor) -> None:
    """Create a backup of existing settings data."""
    print("Creating backup of existing settings...")
    
    # Create backup table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings_backup_pre_migration AS 
        SELECT * FROM settings
    ''')
    
    # Get count of backed up records
    cursor.execute('SELECT COUNT(*) FROM settings_backup_pre_migration')
    count = cursor.fetchone()[0]
    print(f"Backed up {count} existing settings records")

def examine_current_state(use_cloud: bool = True) -> None:
    """Examine the current database state and display information."""
    connection_type = ConnectionType.CLOUD if use_cloud else ConnectionType.LOCAL
    debug_util = DebugUtil()
    
    db_manager = DatabaseManager(
        db_path=None,  # Will use default based on connection type
        connection_type=connection_type,
        debug_util=debug_util
    )
    
    # Get the underlying connection for direct SQL operations
    conn = db_manager.connection
    cursor = conn.cursor()
    
    try:
        print("=== CURRENT DATABASE STATE ===")
        
        # Check if settings table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if not cursor.fetchone():
            print("❌ Settings table does not exist")
            return
        
        print("✅ Settings table exists")
        
        # Show current structure
        print("\n=== CURRENT SETTINGS TABLE STRUCTURE ===")
        columns = get_current_table_structure(cursor, 'settings')
        for col in columns:
            nullable = "NULL" if not col[3] else "NOT NULL"
            default = f"DEFAULT {col[4]}" if col[4] is not None else "NO DEFAULT"
            print(f'{col[1]:<20} {col[2]:<15} {nullable:<10} {default}')
        
        # Show sample data
        print("\n=== SAMPLE SETTINGS DATA ===")
        cursor.execute('SELECT * FROM settings LIMIT 5')
        rows = cursor.fetchall()
        if rows:
            col_names = [desc[1] for desc in columns]
            print(' | '.join(f'{name:<15}' for name in col_names))
            print('-' * (len(col_names) * 17))
            for row in rows:
                print(' | '.join(f'{str(val):<15}' for val in row))
        else:
            print("No data in settings table")
        
        # Show count
        cursor.execute('SELECT COUNT(*) FROM settings')
        count = cursor.fetchone()[0]
        print(f"\nTotal settings: {count}")
        
        # Check users table
        print("\n=== USERS TABLE INFORMATION ===")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            users = get_sample_users(cursor)
            if users:
                print(f"Found {len(users)} sample users:")
                for user in users:
                    print(f"  {user[0]} - {user[1]} {user[2]} ({user[3]})")
            else:
                print("❌ No users found in users table")
        else:
            print("❌ Users table does not exist")
        
        # Check for missing columns
        print("\n=== MISSING COLUMNS ANALYSIS ===")
        required_columns = {
            'created_user_id': 'TEXT NOT NULL',
            'updated_user_id': 'TEXT NOT NULL', 
            'created_at': 'TEXT NOT NULL',
            'row_checksum': 'TEXT NOT NULL'
        }
        
        existing_columns = {col[1] for col in columns}
        missing_columns = []
        
        for col_name, col_type in required_columns.items():
            if col_name not in existing_columns:
                missing_columns.append((col_name, col_type))
                print(f"❌ Missing: {col_name} {col_type}")
            else:
                print(f"✅ Present: {col_name}")
        
        if missing_columns:
            print(f"\n⚠️  Need to add {len(missing_columns)} missing columns")
        else:
            print("\n✅ All required columns are present")
            
    except Exception as e:
        print(f"Error examining database: {e}")
    finally:
        conn.close()

def migrate_settings_table(default_user_id: str, use_cloud: bool = True) -> bool:
    """Migrate the settings table to the new schema."""
    connection_type = ConnectionType.CLOUD if use_cloud else ConnectionType.LOCAL
    debug_util = DebugUtil()
    
    db_manager = DatabaseManager(
        db_path=None,  # Will use default based on connection type
        connection_type=connection_type,
        debug_util=debug_util
    )
    
    # Get the underlying connection for direct SQL operations
    conn = db_manager.connection
    cursor = conn.cursor()
    
    try:
        print(f"\n=== STARTING MIGRATION ===")
        print(f"Using default user ID: {default_user_id}")
        
        # Begin transaction
        cursor.execute('BEGIN TRANSACTION')
        
        # Backup existing data
        backup_existing_settings(cursor)
        
        # Check current structure
        columns = get_current_table_structure(cursor, 'settings')
        existing_columns = {col[1] for col in columns}
        
        # Add missing columns one by one
        current_time = datetime.now(timezone.utc).isoformat()
        
        if 'created_user_id' not in existing_columns:
            print("Adding created_user_id column...")
            cursor.execute(f'ALTER TABLE settings ADD COLUMN created_user_id TEXT DEFAULT "{default_user_id}"')
            cursor.execute(f'UPDATE settings SET created_user_id = "{default_user_id}" WHERE created_user_id IS NULL')
        
        if 'updated_user_id' not in existing_columns:
            print("Adding updated_user_id column...")
            cursor.execute(f'ALTER TABLE settings ADD COLUMN updated_user_id TEXT DEFAULT "{default_user_id}"')
            cursor.execute(f'UPDATE settings SET updated_user_id = "{default_user_id}" WHERE updated_user_id IS NULL')
        
        if 'created_at' not in existing_columns:
            print("Adding created_at column...")
            cursor.execute(f'ALTER TABLE settings ADD COLUMN created_at TEXT DEFAULT "{current_time}"')
            cursor.execute(f'UPDATE settings SET created_at = "{current_time}" WHERE created_at IS NULL')
        
        if 'row_checksum' not in existing_columns:
            print("Adding row_checksum column...")
            cursor.execute('ALTER TABLE settings ADD COLUMN row_checksum TEXT')
            
            # Calculate checksums for existing records
            print("Calculating checksums for existing records...")
            cursor.execute('SELECT rowid, setting_type_id, setting_value, related_entity_id FROM settings')
            records = cursor.fetchall()
            
            for record in records:
                rowid, setting_type_id, setting_value, related_entity_id = record
                checksum = calculate_setting_checksum(setting_type_id, setting_value, related_entity_id)
                cursor.execute('UPDATE settings SET row_checksum = ? WHERE rowid = ?', (checksum, rowid))
        
        # Commit transaction
        cursor.execute('COMMIT')
        
        print("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        cursor.execute('ROLLBACK')
        return False
    finally:
        conn.close()

def verify_migration(use_cloud: bool = True) -> bool:
    """Verify that the migration was successful."""
    connection_type = ConnectionType.CLOUD if use_cloud else ConnectionType.LOCAL
    debug_util = DebugUtil()
    
    db_manager = DatabaseManager(
        db_path=None,  # Will use default based on connection type
        connection_type=connection_type,
        debug_util=debug_util
    )
    
    # Get the underlying connection for direct SQL operations
    conn = db_manager.connection
    cursor = conn.cursor()
    
    try:
        print("\n=== VERIFYING MIGRATION ===")
        
        # Check new structure
        columns = get_current_table_structure(cursor, 'settings')
        required_columns = {'setting_id', 'setting_type_id', 'setting_value', 'related_entity_id', 
                          'created_user_id', 'updated_user_id', 'created_at', 'updated_at', 'row_checksum'}
        
        existing_columns = {col[1] for col in columns}
        missing = required_columns - existing_columns
        
        if missing:
            print(f"❌ Still missing columns: {missing}")
            return False
        
        print("✅ All required columns present")
        
        # Check data integrity
        cursor.execute('SELECT COUNT(*) FROM settings WHERE created_user_id IS NULL OR updated_user_id IS NULL OR created_at IS NULL OR row_checksum IS NULL')
        null_count = cursor.fetchone()[0]
        
        if null_count > 0:
            print(f"❌ Found {null_count} records with NULL values in required columns")
            return False
        
        print("✅ No NULL values in required columns")
        
        # Check checksum validity
        cursor.execute('SELECT setting_type_id, setting_value, related_entity_id, row_checksum FROM settings LIMIT 5')
        sample_records = cursor.fetchall()
        
        for record in sample_records:
            setting_type_id, setting_value, related_entity_id, stored_checksum = record
            calculated_checksum = calculate_setting_checksum(setting_type_id, setting_value, related_entity_id)
            if stored_checksum != calculated_checksum:
                print(f"❌ Checksum mismatch for record: {record}")
                return False
        
        print("✅ Checksums are valid")
        
        cursor.execute('SELECT COUNT(*) FROM settings')
        final_count = cursor.fetchone()[0]
        print(f"✅ Final record count: {final_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
    finally:
        conn.close()

def main():
    """Main migration function."""
    use_cloud = True  # Default to cloud connection like main_menu.py
    
    print("Settings Table Migration Script (Cloud Database)")
    print("=" * 50)
    
    # First, examine current state
    examine_current_state(use_cloud)
    
    # Get user confirmation and default user ID
    print("\n" + "=" * 50)
    print("MIGRATION PLANNING")
    print("=" * 50)
    
    # Check for users
    first_user_id = get_first_user_id(use_cloud)
    users = get_sample_users(use_cloud)
    
    if not first_user_id:
        print("❌ No users found in database. Cannot proceed with migration.")
        print("Please create at least one user before running this migration.")
        return False
    
    print(f"\nFound {len(users)} users in database.")
    print("Available users:")
    for user in users:
        print(f"  {user[0]} - {user[1]} {user[2]} ({user[3]})")
    
    print(f"\nDefault user ID for migration: {first_user_id}")
    
    # Ask for confirmation
    response = input(f"\nProceed with migration using '{first_user_id}' as default user? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled by user.")
        return False
    
    # Perform migration
    success = migrate_settings_table(first_user_id, use_cloud)
    
    if success:
        # Verify migration
        if verify_migration(use_cloud):
            print("\n🎉 Migration completed successfully!")
            print("\nNext steps:")
            print("1. Test the application to ensure settings work correctly")
            print("2. If everything works, you can drop the backup table: DROP TABLE settings_backup_pre_migration")
            return True
        else:
            print("\n❌ Migration verification failed!")
            return False
    else:
        print("\n❌ Migration failed!")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
