"""Comprehensive unit tests for the SettingsCache classes.

Tests SettingsCacheEntry and SettingsCache classes focusing on dirty flag management,
cache operations, and bulk data handling as specified in Settings.md.
"""

import uuid
from datetime import datetime, timezone

import pytest

from models.setting import Setting
from models.setting_type import SettingType
from models.settings_cache import SettingsCacheEntry, SettingsCache


class TestSettingsCacheEntry:
    """Test cases for the SettingsCacheEntry class."""

    def test_cache_entry_creation_new_setting(self) -> None:
        """Test creating SettingsCacheEntry with new setting (dirty by default)."""
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            created_user_id="user1",
            updated_user_id="user1"
        )
        
        entry = SettingsCacheEntry(setting)
        
        assert entry.setting == setting
        assert entry.is_dirty is True  # New settings are dirty by default
        assert entry.is_deleted is False

    def test_cache_entry_mark_clean(self) -> None:
        """Test marking entry as clean."""
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            created_user_id="user1",
            updated_user_id="user1"
        )
        
        entry = SettingsCacheEntry(setting)
        assert entry.is_dirty is True
        
        entry.mark_clean()
        assert entry.is_dirty is False

    def test_cache_entry_mark_dirty(self) -> None:
        """Test marking entry as dirty."""
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            created_user_id="user1",
            updated_user_id="user1"
        )
        
        entry = SettingsCacheEntry(setting)
        entry.mark_clean()
        assert entry.is_dirty is False
        
        entry.mark_dirty()
        assert entry.is_dirty is True

    def test_cache_entry_mark_deleted(self) -> None:
        """Test marking entry as deleted."""
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            created_user_id="user1",
            updated_user_id="user1"
        )
        
        entry = SettingsCacheEntry(setting)
        assert entry.is_deleted is False
        
        entry.mark_deleted()
        assert entry.is_deleted is True
        assert entry.is_dirty is True  # Deleted entries are also dirty

    def test_cache_entry_deleted_stays_dirty(self) -> None:
        """Test that deleted entries remain dirty even when marked clean."""
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            created_user_id="user1",
            updated_user_id="user1"
        )
        
        entry = SettingsCacheEntry(setting)
        entry.mark_deleted()
        assert entry.is_dirty is True
        
        entry.mark_clean()
        assert entry.is_dirty is True  # Should remain dirty because deleted


class TestSettingsCache:
    """Test cases for the SettingsCache class."""

    def test_settings_cache_initialization(self) -> None:
        """Test SettingsCache initialization."""
        cache = SettingsCache()
        
        assert isinstance(cache.entries, dict)
        assert isinstance(cache.setting_types, dict)
        assert isinstance(cache.dirty_entries, set)
        assert isinstance(cache.dirty_setting_types, set)
        assert len(cache.entries) == 0
        assert len(cache.setting_types) == 0
        assert len(cache.dirty_entries) == 0
        assert len(cache.dirty_setting_types) == 0

    def test_cache_set_and_get_setting(self) -> None:
        """Test setting and getting cache entries."""
        cache = SettingsCache()
        
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id="user123",
            created_user_id="user1",
            updated_user_id="user1"
        )
        
        entry = SettingsCacheEntry(setting)
        cache.set("user.theme", "user123", entry)
        
        # Verify entry was stored
        retrieved = cache.get("user.theme", "user123")
        assert retrieved is not None
        assert retrieved.setting == setting
        
        # Verify dirty tracking
        key = ("user.theme", "user123")
        assert key in cache.dirty_entries

    def test_cache_get_nonexistent(self) -> None:
        """Test getting non-existent cache entry."""
        cache = SettingsCache()
        
        result = cache.get("non.existent", "user123")
        assert result is None

    def test_cache_mark_dirty(self) -> None:
        """Test marking cache entries as dirty."""
        cache = SettingsCache()
        
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id="user123",
            created_user_id="user1",
            updated_user_id="user1"
        )
        
        entry = SettingsCacheEntry(setting)
        entry.mark_clean()  # Start clean
        cache.set("user.theme", "user123", entry)
        cache.clear_dirty_flags()  # Clear dirty state
        
        # Mark as dirty
        key = ("user.theme", "user123")
        cache.mark_dirty(key)
        
        assert key in cache.dirty_entries
        assert entry.is_dirty is True

    def test_cache_clear_dirty_flags(self) -> None:
        """Test clearing dirty flags."""
        cache = SettingsCache()
        
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id="user123",
            created_user_id="user1",
            updated_user_id="user1"
        )
        
        entry = SettingsCacheEntry(setting)
        cache.set("user.theme", "user123", entry)
        
        # Should be dirty initially
        key = ("user.theme", "user123")
        assert key in cache.dirty_entries
        assert entry.is_dirty is True
        
        # Clear dirty flags
        cache.clear_dirty_flags()
        
        assert len(cache.dirty_entries) == 0
        assert entry.is_dirty is False

    def test_cache_get_dirty_entries(self) -> None:
        """Test getting list of dirty entries."""
        cache = SettingsCache()
        
        # Add multiple settings
        settings = []
        for i in range(3):
            setting = Setting(
                setting_type_id=f"user.setting{i}",
                setting_value=f"value{i}",
                related_entity_id="user123",
                created_user_id="user1",
                updated_user_id="user1"
            )
            settings.append(setting)
            entry = SettingsCacheEntry(setting)
            cache.set(f"user.setting{i}", "user123", entry)
        
        # Mark one as clean
        clean_key = ("user.setting1", "user123")
        cache.get("user.setting1", "user123").mark_clean()
        cache.dirty_entries.discard(clean_key)
        
        dirty_entries = cache.get_dirty_entries()
        
        assert len(dirty_entries) == 2
        assert all(isinstance(entry, SettingsCacheEntry) for entry in dirty_entries)
        assert all(entry.is_dirty for entry in dirty_entries)

    def test_cache_list_settings_for_entity(self) -> None:
        """Test listing all settings for a specific entity."""
        cache = SettingsCache()
        
        # Add settings for different entities
        user1_settings = []
        user2_settings = []
        
        for i in range(2):
            # User 1 settings
            setting1 = Setting(
                setting_type_id=f"user.setting{i}",
                setting_value=f"value{i}",
                related_entity_id="user1",
                created_user_id="user1",
                updated_user_id="user1"
            )
            user1_settings.append(setting1)
            entry1 = SettingsCacheEntry(setting1)
            cache.set(f"user.setting{i}", "user1", entry1)
            
            # User 2 settings
            setting2 = Setting(
                setting_type_id=f"user.setting{i}",
                setting_value=f"other_value{i}",
                related_entity_id="user2",
                created_user_id="user2",
                updated_user_id="user2"
            )
            user2_settings.append(setting2)
            entry2 = SettingsCacheEntry(setting2)
            cache.set(f"user.setting{i}", "user2", entry2)
        
        # Test listing for user1
        user1_results = cache.list_settings_for_entity("user1")
        assert len(user1_results) == 2
        assert all(s.related_entity_id == "user1" for s in user1_results)
        
        # Test listing for user2
        user2_results = cache.list_settings_for_entity("user2")
        assert len(user2_results) == 2
        assert all(s.related_entity_id == "user2" for s in user2_results)
        
        # Test listing for non-existent entity
        empty_results = cache.list_settings_for_entity("user3")
        assert len(empty_results) == 0

    def test_cache_list_settings_excludes_deleted(self) -> None:
        """Test that list_settings_for_entity excludes deleted entries."""
        cache = SettingsCache()
        
        # Add normal setting
        setting1 = Setting(
            setting_type_id="user.setting1",
            setting_value="value1",
            related_entity_id="user1",
            created_user_id="user1",
            updated_user_id="user1"
        )
        entry1 = SettingsCacheEntry(setting1)
        cache.set("user.setting1", "user1", entry1)
        
        # Add deleted setting
        setting2 = Setting(
            setting_type_id="user.setting2",
            setting_value="value2",
            related_entity_id="user1",
            created_user_id="user1",
            updated_user_id="user1"
        )
        entry2 = SettingsCacheEntry(setting2)
        entry2.mark_deleted()
        cache.set("user.setting2", "user1", entry2)
        
        results = cache.list_settings_for_entity("user1")
        
        assert len(results) == 1
        assert results[0].setting_type_id == "user.setting1"

    def test_cache_setting_types(self) -> None:
        """Test setting type caching."""
        cache = SettingsCache()
        
        setting_type = SettingType(
            setting_type_id="user.theme",
            setting_type_name="User Theme",
            description="User's theme preference",
            related_entity_type="user",
            data_type="string",
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        # Set and get setting type
        cache.set_setting_type("user.theme", setting_type)
        retrieved = cache.get_setting_type("user.theme")
        
        assert retrieved is not None
        assert retrieved == setting_type
        assert "user.theme" in cache.dirty_setting_types

    def test_cache_setting_type_dirty_tracking(self) -> None:
        """Test setting type dirty flag tracking."""
        cache = SettingsCache()
        
        setting_type = SettingType(
            setting_type_id="user.theme",
            setting_type_name="User Theme",
            description="User's theme preference",
            related_entity_type="user",
            data_type="string",
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        cache.set_setting_type("user.theme", setting_type)
        assert "user.theme" in cache.dirty_setting_types
        
        # Clear dirty flags
        cache.clear_setting_type_dirty_flags()
        assert len(cache.dirty_setting_types) == 0
        
        # Modify and mark dirty again
        cache.mark_setting_type_dirty("user.theme")
        assert "user.theme" in cache.dirty_setting_types

    def test_cache_get_dirty_setting_types(self) -> None:
        """Test getting list of dirty setting types."""
        cache = SettingsCache()
        
        # Add multiple setting types
        for i in range(3):
            setting_type = SettingType(
                setting_type_id=f"user.type{i}",
                setting_type_name=f"Type {i}",
                description=f"Description {i}",
                related_entity_type="user",
                data_type="string",
                created_user_id="admin",
                updated_user_id="admin"
            )
            cache.set_setting_type(f"user.type{i}", setting_type)
        
        # Mark one as clean
        cache.dirty_setting_types.discard("user.type1")
        
        dirty_types = cache.get_dirty_setting_types()
        
        assert len(dirty_types) == 2
        assert all(isinstance(st, SettingType) for st in dirty_types)
        assert "user.type0" in [st.setting_type_id for st in dirty_types]
        assert "user.type2" in [st.setting_type_id for st in dirty_types]

    def test_cache_list_setting_types_by_entity_type(self) -> None:
        """Test listing setting types filtered by entity type."""
        cache = SettingsCache()
        
        # Add setting types for different entity types
        user_type = SettingType(
            setting_type_id="user.theme",
            setting_type_name="User Theme",
            description="User theme",
            related_entity_type="user",
            data_type="string",
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        system_type = SettingType(
            setting_type_id="system.config",
            setting_type_name="System Config",
            description="System configuration",
            related_entity_type="system",
            data_type="string",
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        cache.set_setting_type("user.theme", user_type)
        cache.set_setting_type("system.config", system_type)
        
        # Test filtering by entity type
        user_types = cache.list_setting_types_by_entity_type("user")
        assert len(user_types) == 1
        assert user_types[0].related_entity_type == "user"
        
        system_types = cache.list_setting_types_by_entity_type("system")
        assert len(system_types) == 1
        assert system_types[0].related_entity_type == "system"
        
        # Test non-existent entity type
        empty_types = cache.list_setting_types_by_entity_type("organization")
        assert len(empty_types) == 0

    def test_cache_clear(self) -> None:
        """Test clearing all cache data."""
        cache = SettingsCache()
        
        # Add some data
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id="user123",
            created_user_id="user1",
            updated_user_id="user1"
        )
        
        setting_type = SettingType(
            setting_type_id="user.theme",
            setting_type_name="User Theme",
            description="User theme",
            related_entity_type="user",
            data_type="string",
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        entry = SettingsCacheEntry(setting)
        cache.set("user.theme", "user123", entry)
        cache.set_setting_type("user.theme", setting_type)
        
        # Verify data exists
        assert len(cache.entries) > 0
        assert len(cache.setting_types) > 0
        assert len(cache.dirty_entries) > 0
        assert len(cache.dirty_setting_types) > 0
        
        # Clear cache
        cache.clear()
        
        # Verify everything is cleared
        assert len(cache.entries) == 0
        assert len(cache.setting_types) == 0
        assert len(cache.dirty_entries) == 0
        assert len(cache.dirty_setting_types) == 0

    def test_cache_concurrent_access(self) -> None:
        """Test cache behavior with concurrent access simulation."""
        import threading
        cache = SettingsCache()
        results = []
        
        def add_setting(thread_id):
            try:
                setting = Setting(
                    setting_type_id=f"user.setting{thread_id}",
                    setting_value=f"value{thread_id}",
                    related_entity_id="user123",
                    created_user_id="user1",
                    updated_user_id="user1"
                )
                entry = SettingsCacheEntry(setting)
                cache.set(f"user.setting{thread_id}", "user123", entry)
                results.append(True)
            except Exception:
                results.append(False)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=add_setting, args=[i])
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should succeed
        assert all(results)
        assert len(cache.entries) == 10
        assert len(cache.dirty_entries) == 10
