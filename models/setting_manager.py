"""Setting Manager for CRUD operations.

Handles all DB access for settings.
"""

from typing import List, Optional
from uuid import uuid4

from db.database_manager import DatabaseManager
from models.setting import Setting, SettingNotFound, SettingValidationError


class SettingManager:
    """Manager for CRUD operations on Setting, using DatabaseManager for DB access."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize SettingManager with a DatabaseManager instance."""
        self.db_manager: DatabaseManager = db_manager

    def _validate_uniqueness(
        self,
        setting_type_id: str,
        related_entity_id: str,
        setting_id: Optional[str] = None,
    ) -> None:
        """Validate setting for database uniqueness.

        This ensures there is only one setting per entity per type.

        Args:
            setting_type_id: The setting type ID to validate.
            related_entity_id: The entity ID to validate.
            setting_id: The ID of the setting being updated, if any.

        Raises:
            SettingValidationError: If the combination is not unique.
        """
        query = (
            "SELECT 1 FROM settings WHERE setting_type_id = ? AND related_entity_id = ?"
        )
        params = [setting_type_id, related_entity_id]
        if setting_id is not None:
            query += " AND setting_id != ?"
            params.append(setting_id)

        if self.db_manager.execute(query, tuple(params)).fetchone():
            raise SettingValidationError(
                f"Setting with type '{setting_type_id}' already exists "
                f"for entity '{related_entity_id}'."
            )

    def get_setting(
        self,
        setting_type_id: str,
        related_entity_id: str,
        default_value: Optional[str] = None,
    ) -> Setting:
        """Retrieve a single setting by type ID and related entity ID.

        If the setting doesn't exist and a default value is provided,
        returns a new setting with the default.

        Args:
            setting_type_id: The type ID of the setting to retrieve.
            related_entity_id: The related entity ID of the setting to retrieve.
            default_value: Default value to use if the setting doesn't exist.

        Returns:
            Setting: The retrieved or newly created setting.

        Raises:
            SettingNotFound: If no setting exists with the specified IDs and no default is provided.
        """
        row = self.db_manager.execute(
            """
            SELECT setting_id, setting_type_id, setting_value, related_entity_id, updated_at,
                   created_user_id, updated_user_id, created_at, row_checksum
            FROM settings
            WHERE setting_type_id = ? AND related_entity_id = ?
            """,
            (setting_type_id, related_entity_id),
        ).fetchone()

        if row:
            return Setting(
                setting_id=str(row[0]) if row[0] is not None else None,
                setting_type_id=str(row[1]),
                setting_value=str(row[2]),
                related_entity_id=str(row[3]),
                updated_at=row[4],
                created_user_id=str(row[5]) if row[5] is not None else "system",
                updated_user_id=str(row[6]) if row[6] is not None else "system",
                created_at=row[7],
                row_checksum=str(row[8]) if row[8] is not None else None,
            )
        elif default_value is not None:
            # Create a new setting with the default value
            new_setting = Setting(
                setting_id=str(uuid4()),
                setting_type_id=setting_type_id,
                setting_value=default_value,
                related_entity_id=related_entity_id,
                created_user_id="system",
                updated_user_id="system",
            )
            # We don't save it to the database yet - that would be handled by save_setting
            return new_setting
        else:
            raise SettingNotFound(
                f"Setting with type '{setting_type_id}' for entity '{related_entity_id}' "
                "not found. Please ensure the setting exists or provide a default value."
            )

    def list_settings(self, related_entity_id: str) -> List[Setting]:
        """List all settings for a specific entity.

        Args:
            related_entity_id: The entity ID to retrieve settings for.

        Returns:
            List[Setting]: All settings for the specified entity.
        """
        rows = self.db_manager.execute(
            """
            SELECT setting_id, setting_type_id, setting_value, related_entity_id, updated_at,
                   created_user_id, updated_user_id, created_at, row_checksum
            FROM settings
            WHERE related_entity_id = ?
            """,
            (related_entity_id,),
        ).fetchall()

        return [
            Setting(
                setting_id=str(row[0]) if row[0] is not None else None,
                setting_type_id=str(row[1]),
                setting_value=str(row[2]),
                related_entity_id=str(row[3]),
                updated_at=row[4],
                created_user_id=str(row[5]) if row[5] is not None else "system",
                updated_user_id=str(row[6]) if row[6] is not None else "system",
                created_at=row[7],
                row_checksum=str(row[8]) if row[8] is not None else None,
            )
            for row in rows
        ]

    def save_setting(self, setting: Setting) -> bool:
        """Insert or update a setting in the DB. Returns True if successful.

        Also creates an entry in the settings_history table.

        Args:
            setting: The Setting object to save.

        Returns:
            True if the setting was inserted or updated successfully.

        Raises:
            SettingValidationError: If the setting is not unique.
            ValueError: If validation fails (e.g., invalid data).
        """
        # Ensure the updated_at timestamp is current
        from datetime import datetime, timezone
        setting.updated_at = datetime.now(timezone.utc)

        # Check if a setting with this type and entity already exists
        existing_setting_row = self.db_manager.execute(
            (
                "SELECT setting_id FROM settings "
                "WHERE setting_type_id = ? AND related_entity_id = ?"
            ),
            (setting.setting_type_id, setting.related_entity_id),
        ).fetchone()

        if existing_setting_row:
            # Update the existing setting's ID and update it
            existing_setting_id = (
                str(existing_setting_row[0])
                if isinstance(existing_setting_row, tuple)
                else str(existing_setting_row["setting_id"])
            )
            setting.setting_id = existing_setting_id
            return self._update_setting(setting)
        else:
            # Insert a new setting
            return self._insert_setting(setting)

    def _setting_exists(self, setting_id: str) -> bool:
        """Check if a setting exists by ID.
        
        Args:
            setting_id: The ID of the setting to check.
            
        Returns:
            bool: True if the setting exists, False otherwise.
        """
        row = self.db_manager.execute(
            "SELECT 1 FROM settings WHERE setting_id = ?", (setting_id,)
        ).fetchone()
        return row is not None

    def _add_history_entry(self, setting: Setting) -> None:
        """Add an entry to the settings_history table.

        Args:
            setting: The setting that was changed.
        """
        history_id = str(uuid4())
        self.db_manager.execute(
            """
            INSERT INTO settings_history
            (history_id, setting_id, setting_type_id, setting_value, related_entity_id, updated_at,
             created_user_id, updated_user_id, created_at, row_checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                history_id,
                setting.setting_id,
                setting.setting_type_id,
                setting.setting_value,
                setting.related_entity_id,
                setting.updated_at,
                setting.created_user_id,
                setting.updated_user_id,
                setting.created_at,
                setting.row_checksum,
            ),
        )

    def _insert_setting(self, setting: Setting) -> bool:
        """Insert a new setting into the database."""
        self.db_manager.execute(
            """
            INSERT INTO settings
            (setting_id, setting_type_id, setting_value, related_entity_id, updated_at,
             created_user_id, updated_user_id, created_at, row_checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                setting.setting_id,
                setting.setting_type_id,
                setting.setting_value,
                setting.related_entity_id,
                setting.updated_at,
                setting.created_user_id,
                setting.updated_user_id,
                setting.created_at,
                setting.row_checksum,
            ),
        )

        # Add history entry
        self._add_history_entry(setting)
        return True

    def _update_setting(self, setting: Setting) -> bool:
        """Update an existing setting in the database."""
        self.db_manager.execute(
            """
            UPDATE settings
            SET setting_type_id = ?, setting_value = ?, related_entity_id = ?, updated_at = ?,
                created_user_id = ?, updated_user_id = ?, created_at = ?, row_checksum = ?
            WHERE setting_id = ?
            """,
            (
                setting.setting_type_id,
                setting.setting_value,
                setting.related_entity_id,
                setting.updated_at,
                setting.created_user_id,
                setting.updated_user_id,
                setting.created_at,
                setting.row_checksum,
                setting.setting_id,
            ),
        )

        # Add history entry
        self._add_history_entry(setting)
        return True

    def delete_setting(self, setting_type_id: str, related_entity_id: str) -> bool:
        """Delete a setting by its type ID and related entity ID.

        Args:
            setting_type_id: The type ID of the setting to delete.
            related_entity_id: The related entity ID of the setting to delete.

        Returns:
            bool: True if deleted, False if not found.
        """
        # First get the setting to record in history
        try:
            setting = self.get_setting(setting_type_id, related_entity_id)

            # Update the timestamp for the history record
            from datetime import datetime, timezone
            setting.updated_at = datetime.now(timezone.utc)

            # Record in history before deletion
            self._add_history_entry(setting)

            # Now delete the setting
            self.db_manager.execute(
                (
                    "DELETE FROM settings "
                    "WHERE setting_type_id = ? AND related_entity_id = ?"
                ),
                (setting_type_id, related_entity_id),
            )
            return True
        except SettingNotFound:
            return False

    def delete_all_settings(self, related_entity_id: str) -> bool:
        """Delete all settings for a specific entity.

        Args:
            related_entity_id: The entity ID to delete settings for.

        Returns:
            bool: True if any were deleted, False if none were found.
        """
        # Get all settings for this entity first
        settings = self.list_settings(related_entity_id)

        if not settings:
            return False

        # Record all in history before deletion
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        for setting in settings:
            setting.updated_at = now
            self._add_history_entry(setting)

        # Now delete all settings for this entity
        self.db_manager.execute(
            "DELETE FROM settings WHERE related_entity_id = ?",
            (related_entity_id,),
        )
        return True
