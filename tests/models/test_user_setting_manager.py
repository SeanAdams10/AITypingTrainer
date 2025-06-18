"""
Unit tests for models.user_setting_manager.UserSettingsManager.
Covers CRUD, validation (including DB uniqueness), and error handling.
"""

import uuid

import pytest
from pydantic import ValidationError

from db.database_manager import DatabaseManager
from models.user_setting import UserSetting
from models.user_setting_manager import (
    UserSettingsManager,
    UserSettingNotFound,
    UserSettingValidationError,
)


@pytest.fixture(scope="function")
def user_settings_mgr(db_with_tables: DatabaseManager) -> UserSettingsManager:
    """
    Fixture: Provides a UserSettingsManager with a fresh, initialized database.
    """
    return UserSettingsManager(db_with_tables)


class TestUserSettingsManager:
    """Test suite for UserSettingsManager covering all CRUD and validation logic."""

    def test_create_user_setting_valid(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Create user settings with valid data and verify persistence.
        """
        # Test string setting
        setting_str = UserSetting(
            user_id="user123",
            setting_key="theme",
            setting_value="dark",
            value_type="str"
        )
        assert user_settings_mgr.save_user_setting(setting_str)
        assert setting_str.setting_key == "theme"
        assert isinstance(setting_str.user_setting_id, str)
        
        # Verify it's in the DB
        retrieved_setting = user_settings_mgr.get_user_setting_by_key("user123", "theme")
        assert retrieved_setting.setting_value == "dark"
        assert retrieved_setting.value_type == "str"
        
        # Test integer setting
        setting_int = UserSetting(
            user_id="user123",
            setting_key="font_size",
            setting_value=14,
            value_type="int"
        )
        assert user_settings_mgr.save_user_setting(setting_int)
        retrieved_int = user_settings_mgr.get_user_setting_by_key("user123", "font_size")
        assert retrieved_int.setting_value == 14
        assert retrieved_int.value_type == "int"
        
        # Test float setting
        setting_float = UserSetting(
            user_id="user123",
            setting_key="opacity",
            setting_value=0.75,
            value_type="float"
        )
        assert user_settings_mgr.save_user_setting(setting_float)
        retrieved_float = user_settings_mgr.get_user_setting_by_key("user123", "opacity")
        assert retrieved_float.setting_value == 0.75
        assert retrieved_float.value_type == "float"

    @pytest.mark.parametrize(
        "key, expected_error_part",
        [
            ("", "blank"),
            ("  ", "blank"),
            ("A" * 65, "at most 64 characters"),
        ],
    )
    def test_create_user_setting_invalid_format(
        self, user_settings_mgr: UserSettingsManager, key: str, expected_error_part: str
    ) -> None:
        """
        Test objective: Attempt to create a user setting with an invalid key format.
        """
        with pytest.raises((ValueError, UserSettingValidationError)) as e:
            setting = UserSetting(
                user_id="user123",
                setting_key=key,
                setting_value="value",
                value_type="str"
            )
            user_settings_mgr.save_user_setting(setting)
        assert expected_error_part.lower() in str(e.value).lower()

    def test_create_user_setting_duplicate_key(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Attempt to create a user setting with a duplicate key for the same user.
        """
        setting1 = UserSetting(
            user_id="user123",
            setting_key="unique_key",
            setting_value="value1",
            value_type="str"
        )
        user_settings_mgr.save_user_setting(setting1)
        setting2 = UserSetting(
            user_id="user123",
            setting_key="unique_key",
            setting_value="value2",
            value_type="str"
        )
        with pytest.raises(UserSettingValidationError) as e:
            user_settings_mgr.save_user_setting(setting2)
        assert "unique" in str(e.value).lower()

    def test_create_setting_same_key_different_users(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Create settings with the same key but for different users (should succeed).
        """
        setting1 = UserSetting(
            user_id="user123",
            setting_key="theme",
            setting_value="dark",
            value_type="str"
        )
        user_settings_mgr.save_user_setting(setting1)
        
        setting2 = UserSetting(
            user_id="user456",
            setting_key="theme",
            setting_value="light",
            value_type="str"
        )
        # This should not raise, as the key is for a different user
        user_settings_mgr.save_user_setting(setting2)
        
        # Verify both settings exist with different values
        setting1_retrieved = user_settings_mgr.get_user_setting_by_key("user123", "theme")
        setting2_retrieved = user_settings_mgr.get_user_setting_by_key("user456", "theme")
        assert setting1_retrieved.setting_value == "dark"
        assert setting2_retrieved.setting_value == "light"

    def test_get_user_setting_by_key(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Retrieve a user setting by user ID and key.
        """
        setting = UserSetting(
            user_id="user123",
            setting_key="test_setting",
            setting_value="test_value",
            value_type="str"
        )
        user_settings_mgr.save_user_setting(setting)
        retrieved_setting = user_settings_mgr.get_user_setting_by_key("user123", "test_setting")
        assert retrieved_setting is not None
        assert retrieved_setting.user_setting_id == setting.user_setting_id
        assert retrieved_setting.setting_value == "test_value"

    def test_get_user_setting_by_key_not_found(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Attempt to retrieve a non-existent user setting by key.
        """
        with pytest.raises(UserSettingNotFound):
            user_settings_mgr.get_user_setting_by_key("user123", "nonexistent_key")

    def test_get_all_user_settings_empty(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: List user settings when none exist for a user.
        """
        settings = user_settings_mgr.get_all_user_settings("user123")
        assert len(settings) == 0

    def test_get_all_user_settings_populated(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: List user settings when multiple exist, ensuring order.
        """
        # Create multiple settings for the same user
        user_id = "user456"
        keys = ["zebra", "apple", "banana"]
        for i, key in enumerate(keys):
            setting = UserSetting(
                user_id=user_id,
                setting_key=key,
                setting_value=f"value{i}",
                value_type="str"
            )
            user_settings_mgr.save_user_setting(setting)
        
        # Create a setting for a different user (should not be returned)
        other_setting = UserSetting(
            user_id="different_user",
            setting_key="other_key",
            setting_value="other_value",
            value_type="str"
        )
        user_settings_mgr.save_user_setting(other_setting)
        
        # Get all settings for the first user
        settings = user_settings_mgr.get_all_user_settings(user_id)
        assert len(settings) == 3
        # Check if sorted by key
        retrieved_keys = [s.setting_key for s in settings]
        assert retrieved_keys == sorted(retrieved_keys)

    def test_update_user_setting_valid(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Update a user setting successfully using save_user_setting.
        """
        # Create initial setting
        setting = UserSetting(
            user_id="user123",
            setting_key="update_test",
            setting_value="original",
            value_type="str"
        )
        user_settings_mgr.save_user_setting(setting)
        
        # Update the setting value
        setting.setting_value = "updated"
        assert user_settings_mgr.save_user_setting(setting)
        
        # Verify the update in DB
        retrieved_setting = user_settings_mgr.get_user_setting_by_key("user123", "update_test")
        assert retrieved_setting.setting_value == "updated"
        assert retrieved_setting.user_setting_id == setting.user_setting_id

    def test_update_setting_change_type(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Update a user setting's value type.
        """
        # Create initial setting with string value
        setting = UserSetting(
            user_id="user123",
            setting_key="type_change",
            setting_value="42",
            value_type="str"
        )
        user_settings_mgr.save_user_setting(setting)
        
        # Get the saved setting to have the correct ID
        saved_setting = user_settings_mgr.get_user_setting_by_key("user123", "type_change")
        
        # Create a new setting with the same ID but updated type and value
        updated_setting = UserSetting(
            user_setting_id=saved_setting.user_setting_id,
            user_id="user123",
            setting_key="type_change",
            setting_value=42,
            value_type="int"
        )
        
        # Save the updated setting
        assert user_settings_mgr.save_user_setting(updated_setting)
        
        # Verify the type change in DB
        retrieved_setting = user_settings_mgr.get_user_setting_by_key("user123", "type_change")
        assert retrieved_setting.setting_value == 42
        assert isinstance(retrieved_setting.setting_value, int)
        assert retrieved_setting.value_type == "int"

    def test_delete_user_setting(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Delete an existing user setting.
        """
        setting = UserSetting(
            user_id="user123",
            setting_key="to_delete",
            setting_value="delete_me",
            value_type="str"
        )
        user_settings_mgr.save_user_setting(setting)
        assert user_settings_mgr.delete_user_setting("user123", "to_delete") is True
        with pytest.raises(UserSettingNotFound):
            user_settings_mgr.get_user_setting_by_key("user123", "to_delete")

    def test_delete_nonexistent_user_setting(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Attempt to delete a non-existent user setting.
        """
        assert user_settings_mgr.delete_user_setting("user123", "nonexistent") is False

    def test_delete_all_settings_for_user(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Delete all settings for a specific user and verify the action.
        """
        # Create settings for two different users
        for i in range(3):
            setting1 = UserSetting(
                user_id="user_to_clear",
                setting_key=f"key{i}",
                setting_value=f"value{i}",
                value_type="str"
            )
            user_settings_mgr.save_user_setting(setting1)
            
            setting2 = UserSetting(
                user_id="user_to_keep",
                setting_key=f"key{i}",
                setting_value=f"value{i}",
                value_type="str"
            )
            user_settings_mgr.save_user_setting(setting2)
        
        # Delete all settings for the first user
        assert user_settings_mgr.delete_all_settings_for_user("user_to_clear") is True
        
        # Verify first user's settings are gone
        assert len(user_settings_mgr.get_all_user_settings("user_to_clear")) == 0
        
        # Verify second user's settings remain
        assert len(user_settings_mgr.get_all_user_settings("user_to_keep")) == 3
        
        # Deleting again should return False (already empty)
        assert user_settings_mgr.delete_all_settings_for_user("user_to_clear") is False

    def test_value_type_conversion(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Verify correct value type conversion when saving and retrieving settings.
        """
        # Test int conversion
        int_setting = UserSetting(
            user_id="user123",
            setting_key="int_setting",
            setting_value=42,
            value_type="int"
        )
        user_settings_mgr.save_user_setting(int_setting)
        retrieved_int = user_settings_mgr.get_user_setting_by_key("user123", "int_setting")
        assert retrieved_int.setting_value == 42
        assert isinstance(retrieved_int.setting_value, int)
        
        # Test float conversion
        float_setting = UserSetting(
            user_id="user123",
            setting_key="float_setting",
            setting_value=3.14159,
            value_type="float"
        )
        user_settings_mgr.save_user_setting(float_setting)
        retrieved_float = user_settings_mgr.get_user_setting_by_key("user123", "float_setting")
        assert retrieved_float.setting_value == 3.14159
        assert isinstance(retrieved_float.setting_value, float)
        
        # Test string conversion
        str_setting = UserSetting(
            user_id="user123",
            setting_key="str_setting",
            setting_value="string value",
            value_type="str"
        )
        user_settings_mgr.save_user_setting(str_setting)
        retrieved_str = user_settings_mgr.get_user_setting_by_key("user123", "str_setting")
        assert retrieved_str.setting_value == "string value"
        assert isinstance(retrieved_str.setting_value, str)

    def test_user_setting_validation_mismatch(self, user_settings_mgr: UserSettingsManager) -> None:
        """
        Test objective: Test validation for mismatched value types.
        """
        with pytest.raises(ValidationError) as e:
            setting = UserSetting(
                user_id="user123",
                setting_key="mismatch",
                setting_value="not_an_int",
                value_type="int"
            )
            user_settings_mgr.save_user_setting(setting)
        assert "setting_value must be an integer" in str(e.value)


if __name__ == "__main__":
    pytest.main([__file__])
