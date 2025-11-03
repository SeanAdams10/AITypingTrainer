"""Setting Manager for CRUD operations.

Handles all DB access for settings with SCD-2 history tracking.
Follows the same pattern as SettingTypeManager and other managers in the codebase.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from db.database_manager import DatabaseManager
from helpers.debug_util import DebugUtil
from models.setting import Setting, SettingNotFound, SettingValidationError


class SettingManager:
    """Manager for CRUD operations on Setting with SCD-2 history tracking."""

    def __init__(self, *, db_manager: DatabaseManager) -> None:
        """Initialize SettingManager with a DatabaseManager instance.
        
        Args:
            db_manager: An instance of DatabaseManager.
        """
        self.db = db_manager
        self.debug_util = DebugUtil()

    def _validate_uniqueness(
        self,
        *,
        setting_type_id: str,
        related_entity_id: str,
        setting_id: Optional[str] = None
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
        if setting_id is not None:
            query = """SELECT 1 FROM settings 
                       WHERE setting_type_id = %s 
                       AND related_entity_id = %s 
                       AND setting_id != %s"""
            params = (setting_type_id, related_entity_id, setting_id)
        else:
            query = """SELECT 1 FROM settings 
                       WHERE setting_type_id = %s 
                       AND related_entity_id = %s"""
            params = (setting_type_id, related_entity_id)

        existing = self.db.fetchone(query=query, params=params)
        if existing:
            raise SettingValidationError(
                f"Setting with type '{setting_type_id}' already exists "
                f"for entity '{related_entity_id}'."
            )

    def get_setting(
        self,
        *,
        setting_type_id: str,
        related_entity_id: str,
        default_value: Optional[str] = None
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
        row = self.db.fetchone(
            query="""
            SELECT setting_id, setting_type_id, setting_value, related_entity_id,
                   row_checksum, created_dt, updated_dt, created_user_id, updated_user_id
            FROM settings
            WHERE setting_type_id = %s AND related_entity_id = %s
            """,
            params=(setting_type_id, related_entity_id),
        )

        if row:
            return Setting(
                setting_id=row["setting_id"],
                setting_type_id=row["setting_type_id"],
                setting_value=row["setting_value"],
                related_entity_id=row["related_entity_id"],
                row_checksum=(
                    bytes(row["row_checksum"])
                    if isinstance(row["row_checksum"], (bytes, memoryview))
                    else row["row_checksum"]
                ),
                created_dt=row["created_dt"],
                updated_dt=row["updated_dt"],
                created_user_id=row["created_user_id"],
                updated_user_id=row["updated_user_id"],
            )
        elif default_value is not None:
            # Create a new setting with the default value
            now = datetime.now(timezone.utc)
            default_user_id = "a287befc-0570-4eb3-a5d7-46653054cf0f"
            new_setting = Setting(
                setting_id=str(uuid4()),
                setting_type_id=setting_type_id,
                setting_value=default_value,
                related_entity_id=related_entity_id,
                row_checksum=b"",  # Will be calculated when saved
                created_dt=now.isoformat(),
                updated_dt=now.isoformat(),
                created_user_id=default_user_id,
                updated_user_id=default_user_id,
            )
            # We don't save it to the database yet - that would be handled by save_setting
            return new_setting
        else:
            raise SettingNotFound(
                f"Setting with type '{setting_type_id}' for entity "
                f"'{related_entity_id}' not found. "
                "Please ensure the setting exists or provide a default value."
            )

    def list_settings(self, *, related_entity_id: str) -> List[Setting]:
        """List all settings for a specific entity.

        Args:
            related_entity_id: The entity ID to retrieve settings for.

        Returns:
            List[Setting]: All settings for the specified entity.
        """
        rows = self.db.fetchall(
            query="""
            SELECT setting_id, setting_type_id, setting_value, related_entity_id,
                   row_checksum, created_dt, updated_dt, created_user_id, updated_user_id
            FROM settings
            WHERE related_entity_id = %s
            """,
            params=(related_entity_id,),
        )

        return [
            Setting(
                setting_id=row["setting_id"],
                setting_type_id=row["setting_type_id"],
                setting_value=row["setting_value"],
                related_entity_id=row["related_entity_id"],
                row_checksum=(
                    bytes(row["row_checksum"])
                    if isinstance(row["row_checksum"], (bytes, memoryview))
                    else row["row_checksum"]
                ),
                created_dt=row["created_dt"],
                updated_dt=row["updated_dt"],
                created_user_id=row["created_user_id"],
                updated_user_id=row["updated_user_id"],
            )
            for row in rows
        ]

    def save_setting(self, *, setting: Setting) -> bool:
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
        # Ensure the updated_dt timestamp is current
        setting.updated_dt = datetime.now(timezone.utc)

        # Check if a setting with this type and entity already exists
        existing_setting_row = self.db.fetchone(
            query="""
                SELECT setting_id FROM settings
                WHERE setting_type_id = %s AND related_entity_id = %s
            """,
            params=(setting.setting_type_id, setting.related_entity_id),
        )

        if existing_setting_row:
            # Update the existing setting's ID and update it
            setting.setting_id = existing_setting_row["setting_id"]
            return self._update_setting(setting)
        else:
            # Insert a new setting
            return self._insert_setting(setting)

    def _setting_exists(self, setting_id: str) -> bool:
        """Check if a setting exists by ID."""
        row = self.db.fetchone(
            query="SELECT 1 FROM settings WHERE setting_id = %s",
            params=(setting_id,)
        )
        return row is not None

    def _get_next_version_no(self, setting_id: str) -> int:
        """Get the next version number for a setting.
        
        Args:
            setting_id: The setting ID
            
        Returns:
            int: Next version number (1 if no history exists)
        """
        row = self.db.fetchone(
            query="""
                SELECT MAX(version_no) as max_version
                FROM settings_history
                WHERE setting_id = %s
            """,
            params=(setting_id,)
        )
        
        if row and row["max_version"] is not None:
            return row["max_version"] + 1
        return 1
    
    def _close_previous_version(self, setting_id: str, valid_to_dt: str) -> None:
        """Close the previous current version by setting is_current=false and valid_to_dt.
        
        Args:
            setting_id: The setting ID
            valid_to_dt: When the previous version stops being valid
        """
        self.db.execute(
            query="""
                UPDATE settings_history
                SET is_current = false, valid_to_dt = %s
                WHERE setting_id = %s AND is_current = true
            """,
            params=(valid_to_dt, setting_id)
        )
    
    def _add_history_entry(
        self,
        setting: Setting,
        action: str,
        version_no: int,
        valid_from_dt: str,
    ) -> None:
        """Add an entry to the settings_history table following SCD-2 pattern.

        Args:
            setting: The setting that was changed.
            action: Action type ('I' for Insert, 'U' for Update, 'D' for Delete)
            version_no: Version number for this setting (starts at 1)
            valid_from_dt: When this version becomes effective (ISO format timestamp)
        """
        # Convert row_checksum to bytes if it's a memoryview
        checksum_bytes = (
            bytes(setting.row_checksum)
            if isinstance(setting.row_checksum, memoryview)
            else setting.row_checksum
        )
        
        self.db.execute(
            query="""
            INSERT INTO settings_history
            (setting_id, setting_type_id, setting_value, related_entity_id,
             row_checksum, created_dt, updated_dt, created_user_id, updated_user_id,
             action, version_no, valid_from_dt, valid_to_dt, is_current)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            params=(
                setting.setting_id,
                setting.setting_type_id,
                setting.setting_value,
                setting.related_entity_id,
                checksum_bytes,
                setting.created_dt,
                setting.updated_dt,
                setting.created_user_id,
                setting.updated_user_id,
                action,
                version_no,
                valid_from_dt,
                "9999-12-31T23:59:59+00:00",  # valid_to_dt (default far future)
                True,  # is_current (new version is always current)
            ),
        )

    def _insert_setting(self, setting: Setting) -> bool:
        """Insert a new setting into the database."""
        self.db.execute(
            query="""
            INSERT INTO settings
            (setting_id, setting_type_id, setting_value, related_entity_id,
             row_checksum, created_dt, updated_dt, created_user_id, updated_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            params=(
                setting.setting_id,
                setting.setting_type_id,
                setting.setting_value,
                setting.related_entity_id,
                (
                    bytes(setting.row_checksum)
                    if isinstance(setting.row_checksum, (bytes, memoryview))
                    else setting.row_checksum
                ),
                setting.created_dt,
                setting.updated_dt,
                setting.created_user_id,
                setting.updated_user_id,
            ),
        )

        # Add history entry for insert
        now = datetime.now(timezone.utc).isoformat()
        version_no = 1  # First version for new setting
        self._add_history_entry(
            setting=setting,
            action="I",
            version_no=version_no,
            valid_from_dt=now
        )
        return True

    def _update_setting(self, setting: Setting) -> bool:
        """Update an existing setting in the database."""
        self.db.execute(
            query="""
            UPDATE settings
            SET setting_type_id = %s, setting_value = %s, related_entity_id = %s,
                row_checksum = %s, updated_dt = %s, updated_user_id = %s
            WHERE setting_id = %s
            """,
            params=(
                setting.setting_type_id,
                setting.setting_value,
                setting.related_entity_id,
                (
                    bytes(setting.row_checksum)
                    if isinstance(setting.row_checksum, (bytes, memoryview))
                    else setting.row_checksum
                ),
                setting.updated_dt,
                setting.updated_user_id,
                setting.setting_id,
            ),
        )

        # Close previous version and add new history entry for update
        now = datetime.now(timezone.utc).isoformat()
        self._close_previous_version(setting.setting_id, now)
        version_no = self._get_next_version_no(setting.setting_id)
        self._add_history_entry(
            setting=setting,
            action="U",
            version_no=version_no,
            valid_from_dt=now
        )
        return True

    def delete_setting(
        self,
        *,
        setting_type_id: str,
        related_entity_id: str
    ) -> bool:
        """Delete a setting by its type ID and related entity ID.

        Args:
            setting_type_id: The type ID of the setting to delete.
            related_entity_id: The related entity ID of the setting to delete.

        Returns:
            bool: True if deleted, False if not found.
        """
        # First get the setting to record in history
        try:
            setting = self.get_setting(
                setting_type_id=setting_type_id,
                related_entity_id=related_entity_id
            )

            # Update the timestamp for the history record
            now = datetime.now(timezone.utc).isoformat()
            setting.updated_dt = now

            # Close previous version and record deletion in history
            self._close_previous_version(setting.setting_id, now)
            version_no = self._get_next_version_no(setting.setting_id)
            self._add_history_entry(
                setting=setting,
                action="D",
                version_no=version_no,
                valid_from_dt=now
            )

            # Now delete the setting
            self.db.execute(
                query="DELETE FROM settings WHERE setting_type_id = %s AND related_entity_id = %s",
                params=(setting_type_id, related_entity_id),
            )
            return True
        except SettingNotFound:
            return False

    def delete_all_settings_for_entity(self, *, related_entity_id: str) -> bool:
        """Delete all settings for a specific entity.

        Args:
            related_entity_id: The entity ID to delete settings for.

        Returns:
            bool: True if any were deleted, False if none were found.
        """
        # Get all settings for this entity first
        settings = self.list_settings(related_entity_id=related_entity_id)

        if not settings:
            return False

        # Record all in history before deletion
        now = datetime.now(timezone.utc).isoformat()
        for setting in settings:
            setting.updated_dt = now
            # Close previous version and record deletion in history
            self._close_previous_version(setting.setting_id, now)
            version_no = self._get_next_version_no(setting.setting_id)
            self._add_history_entry(
                setting=setting,
                action="D",
                version_no=version_no,
                valid_from_dt=now
            )

        # Now delete all settings for this entity
        self.db.execute(
            query="DELETE FROM settings WHERE related_entity_id = %s",
            params=(related_entity_id,),
        )
        return True
