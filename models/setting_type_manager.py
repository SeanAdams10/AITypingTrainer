"""SettingTypeManager: Class for managing setting types in the database.

Manages CRUD operations for setting types with SCD-2 history tracking.
Follows the same pattern as SnippetManager and other managers in the codebase.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from db.database_manager import DatabaseManager
from helpers.debug_util import DebugUtil
from models.setting_type import SettingType, SettingTypeNotFound, SettingTypeValidationError


class SettingTypeManager:
    """Manages setting types in the database with CRUD operations and SCD-2 history tracking."""

    def __init__(self, *, db_manager: DatabaseManager) -> None:
        """Initialize the SettingTypeManager with a database manager.

        Args:
            db_manager: An instance of DatabaseManager.
        """
        self.db = db_manager
        self.debug_util = DebugUtil()

    def create_setting_type(
        self,
        *,
        setting_type: SettingType,
        user_id: UUID,
    ) -> SettingType:
        """Create a new setting type with initial history entry.

        Args:
            setting_type: SettingType instance to create.
            user_id: UUID of user creating the setting type.

        Returns:
            Created SettingType instance.

        Raises:
            SettingTypeValidationError: If setting type already exists.
        """
        # Check if already exists
        existing = self.db.fetchone(
            query="SELECT 1 FROM setting_types WHERE setting_type_id = %s",
            params=(setting_type.setting_type_id,),
        )
        if existing:
            raise SettingTypeValidationError(
                f"Setting type '{setting_type.setting_type_id}' already exists"
            )

        # Set timestamps and user IDs
        now = datetime.now(timezone.utc)
        setting_type.created_dt = now
        setting_type.updated_dt = now
        setting_type.created_user_id = str(user_id)
        setting_type.updated_user_id = str(user_id)

        # Calculate checksum
        setting_type.row_checksum = setting_type.calculate_checksum()

        # Insert into base table
        self.db.execute(
            query="""
                INSERT INTO setting_types (
                    setting_type_id, setting_type_name, description,
                    related_entity_type, data_type, default_value,
                    validation_rules, is_system, is_active,
                    created_user_id, updated_user_id,
                    created_dt, updated_dt, row_checksum
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            params=(
                setting_type.setting_type_id,
                setting_type.setting_type_name,
                setting_type.description,
                setting_type.related_entity_type,
                setting_type.data_type,
                setting_type.default_value,
                setting_type.validation_rules,
                setting_type.is_system,
                setting_type.is_active,
                str(user_id),
                str(user_id),
                now,
                now,
                bytes.fromhex(setting_type.row_checksum),
            ),
        )

        # Create initial history entry
        self.db.execute(
            query="""
                INSERT INTO setting_types_history (
                    setting_type_id, setting_type_name, description,
                    related_entity_type, data_type, default_value,
                    validation_rules, is_system, is_active,
                    created_user_id, updated_user_id,
                    created_dt, updated_dt, row_checksum,
                    action, version_no, valid_from_dt, valid_to_dt, is_current
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            params=(
                setting_type.setting_type_id,
                setting_type.setting_type_name,
                setting_type.description,
                setting_type.related_entity_type,
                setting_type.data_type,
                setting_type.default_value,
                setting_type.validation_rules,
                setting_type.is_system,
                setting_type.is_active,
                str(user_id),
                str(user_id),
                now,
                now,
                bytes.fromhex(setting_type.row_checksum),
                "I",
                1,
                now,
                datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                True,
            ),
        )

        return setting_type

    def get_setting_type(self, *, setting_type_id: str) -> Optional[SettingType]:
        """Get a setting type by ID.

        Args:
            setting_type_id: 6-character setting type ID.

        Returns:
            SettingType instance or None if not found.
        """
        row = self.db.fetchone(
            query="""
                SELECT setting_type_id, setting_type_name, description,
                       related_entity_type, data_type, default_value,
                       validation_rules, is_system, is_active,
                       created_user_id, updated_user_id,
                       created_dt, updated_dt, row_checksum
                FROM setting_types
                WHERE setting_type_id = %s
            """,
            params=(setting_type_id,),
        )

        if not row:
            return None

        return SettingType(
            setting_type_id=row["setting_type_id"],
            setting_type_name=row["setting_type_name"],
            description=row["description"],
            related_entity_type=row["related_entity_type"],
            data_type=row["data_type"],
            default_value=row["default_value"],
            validation_rules=row["validation_rules"],
            is_system=row["is_system"],
            is_active=row["is_active"],
            created_user_id=row["created_user_id"],
            updated_user_id=row["updated_user_id"],
            created_dt=row["created_dt"],
            updated_dt=row["updated_dt"],
            row_checksum=(
                bytes(row["row_checksum"]).hex()
                if isinstance(row["row_checksum"], (bytes, memoryview))
                else row["row_checksum"]
            ),
        )

    def list_setting_types(
        self,
        *,
        entity_type: Optional[str] = None,
        active_only: bool = True,
    ) -> List[SettingType]:
        """List all setting types, optionally filtered.

        Args:
            entity_type: Filter by related_entity_type ('user', 'keyboard', 'global').
            active_only: If True, only return active setting types.

        Returns:
            List of SettingType instances.
        """
        query = """
            SELECT setting_type_id, setting_type_name, description,
                   related_entity_type, data_type, default_value,
                   validation_rules, is_system, is_active,
                   created_user_id, updated_user_id,
                   created_dt, updated_dt, row_checksum
            FROM setting_types
            WHERE 1=1
        """
        params = []

        if entity_type:
            query += " AND related_entity_type = %s"
            params.append(entity_type)

        if active_only:
            query += " AND is_active = TRUE"

        query += " ORDER BY setting_type_id"

        rows = self.db.fetchall(query=query, params=tuple(params) if params else None)

        return [
            SettingType(
                setting_type_id=row["setting_type_id"],
                setting_type_name=row["setting_type_name"],
                description=row["description"],
                related_entity_type=row["related_entity_type"],
                data_type=row["data_type"],
                default_value=row["default_value"],
                validation_rules=row["validation_rules"],
                is_system=row["is_system"],
                is_active=row["is_active"],
                created_user_id=row["created_user_id"],
                updated_user_id=row["updated_user_id"],
                created_dt=row["created_dt"],
                updated_dt=row["updated_dt"],
                row_checksum=(
                    bytes(row["row_checksum"]).hex()
                    if isinstance(row["row_checksum"], (bytes, memoryview))
                    else row["row_checksum"]
                ),
            )
            for row in rows
        ]

    def update_setting_type(
        self,
        *,
        setting_type: SettingType,
        user_id: UUID,
    ) -> SettingType:
        """Update an existing setting type with history tracking.

        Args:
            setting_type: SettingType instance with updated values.
            user_id: UUID of user making the update.

        Returns:
            Updated SettingType instance.

        Raises:
            SettingTypeNotFound: If setting type doesn't exist.
            SettingTypeValidationError: If trying to update system setting type.
        """
        # Get existing setting type
        existing = self.get_setting_type(setting_type_id=setting_type.setting_type_id)
        if not existing:
            raise SettingTypeNotFound(
                f"Setting type '{setting_type.setting_type_id}' not found"
            )

        if existing.is_system:
            raise SettingTypeValidationError(
                f"Cannot modify system setting type '{setting_type.setting_type_id}'"
            )

        # Calculate new checksum
        new_checksum = setting_type.calculate_checksum()

        # Check for no-op update
        if new_checksum == existing.row_checksum:
            return existing

        # Update timestamps
        now = datetime.now(timezone.utc)
        setting_type.updated_dt = now
        setting_type.updated_user_id = str(user_id)
        setting_type.row_checksum = new_checksum

        # Get current version number
        version_row = self.db.fetchone(
            query="""
                SELECT MAX(version_no) as max_version
                FROM setting_types_history
                WHERE setting_type_id = %s
            """,
            params=(setting_type.setting_type_id,),
        )
        next_version = (version_row["max_version"] + 1) if version_row and version_row["max_version"] else 1

        # Close current history entry
        self.db.execute(
            query="""
                UPDATE setting_types_history
                SET valid_to_dt = %s, is_current = FALSE
                WHERE setting_type_id = %s AND is_current = TRUE
            """,
            params=(now, setting_type.setting_type_id),
        )

        # Update base table
        self.db.execute(
            query="""
                UPDATE setting_types
                SET setting_type_name = %s,
                    description = %s,
                    related_entity_type = %s,
                    data_type = %s,
                    default_value = %s,
                    validation_rules = %s,
                    is_active = %s,
                    updated_user_id = %s,
                    updated_dt = %s,
                    row_checksum = %s
                WHERE setting_type_id = %s
            """,
            params=(
                setting_type.setting_type_name,
                setting_type.description,
                setting_type.related_entity_type,
                setting_type.data_type,
                setting_type.default_value,
                setting_type.validation_rules,
                setting_type.is_active,
                str(user_id),
                now,
                bytes.fromhex(new_checksum),
                setting_type.setting_type_id,
            ),
        )

        # Create new history entry
        self.db.execute(
            query="""
                INSERT INTO setting_types_history (
                    setting_type_id, setting_type_name, description,
                    related_entity_type, data_type, default_value,
                    validation_rules, is_system, is_active,
                    created_user_id, updated_user_id,
                    created_dt, updated_dt, row_checksum,
                    action, version_no, valid_from_dt, valid_to_dt, is_current
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            params=(
                setting_type.setting_type_id,
                setting_type.setting_type_name,
                setting_type.description,
                setting_type.related_entity_type,
                setting_type.data_type,
                setting_type.default_value,
                setting_type.validation_rules,
                setting_type.is_system,
                setting_type.is_active,
                existing.created_user_id,
                str(user_id),
                existing.created_dt,
                now,
                bytes.fromhex(new_checksum),
                "U",
                next_version,
                now,
                datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                True,
            ),
        )

        return setting_type

    def delete_setting_type(
        self,
        *,
        setting_type_id: str,
        user_id: UUID,
    ) -> bool:
        """Delete (soft delete) a setting type.

        Args:
            setting_type_id: 6-character setting type ID.
            user_id: UUID of user performing the deletion.

        Returns:
            True if deleted successfully.

        Raises:
            SettingTypeNotFound: If setting type doesn't exist.
            SettingTypeValidationError: If trying to delete system setting type.
        """
        # Get existing setting type
        existing = self.get_setting_type(setting_type_id=setting_type_id)
        if not existing:
            raise SettingTypeNotFound(f"Setting type '{setting_type_id}' not found")

        if existing.is_system:
            raise SettingTypeValidationError(
                f"Cannot delete system setting type '{setting_type_id}'"
            )

        now = datetime.now(timezone.utc)

        # Get current version number
        version_row = self.db.fetchone(
            query="""
                SELECT MAX(version_no) as max_version
                FROM setting_types_history
                WHERE setting_type_id = %s
            """,
            params=(setting_type_id,),
        )
        next_version = (version_row["max_version"] + 1) if version_row and version_row["max_version"] else 1

        # Close current history entry
        self.db.execute(
            query="""
                UPDATE setting_types_history
                SET valid_to_dt = %s, is_current = FALSE
                WHERE setting_type_id = %s AND is_current = TRUE
            """,
            params=(now, setting_type_id),
        )

        # Soft delete - mark as inactive
        existing.is_active = False
        new_checksum = existing.calculate_checksum()

        self.db.execute(
            query="""
                UPDATE setting_types
                SET is_active = FALSE,
                    updated_user_id = %s,
                    updated_dt = %s,
                    row_checksum = %s
                WHERE setting_type_id = %s
            """,
            params=(
                str(user_id),
                now,
                bytes.fromhex(new_checksum),
                setting_type_id,
            ),
        )

        # Create delete history entry
        self.db.execute(
            query="""
                INSERT INTO setting_types_history (
                    setting_type_id, setting_type_name, description,
                    related_entity_type, data_type, default_value,
                    validation_rules, is_system, is_active,
                    created_user_id, updated_user_id,
                    created_dt, updated_dt, row_checksum,
                    action, version_no, valid_from_dt, valid_to_dt, is_current
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            params=(
                setting_type_id,
                existing.setting_type_name,
                existing.description,
                existing.related_entity_type,
                existing.data_type,
                existing.default_value,
                existing.validation_rules,
                existing.is_system,
                False,  # is_active
                existing.created_user_id,
                str(user_id),
                existing.created_dt,
                now,
                bytes.fromhex(new_checksum),
                "D",
                next_version,
                now,
                datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                True,
            ),
        )

        return True

    def get_setting_type_history(
        self,
        *,
        setting_type_id: str,
    ) -> List[dict[str, any]]:
        """Get complete history for a setting type.

        Args:
            setting_type_id: 6-character setting type ID.

        Returns:
            List of history entries as dictionaries, ordered by version.
        """
        rows = self.db.fetchall(
            query="""
                SELECT audit_id, setting_type_id, setting_type_name, description,
                       action, version_no, valid_from_dt, valid_to_dt,
                       is_current, updated_user_id
                FROM setting_types_history
                WHERE setting_type_id = %s
                ORDER BY version_no
            """,
            params=(setting_type_id,),
        )

        return [
            {
                "audit_id": row["audit_id"],
                "setting_type_id": row["setting_type_id"],
                "setting_type_name": row["setting_type_name"],
                "description": row["description"],
                "action": row["action"],
                "version_no": row["version_no"],
                "valid_from_dt": row["valid_from_dt"].isoformat() if hasattr(row["valid_from_dt"], 'isoformat') else str(row["valid_from_dt"]),
                "valid_to_dt": row["valid_to_dt"].isoformat() if hasattr(row["valid_to_dt"], 'isoformat') else str(row["valid_to_dt"]),
                "is_current": row["is_current"],
                "updated_user_id": str(row["updated_user_id"]),
            }
            for row in rows
        ]
