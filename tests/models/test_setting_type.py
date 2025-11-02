"""Comprehensive unit tests for the SettingType model.

Tests the SettingType Pydantic model focusing on validation, checksum calculation,
JSON validation rules, and business logic as specified in Settings.md.
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from models.setting_type import SettingType, SettingTypeNotFound, SettingTypeValidationError


class TestSettingTypeModel:
    """Test cases for the SettingType Pydantic model."""

    def test_setting_type_creation_minimal(self) -> None:
        """Test creating SettingType with minimal required data."""
        setting_type = SettingType(
            setting_type_id="USRTHM",
            setting_type_name="User Theme",
            description="User's preferred theme",
            related_entity_type="user",
            data_type="string",
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        assert setting_type.setting_type_id == "USRTHM"
        assert setting_type.setting_type_name == "User Theme"
        assert setting_type.data_type == "string"
        assert setting_type.is_system is False  # Default
        assert setting_type.is_active is True   # Default
        assert isinstance(setting_type.created_dt, datetime)
        assert isinstance(setting_type.updated_dt, datetime)
        assert isinstance(setting_type.row_checksum, str)
        assert len(setting_type.row_checksum) == 64  # SHA-256 hex

    def test_setting_type_creation_full(self) -> None:
        """Test creating SettingType with all fields."""
        validation_rules = json.dumps({"enum": ["light", "dark", "auto"]})
        created_dt = datetime.now(timezone.utc)
        updated_dt = datetime.now(timezone.utc)
        
        setting_type = SettingType(
            setting_type_id="GLBTHM",
            setting_type_name="Global Theme",
            description="Global theme setting",
            related_entity_type="global",
            data_type="string",
            default_value="dark",
            validation_rules=validation_rules,
            is_system=True,
            is_active=True,
            created_user_id="system",
            updated_user_id="admin",
            created_dt=created_dt,
            updated_dt=updated_dt
        )
        
        assert setting_type.setting_type_id == "GLBTHM"
        assert setting_type.default_value == "dark"
        assert setting_type.validation_rules == validation_rules
        assert setting_type.is_system is True
        assert setting_type.created_dt == created_dt
        assert setting_type.updated_dt == updated_dt

    def test_setting_type_checksum_calculation(self) -> None:
        """Test checksum calculation is consistent and deterministic."""
        setting_type = SettingType(
            setting_type_id="USRLNG",
            setting_type_name="User Language",
            description="User's preferred language",
            related_entity_type="user",
            data_type="string",
            default_value="en",
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        original_checksum = setting_type.row_checksum
        manual_checksum = setting_type.calculate_checksum()
        
        assert original_checksum == manual_checksum
        
        # Create identical setting type
        setting_type2 = SettingType(
            setting_type_id=setting_type.setting_type_id,
            setting_type_name=setting_type.setting_type_name,
            description=setting_type.description,
            related_entity_type=setting_type.related_entity_type,
            data_type=setting_type.data_type,
            default_value=setting_type.default_value,
            validation_rules=setting_type.validation_rules,
            is_system=setting_type.is_system,
            is_active=setting_type.is_active,
            created_user_id=setting_type.created_user_id,
            updated_user_id=setting_type.updated_user_id,
            created_dt=setting_type.created_dt,
            updated_dt=setting_type.updated_dt
        )
        
        assert setting_type2.row_checksum == original_checksum

    def test_setting_type_checksum_changes_with_data(self) -> None:
        """Test checksum changes when data changes."""
        setting_type = SettingType(
            setting_type_id="USRTHM",
            setting_type_name="User Theme",
            description="Theme preference",
            related_entity_type="user",
            data_type="string",
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        original_checksum = setting_type.row_checksum
        
        # Change description
        setting_type.description = "Updated theme preference"
        new_checksum = setting_type.calculate_checksum()
        
        assert new_checksum != original_checksum

    @pytest.mark.parametrize(
        "field_name, invalid_value",
        [
            ("setting_type_id", ""),
            ("setting_type_id", None),
            ("setting_type_id", "SHORT"),  # Only 5 chars
            ("setting_type_id", "TOOLONG"),  # 7 chars
            ("setting_type_id", "lower1"),  # Lowercase
            ("setting_type_id", "TEST.1"),  # Contains dot
            ("setting_type_name", ""),
            ("setting_type_name", None),
            ("description", ""),
            ("description", None),
            ("related_entity_type", ""),
            ("related_entity_type", None),
            ("related_entity_type", "system"),  # Invalid entity type
            ("data_type", ""),
            ("data_type", None),
            ("data_type", "invalid_type"),
            ("data_type", "number"),  # Not in valid types
            ("data_type", "json"),  # Not in valid types
            ("created_user_id", ""),
            ("created_user_id", None),
            ("updated_user_id", ""),
            ("updated_user_id", None),
        ],
    )
    def test_setting_type_field_validation(self, field_name: str, invalid_value) -> None:
        """Test field validation for required fields and data type enum."""
        valid_data = {
            "setting_type_id": "USRTST",
            "setting_type_name": "Test Setting",
            "description": "Test description",
            "related_entity_type": "user",
            "data_type": "string",
            "created_user_id": "admin",
            "updated_user_id": "admin"
        }
        
        valid_data[field_name] = invalid_value
        
        with pytest.raises(ValidationError):
            SettingType(**valid_data)

    @pytest.mark.parametrize(
        "data_type",
        ["string", "integer", "boolean", "decimal"]
    )
    def test_setting_type_valid_data_types(self, data_type: str) -> None:
        """Test all valid data types per Settings_req.md are accepted."""
        setting_type = SettingType(
            setting_type_id="TSTTYP",
            setting_type_name="Test Type",
            description="Test description",
            related_entity_type="user",
            data_type=data_type,
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        assert setting_type.data_type == data_type

    def test_setting_type_id_format_validation(self) -> None:
        """Test setting_type_id format validation per Settings_req.md.
        
        Must be exactly 6 uppercase alphanumeric characters.
        Constraint: CHECK (setting_type_id ~ '^[A-Z0-9]{6}$')
        """
        valid_ids = [
            "LSTKBD",  # Last keyboard
            "DRICAT",  # Drill category
            "NGRSZE",  # N-gram size
            "TEST01",  # With numbers
            "ABCDEF",  # All letters
            "123456",  # All numbers
        ]
        
        for setting_type_id in valid_ids:
            setting_type = SettingType(
                setting_type_id=setting_type_id,
                setting_type_name="Test",
                description="Test",
                related_entity_type="user",
                data_type="string",
                created_user_id="admin",
                updated_user_id="admin"
            )
            assert setting_type.setting_type_id == setting_type_id
    
    def test_setting_type_id_invalid_formats(self) -> None:
        """Test that invalid setting_type_id formats are rejected."""
        invalid_ids = [
            "short",      # Only 5 chars
            "TOOLONG",    # 7 chars
            "lower1",     # Lowercase
            "Test01",     # Mixed case
            "TEST.1",     # Contains dot
            "TEST-1",     # Contains hyphen
            "TEST 1",     # Contains space
            "TEST_1",     # Contains underscore
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError):
                SettingType(
                    setting_type_id=invalid_id,
                    setting_type_name="Test",
                    description="Test",
                    related_entity_type="user",
                    data_type="string",
                    created_user_id="admin",
                    updated_user_id="admin"
                )

    def test_setting_type_from_dict(self) -> None:
        """Test creating SettingType from dictionary (database row)."""
        created_dt = datetime.now(timezone.utc)
        updated_dt = datetime.now(timezone.utc)
        validation_rules = json.dumps({"enum": ["option1", "option2"]})
        
        row_data = {
            'setting_type_id': 'USRTST',
            'setting_type_name': 'Test Setting',
            'description': 'Test description',
            'related_entity_type': 'user',
            'data_type': 'string',
            'default_value': 'option1',
            'validation_rules': validation_rules,
            'is_system': False,
            'is_active': True,
            'created_user_id': 'admin',
            'updated_user_id': 'user1',
            'created_dt': created_dt.isoformat(),
            'updated_dt': updated_dt.isoformat(),
            'row_checksum': 'abc123def456'
        }
        
        setting_type = SettingType.from_dict(row_data)
        
        assert setting_type.setting_type_id == 'USRTST'
        assert setting_type.setting_type_name == 'Test Setting'
        assert setting_type.validation_rules == validation_rules
        assert setting_type.is_system is False
        assert setting_type.is_active is True
        assert setting_type.row_checksum == 'abc123def456'


class TestSettingTypeValidation:
    """Test setting value validation against setting type rules."""

    def test_string_enum_validation(self) -> None:
        """Test string enumeration validation."""
        setting_type = SettingType(
            setting_type_id="USRTHM",
            setting_type_name="User Theme",
            description="Theme preference",
            related_entity_type="user",
            data_type="string",
            validation_rules=json.dumps({"enum": ["light", "dark", "auto"]}),
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        # Valid values
        assert setting_type.validate_setting_value("light")
        assert setting_type.validate_setting_value("dark")
        assert setting_type.validate_setting_value("auto")
        
        # Invalid values
        assert not setting_type.validate_setting_value("invalid")
        assert not setting_type.validate_setting_value("")
        assert not setting_type.validate_setting_value("Light")  # Case sensitive

    def test_string_length_validation(self) -> None:
        """Test string length validation."""
        setting_type = SettingType(
            setting_type_id="USRNAM",
            setting_type_name="User Name",
            description="User display name",
            related_entity_type="user",
            data_type="string",
            validation_rules=json.dumps({"minLength": 2, "maxLength": 50}),
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        # Valid lengths
        assert setting_type.validate_setting_value("Jo")      # Min length
        assert setting_type.validate_setting_value("John")    # Normal
        assert setting_type.validate_setting_value("x" * 50)  # Max length
        
        # Invalid lengths
        assert not setting_type.validate_setting_value("J")       # Too short
        assert not setting_type.validate_setting_value("x" * 51)  # Too long
        assert not setting_type.validate_setting_value("")        # Empty

    def test_string_pattern_validation(self) -> None:
        """Test string pattern validation."""
        setting_type = SettingType(
            setting_type_id="USRUNM",
            setting_type_name="Username",
            description="User login name",
            related_entity_type="user",
            data_type="string",
            validation_rules=json.dumps({"pattern": "^[a-zA-Z0-9_]+$"}),
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        # Valid patterns
        assert setting_type.validate_setting_value("user123")
        assert setting_type.validate_setting_value("test_user")
        assert setting_type.validate_setting_value("ABC")
        
        # Invalid patterns
        assert not setting_type.validate_setting_value("user-123")    # Hyphen not allowed
        assert not setting_type.validate_setting_value("user 123")    # Space not allowed
        assert not setting_type.validate_setting_value("user@test")   # @ not allowed

    def test_integer_validation(self) -> None:
        """Test integer validation."""
        setting_type = SettingType(
            setting_type_id="USRAGE",
            setting_type_name="User Age",
            description="User age in years",
            related_entity_type="user",
            data_type="integer",
            validation_rules=json.dumps({"minimum": 13, "maximum": 120}),
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        # Valid integers
        assert setting_type.validate_setting_value("13")   # Minimum
        assert setting_type.validate_setting_value("25")   # Normal
        assert setting_type.validate_setting_value("120")  # Maximum
        
        # Invalid integers
        assert not setting_type.validate_setting_value("12")    # Too low
        assert not setting_type.validate_setting_value("121")   # Too high
        assert not setting_type.validate_setting_value("25.5")  # Float
        assert not setting_type.validate_setting_value("abc")   # Not a number
        assert not setting_type.validate_setting_value("")      # Empty

    def test_decimal_validation(self) -> None:
        """Test decimal (float) validation."""
        setting_type = SettingType(
            setting_type_id="TYPSPD",
            setting_type_name="Typing Speed Goal",
            description="Target WPM",
            related_entity_type="user",
            data_type="decimal",
            validation_rules=json.dumps({"minimum": 10.0, "maximum": 200.0}),
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        # Valid numbers
        assert setting_type.validate_setting_value("10.0")   # Minimum
        assert setting_type.validate_setting_value("65.5")   # Normal float
        assert setting_type.validate_setting_value("200")    # Integer as float
        assert setting_type.validate_setting_value("200.0")  # Maximum
        
        # Invalid numbers
        assert not setting_type.validate_setting_value("9.9")    # Too low
        assert not setting_type.validate_setting_value("200.1")  # Too high
        assert not setting_type.validate_setting_value("abc")    # Not a number
        assert not setting_type.validate_setting_value("")       # Empty

    def test_boolean_validation(self) -> None:
        """Test boolean validation."""
        setting_type = SettingType(
            setting_type_id="USRNOT",
            setting_type_name="Email Notifications",
            description="Enable email notifications",
            related_entity_type="user",
            data_type="boolean",
            validation_rules=json.dumps({"type": "boolean"}),
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        # Valid boolean values
        assert setting_type.validate_setting_value("true")
        assert setting_type.validate_setting_value("false")
        
        # Invalid boolean values
        assert not setting_type.validate_setting_value("True")   # Wrong case
        assert not setting_type.validate_setting_value("False")  # Wrong case
        assert not setting_type.validate_setting_value("1")      # Numeric
        assert not setting_type.validate_setting_value("0")      # Numeric
        assert not setting_type.validate_setting_value("yes")    # Other truthy
        assert not setting_type.validate_setting_value("")       # Empty

    def test_related_entity_types(self) -> None:
        """Test all valid related_entity_type values per Settings_req.md.
        
        Valid types: 'user', 'keyboard', 'global'
        Constraint: CHECK (related_entity_type IN ('user', 'keyboard', 'global'))
        """
        valid_entity_types = ["user", "keyboard", "global"]
        
        for entity_type in valid_entity_types:
            setting_type = SettingType(
                setting_type_id="TEST01",
                setting_type_name="Test",
                description="Test",
                related_entity_type=entity_type,
                data_type="string",
                created_user_id="admin",
                updated_user_id="admin"
            )
            assert setting_type.related_entity_type == entity_type
    
    def test_invalid_related_entity_types(self) -> None:
        """Test that invalid related_entity_type values are rejected."""
        invalid_entity_types = ["system", "organization", "admin", "custom"]
        
        for entity_type in invalid_entity_types:
            with pytest.raises(ValidationError):
                SettingType(
                    setting_type_id="TEST01",
                    setting_type_name="Test",
                    description="Test",
                    related_entity_type=entity_type,
                    data_type="string",
                    created_user_id="admin",
                    updated_user_id="admin"
                )

    def test_validation_without_rules(self) -> None:
        """Test validation when no rules are specified."""
        setting_type = SettingType(
            setting_type_id="USRNOT",
            setting_type_name="User Notes",
            description="Free-form user notes",
            related_entity_type="user",
            data_type="string",
            # No validation_rules
            created_user_id="admin",
            updated_user_id="admin"
        )
        
        # Should accept any string value
        assert setting_type.validate_setting_value("Any string")
        assert setting_type.validate_setting_value("")
        assert setting_type.validate_setting_value("Special chars: !@#$%")

    def test_validation_with_invalid_rules(self) -> None:
        """Test behavior with invalid validation rules JSON."""
        with pytest.raises(ValidationError):
            SettingType(
                setting_type_id="USRTST",
                setting_type_name="Test",
                description="Test with invalid rules",
                related_entity_type="user",
                data_type="string",
                validation_rules='{"invalid": json}',  # Invalid JSON
                created_user_id="admin",
                updated_user_id="admin"
            )


class TestSettingTypeExceptions:
    """Test custom exception classes."""
    
    def test_setting_type_not_found_exception(self) -> None:
        """Test SettingTypeNotFound exception."""
        exc = SettingTypeNotFound("Setting type not found")
        assert str(exc) == "Setting type not found"
        assert isinstance(exc, Exception)
    
    def test_setting_type_validation_error_exception(self) -> None:
        """Test SettingTypeValidationError exception."""
        exc = SettingTypeValidationError("Invalid setting type")
        assert str(exc) == "Invalid setting type"
        assert isinstance(exc, Exception)
