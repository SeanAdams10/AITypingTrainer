"""Insert all setting types from Settings_req.md.

This script populates the setting_types table with all defined setting types
and creates initial history entries following the SCD-2 pattern.
"""

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database_manager import ConnectionType, DatabaseManager

# System user ID for initial data population
SYSTEM_USER_ID = "a287befc-0570-4eb3-a5d7-46653054cf0f"

# Setting type definitions from Settings_req.md
SETTING_TYPES = [
    {
        "setting_type_id": "LSTKBD",
        "setting_type_name": "Last Used Keyboard",
        "description": "Stores the last keyboard used by a specific user in the desktop UI",
        "related_entity_type": "user",
        "data_type": "string",
        "default_value": None,
        "validation_rules": None,
        "is_system": True,
        "is_active": True,
    },
    {
        "setting_type_id": "DRICAT",
        "setting_type_name": "Last Selected Drill Category",
        "description": "Stores the last used category in the drill configuration screen",
        "related_entity_type": "keyboard",
        "data_type": "string",
        "default_value": None,
        "validation_rules": None,
        "is_system": True,
        "is_active": True,
    },
    {
        "setting_type_id": "DRISNP",
        "setting_type_name": "Last Selected Drill Snippet",
        "description": "Stores the last used snippet in the drill configuration screen",
        "related_entity_type": "keyboard",
        "data_type": "string",
        "default_value": None,
        "validation_rules": None,
        "is_system": True,
        "is_active": True,
    },
    {
        "setting_type_id": "DRILEN",
        "setting_type_name": "Drill Length",
        "description": "Stores the last used drill length in the drill configuration screen",
        "related_entity_type": "keyboard",
        "data_type": "integer",
        "default_value": None,
        "validation_rules": None,
        "is_system": True,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRSZE",
        "setting_type_name": "N-gram Size",
        "description": "The size of n-grams to analyze and practice",
        "related_entity_type": "keyboard",
        "data_type": "integer",
        "default_value": "4",
        "validation_rules": '{"min": 2, "max": 8}',
        "is_system": True,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRCNT",
        "setting_type_name": "N-gram Count",
        "description": "Number of top problematic n-grams to focus on",
        "related_entity_type": "keyboard",
        "data_type": "integer",
        "default_value": "5",
        "validation_rules": '{"min": 1, "max": 20}',
        "is_system": True,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRMOC",
        "setting_type_name": "N-gram Minimum Occurrences",
        "description": "Minimum number of occurrences for n-gram analysis",
        "related_entity_type": "keyboard",
        "data_type": "integer",
        "default_value": "5",
        "validation_rules": '{"min": 1}',
        "is_system": True,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRLEN",
        "setting_type_name": "N-gram Practice Length",
        "description": "Length of generated practice content in characters",
        "related_entity_type": "keyboard",
        "data_type": "integer",
        "default_value": "200",
        "validation_rules": '{"min": 50, "max": 1000}',
        "is_system": True,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRKEY",
        "setting_type_name": "N-gram Included Keys",
        "description": "Characters to include in practice content",
        "related_entity_type": "keyboard",
        "data_type": "string",
        "default_value": "ueocdtsn",
        "validation_rules": None,
        "is_system": True,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRTYP",
        "setting_type_name": "N-gram Practice Type",
        "description": "Type of practice content generation",
        "related_entity_type": "keyboard",
        "data_type": "string",
        "default_value": "pure ngram",
        "validation_rules": '{"enum": ["pure ngram", "words", "both"]}',
        "is_system": True,
        "is_active": True,
    },
    {
        "setting_type_id": "NGRFST",
        "setting_type_name": "Focus on Speed Target",
        "description": "When enabled, practice focuses only on n-grams slower than target speed",
        "related_entity_type": "keyboard",
        "data_type": "boolean",
        "default_value": "false",
        "validation_rules": None,
        "is_system": True,
        "is_active": True,
    },
]


def calculate_checksum(setting_type: dict) -> bytes:
    """Calculate SHA-256 checksum of business columns.
    
    Business columns exclude: row_checksum, created_dt, updated_dt,
    created_user_id, updated_user_id.
    """
    business_data = "|".join([
        setting_type["setting_type_id"],
        setting_type["setting_type_name"],
        setting_type["description"],
        setting_type["related_entity_type"],
        setting_type["data_type"],
        setting_type["default_value"] or "",
        setting_type["validation_rules"] or "",
        str(setting_type["is_system"]),
        str(setting_type["is_active"]),
    ])
    return hashlib.sha256(business_data.encode("utf-8")).digest()


def insert_setting_types(db_manager: DatabaseManager) -> None:
    """Insert all setting types into setting_types and setting_types_history tables."""
    now = datetime.now(timezone.utc)
    
    print(f"Inserting {len(SETTING_TYPES)} setting types...")
    
    for setting_type in SETTING_TYPES:
        checksum = calculate_checksum(setting_type)
        
        # Check if setting type already exists
        existing = db_manager.fetchone(
            query="""
            SELECT setting_type_id FROM setting_types
            WHERE setting_type_id = %(setting_type_id)s
            """,
            params={"setting_type_id": setting_type["setting_type_id"]}
        )
        
        if existing:
            print(f"  ⏭️  {setting_type['setting_type_id']} - Already exists, skipping")
            continue
        
        # Insert into setting_types table
        db_manager.execute(
            query="""
            INSERT INTO setting_types (
                setting_type_id, setting_type_name, description,
                related_entity_type, data_type, default_value,
                validation_rules, is_system, is_active,
                row_checksum, created_dt, updated_dt,
                created_user_id, updated_user_id
            ) VALUES (
                %(setting_type_id)s, %(setting_type_name)s, %(description)s,
                %(related_entity_type)s, %(data_type)s, %(default_value)s,
                %(validation_rules)s, %(is_system)s, %(is_active)s,
                %(row_checksum)s, %(created_dt)s, %(updated_dt)s,
                %(created_user_id)s, %(updated_user_id)s
            )
            """,
            params={
                "setting_type_id": setting_type["setting_type_id"],
                "setting_type_name": setting_type["setting_type_name"],
                "description": setting_type["description"],
                "related_entity_type": setting_type["related_entity_type"],
                "data_type": setting_type["data_type"],
                "default_value": setting_type["default_value"],
                "validation_rules": setting_type["validation_rules"],
                "is_system": setting_type["is_system"],
                "is_active": setting_type["is_active"],
                "row_checksum": checksum,
                "created_dt": now,
                "updated_dt": now,
                "created_user_id": SYSTEM_USER_ID,
                "updated_user_id": SYSTEM_USER_ID,
            }
        )
        
        # Insert initial history entry (version 1, action 'I')
        db_manager.execute(
            query="""
            INSERT INTO setting_types_history (
                setting_type_id, setting_type_name, description,
                related_entity_type, data_type, default_value,
                validation_rules, is_system, is_active,
                row_checksum, created_dt, updated_dt,
                created_user_id, updated_user_id,
                action, version_no, valid_from_dt, valid_to_dt, is_current
            ) VALUES (
                %(setting_type_id)s, %(setting_type_name)s, %(description)s,
                %(related_entity_type)s, %(data_type)s, %(default_value)s,
                %(validation_rules)s, %(is_system)s, %(is_active)s,
                %(row_checksum)s, %(created_dt)s, %(updated_dt)s,
                %(created_user_id)s, %(updated_user_id)s,
                'I', 1, %(valid_from_dt)s, '9999-12-31T23:59:59Z', true
            )
            """,
            params={
                "setting_type_id": setting_type["setting_type_id"],
                "setting_type_name": setting_type["setting_type_name"],
                "description": setting_type["description"],
                "related_entity_type": setting_type["related_entity_type"],
                "data_type": setting_type["data_type"],
                "default_value": setting_type["default_value"],
                "validation_rules": setting_type["validation_rules"],
                "is_system": setting_type["is_system"],
                "is_active": setting_type["is_active"],
                "row_checksum": checksum,
                "created_dt": now,
                "updated_dt": now,
                "created_user_id": SYSTEM_USER_ID,
                "updated_user_id": SYSTEM_USER_ID,
                "valid_from_dt": now,
            }
        )
        
        print(f"  ✅ {setting_type['setting_type_id']} - {setting_type['setting_type_name']}")
    
    print(f"\n✅ Successfully inserted {len(SETTING_TYPES)} setting types!")


def main() -> None:
    """Main entry point."""
    print("=" * 80)
    print("Setting Types Insertion Script")
    print("=" * 80)
    print()
    
    # Create database manager (cloud connection)
    db_manager = DatabaseManager(connection_type=ConnectionType.CLOUD)
    
    try:
        insert_setting_types(db_manager)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db_manager.close()
    
    print("\n" + "=" * 80)
    print("Script completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
