"""Unit tests for models.settings_cache.

Tests SettingsCacheEntry and SettingsCache classes focusing on dirty flag management,
cache operations, and bulk data handling.
"""

import sys
import uuid
from datetime import datetime, timezone

import pytest

from models.setting import Setting
from models.setting_type import SettingType
from models.settings_cache import SettingsCacheEntry, SettingsCache


def create_test_setting(
    setting_type_id: str = "USRTHM",
    setting_value: str = "dark",
    related_entity_id: str | None = None,
    user_id: str | None = None,
) -> Setting:
    """Helper: Create a valid Setting for testing with all required fields."""
    now = datetime.now(timezone.utc)
    uid = user_id or str(uuid.uuid4())
    entity_id = related_entity_id or str(uuid.uuid4())
    
    setting = Setting(
        setting_type_id=setting_type_id,
        setting_value=setting_value,
        related_entity_id=entity_id,
        row_checksum=b"",
        created_dt=now,
        updated_dt=now,
        created_user_id=uid,
        updated_user_id=uid,
    )
    setting.row_checksum = setting.calculate_checksum()
    return setting


def create_test_setting_type(
    setting_type_id: str = "USRTHM",
    setting_type_name: str = "User Theme",
    related_entity_type: str = "user",
) -> SettingType:
    """Helper: Create a valid SettingType for testing."""
    now = datetime.now(timezone.utc)
    user_id = str(uuid.uuid4())
    
    setting_type = SettingType(
        setting_type_id=setting_type_id,
        setting_type_name=setting_type_name,
        description="Test setting type",
        related_entity_type=related_entity_type,
        data_type="string",
        default_value="default",
        validation_rules=None,
        is_system=False,
        is_active=True,
        created_user_id=user_id,
        updated_user_id=user_id,
        created_dt=now,
        updated_dt=now,
        row_checksum="",
    )
    setting_type.row_checksum = setting_type.calculate_checksum()
    return setting_type


class TestSettingsCacheEntry:
    """Test suite for SettingsCacheEntry class."""

    def test_cache_entry_creation(self) -> None:
        """Test objective: Create a cache entry with default state."""
        setting = create_test_setting()
        entry = SettingsCacheEntry(setting)
        
        assert entry.setting == setting
        assert entry.is_dirty is False
        assert entry.is_deleted is False
        assert entry.cache_timestamp is not None

    def test_mark_dirty(self) -> None:
        """Test objective: Mark entry as dirty."""
        setting = create_test_setting()
        entry = SettingsCacheEntry(setting)
        
        assert entry.is_dirty is False
        entry.mark_dirty()
        assert entry.is_dirty is True

    def test_mark_clean(self) -> None:
        """Test objective: Mark entry as clean."""
        setting = create_test_setting()
        entry = SettingsCacheEntry(setting)
        
        entry.mark_dirty()
        assert entry.is_dirty is True
        
        entry.mark_clean()
        assert entry.is_dirty is False

    def test_mark_deleted(self) -> None:
        """Test objective: Mark entry as deleted sets both flags."""
        setting = create_test_setting()
        entry = SettingsCacheEntry(setting)
        
        entry.mark_deleted()
        assert entry.is_deleted is True
        assert entry.is_dirty is True

    def test_deleted_stays_dirty(self) -> None:
        """Test objective: Deleted entries remain dirty even when marked clean."""
        setting = create_test_setting()
        entry = SettingsCacheEntry(setting)
        
        entry.mark_deleted()
        assert entry.is_dirty is True
        
        # Try to mark clean
        entry.mark_clean()
        # Should still be dirty because it's deleted
        assert entry.is_dirty is True
        assert entry.is_deleted is True


class TestSettingsCache:
    """Test suite for SettingsCache class."""

    def test_cache_initialization(self) -> None:
        """Test objective: Initialize empty cache."""
        cache = SettingsCache()
        
        assert len(cache.entries) == 0
        assert len(cache.dirty_entries) == 0
        assert len(cache.setting_types) == 0
        assert len(cache.dirty_setting_types) == 0

    def test_get_nonexistent(self) -> None:
        """Test objective: Get nonexistent entry returns None."""
        cache = SettingsCache()
        
        entry = cache.get("USRTHM", str(uuid.uuid4()))
        assert entry is None

    def test_set_and_get(self) -> None:
        """Test objective: Set and retrieve cache entry."""
        cache = SettingsCache()
        setting = create_test_setting(setting_type_id="USRTHM")
        entry = SettingsCacheEntry(setting)
        
        cache.set("USRTHM", setting.related_entity_id, entry)
        
        retrieved = cache.get("USRTHM", setting.related_entity_id)
        assert retrieved is not None
        assert retrieved.setting == setting

    def test_set_marks_dirty(self) -> None:
        """Test objective: Setting an entry marks it as dirty."""
        cache = SettingsCache()
        setting = create_test_setting(setting_type_id="USRTHM")
        entry = SettingsCacheEntry(setting)
        
        cache.set("USRTHM", setting.related_entity_id, entry)
        
        key = ("USRTHM", setting.related_entity_id)
        assert key in cache.dirty_entries
        assert entry.is_dirty is True

    def test_mark_clean(self) -> None:
        """Test objective: Mark entry as clean removes from dirty set."""
        cache = SettingsCache()
        setting = create_test_setting(setting_type_id="USRTHM")
        entry = SettingsCacheEntry(setting)
        
        cache.set("USRTHM", setting.related_entity_id, entry)
        key = ("USRTHM", setting.related_entity_id)
        assert key in cache.dirty_entries
        
        cache.mark_clean(key)
        assert key not in cache.dirty_entries
        assert entry.is_dirty is False

    def test_get_dirty_entries(self) -> None:
        """Test objective: Get all dirty entries."""
        cache = SettingsCache()
        
        # Create three settings, mark two as dirty
        settings = [
            create_test_setting(setting_type_id="TYPE01"),
            create_test_setting(setting_type_id="TYPE02"),
            create_test_setting(setting_type_id="TYPE03"),
        ]
        
        for setting in settings:
            entry = SettingsCacheEntry(setting)
            cache.set(setting.setting_type_id, setting.related_entity_id, entry)
        
        # Mark one as clean
        key = ("TYPE02", settings[1].related_entity_id)
        cache.mark_clean(key)
        
        dirty = cache.get_dirty_entries()
        assert len(dirty) == 2
        dirty_type_ids = {entry.setting.setting_type_id for entry in dirty}
        assert dirty_type_ids == {"TYPE01", "TYPE03"}

    def test_clear_dirty_flags(self) -> None:
        """Test objective: Clear all dirty flags."""
        cache = SettingsCache()
        
        # Create and add settings
        for i in range(3):
            setting = create_test_setting(setting_type_id=f"TYPE0{i+1}")
            entry = SettingsCacheEntry(setting)
            cache.set(setting.setting_type_id, setting.related_entity_id, entry)
        
        assert len(cache.dirty_entries) == 3
        
        cache.clear_dirty_flags()
        assert len(cache.dirty_entries) == 0
        assert len(cache.get_dirty_entries()) == 0

    def test_get_deleted_entry_returns_none(self) -> None:
        """Test objective: Getting a deleted entry returns None."""
        cache = SettingsCache()
        setting = create_test_setting(setting_type_id="USRTHM")
        entry = SettingsCacheEntry(setting)
        
        cache.set("USRTHM", setting.related_entity_id, entry)
        entry.mark_deleted()
        
        retrieved = cache.get("USRTHM", setting.related_entity_id)
        assert retrieved is None

    def test_list_settings_for_entity(self) -> None:
        """Test objective: List all settings for a specific entity."""
        cache = SettingsCache()
        entity_id = str(uuid.uuid4())
        
        # Create three settings for the same entity
        for i in range(3):
            setting = create_test_setting(
                setting_type_id=f"TYPE0{i+1}",
                related_entity_id=entity_id
            )
            entry = SettingsCacheEntry(setting)
            cache.set(setting.setting_type_id, entity_id, entry)
        
        # Create one for a different entity
        other_setting = create_test_setting(setting_type_id="OTHER1")
        other_entry = SettingsCacheEntry(other_setting)
        cache.set("OTHER1", other_setting.related_entity_id, other_entry)
        
        # List settings for the first entity
        settings = cache.list_settings_for_entity(entity_id)
        assert len(settings) == 3
        assert all(s.related_entity_id == entity_id for s in settings)

    def test_list_settings_excludes_deleted(self) -> None:
        """Test objective: List settings excludes deleted entries."""
        cache = SettingsCache()
        entity_id = str(uuid.uuid4())
        
        # Create three settings
        settings = []
        for i in range(3):
            setting = create_test_setting(
                setting_type_id=f"TYPE0{i+1}",
                related_entity_id=entity_id
            )
            entry = SettingsCacheEntry(setting)
            cache.set(setting.setting_type_id, entity_id, entry)
            settings.append((setting, entry))
        
        # Mark one as deleted
        settings[1][1].mark_deleted()
        
        # List should only return 2
        result = cache.list_settings_for_entity(entity_id)
        assert len(result) == 2
        type_ids = {s.setting_type_id for s in result}
        assert type_ids == {"TYPE01", "TYPE03"}

    def test_clear(self) -> None:
        """Test objective: Clear all cache data."""
        cache = SettingsCache()
        
        # Add some settings
        for i in range(3):
            setting = create_test_setting(setting_type_id=f"TYPE0{i+1}")
            entry = SettingsCacheEntry(setting)
            cache.set(setting.setting_type_id, setting.related_entity_id, entry)
        
        # Add some setting types
        for i in range(2):
            st = create_test_setting_type(setting_type_id=f"STYPE{i+1}")
            cache.set_setting_type(st.setting_type_id, st)
        
        assert len(cache.entries) == 3
        assert len(cache.dirty_entries) == 3
        assert len(cache.setting_types) == 2
        assert len(cache.dirty_setting_types) == 2
        
        cache.clear()
        
        assert len(cache.entries) == 0
        assert len(cache.dirty_entries) == 0
        assert len(cache.setting_types) == 0
        assert len(cache.dirty_setting_types) == 0


class TestSettingsCacheSettingTypes:
    """Test suite for setting type cache operations."""

    def test_get_setting_type_nonexistent(self) -> None:
        """Test objective: Get nonexistent setting type returns None."""
        cache = SettingsCache()
        
        st = cache.get_setting_type("USRTHM")
        assert st is None

    def test_set_and_get_setting_type(self) -> None:
        """Test objective: Set and retrieve setting type."""
        cache = SettingsCache()
        setting_type = create_test_setting_type(setting_type_id="USRTHM")
        
        cache.set_setting_type("USRTHM", setting_type)
        
        retrieved = cache.get_setting_type("USRTHM")
        assert retrieved is not None
        assert retrieved.setting_type_id == "USRTHM"

    def test_set_setting_type_marks_dirty(self) -> None:
        """Test objective: Setting a type marks it as dirty."""
        cache = SettingsCache()
        setting_type = create_test_setting_type(setting_type_id="USRTHM")
        
        cache.set_setting_type("USRTHM", setting_type)
        
        assert "USRTHM" in cache.dirty_setting_types

    def test_mark_setting_type_clean(self) -> None:
        """Test objective: Mark setting type as clean."""
        cache = SettingsCache()
        setting_type = create_test_setting_type(setting_type_id="USRTHM")
        
        cache.set_setting_type("USRTHM", setting_type)
        assert "USRTHM" in cache.dirty_setting_types
        
        cache.mark_setting_type_clean("USRTHM")
        assert "USRTHM" not in cache.dirty_setting_types

    def test_get_dirty_setting_types(self) -> None:
        """Test objective: Get all dirty setting types."""
        cache = SettingsCache()
        
        # Create three setting types
        for i in range(3):
            st = create_test_setting_type(setting_type_id=f"TYPE0{i+1}")
            cache.set_setting_type(st.setting_type_id, st)
        
        # Mark one as clean
        cache.mark_setting_type_clean("TYPE02")
        
        dirty = cache.get_dirty_setting_types()
        assert len(dirty) == 2
        dirty_ids = {st.setting_type_id for st in dirty}
        assert dirty_ids == {"TYPE01", "TYPE03"}

    def test_clear_setting_type_dirty_flags(self) -> None:
        """Test objective: Clear all setting type dirty flags."""
        cache = SettingsCache()
        
        # Create setting types
        for i in range(3):
            st = create_test_setting_type(setting_type_id=f"TYPE0{i+1}")
            cache.set_setting_type(st.setting_type_id, st)
        
        assert len(cache.dirty_setting_types) == 3
        
        cache.clear_setting_type_dirty_flags()
        assert len(cache.dirty_setting_types) == 0

    def test_list_setting_types_by_entity_type(self) -> None:
        """Test objective: List setting types filtered by entity type."""
        cache = SettingsCache()
        
        # Create setting types for different entity types
        user_types = [
            create_test_setting_type(
                setting_type_id=f"USR00{i+1}",
                related_entity_type="user"
            )
            for i in range(2)
        ]
        global_types = [
            create_test_setting_type(
                setting_type_id=f"GLB00{i+1}",
                related_entity_type="global"
            )
            for i in range(2)
        ]
        
        for st in user_types + global_types:
            cache.set_setting_type(st.setting_type_id, st)
        
        # List user types
        user_result = cache.list_setting_types_by_entity_type("user")
        assert len(user_result) == 2
        assert all(st.related_entity_type == "user" for st in user_result)
        
        # List global types
        global_result = cache.list_setting_types_by_entity_type("global")
        assert len(global_result) == 2
        assert all(st.related_entity_type == "global" for st in global_result)

    def test_list_setting_types_excludes_inactive(self) -> None:
        """Test objective: List setting types excludes inactive ones."""
        cache = SettingsCache()
        
        # Create active and inactive setting types
        active_st = create_test_setting_type(setting_type_id="ACTIVE")
        active_st.is_active = True
        
        inactive_st = create_test_setting_type(setting_type_id="INACTV")
        inactive_st.is_active = False
        
        cache.set_setting_type("ACTIVE", active_st)
        cache.set_setting_type("INACTV", inactive_st)
        
        # List should only return active
        result = cache.list_setting_types_by_entity_type("user")
        assert len(result) == 1
        assert result[0].setting_type_id == "ACTIVE"


class TestSettingsCacheEdgeCases:
    """Test suite for edge cases and complex scenarios."""

    def test_multiple_entities_same_type(self) -> None:
        """Test objective: Handle multiple entities with same setting type."""
        cache = SettingsCache()
        
        # Create same setting type for different entities
        entity_ids = [str(uuid.uuid4()) for _ in range(3)]
        for entity_id in entity_ids:
            setting = create_test_setting(
                setting_type_id="USRTHM",
                related_entity_id=entity_id
            )
            entry = SettingsCacheEntry(setting)
            cache.set("USRTHM", entity_id, entry)
        
        # Each entity should have its own entry
        for entity_id in entity_ids:
            entry = cache.get("USRTHM", entity_id)
            assert entry is not None
            assert entry.setting.related_entity_id == entity_id

    def test_update_existing_entry(self) -> None:
        """Test objective: Update an existing cache entry."""
        cache = SettingsCache()
        entity_id = str(uuid.uuid4())
        
        # Create initial setting
        setting1 = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=entity_id
        )
        entry1 = SettingsCacheEntry(setting1)
        cache.set("USRTHM", entity_id, entry1)
        cache.mark_clean(("USRTHM", entity_id))
        
        # Update with new value
        setting2 = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="light",
            related_entity_id=entity_id
        )
        entry2 = SettingsCacheEntry(setting2)
        cache.set("USRTHM", entity_id, entry2)
        
        # Should have new value and be dirty
        retrieved = cache.get("USRTHM", entity_id)
        assert retrieved is not None
        assert retrieved.setting.setting_value == "light"
        assert ("USRTHM", entity_id) in cache.dirty_entries


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
