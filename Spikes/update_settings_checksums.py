"""Update all settings with calculated row checksums and proper user IDs.

This script:
1. Finds Sean's user_id from the users table
2. Reads all settings from the settings table
3. Calculates the row_checksum for each setting
4. Updates each setting with the checksum and user IDs
"""

import sys
from pathlib import Path

# Add project root to path before importing project modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import project modules after path setup (ruff: noqa: E402)
from db.database_manager import ConnectionType, DatabaseManager  # noqa: E402
from models.setting import Setting  # noqa: E402


def get_sean_user_id(db: DatabaseManager) -> str:
    """Get Sean's user_id from the users table.
    
    Args:
        db: DatabaseManager instance
        
    Returns:
        str: Sean's user_id as a string
        
    Raises:
        ValueError: If Sean's user not found
    """
    row = db.fetchone(
        query="""
            SELECT user_id FROM users
            WHERE first_name = %s
        """,
        params=("Sean",)
    )
    
    if not row:
        raise ValueError("User 'Sean' not found in users table")
    
    return str(row["user_id"])


def update_settings_checksums(db: DatabaseManager, user_id: str) -> None:
    """Update all settings with calculated checksums and user IDs.
    
    Args:
        db: DatabaseManager instance
        user_id: User ID to use for created_user_id and updated_user_id
    """
    # Get all settings
    rows = db.fetchall(
        query="""
            SELECT setting_id, setting_type_id, setting_value, related_entity_id,
                   row_checksum, created_dt, updated_dt, created_user_id, updated_user_id
            FROM settings
        """
    )
    
    if not rows:
        print("No settings found in the database.")
        return
    
    print(f"Found {len(rows)} settings to update.")
    updated_count = 0
    
    for row in rows:
        # Create Setting object to calculate checksum
        setting = Setting(
            setting_id=str(row["setting_id"]),
            setting_type_id=str(row["setting_type_id"]),
            setting_value=str(row["setting_value"]),
            related_entity_id=str(row["related_entity_id"]),
            row_checksum=bytes(row["row_checksum"]) if row["row_checksum"] else b"",
            created_dt=str(row["created_dt"]),
            updated_dt=str(row["updated_dt"]),
            created_user_id=str(row["created_user_id"]) if row["created_user_id"] else user_id,
            updated_user_id=str(row["updated_user_id"]) if row["updated_user_id"] else user_id,
        )
        
        # Calculate the correct checksum
        new_checksum = setting.calculate_checksum()
        
        # Update the setting in the database
        db.execute(
            query="""
                UPDATE settings
                SET row_checksum = %s,
                    created_user_id = %s,
                    updated_user_id = %s
                WHERE setting_id = %s
            """,
            params=(
                new_checksum,
                user_id,
                user_id,
                setting.setting_id,
            )
        )
        
        updated_count += 1
        print(f"Updated setting {setting.setting_id} ({setting.setting_type_id})")
    
    print(f"\nSuccessfully updated {updated_count} settings with checksums and user IDs.")


def main() -> None:
    """Main execution function."""
    print("=" * 70)
    print("Settings Checksum Update Script")
    print("=" * 70)
    print()
    
    # Connect to the database
    print("Connecting to database...")
    db = DatabaseManager(connection_type=ConnectionType.CLOUD)
    
    try:
        # Get Sean's user_id
        print("Finding Sean's user_id...")
        sean_user_id = get_sean_user_id(db)
        print(f"Found Sean's user_id: {sean_user_id}")
        print()
        
        # Update all settings
        print("Updating settings with checksums...")
        update_settings_checksums(db, sean_user_id)
        
        print()
        print("=" * 70)
        print("Update completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
