#!/usr/bin/env python3
"""Test script to verify cloud database connection."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath("."))

from db.database_manager import DatabaseManager, ConnectionType
from helpers.debug_util import DebugUtil


def test_cloud_connection():
    """Test cloud database connection and show basic info."""
    print("Testing cloud database connection...")
    
    try:
        debug_util = DebugUtil()
        db_manager = DatabaseManager(
            db_path=None,
            connection_type=ConnectionType.CLOUD,
            debug_util=debug_util
        )
        
        print("✅ Cloud connection successful")
        
        cursor = db_manager.connection.cursor()
        
        # Check users table
        try:
            cursor.execute('SELECT COUNT(*) FROM users')
            user_count = cursor.fetchone()[0]
            print(f"Users in database: {user_count}")
            
            if user_count > 0:
                cursor.execute('SELECT user_id, first_name, last_name FROM users LIMIT 3')
                users = cursor.fetchall()
                print("Sample users:")
                for user in users:
                    print(f"  {user[0]} - {user[1]} {user[2]}")
        except Exception as e:
            print(f"Error checking users: {e}")
        
        # Check settings table
        try:
            cursor.execute('SELECT COUNT(*) FROM settings')
            settings_count = cursor.fetchone()[0]
            print(f"Settings in database: {settings_count}")
        except Exception as e:
            print(f"Error checking settings: {e}")
        
        db_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Cloud connection failed: {e}")
        return False


if __name__ == '__main__':
    success = test_cloud_connection()
    sys.exit(0 if success else 1)
