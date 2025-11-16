"""Singleton Settings Manager with caching and bulk persistence.

Provides globally accessible settings management with efficient caching.
"""

import threading
from datetime import datetime, timezone
from typing import List, Optional

from db.database_manager import DatabaseManager
from models.setting import Setting, SettingNotFound, SettingValidationError
from models.setting_type import SettingType, SettingTypeNotFound, SettingTypeValidationError
from models.settings_cache import SettingsCacheEntry, global_settings_cache


class SettingsManager:
    """Singleton manager for settings and setting types with caching and bulk persistence."""

    _instance: Optional['SettingsManager'] = None
    _lock = threading.Lock()

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Private constructor. Use get_instance() instead.

        Args:
            db_manager: DatabaseManager instance for database operations.
        """
        if SettingsManager._instance is not None:
            msg = "Use get_instance() to access SettingsManager"
            raise RuntimeError(msg)
        
        self.db_manager = db_manager
        # Use the shared global_settings_cache singleton
        self.cache = global_settings_cache
        
        # Load data immediately on initialization
        self._load_all_settings()

    @classmethod
    def get_instance(cls, db_manager: DatabaseManager) -> "SettingsManager":
        """Get the singleton instance of SettingsManager.

        Args:
            db_manager: DatabaseManager instance for database operations.
                       Required on first call, ignored on subsequent calls.

        Returns:
            The singleton SettingsManager instance.

        Example:
            >>> from db.database_manager import DatabaseManager, ConnectionType
            >>> db = DatabaseManager(connection_type=ConnectionType.CLOUD)
            >>> settings_mgr = SettingsManager.get_instance(db)
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_manager)
        return cls._instance

    def _load_all_settings(self) -> None:
        """Load all settings from database into cache."""
        # Debug message for cache hydration
        try:
            print("Debug: Hydrating settings cache")
        except Exception:
            # Ensure debug output does not interfere with initialization
            pass
        query = """
        SELECT setting_id, setting_type_id, setting_value, related_entity_id,
               created_user_id, updated_user_id, created_dt, updated_dt, row_checksum
        FROM settings
        """
        
        rows = self.db_manager.fetchall(query=query)
        for row in rows:
            # Normalize row_checksum to bytes (PostgreSQL returns BYTEA as memoryview)
            # to satisfy the Setting model's expectation of a bytes field.
            if isinstance(row.get("row_checksum"), memoryview):
                row = dict(row)
                row["row_checksum"] = bytes(row["row_checksum"])

            setting = Setting.from_dict(row)
            entry = SettingsCacheEntry(setting)
            entry.mark_clean()  # Loaded from DB, so clean
            key = (setting.setting_type_id, setting.related_entity_id)
            self.cache.entries[key] = entry

    def get_setting(
        self,
        setting_type_id: str,
        related_entity_id: str,
        default_value: Optional[str] = None,
    ) -> str:
        """Deprecated direct getter.

        This method is kept only for legacy compatibility. New code should read
        settings via global_settings_cache instead of calling get_setting.
        """
        # Original implementation (now commented out):
        # entry = self.cache.get(setting_type_id, related_entity_id)
        # if entry:
        #     return entry.setting.setting_value
        #
        # # Check setting type for default
        # setting_type = self.cache.get_setting_type(setting_type_id)
        # if setting_type and setting_type.default_value:
        #     return setting_type.default_value
        #
        # # Use provided default or raise exception
        # if default_value is not None:
        #     return default_value
        #
        # raise SettingNotFound(
        #     f"Setting '{setting_type_id}' not found for entity '{related_entity_id}'"
        # )

        msg = (
            "SettingsManager.get_setting is deprecated. "
            "Read settings via global_settings_cache instead."
        )
        raise RuntimeError(msg)

    def set_setting(
        self,
        setting_type_id: str,
        related_entity_id: str,
        value: str,
        user_id: str,
    ) -> None:
        """Deprecated direct setter.

        This method is kept only for legacy compatibility. New code should
        construct/update SettingsCacheEntry instances directly via
        global_settings_cache and then call flush() to persist.
        """
        # Original implementation (now commented out):
        # setting_type = self.cache.get_setting_type(setting_type_id)
        # if not setting_type:
        #     msg = f"Setting type '{setting_type_id}' not found"
        #     raise SettingTypeNotFound(msg)
        #
        # if not setting_type.validate_setting_value(value):
        #     msg = f"Value '{value}' is invalid for setting type '{setting_type_id}'"
        #     raise SettingValidationError(msg)
        #
        # entry = self.cache.get(setting_type_id, related_entity_id)
        # if entry:
        #     if entry.setting.setting_value == value:
        #         return
        #     entry.setting.setting_value = value
        #     entry.setting.updated_user_id = user_id
        #     entry.setting.row_checksum = entry.setting.calculate_checksum()
        # else:
        #     setting = Setting(
        #         setting_type_id=setting_type_id,
        #         setting_value=value,
        #         related_entity_id=related_entity_id,
        #         created_user_id=user_id,
        #         updated_user_id=user_id,
        #     )
        #     entry = SettingsCacheEntry(setting)
        #
        # self.cache.set(setting_type_id, related_entity_id, entry)

        msg = (
            "SettingsManager.set_setting is deprecated. "
            "Write settings via global_settings_cache and flush() instead."
        )
        raise RuntimeError(msg)

    def delete_setting(
        self,
        setting_type_id: str,
        related_entity_id: str,
        user_id: str,
    ) -> None:
        """Mark setting for deletion in cache."""
        entry = self.cache.get(setting_type_id, related_entity_id)
        if not entry:
            msg = (
                f"Setting '{setting_type_id}' not found for entity "
                f"'{related_entity_id}'"
            )
            raise SettingNotFound(msg)
        
        entry.mark_deleted()
        key = (setting_type_id, related_entity_id)
        self.cache.mark_dirty(key)

    def list_settings(self, related_entity_id: str) -> List[Setting]:
        """List all settings for a specific entity from cache."""
        return self.cache.list_settings_for_entity(related_entity_id)

    def get_setting_type(self, setting_type_id: str) -> SettingType:
        """Get setting type from cache."""
        setting_type = self.cache.get_setting_type(setting_type_id)
        if not setting_type:
            raise SettingTypeNotFound(f"Setting type '{setting_type_id}' not found")
        return setting_type

    def create_setting_type(self, setting_type: SettingType) -> bool:
        """Create new setting type."""
        # Check if already exists
        existing = self.cache.get_setting_type(setting_type.setting_type_id)
        if existing:
            msg = f"Setting type '{setting_type.setting_type_id}' already exists"
            raise SettingTypeValidationError(msg)
        
        self.cache.set_setting_type(setting_type.setting_type_id, setting_type)
        return True

    def update_setting_type(self, setting_type: SettingType) -> bool:
        """Update existing setting type."""
        existing = self.cache.get_setting_type(setting_type.setting_type_id)
        if not existing:
            msg = f"Setting type '{setting_type.setting_type_id}' not found"
            raise SettingTypeNotFound(msg)
        
        # Prevent modification of system setting types
        if existing.is_system:
            msg = (
                f"Cannot modify system setting type "
                f"'{setting_type.setting_type_id}'"
            )
            raise SettingTypeValidationError(msg)
        
        # Check for no-op update
        if existing.calculate_checksum() == setting_type.calculate_checksum():
            return True  # No change needed
        
        self.cache.set_setting_type(setting_type.setting_type_id, setting_type)
        return True

    def delete_setting_type(self, setting_type_id: str, user_id: str) -> bool:
        """Delete setting type (soft delete by marking inactive)."""
        setting_type = self.cache.get_setting_type(setting_type_id)
        if not setting_type:
            raise SettingTypeNotFound(f"Setting type '{setting_type_id}' not found")
        
        if setting_type.is_system:
            msg = f"Cannot delete system setting type '{setting_type_id}'"
            raise SettingTypeValidationError(msg)
        
        # Check if any settings reference this type
        for entry in self.cache.entries.values():
            if (
                entry.setting.setting_type_id == setting_type_id
                and not entry.is_deleted
            ):
                msg = (
                    f"Cannot delete setting type '{setting_type_id}' - "
                    "settings still reference it"
                )
                raise SettingTypeValidationError(msg)
        
        # Soft delete by marking inactive
        setting_type.is_active = False
        setting_type.updated_user_id = user_id
        setting_type.row_checksum = setting_type.calculate_checksum()
        self.cache.set_setting_type(setting_type_id, setting_type)
        return True

    def list_setting_types(
        self, entity_type: Optional[str] = None
    ) -> List[SettingType]:
        """List setting types, optionally filtered by entity type."""
        if entity_type:
            return self.cache.list_setting_types_by_entity_type(entity_type)
        return [st for st in self.cache.setting_types.values() if st.is_active]

    def save(self) -> bool:
        """Persist all dirty settings and setting types to database in bulk."""
        return self.flush()

    def flush(self) -> bool:
        """Persist all dirty settings and setting types to database in bulk."""
        if not self.db_manager:
            return False

        try:
            dirty_settings = self.cache.get_dirty_entries()
            dirty_setting_types = self.cache.get_dirty_setting_types()
            
            if not dirty_settings and not dirty_setting_types:
                return True  # Nothing to save

            # Debug output for flush operations
            try:
                print("DEBUG: flushing the cache")
                for entry in dirty_settings:
                    try:
                        print(
                            f"Debug: Dirty value {entry.setting.setting_value} being written"
                        )
                    except Exception:
                        # Avoid breaking flush if debug printing fails
                        pass
            except Exception:
                # Ensure no debug failure prevents persistence
                pass

            # Start transaction
            # Note: DatabaseManager handles transactions internally
            
            success = True
            if dirty_setting_types:
                success = success and self._persist_dirty_setting_types(
                    dirty_setting_types
                )
            
            if dirty_settings and success:
                success = success and self._persist_dirty_settings(dirty_settings)
            
            if success:
                self.cache.clear_dirty_flags()
                self.cache.clear_setting_type_dirty_flags()
                try:
                    print("Debug: completing cache flush")
                except Exception:
                    pass

            return success

        except Exception as e:
            # Log error and preserve dirty flags for retry
            print(f"Error saving settings: {e}")
            return False

    def _persist_dirty_setting_types(
        self, dirty_setting_types: List[SettingType]
    ) -> bool:
        """Persist dirty setting types using bulk operations."""
        if not self.db_manager:
            return False
        
        insert_data = []
        update_data = []
        
        for setting_type in dirty_setting_types:
            # Check if exists in database
            existing = self.db_manager.fetchone(
                query="SELECT 1 FROM setting_types WHERE setting_type_id = ?",
                params=(setting_type.setting_type_id,),
            )
            
            if existing:
                update_data.append((
                    setting_type.setting_type_name,
                    setting_type.description,
                    setting_type.related_entity_type,
                    setting_type.data_type,
                    setting_type.default_value,
                    setting_type.validation_rules,
                    setting_type.is_system,
                    setting_type.is_active,
                    setting_type.updated_user_id,
                    (setting_type.updated_dt.isoformat() 
                     if setting_type.updated_dt 
                     else datetime.now(timezone.utc).isoformat()),
                    setting_type.row_checksum,
                    setting_type.setting_type_id
                ))
            else:
                insert_data.append((
                    setting_type.setting_type_id,
                    setting_type.setting_type_name,
                    setting_type.description,
                    setting_type.related_entity_type,
                    setting_type.data_type,
                    setting_type.default_value,
                    setting_type.validation_rules,
                    setting_type.is_system,
                    setting_type.is_active,
                    setting_type.created_user_id,
                    setting_type.updated_user_id,
                    (
                        setting_type.created_dt.isoformat()
                        if setting_type.created_dt
                        else datetime.now(timezone.utc).isoformat()
                    ),
                    (
                        setting_type.updated_dt.isoformat()
                        if setting_type.updated_dt
                        else datetime.now(timezone.utc).isoformat()
                    ),
                    setting_type.row_checksum
                ))
        
        # Execute bulk operations
        if insert_data:
            insert_sql = """
            INSERT INTO setting_types (
                setting_type_id, setting_type_name, description,
                related_entity_type, data_type, default_value, validation_rules,
                is_system, is_active, created_user_id, updated_user_id,
                created_dt, updated_dt, row_checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_many(query=insert_sql, params_seq=insert_data)
        
        if update_data:
            update_sql = """
            UPDATE setting_types SET
                setting_type_name = ?, description = ?, related_entity_type = ?,
                data_type = ?, default_value = ?, validation_rules = ?,
                is_system = ?, is_active = ?, updated_user_id = ?,
                updated_dt = ?, row_checksum = ?
            WHERE setting_type_id = ?
            """
            self.db_manager.execute_many(query=update_sql, params_seq=update_data)
        
        return True

    def _persist_dirty_settings(
        self, dirty_entries: List[SettingsCacheEntry]
    ) -> bool:
        """Persist dirty settings using bulk operations."""
        if not self.db_manager:
            return False
        
        insert_data = []
        update_data = []
        delete_data = []
        
        for entry in dirty_entries:
            setting = entry.setting
            # Normalize timestamps to avoid None values
            if not setting.created_dt:
                setting.created_dt = datetime.now(timezone.utc)
            if not setting.updated_dt:
                setting.updated_dt = datetime.now(timezone.utc)

            if entry.is_deleted:
                # Only attempt delete/history if the setting exists in the base table
                existing_for_delete = self.db_manager.fetchone(
                    query="SELECT 1 FROM settings WHERE setting_id = ?",
                    params=(setting.setting_id,),
                )
                if existing_for_delete:
                    delete_data.append((setting.setting_id,))
                    # Record SCD-2 history delete version
                    self._create_settings_history_entry(setting=setting, action="D")
            else:
                # Check if exists in database and whether this is a no-op update
                existing_row = self.db_manager.fetchone(
                    query=(
                        "SELECT setting_id, row_checksum FROM settings "
                        "WHERE setting_id = ?"
                    ),
                    params=(setting.setting_id,),
                )

                # If no row found by setting_id, attempt to find an existing row
                # for this (setting_type_id, related_entity_id) pair. The
                # settings table enforces a UNIQUE constraint on
                # (setting_type_id, related_entity_id), so we must treat these
                # as upserts keyed by that pair.
                if not existing_row:
                    existing_row = self.db_manager.fetchone(
                        query=(
                            "SELECT setting_id, row_checksum FROM settings "
                            "WHERE setting_type_id = ? AND related_entity_id = ?"
                        ),
                        params=(
                            setting.setting_type_id,
                            setting.related_entity_id,
                        ),
                    )
                    if existing_row:
                        # Reuse existing setting_id so we update instead of
                        # violating the UNIQUE constraint.
                        setting.setting_id = existing_row.get("setting_id")

                if existing_row:
                    # For PostgreSQL, BYTEA may be returned as memoryview
                    existing_checksum = existing_row.get("row_checksum")
                    if isinstance(existing_checksum, memoryview):
                        existing_checksum = bytes(existing_checksum)

                    # Skip no-op updates (same checksum) entirely
                    if existing_checksum == setting.row_checksum:
                        continue

                    update_data.append((
                        setting.setting_value,
                        setting.updated_user_id,
                        (
                            setting.updated_dt.isoformat()
                            if setting.updated_dt
                            else datetime.now(timezone.utc).isoformat()
                        ),
                        setting.row_checksum,
                        setting.setting_id,
                    ))
                    # Record SCD-2 history update version
                    self._create_settings_history_entry(setting=setting, action="U")
                else:
                    insert_data.append((
                        setting.setting_id,
                        setting.setting_type_id,
                        setting.setting_value,
                        setting.related_entity_id,
                        setting.created_user_id,
                        setting.updated_user_id,
                        (
                            setting.created_dt.isoformat()
                            if setting.created_dt
                            else datetime.now(timezone.utc).isoformat()
                        ),
                        (
                            setting.updated_dt.isoformat()
                            if setting.updated_dt
                            else datetime.now(timezone.utc).isoformat()
                        ),
                        setting.row_checksum
                    ))
                    # Record SCD-2 history insert version
                    self._create_settings_history_entry(setting=setting, action="I")
        
        # Execute bulk operations
        if delete_data:
            delete_sql = "DELETE FROM settings WHERE setting_id = ?"
            self.db_manager.execute_many(query=delete_sql, params_seq=delete_data)
        
        if insert_data:
            insert_sql = """
            INSERT INTO settings (
                setting_id, setting_type_id, setting_value, related_entity_id,
                created_user_id, updated_user_id, created_dt, updated_dt,
                row_checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_many(query=insert_sql, params_seq=insert_data)
        
        if update_data:
            update_sql = """
            UPDATE settings SET
                setting_value = ?, updated_user_id = ?, updated_dt = ?,
                row_checksum = ?
            WHERE setting_id = ?
            """
            self.db_manager.execute_many(query=update_sql, params_seq=update_data)
        
        return True

    def _create_settings_history_entry(self, setting: Setting, action: str) -> None:
        """Create or update SCD-2 history rows for a setting.

        This method ensures that settings_history follows the SCD-2 pattern:

        - On insert (action='I'): create version 1 row with is_current = true.
        - On update (action='U'): close previous current version and insert new
          version with incremented version_no and is_current = true.
        - On delete (action='D'): close previous current version and insert new
          delete version as the current row.

        No-op updates (where the row_checksum has not changed) should be
        filtered out before calling this helper.
        """
        if not self.db_manager:
            return

        # Determine next version number and close any current version
        now_iso = datetime.now(timezone.utc).isoformat()

        # Get latest version for this setting_id, if any
        latest = self.db_manager.fetchone(
            query=(
                "SELECT version_no FROM settings_history "
                "WHERE setting_id = ? ORDER BY version_no DESC LIMIT 1"
            ),
            params=(setting.setting_id,),
        )

        next_version = 1
        if latest and "version_no" in latest:
            try:
                # version_no is stored as integer in DB
                next_version = int(latest["version_no"]) + 1
            except Exception:
                next_version = 1

        # Close any current version window
        self.db_manager.execute(
            query=(
                "UPDATE settings_history "
                "SET is_current = FALSE, valid_to_dt = ? "
                "WHERE setting_id = ? AND is_current = TRUE"
            ),
            params=(now_iso, setting.setting_id),
        )

        # Insert new history row
        insert_sql = """
        INSERT INTO settings_history (
            setting_id,
            setting_type_id,
            setting_value,
            related_entity_id,
            row_checksum,
            created_dt,
            updated_dt,
            created_user_id,
            updated_user_id,
            action,
            version_no,
            valid_from_dt,
            valid_to_dt,
            is_current
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.db_manager.execute(
            query=insert_sql,
            params=(
                setting.setting_id,
                setting.setting_type_id,
                setting.setting_value,
                setting.related_entity_id,
                setting.row_checksum,
                setting.created_dt.isoformat(),
                setting.updated_dt.isoformat(),
                setting.created_user_id,
                setting.updated_user_id,
                action,
                next_version,
                now_iso,
                "9999-12-31T23:59:59Z",
                True,
            ),
        )

    def has_dirty_settings(self) -> bool:
        """Check if there are any dirty settings."""
        return len(self.cache.dirty_entries) > 0

    def has_dirty_setting_types(self) -> bool:
        """Check if there are any dirty setting types."""
        return len(self.cache.dirty_setting_types) > 0

    def clear_cache(self) -> None:
        """Clear all cache data (for testing)."""
        self.cache.clear()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing).
        
        This allows tests to create a new instance with a different database connection.
        """
        with cls._lock:
            cls._instance = None
