"""Singleton Settings Manager with caching and bulk persistence.

Provides globally accessible settings management with efficient caching.
"""

import threading
from datetime import datetime, timezone
from typing import List, Optional

from db.database_manager import DatabaseManager
from models.setting import Setting, SettingNotFound, SettingValidationError
from models.setting_type import SettingType, SettingTypeNotFound, SettingTypeValidationError
from models.settings_cache import SettingsCache, SettingsCacheEntry


class SettingsManager:
    """Singleton manager for settings and setting types with caching and bulk persistence."""

    _instance: Optional['SettingsManager'] = None
    _lock = threading.Lock()
    _initialized = False

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        """Private constructor. Use get_instance() instead."""
        if SettingsManager._instance is not None:
            msg = "Use get_instance() to access SettingsManager"
            raise RuntimeError(msg)
        
        self.db_manager: Optional[DatabaseManager] = db_manager
        self.cache = SettingsCache()

    @classmethod
    def get_instance(cls) -> "SettingsManager":
        """Get the singleton instance of SettingsManager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, db_manager: DatabaseManager) -> None:
        """Initialize the settings manager with database connection."""
        with self._lock:
            if self._initialized:
                return
            
            self.db_manager = db_manager
            self._load_all_setting_types()
            self._load_all_settings()
            self._initialized = True

    def _load_all_setting_types(self) -> None:
        """Load all setting types from database into cache."""
        if not self.db_manager:
            return

        query = """
        SELECT setting_type_id, setting_type_name, description,
               related_entity_type, data_type, default_value,
               validation_rules, is_system, is_active,
               created_user_id, updated_user_id, created_at,
               updated_at, row_checksum
        FROM setting_types WHERE is_active = 1
        """
        
        rows = self.db_manager.fetchall(query)
        for row in rows:
            setting_type = SettingType.from_dict(row)
            self.cache.setting_types[setting_type.setting_type_id] = setting_type

    def _load_all_settings(self) -> None:
        """Load all settings from database into cache."""
        if not self.db_manager:
            return

        query = """
        SELECT setting_id, setting_type_id, setting_value, related_entity_id,
               created_user_id, updated_user_id, created_at, updated_at, row_checksum
        FROM settings
        """
        
        rows = self.db_manager.fetchall(query)
        for row in rows:
            setting = Setting.from_dict(row)
            entry = SettingsCacheEntry(setting)
            entry.mark_clean()  # Loaded from DB, so clean
            key = (setting.setting_type_id, setting.related_entity_id)
            self.cache.entries[key] = entry

    def get_setting(self, setting_type_id: str, related_entity_id: str, 
                   default_value: Optional[str] = None) -> str:
        """Get setting value from cache with optional default."""
        entry = self.cache.get(setting_type_id, related_entity_id)
        if entry:
            return entry.setting.setting_value
        
        # Check setting type for default
        setting_type = self.cache.get_setting_type(setting_type_id)
        if setting_type and setting_type.default_value:
            return setting_type.default_value
        
        # Use provided default or raise exception
        if default_value is not None:
            return default_value
        
        raise SettingNotFound(
            f"Setting '{setting_type_id}' not found for entity '{related_entity_id}'"
        )

    def set_setting(
        self,
        setting_type_id: str,
        related_entity_id: str,
        value: str,
        user_id: str,
    ) -> None:
        """Set setting value in cache and mark as dirty."""
        # Validate setting type exists
        setting_type = self.cache.get_setting_type(setting_type_id)
        if not setting_type:
            msg = f"Setting type '{setting_type_id}' not found"
            raise SettingTypeNotFound(msg)
        
        # Validate value against setting type
        if not setting_type.validate_setting_value(value):
            msg = f"Value '{value}' is invalid for setting type '{setting_type_id}'"
            raise SettingValidationError(msg)

        # Get or create setting
        entry = self.cache.get(setting_type_id, related_entity_id)
        if entry:
            # Check for no-op update
            if entry.setting.setting_value == value:
                return  # No change needed
            
            # Update existing setting
            entry.setting.setting_value = value
            entry.setting.updated_user_id = user_id
            entry.setting.row_checksum = entry.setting.calculate_checksum()
        else:
            # Create new setting
            setting = Setting(
                setting_type_id=setting_type_id,
                setting_value=value,
                related_entity_id=related_entity_id,
                created_user_id=user_id,
                updated_user_id=user_id
            )
            entry = SettingsCacheEntry(setting)
        
        # Mark as dirty and update cache
        self.cache.set(setting_type_id, related_entity_id, entry)

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
                    (setting_type.updated_at.isoformat() 
                     if setting_type.updated_at 
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
                        setting_type.created_at.isoformat()
                        if setting_type.created_at
                        else datetime.now(timezone.utc).isoformat()
                    ),
                    (
                        setting_type.updated_at.isoformat()
                        if setting_type.updated_at
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
                created_at, updated_at, row_checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_many(query=insert_sql, params_seq=insert_data)
        
        if update_data:
            update_sql = """
            UPDATE setting_types SET
                setting_type_name = ?, description = ?, related_entity_type = ?,
                data_type = ?, default_value = ?, validation_rules = ?,
                is_system = ?, is_active = ?, updated_user_id = ?,
                updated_at = ?, row_checksum = ?
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
            if entry.is_deleted:
                delete_data.append((entry.setting.setting_id,))
            else:
                # Check if exists in database
                existing = self.db_manager.fetchone(
                    query="SELECT 1 FROM settings WHERE setting_id = ?",
                    params=(entry.setting.setting_id,),
                )
                
                if existing:
                    update_data.append((
                        entry.setting.setting_value,
                        entry.setting.updated_user_id,
                        (
                            entry.setting.updated_at.isoformat()
                            if entry.setting.updated_at
                            else datetime.now(timezone.utc).isoformat()
                        ),
                        entry.setting.row_checksum,
                        entry.setting.setting_id
                    ))
                else:
                    insert_data.append((
                        entry.setting.setting_id,
                        entry.setting.setting_type_id,
                        entry.setting.setting_value,
                        entry.setting.related_entity_id,
                        entry.setting.created_user_id,
                        entry.setting.updated_user_id,
                        (
                            entry.setting.created_at.isoformat()
                            if entry.setting.created_at
                            else datetime.now(timezone.utc).isoformat()
                        ),
                        (
                            entry.setting.updated_at.isoformat()
                            if entry.setting.updated_at
                            else datetime.now(timezone.utc).isoformat()
                        ),
                        entry.setting.row_checksum
                    ))
        
        # Execute bulk operations
        if delete_data:
            delete_sql = "DELETE FROM settings WHERE setting_id = ?"
            self.db_manager.execute_many(query=delete_sql, params_seq=delete_data)
        
        if insert_data:
            insert_sql = """
            INSERT INTO settings (
                setting_id, setting_type_id, setting_value, related_entity_id,
                created_user_id, updated_user_id, created_at, updated_at,
                row_checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_many(query=insert_sql, params_seq=insert_data)
        
        if update_data:
            update_sql = """
            UPDATE settings SET
                setting_value = ?, updated_user_id = ?, updated_at = ?,
                row_checksum = ?
            WHERE setting_id = ?
            """
            self.db_manager.execute_many(query=update_sql, params_seq=update_data)
        
        return True

    def has_dirty_settings(self) -> bool:
        """Check if there are any dirty settings."""
        return len(self.cache.dirty_entries) > 0

    def has_dirty_setting_types(self) -> bool:
        """Check if there are any dirty setting types."""
        return len(self.cache.dirty_setting_types) > 0

    def clear_cache(self) -> None:
        """Clear all cache data (for testing)."""
        self.cache.clear()
        self._initialized = False

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        with cls._lock:
            cls._instance = None
            cls._initialized = False
