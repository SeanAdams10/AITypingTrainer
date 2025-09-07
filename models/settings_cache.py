"""Settings Cache for in-memory storage with dirty flag tracking.

Provides efficient caching layer for settings and setting types.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from models.setting import Setting
from models.setting_type import SettingType


class SettingsCacheEntry:
    """Cache entry wrapping a Setting with metadata."""

    def __init__(self, setting: Setting) -> None:
        """Initialize cache entry with setting."""
        self.setting = setting
        self.is_dirty = False
        self.is_deleted = False
        self.cache_timestamp = datetime.now(timezone.utc)

    def mark_dirty(self) -> None:
        """Mark this entry as dirty (needs saving)."""
        self.is_dirty = True

    def mark_clean(self) -> None:
        """Mark this entry as clean (saved)."""
        if not self.is_deleted:
            self.is_dirty = False

    def mark_deleted(self) -> None:
        """Mark this entry for deletion."""
        self.is_deleted = True
        self.is_dirty = True


class SettingsCache:
    """In-memory cache for settings and setting types with dirty flag tracking."""

    def __init__(self) -> None:
        """Initialize empty cache."""
        # Map of (setting_type_id, related_entity_id) -> SettingsCacheEntry
        self.entries: Dict[Tuple[str, str], SettingsCacheEntry] = {}
        # Set of dirty entry keys
        self.dirty_entries: Set[Tuple[str, str]] = set()
        
        # Map of setting_type_id -> SettingType
        self.setting_types: Dict[str, SettingType] = {}
        # Set of dirty setting type IDs
        self.dirty_setting_types: Set[str] = set()

    def get(self, setting_type_id: str, related_entity_id: str) -> Optional[SettingsCacheEntry]:
        """Get cache entry by key."""
        key = (setting_type_id, related_entity_id)
        entry = self.entries.get(key)
        if entry and not entry.is_deleted:
            return entry
        return None

    def set(self, setting_type_id: str, related_entity_id: str, entry: SettingsCacheEntry) -> None:
        """Set cache entry and mark as dirty."""
        key = (setting_type_id, related_entity_id)
        self.entries[key] = entry
        self.mark_dirty(key)

    def mark_dirty(self, key: Tuple[str, str]) -> None:
        """Mark entry as dirty."""
        self.dirty_entries.add(key)
        if key in self.entries:
            self.entries[key].mark_dirty()

    def mark_clean(self, key: Tuple[str, str]) -> None:
        """Mark entry as clean."""
        self.dirty_entries.discard(key)
        if key in self.entries:
            self.entries[key].mark_clean()

    def get_dirty_entries(self) -> List[SettingsCacheEntry]:
        """Get all dirty cache entries."""
        return [self.entries[key] for key in self.dirty_entries if key in self.entries]

    def clear_dirty_flags(self) -> None:
        """Clear all dirty flags."""
        for key in list(self.dirty_entries):
            self.mark_clean(key)

    def get_setting_type(self, setting_type_id: str) -> Optional[SettingType]:
        """Get setting type by ID."""
        return self.setting_types.get(setting_type_id)

    def set_setting_type(self, setting_type_id: str, setting_type: SettingType) -> None:
        """Set setting type and mark as dirty."""
        self.setting_types[setting_type_id] = setting_type
        self.mark_setting_type_dirty(setting_type_id)

    def mark_setting_type_dirty(self, setting_type_id: str) -> None:
        """Mark setting type as dirty."""
        self.dirty_setting_types.add(setting_type_id)

    def mark_setting_type_clean(self, setting_type_id: str) -> None:
        """Mark setting type as clean."""
        self.dirty_setting_types.discard(setting_type_id)

    def get_dirty_setting_types(self) -> List[SettingType]:
        """Get all dirty setting types."""
        return [
            self.setting_types[type_id]
            for type_id in self.dirty_setting_types
            if type_id in self.setting_types
        ]

    def clear_setting_type_dirty_flags(self) -> None:
        """Clear all setting type dirty flags."""
        self.dirty_setting_types.clear()

    def list_settings_for_entity(self, related_entity_id: str) -> List[Setting]:
        """List all settings for a specific entity."""
        result = []
        for (_type_id, entity_id), entry in self.entries.items():
            if entity_id == related_entity_id and not entry.is_deleted:
                result.append(entry.setting)
        return result

    def list_setting_types_by_entity_type(
        self, entity_type: str
    ) -> List[SettingType]:
        """List all setting types for a specific entity type."""
        return [
            st
            for st in self.setting_types.values()
            if st.related_entity_type == entity_type and st.is_active
        ]

    def clear(self) -> None:
        """Clear all cache data."""
        self.entries.clear()
        self.dirty_entries.clear()
        self.setting_types.clear()
        self.dirty_setting_types.clear()
