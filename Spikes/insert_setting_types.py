"""Insert all setting types from Requirements/Settings_req.md into the database.

This script:
1. Connects to the cloud database
2. Inserts all setting types defined in the requirements
3. Creates proper SCD-2 history entries for each setting type
4. Uses the system default user ID for audit fields
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

# Add project root to path before importing project modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import project modules after path setup (ruff: noqa: E402)
from db.database_manager import ConnectionType, DatabaseManager  # noqa: E402
from models.setting_type import SettingType  # noqa: E402
from models.setting_type_manager import SettingTypeManager  # noqa: E402, I001


# Setting type definitions from Requirements/Settings_req.md
SETTING_TYPES = [
    {
        "setting_type_id": "LSTKBD",
        "setting_type_name": "Last Used Keyboard",
        "description": "Last used keyboard for a user in the desktop UI",
        "related_entity_type": "user",
        "data_type": "string",
        "default_value": None,
        "validation_rules": None,
        "is_system": False,
        "is_active": True,
    },
    {
        "setting_type_id": "DRICAT",
        "setting_type_name": "Last Selected Drill Category",
        "description": "Last selected drill category",
        "related_entity_type": "keyboard",
        "data_type": "string",
        "default_value": None,
        "validation_rules": None,
        "is_system": False,
        "is_active": True,
    },
    {
        "setting_type_id": "DRISNP",
        "setting_type_name": "Last Selected Drill Snippet",
        "description": "Last selected drill snippet",
        "related_entity_type": "keyboard",
        "data_type": "string",
        "default_value": None,
        "validation_rules": None,
        "is_system": False,
        "is_active": True,
    },
    {
        "setting_type_id": "DRILEN",
        "setting_type_name": "Drill Length",
        "description": "Drill length (characters to type)",
        "related_entity_type": "keyboard",
        "data_type": "integer",
        "default_value": None,
        "validation_rules": '{"min": 1, "max": 10000}',
        "is_system": False,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRSZE",
        "setting_type_name": "N-gram Size",
        "description": "N-gram Size",
        "related_entity_type": "keyboard",
        "data_type": "integer",
        "default_value": "4",
        "validation_rules": '{"min": 2, "max": 10}',
        "is_system": False,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRCNT",
        "setting_type_name": "N-gram Count",
        "description": "N-gram Count",
        "related_entity_type": "keyboard",
        "data_type": "integer",
        "default_value": "5",
        "validation_rules": '{"min": 1, "max": 100}',
        "is_system": False,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRMOC",
        "setting_type_name": "N-gram Minimum Occurrences",
        "description": "N-gram Minimum Occurrences",
        "related_entity_type": "keyboard",
        "data_type": "integer",
        "default_value": "5",
        "validation_rules": '{"min": 1, "max": 1000}',
        "is_system": False,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRLEN",
        "setting_type_name": "N-gram Practice Length",
        "description": "N-gram Practice Length",
        "related_entity_type": "keyboard",
        "data_type": "integer",
        "default_value": "200",
        "validation_rules": '{"min": 10, "max": 10000}',
        "is_system": False,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRKEY",
        "setting_type_name": "N-gram Included Keys",
        "description": "N-gram Included Keys",
        "related_entity_type": "keyboard",
        "data_type": "string",
        "default_value": "ueocdtsn",
        "validation_rules": '{"pattern": "^[a-z]+$"}',
        "is_system": False,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRTYP",
        "setting_type_name": "N-gram Practice Type",
        "description": "N-gram Practice Type",
        "related_entity_type": "keyboard",
        "data_type": "string",
        "default_value": "pure ngram",
        "validation_rules": '{"enum": ["pure ngram", "contextual", "mixed"]}',
        "is_system": False,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRFST",
        "setting_type_name": "Focus on Speed Target",
        "description": "Focus on Speed Target (filter slower than target)",
        "related_entity_type": "keyboard",
        "data_type": "boolean",
        "default_value": "false",
        "validation_rules": None,
        "is_system": False,
        "is_active": True,
    },
]


def insert_setting_types(
    db: DatabaseManager,
    setting_type_manager: SettingTypeManager,
    user_id: UUID,
) -> None:
    """Insert all setting types into the database.
    
    Args:
        db: DatabaseManager instance
        setting_type_manager: SettingTypeManager instance
        user_id: User ID to use for created_user_id and updated_user_id
    """
    print(f"Inserting {len(SETTING_TYPES)} setting types...")
    print()
    
    inserted_count = 0
    skipped_count = 0
    
    for st_data in SETTING_TYPES:
        setting_type_id = st_data["setting_type_id"]
        
        # Check if setting type already exists
        try:
            existing = setting_type_manager.get_setting_type(
                setting_type_id=setting_type_id
            )
            if existing:
                print(f"⏭️  SKIPPED: {setting_type_id} - Already exists")
                skipped_count += 1
                continue
        except Exception:
            # Setting type doesn't exist, continue with insert
            pass
        
        # Create SettingType object
        now = datetime.now(timezone.utc)
        setting_type = SettingType(
            setting_type_id=st_data["setting_type_id"],
            setting_type_name=st_data["setting_type_name"],
            description=st_data["description"],
            related_entity_type=st_data["related_entity_type"],
            data_type=st_data["data_type"],
            default_value=st_data["default_value"],
            validation_rules=st_data["validation_rules"],
            is_system=st_data["is_system"],
            is_active=st_data["is_active"],
            created_user_id=str(user_id),
            updated_user_id=str(user_id),
            created_dt=now,
            updated_dt=now,
        )
        
        # Insert using SettingTypeManager (handles both base and history tables)
        try:
            setting_type_manager.create_setting_type(
                setting_type=setting_type,
                user_id=user_id,
            )
            print(f"✅ INSERTED: {setting_type_id} - {st_data['setting_type_name']}")
            inserted_count += 1
        except Exception as e:
            print(f"❌ ERROR: {setting_type_id} - {str(e)}")
    
    print()
    print("Summary:")
    print(f"  ✅ Inserted: {inserted_count}")
    print(f"  ⏭️  Skipped:  {skipped_count}")
    print(f"  📊 Total:    {len(SETTING_TYPES)}")


def main() -> None:
    """Main execution function."""
    print("=" * 70)
    print("Setting Types Insertion Script")
    print("=" * 70)
    print()
    
    # Connect to the database
    print("Connecting to database...")
    db = DatabaseManager(connection_type=ConnectionType.CLOUD)
    
    try:
        # Create SettingTypeManager
        setting_type_manager = SettingTypeManager(db_manager=db)
        
        # Use system default user ID
        system_user_id = UUID("a287befc-0570-4eb3-a5d7-46653054cf0f")
        print(f"Using system user ID: {system_user_id}")
        print()
        
        # Insert all setting types
        insert_setting_types(db, setting_type_manager, system_user_id)
        
        print()
        print("=" * 70)
        print("Insertion completed successfully!")
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
