"""Validate that all setting types were inserted correctly.

This script:
1. Connects to the cloud database
2. Counts rows in setting_types table
3. Counts rows in setting_types_history table
4. Lists all setting type IDs
5. Validates expected setting types are present
"""

import sys
from pathlib import Path

# Add project root to path before importing project modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import project modules after path setup (ruff: noqa: E402)
from db.database_manager import ConnectionType, DatabaseManager  # noqa: E402, I001


EXPECTED_SETTING_TYPES = [
    "LSTKBD", "DRICAT", "DRISNP", "DRILEN", "NGRSZE", 
    "NGRCNT", "NGRMOC", "NGRLEN", "NGRKEY", "NGRTYP", "NGRFST"
]


def validate_setting_types(db: DatabaseManager) -> None:
    """Validate setting types in the database.
    
    Args:
        db: DatabaseManager instance
    """
    print("Validating setting_types table...")
    print()
    
    # Count rows in setting_types
    count_row = db.fetchone(
        query="SELECT COUNT(*) as count FROM setting_types"
    )
    base_count = count_row["count"] if count_row else 0
    print(f"📊 setting_types table: {base_count} rows")
    
    # Count rows in setting_types_history
    history_count_row = db.fetchone(
        query="SELECT COUNT(*) as count FROM setting_types_history"
    )
    history_count = history_count_row["count"] if history_count_row else 0
    print(f"📊 setting_types_history table: {history_count} rows")
    print()
    
    # Get all setting type IDs
    rows = db.fetchall(
        query="""
            SELECT setting_type_id, setting_type_name, related_entity_type, 
                   data_type, default_value, is_active
            FROM setting_types
            ORDER BY setting_type_id
        """
    )
    
    print(f"Setting Types in Database ({len(rows)}):")
    print("-" * 80)
    for row in rows:
        active_mark = "✅" if row["is_active"] else "❌"
        default = row["default_value"] or "None"
        print(f"{active_mark} {row['setting_type_id']} - {row['setting_type_name']}")
        print(f"   Entity: {row['related_entity_type']}, Type: {row['data_type']}, Default: {default}")
    print()
    
    # Validate expected setting types
    found_ids = {row["setting_type_id"] for row in rows}
    missing = set(EXPECTED_SETTING_TYPES) - found_ids
    extra = found_ids - set(EXPECTED_SETTING_TYPES)
    
    print("Validation Results:")
    print("-" * 80)
    print(f"Expected: {len(EXPECTED_SETTING_TYPES)} setting types")
    print(f"Found:    {len(found_ids)} setting types")
    print()
    
    if missing:
        print(f"❌ Missing setting types: {', '.join(sorted(missing))}")
    else:
        print("✅ All expected setting types are present")
    
    if extra:
        print(f"ℹ️  Extra setting types: {', '.join(sorted(extra))}")
    
    print()
    
    # Validate history entries
    print("History Validation:")
    print("-" * 80)
    for setting_type_id in EXPECTED_SETTING_TYPES:
        history_rows = db.fetchall(
            query="""
                SELECT version_no, action, is_current
                FROM setting_types_history
                WHERE setting_type_id = %s
                ORDER BY version_no
            """,
            params=(setting_type_id,)
        )
        
        if not history_rows:
            print(f"❌ {setting_type_id}: No history entries found")
        else:
            current_count = sum(1 for r in history_rows if r["is_current"])
            if current_count == 1 and history_rows[0]["action"] == "I" and history_rows[0]["version_no"] == 1:
                print(f"✅ {setting_type_id}: {len(history_rows)} version(s), current={current_count}")
            else:
                print(f"⚠️  {setting_type_id}: {len(history_rows)} version(s), current={current_count}")


def main() -> None:
    """Main execution function."""
    print("=" * 80)
    print("Setting Types Validation Script")
    print("=" * 80)
    print()
    
    # Connect to the database
    print("Connecting to database...")
    db = DatabaseManager(connection_type=ConnectionType.CLOUD)
    
    try:
        validate_setting_types(db)
        
        print()
        print("=" * 80)
        print("Validation completed!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
