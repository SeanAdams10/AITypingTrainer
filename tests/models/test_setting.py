"""Unit tests for models.setting.Setting.

Tests the Setting Pydantic model including validation, checksum calculation,
and serialization based on Requirements/Settings_req.md.
"""

import sys
import uuid
from datetime import datetime, timezone

import pytest

from models.setting import Setting


class TestSettingCreation:
    """Test suite for Setting object creation and initialization."""

    def test_create_setting_with_all_fields(self) -> None:
        """Test objective: Create a setting with all required fields."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        entity_id = str(uuid.uuid4())
        
        setting = Setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=entity_id,
            row_checksum=b"test_checksum_32_bytes_______",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        assert setting.setting_type_id == "USRTHM"
        assert setting.setting_value == "dark"
        assert setting.related_entity_id == entity_id
        assert setting.created_user_id == user_id
        assert setting.updated_user_id == user_id

    def test_setting_id_auto_generated(self) -> None:
        """Test objective: Verify setting_id is auto-generated if not provided."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        
        setting = Setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            row_checksum=b"test",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        assert setting.setting_id is not None
        # Verify it's a valid UUID
        uuid.UUID(setting.setting_id)


class TestSettingTypeIdValidation:
    """Test suite for setting_type_id validation rules."""

    def test_valid_6_character_type_id(self) -> None:
        """Test objective: Accept valid 6-character setting type IDs."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        
        valid_ids = ["USRTHM", "LSTKBD", "DRILEN", "ABC123", "123456"]
        
        for type_id in valid_ids:
            setting = Setting(
                setting_type_id=type_id,
                setting_value="test",
                related_entity_id=str(uuid.uuid4()),
                row_checksum=b"test",
                created_dt=now,
                updated_dt=now,
                created_user_id=user_id,
                updated_user_id=user_id,
            )
            assert setting.setting_type_id == type_id

    @pytest.mark.parametrize("invalid_id", [
        "",           # Empty
        "ABC",        # Too short
        "ABCDEFGH",   # Too long
        "ABC€ΩΨ",     # Non-ASCII
    ])
    def test_invalid_setting_type_id_length(self, invalid_id: str) -> None:
        """Test objective: Reject setting type IDs that don't meet format requirements."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        
        with pytest.raises(ValueError):
            Setting(
                setting_type_id=invalid_id,
                setting_value="test",
                related_entity_id=str(uuid.uuid4()),
                row_checksum=b"test",
                created_dt=now,
                updated_dt=now,
                created_user_id=user_id,
                updated_user_id=user_id,
            )


class TestRelatedEntityIdValidation:
    """Test suite for related_entity_id validation."""

    def test_valid_uuid_entity_id(self) -> None:
        """Test objective: Accept valid UUID strings for related_entity_id."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        entity_id = str(uuid.uuid4())
        
        setting = Setting(
            setting_type_id="USRTHM",
            setting_value="test",
            related_entity_id=entity_id,
            row_checksum=b"test",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        assert setting.related_entity_id == entity_id

    @pytest.mark.parametrize("invalid_id", [
        "not-a-uuid",
        "12345",
        "",
        "abc-def-ghi",
    ])
    def test_invalid_entity_id(self, invalid_id: str) -> None:
        """Test objective: Reject invalid UUID strings for related_entity_id."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        
        with pytest.raises(ValueError) as exc_info:
            Setting(
                setting_type_id="USRTHM",
                setting_value="test",
                related_entity_id=invalid_id,
                row_checksum=b"test",
                created_dt=now,
                updated_dt=now,
                created_user_id=user_id,
                updated_user_id=user_id,
            )
        # Check that error mentions related_entity_id
        assert "related_entity_id" in str(exc_info.value).lower()


class TestUserIdValidation:
    """Test suite for user ID validation."""

    def test_valid_user_ids(self) -> None:
        """Test objective: Accept valid UUID strings for created_user_id and updated_user_id."""
        now = datetime.now(timezone.utc)
        created_user = str(uuid.uuid4())
        updated_user = str(uuid.uuid4())
        
        setting = Setting(
            setting_type_id="USRTHM",
            setting_value="test",
            related_entity_id=str(uuid.uuid4()),
            row_checksum=b"test",
            created_dt=now,
            updated_dt=now,
            created_user_id=created_user,
            updated_user_id=updated_user,
        )
        
        assert setting.created_user_id == created_user
        assert setting.updated_user_id == updated_user

    def test_invalid_created_user_id(self) -> None:
        """Test objective: Reject invalid UUID for created_user_id."""
        now = datetime.now(timezone.utc)
        
        with pytest.raises(ValueError) as exc_info:
            Setting(
                setting_type_id="USRTHM",
                setting_value="test",
                related_entity_id=str(uuid.uuid4()),
                row_checksum=b"test",
                created_dt=now,
                updated_dt=now,
                created_user_id="invalid-uuid",
                updated_user_id=str(uuid.uuid4()),
            )
        assert "created_user_id" in str(exc_info.value).lower()

    def test_invalid_updated_user_id(self) -> None:
        """Test objective: Reject invalid UUID for updated_user_id."""
        now = datetime.now(timezone.utc)
        
        with pytest.raises(ValueError) as exc_info:
            Setting(
                setting_type_id="USRTHM",
                setting_value="test",
                related_entity_id=str(uuid.uuid4()),
                row_checksum=b"test",
                created_dt=now,
                updated_dt=now,
                created_user_id=str(uuid.uuid4()),
                updated_user_id="invalid-uuid",
            )
        assert "updated_user_id" in str(exc_info.value).lower()


class TestDateTimeValidation:
    """Test suite for datetime field validation."""

    def test_valid_iso_datetime_strings(self) -> None:
        """Test objective: Accept valid ISO format datetime strings."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        
        setting = Setting(
            setting_type_id="USRTHM",
            setting_value="test",
            related_entity_id=str(uuid.uuid4()),
            row_checksum=b"test",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        assert setting.created_dt == now
        assert setting.updated_dt == now

    def test_invalid_created_dt(self) -> None:
        """Test objective: Reject invalid datetime string for created_dt."""
        user_id = str(uuid.uuid4())
        
        with pytest.raises(ValueError) as exc_info:
            Setting(
                setting_type_id="USRTHM",
                setting_value="test",
                related_entity_id=str(uuid.uuid4()),
                row_checksum=b"test",
                created_dt="not-a-datetime",
                updated_dt=datetime.now(timezone.utc).isoformat(),
                created_user_id=user_id,
                updated_user_id=user_id,
            )
        assert "created_dt" in str(exc_info.value).lower()

    def test_invalid_updated_dt(self) -> None:
        """Test objective: Reject invalid datetime string for updated_dt."""
        user_id = str(uuid.uuid4())
        
        with pytest.raises(ValueError) as exc_info:
            Setting(
                setting_type_id="USRTHM",
                setting_value="test",
                related_entity_id=str(uuid.uuid4()),
                row_checksum=b"test",
                created_dt=datetime.now(timezone.utc).isoformat(),
                updated_dt="not-a-datetime",
                created_user_id=user_id,
                updated_user_id=user_id,
            )
        assert "updated_dt" in str(exc_info.value).lower()


class TestChecksumCalculation:
    """Test suite for row checksum calculation."""

    def test_calculate_checksum_returns_bytes(self) -> None:
        """Test objective: Verify calculate_checksum returns bytes."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        
        setting = Setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            row_checksum=b"placeholder",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        checksum = setting.calculate_checksum()
        assert isinstance(checksum, bytes)
        assert len(checksum) == 32  # SHA-256 produces 32 bytes

    def test_checksum_changes_with_business_data(self) -> None:
        """Test objective: Checksum changes when business columns change."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        entity_id = str(uuid.uuid4())
        
        setting1 = Setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=entity_id,
            row_checksum=b"placeholder",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        setting2 = Setting(
            setting_type_id="USRTHM",
            setting_value="light",  # Different value
            related_entity_id=entity_id,
            row_checksum=b"placeholder",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        assert setting1.calculate_checksum() != setting2.calculate_checksum()

    def test_checksum_ignores_audit_columns(self) -> None:
        """Test objective: Checksum doesn't change when only audit columns change."""
        now = datetime.now(timezone.utc)
        later = datetime.now(timezone.utc)
        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())
        entity_id = str(uuid.uuid4())
        
        setting1 = Setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=entity_id,
            row_checksum=b"placeholder",
            created_dt=now,
            updated_dt=now,
            created_user_id=user1,
            updated_user_id=user1,
        )
        
        setting2 = Setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=entity_id,
            row_checksum=b"different",  # Different checksum
            created_dt=later,  # Different timestamp
            updated_dt=later,  # Different timestamp
            created_user_id=user2,  # Different user
            updated_user_id=user2,  # Different user
        )
        
        # Business data is the same, so checksums should match
        assert setting1.calculate_checksum() == setting2.calculate_checksum()


class TestSettingSerialization:
    """Test suite for Setting serialization methods."""

    def test_to_dict(self) -> None:
        """Test objective: Verify to_dict converts Setting to dictionary."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        entity_id = str(uuid.uuid4())
        setting_id = str(uuid.uuid4())
        
        setting = Setting(
            setting_id=setting_id,
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=entity_id,
            row_checksum=b"test",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        result = setting.to_dict()
        
        assert isinstance(result, dict)
        assert result["setting_id"] == setting_id
        assert result["setting_type_id"] == "USRTHM"
        assert result["setting_value"] == "dark"
        assert result["related_entity_id"] == entity_id

    def test_from_dict(self) -> None:
        """Test objective: Verify from_dict creates Setting from dictionary."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        entity_id = str(uuid.uuid4())
        
        data = {
            "setting_type_id": "USRTHM",
            "setting_value": "dark",
            "related_entity_id": entity_id,
            "row_checksum": b"test",
            "created_dt": now,
            "updated_dt": now,
            "created_user_id": user_id,
            "updated_user_id": user_id,
        }
        
        setting = Setting.from_dict(data)
        
        assert setting.setting_type_id == "USRTHM"
        assert setting.setting_value == "dark"
        assert setting.related_entity_id == entity_id

    def test_from_dict_rejects_extra_fields(self) -> None:
        """Test objective: Verify from_dict rejects dictionaries with extra fields."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        
        data = {
            "setting_type_id": "USRTHM",
            "setting_value": "dark",
            "related_entity_id": str(uuid.uuid4()),
            "row_checksum": b"test",
            "created_dt": now,
            "updated_dt": now,
            "created_user_id": user_id,
            "updated_user_id": user_id,
            "extra_field": "not_allowed",
        }
        
        with pytest.raises(ValueError) as exc_info:
            Setting.from_dict(data)
        assert "extra fields" in str(exc_info.value).lower()

    def test_round_trip_serialization(self) -> None:
        """Test objective: Verify to_dict and from_dict are inverses."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        entity_id = str(uuid.uuid4())
        
        original = Setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=entity_id,
            row_checksum=b"test_checksum",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = Setting.from_dict(data)
        
        assert restored.setting_type_id == original.setting_type_id
        assert restored.setting_value == original.setting_value
        assert restored.related_entity_id == original.related_entity_id
        assert restored.created_user_id == original.created_user_id


class TestSettingEdgeCases:
    """Test suite for edge cases and special scenarios."""

    def test_empty_setting_value(self) -> None:
        """Test objective: Allow empty string as setting value."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        
        setting = Setting(
            setting_type_id="USRTHM",
            setting_value="",  # Empty value
            related_entity_id=str(uuid.uuid4()),
            row_checksum=b"test",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        assert setting.setting_value == ""

    def test_very_long_setting_value(self) -> None:
        """Test objective: Handle very long setting values."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        long_value = "x" * 10000
        
        setting = Setting(
            setting_type_id="USRTHM",
            setting_value=long_value,
            related_entity_id=str(uuid.uuid4()),
            row_checksum=b"test",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        assert setting.setting_value == long_value
        assert len(setting.setting_value) == 10000

    def test_unicode_in_setting_value(self) -> None:
        """Test objective: Handle Unicode characters in setting values."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        unicode_value = "日本語 Español Français 中文 🎉"
        
        setting = Setting(
            setting_type_id="USRTHM",
            setting_value=unicode_value,
            related_entity_id=str(uuid.uuid4()),
            row_checksum=b"test",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        assert setting.setting_value == unicode_value

    def test_special_characters_in_value(self) -> None:
        """Test objective: Handle special characters in setting values."""
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        special_value = "Test with 'quotes', \"double quotes\", and symbols: @#$%^&*()"
        
        setting = Setting(
            setting_type_id="USRTHM",
            setting_value=special_value,
            related_entity_id=str(uuid.uuid4()),
            row_checksum=b"test",
            created_dt=now,
            updated_dt=now,
            created_user_id=user_id,
            updated_user_id=user_id,
        )
        
        assert setting.setting_value == special_value


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
