"""Check settings tables schema against Settings_req.md definitions.

This script compares the actual database schema for settings tables
with the expected schema defined in Settings_req.md and reports differences.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database_manager import ConnectionType, DatabaseManager


# Expected schema definitions from Settings_req.md
EXPECTED_SCHEMAS = {
    "setting_types": {
        "columns": {
            "setting_type_id": {"type": "text", "nullable": False, "primary_key": True},
            "setting_type_name": {"type": "text", "nullable": False},
            "description": {"type": "text", "nullable": False},
            "related_entity_type": {"type": "text", "nullable": False},
            "data_type": {"type": "text", "nullable": False},
            "default_value": {"type": "text", "nullable": True},
            "validation_rules": {"type": "text", "nullable": True},
            "is_system": {"type": "boolean", "nullable": False},
            "is_active": {"type": "boolean", "nullable": False},
            "row_checksum": {"type": "bytea", "nullable": False},
            "created_dt": {"type": "timestamp with time zone", "nullable": False},
            "updated_dt": {"type": "timestamp with time zone", "nullable": False},
            "created_user_id": {"type": "uuid", "nullable": False},
            "updated_user_id": {"type": "uuid", "nullable": False},
        },
        "constraints": [
            "PRIMARY KEY (setting_type_id)",
            "CHECK (related_entity_type IN ('user', 'keyboard', 'global'))",
            "CHECK (data_type IN ('string', 'integer', 'boolean', 'decimal'))",
        ],
    },
    "setting_types_history": {
        "columns": {
            "audit_id": {"type": "bigint", "nullable": False, "primary_key": True},
            "setting_type_id": {"type": "text", "nullable": False},
            "setting_type_name": {"type": "text", "nullable": False},
            "description": {"type": "text", "nullable": False},
            "related_entity_type": {"type": "text", "nullable": False},
            "data_type": {"type": "text", "nullable": False},
            "default_value": {"type": "text", "nullable": True},
            "validation_rules": {"type": "text", "nullable": True},
            "is_system": {"type": "boolean", "nullable": False},
            "is_active": {"type": "boolean", "nullable": False},
            "row_checksum": {"type": "bytea", "nullable": False},
            "created_dt": {"type": "timestamp with time zone", "nullable": False},
            "updated_dt": {"type": "timestamp with time zone", "nullable": False},
            "created_user_id": {"type": "uuid", "nullable": False},
            "updated_user_id": {"type": "uuid", "nullable": False},
            "action": {"type": "text", "nullable": False},
            "version_no": {"type": "integer", "nullable": False},
            "valid_from_dt": {"type": "timestamp with time zone", "nullable": False},
            "valid_to_dt": {"type": "timestamp with time zone", "nullable": False},
            "is_current": {"type": "boolean", "nullable": False},
        },
        "constraints": [
            "PRIMARY KEY (audit_id)",
            "CHECK (action IN ('I', 'U', 'D'))",
            "UNIQUE (setting_type_id, version_no)",
        ],
    },
    "settings": {
        "columns": {
            "setting_id": {"type": "uuid", "nullable": False, "primary_key": True},
            "setting_type_id": {"type": "text", "nullable": False},
            "setting_value": {"type": "text", "nullable": False},
            "related_entity_id": {"type": "uuid", "nullable": False},
            "row_checksum": {"type": "bytea", "nullable": False},
            "created_dt": {"type": "timestamp with time zone", "nullable": False},
            "updated_dt": {"type": "timestamp with time zone", "nullable": False},
            "created_user_id": {"type": "uuid", "nullable": False},
            "updated_user_id": {"type": "uuid", "nullable": False},
        },
        "constraints": [
            "PRIMARY KEY (setting_id)",
            "UNIQUE (setting_type_id, related_entity_id)",
            "FOREIGN KEY (setting_type_id) REFERENCES setting_types(setting_type_id)",
        ],
    },
    "settings_history": {
        "columns": {
            "audit_id": {"type": "bigint", "nullable": False, "primary_key": True},
            "setting_id": {"type": "uuid", "nullable": False},
            "setting_type_id": {"type": "text", "nullable": False},
            "setting_value": {"type": "text", "nullable": False},
            "related_entity_id": {"type": "uuid", "nullable": False},
            "row_checksum": {"type": "bytea", "nullable": False},
            "created_dt": {"type": "timestamp with time zone", "nullable": False},
            "updated_dt": {"type": "timestamp with time zone", "nullable": False},
            "created_user_id": {"type": "uuid", "nullable": False},
            "updated_user_id": {"type": "uuid", "nullable": False},
            "action": {"type": "text", "nullable": False},
            "version_no": {"type": "integer", "nullable": False},
            "valid_from_dt": {"type": "timestamp with time zone", "nullable": False},
            "valid_to_dt": {"type": "timestamp with time zone", "nullable": False},
            "is_current": {"type": "boolean", "nullable": False},
        },
        "constraints": [
            "PRIMARY KEY (audit_id)",
            "CHECK (action IN ('I', 'U', 'D'))",
            "UNIQUE (setting_id, version_no)",
        ],
    },
}


def get_table_schema(db_manager: DatabaseManager, table_name: str) -> Optional[Dict[str, Any]]:
    """Get the actual schema for a table from the database."""
    # Check if table exists
    table_check = db_manager.fetchone(
        query="""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'typing'
            AND table_name = %(table_name)s
        )
        """,
        params={"table_name": table_name},
    )

    if not table_check or not table_check.get("exists"):
        return None

    # Get column information
    columns_query = """
    SELECT
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = 'typing'
    AND table_name = %(table_name)s
    ORDER BY ordinal_position
    """

    columns = db_manager.fetchall(query=columns_query, params={"table_name": table_name})

    # Get constraint information
    constraints_query = """
    SELECT
        tc.constraint_name,
        tc.constraint_type,
        kcu.column_name,
        cc.check_clause
    FROM information_schema.table_constraints tc
    LEFT JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    LEFT JOIN information_schema.check_constraints cc
        ON tc.constraint_name = cc.constraint_name
        AND tc.table_schema = cc.constraint_schema
    WHERE tc.table_schema = 'typing'
    AND tc.table_name = %(table_name)s
    """

    constraints = db_manager.fetchall(query=constraints_query, params={"table_name": table_name})

    return {"columns": columns, "constraints": constraints}


def normalize_type(pg_type: str) -> str:
    """Normalize PostgreSQL type names for comparison."""
    type_map = {
        "character varying": "text",
        "timestamp without time zone": "timestamp",
        "timestamp with time zone": "timestamp with time zone",
        "bigserial": "bigint",
    }
    return type_map.get(pg_type.lower(), pg_type.lower())


def compare_schemas(
    table_name: str, expected: Dict[str, Any], actual: Optional[Dict[str, Any]]
) -> List[str]:
    """Compare expected and actual schemas and return list of differences."""
    differences = []

    if actual is None:
        differences.append(f"❌ Table '{table_name}' does not exist in database")
        return differences

    # Build actual columns dict
    actual_columns = {}
    for col in actual["columns"]:
        actual_columns[col["column_name"]] = {
            "type": normalize_type(col["data_type"]),
            "nullable": col["is_nullable"] == "YES",
            "default": col["column_default"],
        }

    # Check for missing columns
    for col_name, col_def in expected["columns"].items():
        if col_name not in actual_columns:
            differences.append(
                f"  ❌ Column '{col_name}' is missing from table '{table_name}'"
            )
        else:
            actual_col = actual_columns[col_name]
            expected_type = col_def["type"].lower()
            actual_type = actual_col["type"]

            # Compare type
            if expected_type != actual_type:
                differences.append(
                    f"  ⚠️  Column '{col_name}' type mismatch: "
                    f"expected '{expected_type}', got '{actual_type}'"
                )

            # Compare nullable
            if col_def["nullable"] != actual_col["nullable"]:
                expected_null = "NULL" if col_def["nullable"] else "NOT NULL"
                actual_null = "NULL" if actual_col["nullable"] else "NOT NULL"
                differences.append(
                    f"  ⚠️  Column '{col_name}' nullable mismatch: "
                    f"expected '{expected_null}', got '{actual_null}'"
                )

    # Check for extra columns
    for col_name in actual_columns:
        if col_name not in expected["columns"]:
            differences.append(
                f"  ℹ️  Column '{col_name}' exists in database but not in expected schema"
            )

    return differences


def main() -> None:
    """Main entry point."""
    print("=" * 80)
    print("Settings Tables Schema Comparison")
    print("=" * 80)
    print()

    # Create database manager (cloud connection)
    db_manager = DatabaseManager(connection_type=ConnectionType.CLOUD)

    try:
        all_differences = []

        for table_name, expected_schema in EXPECTED_SCHEMAS.items():
            print(f"Checking table: {table_name}")
            print("-" * 80)

            actual_schema = get_table_schema(db_manager, table_name)
            differences = compare_schemas(table_name, expected_schema, actual_schema)

            if differences:
                all_differences.extend(differences)
                for diff in differences:
                    print(diff)
            else:
                print(f"  ✅ Table '{table_name}' schema matches expected definition")

            print()

        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)

        if all_differences:
            print(f"\n❌ Found {len(all_differences)} schema differences:\n")
            print("\n📋 TO-DO LIST:\n")

            for i, diff in enumerate(all_differences, 1):
                print(f"{i}. {diff}")

            print("\n⚠️  RECOMMENDATION:")
            print("   Review the differences above before making any changes.")
            print("   Consider creating a migration script to update the schema.")
            print("   Test changes in a development environment first.")
        else:
            print("\n✅ All tables match the expected schema definitions!")
            print("   No action required.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db_manager.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
