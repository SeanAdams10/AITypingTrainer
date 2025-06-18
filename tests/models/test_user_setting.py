"""
Unit tests for the UserSetting Pydantic model in models.user_setting.
Focuses on validation logic within the UserSetting model itself.
"""

# Standard library imports
import uuid

# Third-party imports
import pytest
from pydantic import ValidationError

# Local application imports
from models.user_setting import UserSetting
from models.user_setting_manager import UserSettingNotFound, UserSettingValidationError


class TestUserSettingModel:
    """Test cases for the UserSetting Pydantic model."""

    def test_user_setting_creation_valid(self) -> None:
        """Test objective: Create a UserSetting instance with valid data."""
        # String value
        setting_str = UserSetting(
            user_setting_id=str(uuid.uuid4()),
            user_id="user123",
            setting_key="theme",
            setting_value="dark",
            value_type="str"
        )
        assert isinstance(setting_str.user_setting_id, str)
        assert setting_str.user_id == "user123"
        assert setting_str.setting_key == "theme"
        assert setting_str.setting_value == "dark"
        assert setting_str.value_type == "str"

        # Integer value
        setting_int = UserSetting(
            user_setting_id=str(uuid.uuid4()),
            user_id="user123",
            setting_key="font_size",
            setting_value=14,
            value_type="int"
        )
        assert setting_int.setting_value == 14
        assert setting_int.value_type == "int"

        # Float value
        setting_float = UserSetting(
            user_setting_id=str(uuid.uuid4()),
            user_id="user123",
            setting_key="opacity",
            setting_value=0.75,
            value_type="float"
        )
        assert setting_float.setting_value == 0.75
        assert setting_float.value_type == "float"

        # Test key stripping
        setting_stripped = UserSetting(
            user_setting_id=str(uuid.uuid4()),
            user_id="user123",
            setting_key="  spaced_key  ",
            setting_value="value",
            value_type="str"
        )
        assert setting_stripped.setting_key == "spaced_key"

    @pytest.mark.parametrize(
        "key, expected_error_message_part",
        [
            ("", "setting_key cannot be blank."),
            ("   ", "setting_key cannot be blank."),
            ("A" * 65, "setting_key must be at most 64 characters."),
        ],
    )
    def test_user_setting_key_validation(self, key: str, expected_error_message_part: str) -> None:
        """
        Test objective: Verify UserSetting model's key validation for format and length.
        """
        with pytest.raises(ValidationError) as exc_info:
            UserSetting(
                user_setting_id=str(uuid.uuid4()),
                user_id="user123",
                setting_key=key,
                setting_value="value",
                value_type="str"
            )
        assert expected_error_message_part in str(exc_info.value)

    @pytest.mark.parametrize(
        "value, value_type, expected_error_message_part",
        [
            ("string", "int", "setting_value must be an integer"),
            (10, "str", "setting_value must be a string"),
            (1.5, "int", "setting_value must be an integer"),
            ("1.5", "float", "setting_value must be a float"),
            (10, "float", "setting_value must be a float"),
            (1, "invalid", "value_type must be one of: str, float, int"),
        ],
    )
    def test_user_setting_value_type_validation(
        self, value: object, value_type: str, expected_error_message_part: str
    ) -> None:
        """
        Test objective: Verify UserSetting model's validation for value type matching.
        """
        with pytest.raises(ValidationError) as exc_info:
            UserSetting(
                user_setting_id=str(uuid.uuid4()),
                user_id="user123",
                setting_key="test_key",
                setting_value=value,
                value_type=value_type
            )
        assert expected_error_message_part in str(exc_info.value)

    def test_user_setting_exceptions_instantiable(self) -> None:
        """Test objective: Ensure custom exceptions can be instantiated."""
        with pytest.raises(UserSettingValidationError) as e_val:
            raise UserSettingValidationError("Test validation error")
        assert "Test validation error" in str(e_val.value)

        with pytest.raises(UserSettingNotFound) as e_nf:
            raise UserSettingNotFound("Test not found error")
        assert "Test not found error" in str(e_nf.value)

    def test_user_setting_init_autogenerates_id(self) -> None:
        """Test that __init__ auto-generates a UUID if not provided."""
        setting = UserSetting(
            user_id="user123",
            setting_key="auto_id_test",
            setting_value="test",
            value_type="str"
        )
        assert isinstance(setting.user_setting_id, str)
        uuid_obj = uuid.UUID(setting.user_setting_id)
        assert str(uuid_obj) == setting.user_setting_id

    def test_user_setting_from_dict_valid_and_extra_fields(self) -> None:
        """Test from_dict with valid and extra fields."""
        data = {
            "user_id": "user123",
            "setting_key": "from_dict_test",
            "setting_value": "value",
            "value_type": "str"
        }
        setting = UserSetting.from_dict(data)
        assert setting.user_id == "user123"
        assert setting.setting_key == "from_dict_test"
        assert setting.setting_value == "value"
        assert isinstance(setting.user_setting_id, str)
        
        # Extra fields should raise ValueError
        data_extra = {
            "user_id": "user123", 
            "setting_key": "test", 
            "setting_value": "value", 
            "value_type": "str",
            "extra_field": "should_not_be_here"
        }
        with pytest.raises(ValueError) as e:
            UserSetting.from_dict(data_extra)
        assert "Extra fields not permitted" in str(e.value)

    def test_user_setting_to_dict(self) -> None:
        """Test to_dict returns correct dictionary."""
        setting = UserSetting(
            user_id="user123",
            setting_key="dict_test",
            setting_value=42,
            value_type="int"
        )
        d = setting.to_dict()
        assert d["user_setting_id"] == setting.user_setting_id
        assert d["user_id"] == "user123"
        assert d["setting_key"] == "dict_test"
        assert d["setting_value"] == 42
        assert d["value_type"] == "int"

    @pytest.mark.parametrize(
        "field, value, expected_error",
        [
            # user_setting_id=None should auto-generate a UUID, not error
            ("user_setting_id", 123, "Input should be a valid string"),
            ("user_setting_id", "not-a-uuid", "user_setting_id must be a valid UUID string"),
            ("user_id", None, "Input should be a valid string"),
            ("user_id", "", "user_id cannot be blank"),
            ("setting_key", None, "Input should be a valid string"),
            ("setting_key", "", "setting_key cannot be blank"),
            ("setting_value", None, "Input should be a valid"),
            ("value_type", "invalid", "value_type must be one of: str, float, int"),
        ],
    )
    def test_user_setting_field_type_and_value_errors(
        self, field: str, value: object, expected_error: str
    ) -> None:
        """Test wrong types and bad values for user setting fields."""
        data = {
            "user_setting_id": str(uuid.uuid4()),
            "user_id": "user123",
            "setting_key": "valid_key",
            "setting_value": "valid_value",
            "value_type": "str"
        }
        if field == "user_setting_id" and value is None:
            setting = UserSetting(
                user_id="user123",
                setting_key="valid_key",
                setting_value="valid_value",
                value_type="str"
            )
            uuid_obj = uuid.UUID(setting.user_setting_id)
            assert str(uuid_obj) == setting.user_setting_id
            return
        data[field] = value  # type: ignore
        with pytest.raises(Exception) as e:
            UserSetting(**data)
        assert expected_error in str(e.value)


if __name__ == "__main__":
    pytest.main([__file__])
