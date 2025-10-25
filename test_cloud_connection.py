#!/usr/bin/env python3
"""Test script to verify cloud database connection."""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath("."))

from db.database_manager import ConnectionType, DatabaseManager
from helpers.debug_util import DebugUtil


def test_cloud_connection() -> bool:
    """Test cloud database connection and show basic info."""
    print("Testing cloud database connection...")

    try:
        debug_util = DebugUtil()
        db_manager = DatabaseManager(
            db_path=None, connection_type=ConnectionType.CLOUD, debug_util=debug_util
        )

        print("✅ Cloud connection successful")

        # Use the database manager's execute method instead of direct cursor access
        # cursor = db_manager.connection.cursor()

        # Check users table
        try:
            result = db_manager.fetchone("SELECT COUNT(*) FROM users")
            user_count = 0
            if result:
                result_dict = dict(result)
                count_val = result_dict.get("COUNT(*)", 0)
                user_count = int(str(count_val)) if count_val is not None else 0
            print(f"Users in database: {user_count}")

            if user_count > 0:
                users = db_manager.fetchall(
                    "SELECT user_id, first_name, surname FROM users LIMIT 3"
                )
                print("Sample users:")
                for user in users:
                    user_dict = dict(user)
                    uid = user_dict["user_id"]
                    fname = user_dict["first_name"]
                    surname = user_dict["surname"]
                    print(f"  {uid} - {fname} {surname}")
        except Exception as e:
            print(f"Error checking users: {e}")

        # Check settings table
        try:
            result = db_manager.fetchone("SELECT COUNT(*) FROM settings")
            settings_count = 0
            if result:
                result_dict = dict(result)
                count_val = result_dict.get("COUNT(*)", 0)
                settings_count = int(str(count_val)) if count_val is not None else 0
            print(f"Settings in database: {settings_count}")
        except Exception as e:
            print(f"Error checking settings: {e}")

        db_manager.close()
        return True

    except Exception as e:
        print(f"❌ Cloud connection failed: {e}")
        return False


if __name__ == "__main__":
    success = test_cloud_connection()
    sys.exit(0 if success else 1)
