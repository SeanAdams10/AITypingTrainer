"""
Unit tests for the Setting Pydantic model in models.setting.
Focuses on validation logic within the Setting model itself.
"""

# Standard library imports
import uuid
from datetime import datetime, timezone

# Third-party imports
import pytest
from pydantic import ValidationError

# Local application imports
from models.setting import Setting, SettingNotFound, SettingValidationError


class TestSettingModel:
    """Test cases for the Setting Pydantic model."""

    def test_setting_creation_valid(self) -> None:
        """Test objective: Create a Setting instance with valid data."""
        setting_id = str(uuid.uuid4())
        related_entity_id = str(uuid.uuid4())
        setting = Setting(
            setting_id=setting_id,
            setting_type_id="ABCDEF",
            setting_value="test value",
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat()
        )

        assert isinstance(setting.setting_id, str)
        assert setting.setting_type_id == "ABCDEF"
        assert setting.setting_value == "test value"
        assert setting.related_entity_id == related_entity_id

    @pytest.mark.parametrize(
        "setting_type_id, expected_error_message_part",
        [
            ("", "setting_type_id must be exactly 6 characters"),
            ("ABC", "setting_type_id must be exactly 6 characters"),
            ("ABCDEFG", "setting_type_id must be exactly 6 characters"),
            ("ABCD€Ω", "setting_type_id must be ASCII-only"),
        ],
    )
    def test_setting_type_id_validation(self, setting_type_id: str, expected_error_message_part: str) -> None:
        """
        Test objective: Verify Setting model's type_id validation for format, length, and ASCII.
        """
        with pytest.raises(ValidationError) as exc_info:
            Setting(
                setting_id=str(uuid.uuid4()),
                setting_type_id=setting_type_id,
                setting_value="test",
                related_entity_id=str(uuid.uuid4()),
                updated_at=datetime.now(timezone.utc).isoformat()
            )
        assert expected_error_message_part in str(exc_info.value)

    def test_setting_exceptions_instantiable(self) -> None:
        """Test objective: Ensure custom exceptions can be instantiated."""
        with pytest.raises(SettingValidationError) as e_val:
            raise SettingValidationError("Test validation error")
        assert "Test validation error" in str(e_val.value)

        with pytest.raises(SettingNotFound) as e_nf:
            raise SettingNotFound("Test not found error")
        assert "Test not found error" in str(e_nf.value)

    def test_setting_init_autogenerates_id(self) -> None:
        """Test that __init__ auto-generates a UUID if not provided."""
        setting = Setting(
            setting_type_id="ABCDEF",
            setting_value="test",
            related_entity_id=str(uuid.uuid4()),
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        assert isinstance(setting.setting_id, str)
        uuid_obj = uuid.UUID(setting.setting_id)
        assert str(uuid_obj) == setting.setting_id

    def test_setting_from_dict_valid_and_extra_fields(self) -> None:
        """Test from_dict with valid and extra fields."""
        data = {
            "setting_type_id": "ABCDEF",
            "setting_value": "test",
            "related_entity_id": str(uuid.uuid4()),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        setting = Setting.from_dict(data)
        assert setting.setting_type_id == "ABCDEF"
        assert setting.setting_value == "test"
        assert isinstance(setting.setting_id, str)

        # Extra fields should raise ValueError
        data_extra = {
            "setting_type_id": "ABCDEF",
            "setting_value": "test",
            "related_entity_id": str(uuid.uuid4()),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "foo": 123
        }
        with pytest.raises(ValueError) as e:
            Setting.from_dict(data_extra)
        assert "Extra fields not permitted" in str(e.value)

    def test_setting_to_dict(self) -> None:
        """Test to_dict returns correct dictionary."""
        setting_id = str(uuid.uuid4())
        related_entity_id = str(uuid.uuid4())
        updated_at = datetime.now(timezone.utc).isoformat()

        setting = Setting(
            setting_id=setting_id,
            setting_type_id="ABCDEF",
            setting_value="test value",
            related_entity_id=related_entity_id,
            updated_at=updated_at
        )

        d = setting.to_dict()
        assert d["setting_id"] == setting_id
        assert d["setting_type_id"] == "ABCDEF"
        assert d["setting_value"] == "test value"
        assert d["related_entity_id"] == related_entity_id
        assert d["updated_at"] == updated_at

    @pytest.mark.parametrize(
        "field, value, expected_error",
        [
            # setting_id=None should auto-generate a UUID, not error
            ("setting_id", 123, "Input should be a valid string"),
            ("setting_id", "not-a-uuid", "setting_id must be a valid UUID string"),
            ("setting_type_id", None, "Input should be a valid string"),
            ("setting_type_id", "", "setting_type_id must be exactly 6 characters"),
            ("setting_type_id", "ABC", "setting_type_id must be exactly 6 characters"),
            ("related_entity_id", None, "Input should be a valid string"),
            ("related_entity_id", "not-a-uuid", "related_entity_id must be a valid UUID string"),
            ("updated_at", None, "Input should be a valid string"),
            ("updated_at", "not-iso-format", "updated_at must be a valid ISO datetime string"),
        ],
    )
    def test_setting_field_type_and_value_errors(
        self, field: str, value: object, expected_error: str
    ) -> None:
        """Test wrong types and bad values for setting fields."""
        setting_id = str(uuid.uuid4())
        related_entity_id = str(uuid.uuid4())
        updated_at = datetime.now(timezone.utc).isoformat()

        data = {
            "setting_id": setting_id,
            "setting_type_id": "ABCDEF",
            "setting_value": "test",
            "related_entity_id": related_entity_id,
            "updated_at": updated_at
        }

        if field == "setting_id" and value is None:
            setting = Setting(
                setting_id=None,
                setting_type_id="ABCDEF",
                setting_value="test",
                related_entity_id=related_entity_id,
                updated_at=updated_at
            )
            uuid_obj = uuid.UUID(setting.setting_id)
            assert str(uuid_obj) == setting.setting_id
            return

        data[field] = value  # type: ignore
        with pytest.raises(Exception) as e:
            Setting(**data)
        assert expected_error in str(e.value)


if __name__ == "__main__":
    pytest.main([__file__])
