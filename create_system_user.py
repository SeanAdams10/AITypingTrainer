#!/usr/bin/env python3
"""
Script to create a system user for migration purposes.
"""

import sqlite3
import uuid
from datetime import datetime, timezone

def create_system_user(db_path: str) -> str:
    """Create a system user for migration purposes."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("❌ Users table does not exist. Creating it first...")
            # Create a basic users table structure
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
        
        # Check if system user already exists
        cursor.execute("SELECT user_id FROM users WHERE email = 'system@aitypingtrainer.local'")
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"✅ System user already exists: {existing_user[0]}")
            return existing_user[0]
        
        # Create system user
        system_user_id = str(uuid.uuid4())
        current_time = datetime.now(timezone.utc).isoformat()
        
        cursor.execute('''
            INSERT INTO users (user_id, first_name, last_name, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (system_user_id, 'System', 'User', 'system@aitypingtrainer.local', current_time, current_time))
        
        conn.commit()
        print(f"✅ Created system user: {system_user_id}")
        return system_user_id
        
    except Exception as e:
        print(f"❌ Error creating system user: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    db_path = 'typing_data.db'
    system_user_id = create_system_user(db_path)
    print(f"System user ID: {system_user_id}")
