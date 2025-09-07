"""Comprehensive unit tests for the SettingsManager singleton.

Tests the SettingsManager class including singleton behavior, caching,
bulk persistence, and all CRUD operations as specified in Settings.md.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import call

import pytest

from models.setting import Setting, SettingNotFound, SettingValidationError
from models.setting_type import SettingType, SettingTypeNotFound, SettingTypeValidationError
from models.settings_manager import SettingsManager
from tests.fixtures.settings_fixtures import (
    mock_db_manager, sample_setting_types, sample_settings,
    initialized_settings_manager, user_id, admin_user_id, system_user_id,
    test_entity_ids, settings_test_helper, data_type_test_case, validation_test_cases
)


class TestSettingsManagerSingleton:
    """Test singleton behavior of SettingsManager."""

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        SettingsManager.reset_instance()

    def test_singleton_instance_creation(self) -> None:
        """Test that SettingsManager maintains singleton pattern."""
        manager1 = SettingsManager.get_instance()
        manager2 = SettingsManager.get_instance()
        
        assert manager1 is manager2
        assert isinstance(manager1, SettingsManager)

    def test_direct_constructor_raises_error(self) -> None:
        """Test that direct constructor usage raises error after singleton is created."""
        # First instance via get_instance() should work
        manager1 = SettingsManager.get_instance()
        
        # Direct constructor should now raise error
        with pytest.raises(RuntimeError, match="Use get_instance"):
            SettingsManager()

    def test_singleton_thread_safety(self) -> None:
        """Test singleton is thread-safe."""
        import threading
        instances = []
        
        def create_instance():
            instances.append(SettingsManager.get_instance())
        
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All instances should be the same
        assert len(set(id(instance) for instance in instances)) == 1

    def test_reset_instance(self) -> None:
        """Test that reset_instance properly clears singleton."""
        manager1 = SettingsManager.get_instance()
        SettingsManager.reset_instance()
        manager2 = SettingsManager.get_instance()
        
        assert manager1 is not manager2


class TestSettingsManagerInitialization:
    """Test SettingsManager initialization and data loading."""

    def test_initialize_with_database(self, mock_db_manager, sample_setting_types, sample_settings) -> None:
        """Test manager initialization loads data from database."""
        SettingsManager.reset_instance()
        
        # Setup mock responses
        setting_type_rows = [
            {
                'setting_type_id': st.setting_type_id,
                'setting_type_name': st.setting_type_name,
                'description': st.description,
                'related_entity_type': st.related_entity_type,
                'data_type': st.data_type,
                'default_value': st.default_value,
                'validation_rules': st.validation_rules,
                'is_system': st.is_system,
                'is_active': st.is_active,
                'created_user_id': st.created_user_id,
                'updated_user_id': st.updated_user_id,
                'created_at': st.created_at.isoformat(),
                'updated_at': st.updated_at.isoformat(),
                'row_checksum': st.row_checksum
            } for st in sample_setting_types
        ]
        
        setting_rows = [
            {
                'setting_id': s.setting_id,
                'setting_type_id': s.setting_type_id,
                'setting_value': s.setting_value,
                'related_entity_id': s.related_entity_id,
                'created_user_id': s.created_user_id,
                'updated_user_id': s.updated_user_id,
                'created_at': s.created_at.isoformat(),
                'updated_at': s.updated_at.isoformat(),
                'row_checksum': s.row_checksum
            } for s in sample_settings
        ]
        
        def mock_fetchall(query, params=None):
            if "setting_types" in query:
                return setting_type_rows
            elif "settings" in query:
                return setting_rows
            return []
        
        mock_db_manager.fetchall.side_effect = mock_fetchall
        
        manager = SettingsManager.get_instance()
        manager.initialize(mock_db_manager)
        
        # Verify data was loaded
        assert len(manager.cache.setting_types) == len(sample_setting_types)
        assert len(manager.cache.entries) == len(sample_settings)
        
        # Verify specific data
        assert "user.theme" in manager.cache.setting_types
        assert manager.cache.setting_types["user.theme"].setting_type_name == "User Theme"

    def test_initialize_only_once(self, mock_db_manager) -> None:
        """Test that initialization only happens once."""
        SettingsManager.reset_instance()
        manager = SettingsManager.get_instance()
        
        manager.initialize(mock_db_manager)
        manager.initialize(mock_db_manager)  # Should not reload
        
        # fetchall should only be called twice (once for setting_types, once for settings)
        assert mock_db_manager.fetchall.call_count == 2


class TestSettingsManagerCRUD:
    """Test CRUD operations for settings."""

    def test_get_setting_existing(self, initialized_settings_manager, ) -> None:
        """Test retrieving existing setting."""
        manager = initialized_settings_manager
        
        # Assuming sample data has user.theme setting
        value = manager.get_setting("user.theme", user_id)
        assert value == "dark"

    def test_get_setting_with_default(self, ) -> None:
        """Test retrieving setting with default value."""
        manager = initialized_settings_manager
        
        # Non-existent setting should return default
        value = manager.get_setting("user.theme", "non-existent-user", default_value="light")
        assert value == "light"

    def test_get_setting_from_setting_type_default(self, ) -> None:
        """Test retrieving default from setting type when setting doesn't exist."""
        manager = initialized_settings_manager
        
        # Should return setting type's default value
        value = manager.get_setting("user.language", "new-user")
        assert value == "en"  # Default from setting type

    def test_get_setting_not_found(self, ) -> None:
        """Test exception when setting not found and no default."""
        manager = initialized_settings_manager
        
        with pytest.raises(SettingNotFound):
            manager.get_setting("non.existent", "user123")

    def test_set_setting_new(self, initialized_settings_manager, admin_) -> None:
        """Test creating new setting."""
        manager = initialized_settings_manager
        
        manager.set_setting("user.language", user_id, "es", admin_user_id)
        
        # Verify setting was cached
        value = manager.get_setting("user.language", user_id)
        assert value == "es"
        
        # Verify it's marked as dirty
        assert manager.has_dirty_settings()

    def test_set_setting_update_existing(self, initialized_settings_manager, admin_) -> None:
        """Test updating existing setting."""
        manager = initialized_settings_manager
        
        # First set a value
        manager.set_setting("user.theme", user_id, "light", admin_user_id)
        
        # Verify updated
        value = manager.get_setting("user.theme", user_id)
        assert value == "light"

    def test_set_setting_no_op_detection(self, initialized_settings_manager, admin_) -> None:
        """Test that setting same value is detected as no-op."""
        manager = initialized_settings_manager
        
        # Set initial value
        manager.set_setting("user.theme", user_id, "dark", admin_user_id)
        manager.cache.clear_dirty_flags()  # Clear dirty state
        
        # Set same value again
        manager.set_setting("user.theme", user_id, "dark", admin_user_id)
        
        # Should not be dirty (no-op detected)
        assert not manager.has_dirty_settings()

    def test_set_setting_invalid_type(self, initialized_settings_manager, admin_) -> None:
        """Test setting with invalid setting type."""
        manager = initialized_settings_manager
        
        with pytest.raises(SettingTypeNotFound):
            manager.set_setting("invalid.type", user_id, "value", admin_user_id)

    def test_set_setting_invalid_value(self, initialized_settings_manager, admin_) -> None:
        """Test setting with invalid value for setting type."""
        manager = initialized_settings_manager
        
        # Assuming user.theme has enum validation
        with pytest.raises(SettingValidationError):
            manager.set_setting("user.theme", user_id, "invalid_theme", admin_user_id)

    def test_delete_setting(self, initialized_settings_manager, admin_) -> None:
        """Test deleting setting."""
        manager = initialized_settings_manager
        
        # First create a setting
        manager.set_setting("user.theme", user_id, "dark", admin_user_id)
        
        # Then delete it
        manager.delete_setting("user.theme", user_id, admin_user_id)
        
        # Should be marked as deleted and dirty
        assert manager.has_dirty_settings()
        
        # Should raise exception when trying to get
        with pytest.raises(SettingNotFound):
            manager.get_setting("user.theme", user_id)

    def test_delete_setting_not_found(self, initialized_settings_manager, admin_) -> None:
        """Test deleting non-existent setting."""
        manager = initialized_settings_manager
        
        with pytest.raises(SettingNotFound):
            manager.delete_setting("non.existent", user_id, admin_user_id)

    def test_list_settings_for_entity(self, initialized_settings_manager, ) -> None:
        """Test listing all settings for an entity."""
        manager = initialized_settings_manager
        
        settings = manager.list_settings(user_id)
        
        # Should return list of Setting objects
        assert isinstance(settings, list)
        assert all(isinstance(s, Setting) for s in settings)
        assert all(s.related_entity_id == user_id for s in settings)


class TestSettingsManagerSettingTypes:
    """Test CRUD operations for setting types."""

    def test_get_setting_type_existing(self, ) -> None:
        """Test retrieving existing setting type."""
        manager = initialized_settings_manager
        
        setting_type = manager.get_setting_type("user.theme")
        assert setting_type.setting_type_id == "user.theme"
        assert setting_type.setting_type_name == "User Theme"

    def test_get_setting_type_not_found(self, ) -> None:
        """Test exception when setting type not found."""
        manager = initialized_settings_manager
        
        with pytest.raises(SettingTypeNotFound):
            manager.get_setting_type("non.existent")

    def test_create_setting_type(self, initialized_settings_manager, settings_test_helper, admin_) -> None:
        """Test creating new setting type."""
        manager = initialized_settings_manager
        
        new_type = settings_test_helper.create_test_setting_type(
            "user.custom",
            data_type="string",
            created_user_id=admin_user_id,
            updated_user_id=admin_user_id
        )
        
        result = manager.create_setting_type(new_type)
        assert result is True
        
        # Verify it was added
        retrieved = manager.get_setting_type("user.custom")
        assert retrieved.setting_type_id == "user.custom"

    def test_create_setting_type_duplicate(self, initialized_settings_manager, ) -> None:
        """Test creating duplicate setting type raises error."""
        manager = initialized_settings_manager
        
        # Try to create existing setting type
        existing_type = settings_test_helper.create_test_setting_type("user.theme")
        
        with pytest.raises(SettingTypeValidationError):
            manager.create_setting_type(existing_type)

    def test_update_setting_type(self, initialized_settings_manager, admin_) -> None:
        """Test updating existing setting type."""
        manager = initialized_settings_manager
        
        # Get existing setting type
        setting_type = manager.get_setting_type("user.theme")
        
        # Modify it
        setting_type.description = "Updated description"
        setting_type.updated_user_id = admin_user_id
        setting_type.row_checksum = setting_type.calculate_checksum()
        
        result = manager.update_setting_type(setting_type)
        assert result is True
        
        # Verify update
        updated = manager.get_setting_type("user.theme")
        assert updated.description == "Updated description"

    def test_update_setting_type_not_found(self, initialized_settings_manager, ) -> None:
        """Test updating non-existent setting type."""
        manager = initialized_settings_manager
        
        non_existent = settings_test_helper.create_test_setting_type("non.existent")
        
        with pytest.raises(SettingTypeNotFound):
            manager.update_setting_type(non_existent)

    def test_update_system_setting_type_forbidden(self, initialized_settings_manager, admin_) -> None:
        """Test updating system setting type is forbidden."""
        manager = initialized_settings_manager
        
        # Get system setting type
        system_type = manager.get_setting_type("system.max_session_duration")
        system_type.description = "Modified description"
        
        with pytest.raises(SettingTypeValidationError):
            manager.update_setting_type(system_type)

    def test_update_setting_type_no_op(self, ) -> None:
        """Test updating setting type with no changes."""
        manager = initialized_settings_manager
        
        setting_type = manager.get_setting_type("user.theme")
        original_checksum = setting_type.row_checksum
        
        # No actual changes
        result = manager.update_setting_type(setting_type)
        assert result is True
        
        # Should detect no-op
        assert not manager.has_dirty_setting_types()

    def test_delete_setting_type(self, initialized_settings_manager, settings_test_helper, admin_) -> None:
        """Test soft deleting setting type."""
        manager = initialized_settings_manager
        
        # Create a setting type with no references
        new_type = settings_test_helper.create_test_setting_type(
            "user.deletable",
            created_user_id=admin_user_id,
            updated_user_id=admin_user_id
        )
        manager.create_setting_type(new_type)
        
        # Delete it
        result = manager.delete_setting_type("user.deletable", admin_user_id)
        assert result is True
        
        # Should be marked inactive
        setting_type = manager.get_setting_type("user.deletable")
        assert not setting_type.is_active

    def test_delete_system_setting_type_forbidden(self, initialized_settings_manager, admin_) -> None:
        """Test deleting system setting type is forbidden."""
        manager = initialized_settings_manager
        
        with pytest.raises(SettingTypeValidationError):
            manager.delete_setting_type("system.max_session_duration", admin_user_id)

    def test_delete_setting_type_with_references(self, initialized_settings_manager, admin_) -> None:
        """Test deleting setting type with existing settings fails."""
        manager = initialized_settings_manager
        
        # user.theme has settings referencing it
        with pytest.raises(SettingTypeValidationError):
            manager.delete_setting_type("user.theme", admin_user_id)

    def test_list_setting_types(self, ) -> None:
        """Test listing all active setting types."""
        manager = initialized_settings_manager
        
        setting_types = manager.list_setting_types()
        
        assert isinstance(setting_types, list)
        assert all(isinstance(st, SettingType) for st in setting_types)
        assert all(st.is_active for st in setting_types)

    def test_list_setting_types_by_entity_type(self, ) -> None:
        """Test listing setting types filtered by entity type."""
        manager = initialized_settings_manager
        
        user_types = manager.list_setting_types("user")
        system_types = manager.list_setting_types("system")
        
        assert all(st.related_entity_type == "user" for st in user_types)
        assert all(st.related_entity_type == "system" for st in system_types)


class TestSettingsManagerPersistence:
    """Test bulk persistence and caching behavior."""

    def test_save_dirty_settings(self, initialized_settings_manager, admin_) -> None:
        """Test saving dirty settings to database."""
        manager = initialized_settings_manager
        
        # Make some changes
        manager.set_setting("user.theme", user_id, "light", admin_user_id)
        manager.set_setting("user.language", user_id, "es", admin_user_id)
        
        assert manager.has_dirty_settings()
        
        # Save changes
        result = manager.save()
        assert result is True
        
        # Should no longer be dirty
        assert not manager.has_dirty_settings()
        
        # Verify database calls were made
        manager.db_manager.execute_many.assert_called()

    def test_save_no_dirty_data(self, ) -> None:
        """Test save with no dirty data."""
        manager = initialized_settings_manager
        
        result = manager.save()
        assert result is True
        
        # No database calls should be made
        manager.db_manager.execute_many.assert_not_called()

    def test_flush_vs_save_equivalence(self, initialized_settings_manager, admin_) -> None:
        """Test that flush() and save() are equivalent."""
        manager = initialized_settings_manager
        
        # Make changes and save
        manager.set_setting("user.theme", user_id, "light", admin_user_id)
        save_result = manager.save()
        
        # Make changes and flush
        manager.set_setting("user.language", user_id, "es", admin_user_id)
        flush_result = manager.flush()
        
        assert save_result == flush_result

    def test_persistence_error_preserves_dirty_flags(self, initialized_settings_manager, admin_) -> None:
        """Test that persistence errors preserve dirty flags for retry."""
        manager = initialized_settings_manager
        
        # Make database fail
        manager.db_manager.execute_many.side_effect = Exception("Database error")
        
        manager.set_setting("user.theme", user_id, "light", admin_user_id)
        
        result = manager.save()
        assert result is False
        
        # Should still be dirty for retry
        assert manager.has_dirty_settings()

    def test_clear_cache(self, ) -> None:
        """Test clearing cache data."""
        manager = initialized_settings_manager
        
        # Verify cache has data
        assert len(manager.cache.setting_types) > 0
        assert len(manager.cache.entries) > 0
        
        manager.clear_cache()
        
        # Cache should be empty
        assert len(manager.cache.setting_types) == 0
        assert len(manager.cache.entries) == 0
        assert not manager._initialized


class TestSettingsManagerValidation:
    """Test validation using different data types and rules."""

    def test_string_enum_validation(self, initialized_settings_manager, admin_) -> None:
        """Test string enum validation."""
        manager = initialized_settings_manager
        
        # Valid enum value should work
        manager.set_setting("user.theme", user_id, "dark", admin_user_id)
        value = manager.get_setting("user.theme", user_id)
        assert value == "dark"
        
        # Invalid enum value should fail
        with pytest.raises(SettingValidationError):
            manager.set_setting("user.theme", user_id, "invalid_theme", admin_user_id)

    def test_integer_validation(self, initialized_settings_manager, admin_) -> None:
        """Test integer validation with range."""
        manager = initialized_settings_manager
        
        # Valid integer should work
        manager.set_setting("system.max_session_duration", "system", "720", admin_user_id)
        value = manager.get_setting("system.max_session_duration", "system")
        assert value == "720"

    def test_boolean_validation(self, initialized_settings_manager, admin_) -> None:
        """Test boolean validation."""
        manager = initialized_settings_manager
        
        # Valid boolean values
        for bool_val in ["true", "false"]:
            manager.set_setting("user.notification_email", user_id, bool_val, admin_user_id)
            value = manager.get_setting("user.notification_email", user_id)
            assert value == bool_val

    def test_number_validation(self, initialized_settings_manager, admin_) -> None:
        """Test number validation."""
        manager = initialized_settings_manager
        
        # Valid number should work
        manager.set_setting("user.typing_speed_goal", user_id, "75.5", admin_user_id)
        value = manager.get_setting("user.typing_speed_goal", user_id)
        assert value == "75.5"


class TestSettingsManagerEdgeCases:
    """Test edge cases and error scenarios."""

    def test_manager_without_initialization(self) -> None:
        """Test manager behavior before initialization."""
        SettingsManager.reset_instance()
        manager = SettingsManager.get_instance()
        
        # Should handle gracefully
        value = manager.get_setting("user.theme", "user123", default_value="default")
        assert value == "default"

    def test_concurrent_access(self, initialized_settings_manager, admin_) -> None:
        """Test concurrent access to settings manager."""
        import threading
        
        manager = initialized_settings_manager
        results = []
        
        def set_setting(value):
            try:
                manager.set_setting("user.theme", user_id, value, admin_user_id)
                results.append(True)
            except Exception:
                results.append(False)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=set_setting, args=[f"theme_{i}"])
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should succeed (last one wins)
        assert all(results)
        assert manager.has_dirty_settings()

    def test_large_setting_value(self, initialized_settings_manager, admin_) -> None:
        """Test handling of large setting values."""
        manager = initialized_settings_manager
        
        # Large but reasonable value
        large_value = "x" * 1000
        manager.set_setting("user.theme", user_id, large_value, admin_user_id)
        
        retrieved = manager.get_setting("user.theme", user_id)
        assert retrieved == large_value

    @pytest.mark.parametrize(
        "setting_type_id,err_msg_part",
        [
            ("", "must be exactly 6 characters"),
            ("ABC", "must be exactly 6 characters"),
            ("ABCDEFG", "must be exactly 6 characters"),
            ("ABCD€Ω", "must be ASCII-only"),
        ],
    )
    def test_create_setting_invalid_format(
        self, setting_mgr: SettingsManager, setting_type_id: str, err_msg_part: str
    ) -> None:
        """Test objective: Attempt to create a setting with an invalid type_id format."""
        with pytest.raises((ValueError, SettingValidationError)) as e:
            setting = Setting(
                setting_type_id=setting_type_id,
                setting_value="test value",
                related_entity_id=str(uuid.uuid4()),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            setting_mgr.save_setting(setting)
        assert err_msg_part.lower() in str(e.value).lower()

    def test_update_existing_setting_with_new_value(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Verify that saving a setting with an existing type_id and entity_id updates

        the setting value and creates a new history entry.
        """
        setting_type_id = "UPDSET"
        related_entity_id = str(uuid.uuid4())
        initial_value = "initial value"
        updated_value = "updated value"

        # Create initial setting
        setting1 = Setting(
            setting_type_id=setting_type_id,
            setting_value=initial_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting1)
        original_setting_id = setting1.setting_id

        # Save a new setting with the same type_id and entity_id but different value
        setting2 = Setting(
            setting_type_id=setting_type_id,
            setting_value=updated_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting2)

        # Verify the setting was updated, not duplicated
        updated_setting = setting_mgr.get_setting(setting_type_id, related_entity_id)
        assert updated_setting.setting_value == updated_value
        assert updated_setting.setting_id == original_setting_id

        # Check history table for both entries
        history_rows = setting_mgr.db_manager.execute(
            """SELECT setting_id, setting_value FROM settings_history
            WHERE setting_type_id = ? ORDER BY updated_at
            """,
            (setting_type_id,),
        ).fetchall()

        # Should have two history entries with the same setting_id but different values
        assert len(history_rows) == 2
        assert history_rows[0][0] == original_setting_id
        assert history_rows[0][1] == initial_value
        assert history_rows[1][0] == original_setting_id
        assert history_rows[1][1] == updated_value

    def test_get_setting_by_type_and_entity(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Retrieve a setting by its type_id and related_entity_id."""
        setting_type_id = "GETSET"
        related_entity_id = str(uuid.uuid4())
        setting_value = "test retrieve"

        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value=setting_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        retrieved = setting_mgr.get_setting(setting_type_id, related_entity_id)
        assert retrieved is not None
        assert retrieved.setting_id == setting.setting_id
        assert retrieved.setting_type_id == setting_type_id
        assert retrieved.setting_value == setting_value
        assert retrieved.related_entity_id == related_entity_id

    def test_get_setting_with_default(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Test get_setting with a default value when setting doesn't exist."""
        setting_type_id = "DEFVAL"
        related_entity_id = str(uuid.uuid4())
        default_value = "default value"

        # Get with default - should return a new setting with the default value
        setting = setting_mgr.get_setting(setting_type_id, related_entity_id, default_value)
        assert setting.setting_type_id == setting_type_id
        assert setting.setting_value == default_value
        assert setting.related_entity_id == related_entity_id

        # Setting should not be saved to DB yet
        with pytest.raises(SettingNotFound):
            setting_mgr.get_setting(setting_type_id, related_entity_id)

        # Now save the setting
        setting_mgr.save_setting(setting)

        # Should be able to retrieve it now
        retrieved = setting_mgr.get_setting(setting_type_id, related_entity_id)
        assert retrieved.setting_value == default_value

    def test_get_setting_not_found(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Attempt to retrieve a non-existent setting."""
        with pytest.raises(SettingNotFound):
            setting_mgr.get_setting("NOTEXS", str(uuid.uuid4()))

    def test_list_settings_empty(self, setting_mgr: SettingsManager) -> None:
        """Test objective: List settings for an entity when none exist."""
        settings = setting_mgr.list_settings(str(uuid.uuid4()))
        assert len(settings) == 0

    def test_list_settings_populated(self, setting_mgr: SettingsManager) -> None:
        """Test objective: List settings for an entity with multiple settings."""
        related_entity_id = str(uuid.uuid4())

        # Create three settings for the same entity
        setting_types = ["TYPE01", "TYPE02", "TYPE03"]
        for type_id in setting_types:
            setting = Setting(
                setting_type_id=type_id,
                setting_value=f"value for {type_id}",
                related_entity_id=related_entity_id,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            setting_mgr.save_setting(setting)

        # List settings for the entity
        settings = setting_mgr.list_settings(related_entity_id)
        assert len(settings) == 3

        # Verify type_ids
        type_ids = [s.setting_type_id for s in settings]
        assert sorted(type_ids) == sorted(setting_types)

    def test_update_setting_value(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Update a setting's value using save_setting."""
        setting_type_id = "UPDATE"
        related_entity_id = str(uuid.uuid4())
        original_value = "original"
        new_value = "updated"

        # Create initial setting
        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value=original_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        # Change the value and save
        setting.setting_value = new_value
        assert setting_mgr.save_setting(setting)

        # Verify the update
        updated = setting_mgr.get_setting(setting_type_id, related_entity_id)
        assert updated.setting_value == new_value

    def test_history_tracking_on_create(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Verify history record is created when a setting is created."""
        setting_type_id = "HISCRE"
        related_entity_id = str(uuid.uuid4())
        setting_value = "history test create"

        # Create a setting
        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value=setting_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        # Check history table
        history_rows = setting_mgr.db_manager.execute(
            """SELECT setting_id, setting_type_id, setting_value
            FROM settings_history
            WHERE setting_type_id = ?""",
            (setting_type_id,),
        ).fetchall()

        assert len(history_rows) == 1
        assert history_rows[0][0] == setting.setting_id
        assert history_rows[0][1] == setting_type_id
        assert history_rows[0][2] == setting_value

    def test_history_tracking_on_update(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Verify history records are created when a setting is updated."""
        setting_type_id = "HISUPD"
        related_entity_id = str(uuid.uuid4())
        values = ["original", "update 1", "update 2"]

        # Create a setting
        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value=values[0],
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        # Update the setting twice
        for value in values[1:]:
            setting.setting_value = value
            setting_mgr.save_setting(setting)

        # Check history table
        history_rows = setting_mgr.db_manager.execute(
            """
            SELECT setting_value FROM settings_history
            WHERE setting_type_id = ?
            ORDER BY updated_at
            """,
            (setting_type_id,),
        ).fetchall()

        assert len(history_rows) == 3
        for i, row in enumerate(history_rows):
            assert row[0] == values[i]

    def test_history_tracking_on_delete(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Verify history record is created when a setting is deleted."""
        setting_type_id = "HISDEL"
        related_entity_id = str(uuid.uuid4())
        setting_value = "delete me"

        # Create a setting
        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value=setting_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        # Delete the setting
        setting_mgr.delete_setting(setting_type_id, related_entity_id)

        # Check history table - should have two entries
        history_rows = setting_mgr.db_manager.execute(
            "SELECT setting_value FROM settings_history WHERE setting_type_id = ?",
            (setting_type_id,),
        ).fetchall()

        assert len(history_rows) == 2
        assert history_rows[0][0] == setting_value  # Creation record
        assert history_rows[1][0] == setting_value  # Deletion record

    def test_delete_setting(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Delete an existing setting."""
        setting_type_id = "DELETE"
        related_entity_id = str(uuid.uuid4())

        # Create a setting
        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value="to delete",
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        # Delete the setting
        assert setting_mgr.delete_setting(setting_type_id, related_entity_id) is True

        # Verify it's gone
        with pytest.raises(SettingNotFound):
            setting_mgr.get_setting(setting_type_id, related_entity_id)

    def test_delete_nonexistent_setting(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Attempt to delete a non-existent setting."""
        assert setting_mgr.delete_setting("NOEXST", str(uuid.uuid4())) is False

    def test_delete_all_settings(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Delete all settings for an entity and verify the action."""
        related_entity_id = str(uuid.uuid4())

        # Create multiple settings for the entity
        for i, type_id in enumerate(["TYPE01", "TYPE02", "TYPE03"]):
            setting = Setting(
                setting_type_id=type_id,
                setting_value=f"value {i}",
                related_entity_id=related_entity_id,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            setting_mgr.save_setting(setting)

        # Check that all settings exist
        settings = setting_mgr.list_settings(related_entity_id)
        assert len(settings) == 3

        # Delete all settings for the entity
        assert setting_mgr.delete_all_settings(related_entity_id) is True

        # Verify all are gone
        settings = setting_mgr.list_settings(related_entity_id)
        assert len(settings) == 0

        # Verify history entries were created for each deletion
        history_rows = setting_mgr.db_manager.execute(
            "SELECT setting_type_id FROM settings_history WHERE related_entity_id = ?",
            (related_entity_id,),
        ).fetchall()

        # Should have 6 entries: 3 for creation and 3 for deletion
        assert len(history_rows) == 6

    def test_history_for_bulk_delete(self, setting_mgr: SettingsManager) -> None:
        """Test objective: Verify history tracking for bulk deletion of settings."""
        related_entity_id = str(uuid.uuid4())
        setting_types = ["BULK01", "BULK02", "BULK03"]

        # Create multiple settings
        for type_id in setting_types:
            setting = Setting(
                setting_type_id=type_id,
                setting_value=f"bulk value for {type_id}",
                related_entity_id=related_entity_id,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            setting_mgr.save_setting(setting)

        # Delete all settings for the entity
        setting_mgr.delete_all_settings(related_entity_id)

        # Check that settings are gone
        settings = setting_mgr.list_settings(related_entity_id)
        assert len(settings) == 0

        # Check for history entries
        for type_id in setting_types:
            history_rows = setting_mgr.db_manager.execute(
                """
                SELECT updated_at FROM settings_history
                WHERE setting_type_id = ? AND related_entity_id = ?
                ORDER BY updated_at
                """,
                (type_id, related_entity_id),
            ).fetchall()

            # Should have 2 entries per setting: creation and deletion
            assert len(history_rows) == 2

            # The timestamps should be different (creation vs deletion)
            assert history_rows[0][0] != history_rows[1][0]


if __name__ == "__main__":
    pytest.main([__file__])
