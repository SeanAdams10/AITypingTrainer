"""Comprehensive unit tests for the Setting model.

Tests the Setting Pydantic model focusing on validation, checksum calculation,
field constraints, and business rules as specified in Settings.md.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from models.setting import Setting, SettingNotFound, SettingValidationError


class TestSettingModel:
    """Test cases for the Setting Pydantic model."""

    def test_setting_creation_with_minimal_data(self) -> None:
        """Test creating a Setting with minimal required data."""
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            created_user_id="test-user",
            updated_user_id="test-user"
        )
        
        assert setting.setting_type_id == "user.theme"
        assert setting.setting_value == "dark"
        assert isinstance(setting.setting_id, str)
        assert len(setting.setting_id) == 36  # UUID4 format
        assert isinstance(setting.created_at, datetime)
        assert isinstance(setting.updated_at, datetime)
        assert isinstance(setting.row_checksum, str)
        assert len(setting.row_checksum) == 64  # SHA-256 hex

    def test_setting_creation_with_all_fields(self) -> None:
        """Test creating a Setting with all fields explicitly set."""
        setting_id = str(uuid.uuid4())
        related_entity_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        
        setting = Setting(
            setting_id=setting_id,
            setting_type_id="user.language",
            setting_value="en",
            related_entity_id=related_entity_id,
            created_user_id="user1",
            updated_user_id="user2",
            created_at=created_at,
            updated_at=updated_at
        )
        
        assert setting.setting_id == setting_id
        assert setting.setting_type_id == "user.language"
        assert setting.setting_value == "en"
        assert setting.related_entity_id == related_entity_id
        assert setting.created_user_id == "user1"
        assert setting.updated_user_id == "user2"
        assert setting.created_at == created_at
        assert setting.updated_at == updated_at

    def test_setting_checksum_calculation(self) -> None:
        """Test that row checksum is calculated correctly and consistently."""
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id="user123",
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        original_checksum = setting.row_checksum
        
        # Calculate checksum manually and verify
        manual_checksum = setting.calculate_checksum()
        assert original_checksum == manual_checksum
        
        # Create identical setting and verify same checksum
        setting2 = Setting(
            setting_id=setting.setting_id,
            setting_type_id=setting.setting_type_id,
            setting_value=setting.setting_value,
            related_entity_id=setting.related_entity_id,
            created_user_id=setting.created_user_id,
            updated_user_id=setting.updated_user_id,
            created_at=setting.created_at,
            updated_at=setting.updated_at
        )
        
        assert setting2.row_checksum == original_checksum

    def test_setting_checksum_changes_with_data(self) -> None:
        """Test that checksum changes when setting data changes."""
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id="user123",
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        original_checksum = setting.row_checksum
        
        # Change value and recalculate checksum
        setting.setting_value = "light"
        new_checksum = setting.calculate_checksum()
        
        assert new_checksum != original_checksum
        
        # Update the model's checksum
        setting.row_checksum = new_checksum
        assert setting.row_checksum == new_checksum

    @pytest.mark.parametrize(
        "field_name, invalid_value, expected_error_type",
        [
            ("setting_type_id", "", ValidationError),
            ("setting_type_id", None, ValidationError),
            ("setting_value", None, ValidationError),
            ("related_entity_id", "", ValidationError),
            ("related_entity_id", None, ValidationError),
            ("created_user_id", "", ValidationError),
            ("created_user_id", None, ValidationError),
            ("updated_user_id", "", ValidationError),
            ("updated_user_id", None, ValidationError),
        ],
    )
    def test_setting_field_validation(self, field_name: str, invalid_value, expected_error_type) -> None:
        """Test that required fields are properly validated."""
        valid_data = {
            "setting_type_id": "user.theme",
            "setting_value": "dark",
            "related_entity_id": str(uuid.uuid4()),
            "created_user_id": "test-user",
            "updated_user_id": "test-user"
        }
        
        valid_data[field_name] = invalid_value
        
        with pytest.raises(expected_error_type):
            Setting(**valid_data)

    def test_setting_type_id_format_validation(self) -> None:
        """Test setting_type_id follows expected dot notation format."""
        # Valid formats
        valid_ids = [
            "user.theme",
            "system.max_sessions", 
            "organization.default_language",
            "a.b",  # Minimal valid format
            "user.notification.email.enabled"  # Multiple dots allowed
        ]
        
        for setting_type_id in valid_ids:
            setting = Setting(
                setting_type_id=setting_type_id,
                setting_value="test",
                related_entity_id=str(uuid.uuid4()),
                created_user_id="test",
                updated_user_id="test"
            )
            assert setting.setting_type_id == setting_type_id

    def test_setting_value_validation_with_type(self) -> None:
        """Test that setting values can be validated based on setting type rules."""
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            created_user_id="test",
            updated_user_id="test"
        )
        
        # Test validate_value method with mock setting type
        class MockSettingType:
            def validate_setting_value(self, value: str) -> bool:
                return value in ["light", "dark", "auto"]
        
        mock_type = MockSettingType()
        
        # Valid values should pass
        assert setting.validate_value("dark", mock_type)
        assert setting.validate_value("light", mock_type)
        assert setting.validate_value("auto", mock_type)
        
        # Invalid values should fail
        assert not setting.validate_value("invalid", mock_type)
        assert not setting.validate_value("", mock_type)

    def test_setting_from_dict(self) -> None:
        """Test creating Setting from dictionary (database row)."""
        setting_id = str(uuid.uuid4())
        related_entity_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        
        row_data = {
            'setting_id': setting_id,
            'setting_type_id': 'user.theme',
            'setting_value': 'dark',
            'related_entity_id': related_entity_id,
            'created_user_id': 'user1',
            'updated_user_id': 'user2',
            'created_at': created_at.isoformat(),
            'updated_at': updated_at.isoformat(),
            'row_checksum': 'abc123def456'
        }
        
        setting = Setting.from_dict(row_data)
        
        assert setting.setting_id == setting_id
        assert setting.setting_type_id == 'user.theme'
        assert setting.setting_value == 'dark'
        assert setting.related_entity_id == related_entity_id
        assert setting.created_user_id == 'user1'
        assert setting.updated_user_id == 'user2'
        assert setting.row_checksum == 'abc123def456'

    def test_setting_timestamps_auto_generated(self) -> None:
        """Test that created_at and updated_at are auto-generated when not provided."""
        before_creation = datetime.now(timezone.utc)
        
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            created_user_id="test",
            updated_user_id="test"
        )
        
        after_creation = datetime.now(timezone.utc)
        
        assert before_creation <= setting.created_at <= after_creation
        assert before_creation <= setting.updated_at <= after_creation

    def test_setting_id_auto_generated(self) -> None:
        """Test that setting_id is auto-generated as UUID when not provided."""
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            created_user_id="test",
            updated_user_id="test"
        )
        
        # Verify it's a valid UUID
        uuid.UUID(setting.setting_id)  # Should not raise
        assert len(setting.setting_id) == 36
        assert setting.setting_id.count('-') == 4

    def test_setting_immutable_after_creation(self) -> None:
        """Test that setting behaves as expected for field updates."""
        setting = Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id=str(uuid.uuid4()),
            created_user_id="test",
            updated_user_id="test"
        )
        
        original_checksum = setting.row_checksum
        
        # Pydantic models are mutable by default, so this should work
        setting.setting_value = "light"
        setting.updated_user_id = "new-user"
        
        # But checksum won't auto-update
        assert setting.row_checksum == original_checksum
        
        # Manual checksum update needed
        setting.row_checksum = setting.calculate_checksum()
        assert setting.row_checksum != original_checksum


class TestSettingExceptions:
    """Test custom exception classes."""
    
    def test_setting_not_found_exception(self) -> None:
        """Test SettingNotFound exception."""
        exc = SettingNotFound("Setting not found")
        assert str(exc) == "Setting not found"
        assert isinstance(exc, Exception)
    
    def test_setting_validation_error_exception(self) -> None:
        """Test SettingValidationError exception.""" 
        exc = SettingValidationError("Invalid setting value")
        assert str(exc) == "Invalid setting value"
        assert isinstance(exc, Exception)
