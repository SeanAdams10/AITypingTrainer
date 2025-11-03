"""Setting Type data model.

Defines the structure and validation for setting type definitions.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class SettingTypeValidationError(Exception):
    """Exception raised when setting type validation fails."""

    def __init__(self, message: str = "Setting type validation failed") -> None:
        """Initialize the exception with a message."""
        self.message = message
        super().__init__(self.message)


class SettingTypeNotFound(Exception):
    """Exception raised when a requested setting type cannot be found."""

    def __init__(self, message: str = "Setting type not found") -> None:
        """Initialize the exception with a message."""
        self.message = message
        super().__init__(self.message)


class SettingType(BaseModel):
    """Setting Type data model with validation.

    Attributes:
        setting_type_id: 6-character key identifying the setting type.
        setting_type_name: Human-readable name for the setting type.
        description: Detailed description of what this setting controls.
        related_entity_type: Type of entity this setting applies to.
        data_type: Expected data type for values.
        default_value: Default value as text, null if no default.
        validation_rules: JSON string with validation rules.
        is_system: True for system settings that cannot be deleted.
        is_active: False to disable a setting type.
        created_user_id: User who created this setting type.
        updated_user_id: User who last updated this setting type.
        created_dt: When setting type was first created.
        updated_dt: When setting type was last updated.
        row_checksum: SHA-256 hash of business columns for no-op detection.
    """

    setting_type_id: str = Field(..., min_length=6, max_length=6)
    setting_type_name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    related_entity_type: str = Field(..., pattern="^(user|keyboard|global)$")
    data_type: str = Field(..., pattern="^(string|integer|boolean|decimal)$")
    default_value: Optional[str] = None
    validation_rules: Optional[str] = None
    is_system: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_user_id: str = Field(..., min_length=1)
    updated_user_id: str = Field(..., min_length=1)
    created_dt: datetime = Field(default_factory=lambda: datetime.now())
    updated_dt: datetime = Field(default_factory=lambda: datetime.now())
    row_checksum: str = Field(default="")

    @field_validator("setting_type_id")
    @classmethod
    def validate_setting_type_id(cls, v: str) -> str:
        """Validate setting type ID format per Settings_req.md.
        
        Must be exactly 6 uppercase alphanumeric characters.
        Constraint: CHECK (setting_type_id ~ '^[A-Z0-9]{6}$')
        """
        if len(v) != 6:
            raise ValueError("setting_type_id must be exactly 6 characters")
        if not v.isalnum():
            raise ValueError("setting_type_id must be alphanumeric")
        # Check that all alphabetic characters are uppercase
        if any(c.isalpha() and not c.isupper() for c in v):
            raise ValueError("setting_type_id must be uppercase")
        return v

    @field_validator("validation_rules")
    @classmethod
    def validate_json_rules(cls, v: Optional[str]) -> Optional[str]:
        """Validate that validation_rules is valid JSON if provided."""
        if v is not None:
            try:
                json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(f"validation_rules must be valid JSON: {e}") from e
        return v

    def model_post_init(self, __context: object) -> None:
        """Calculate checksum if not provided."""
        if not self.row_checksum:
            self.row_checksum = self.calculate_checksum()

    def calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum of business columns."""
        business_data = "|".join([
            self.setting_type_id,
            self.setting_type_name,
            self.description,
            self.related_entity_type,
            self.data_type,
            self.default_value or "",
            self.validation_rules or "",
            str(self.is_system),
            str(self.is_active),
        ])
        return hashlib.sha256(business_data.encode("utf-8")).hexdigest()

    def validate_setting_value(self, value: str) -> bool:
        """Validate a setting value against this type's constraints.
        
        Validates based on data_type and validation_rules JSON.
        Supports: enum, minLength, maxLength, pattern, minimum, maximum.
        
        Args:
            value: String value to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        try:
            # Parse validation rules if present
            rules = {}
            if self.validation_rules:
                rules = json.loads(self.validation_rules)
            
            # Type-specific validation
            if self.data_type == "integer":
                int_val = int(value)
                # Check minimum/maximum
                if "minimum" in rules and int_val < rules["minimum"]:
                    return False
                if "maximum" in rules and int_val > rules["maximum"]:
                    return False
                    
            elif self.data_type == "decimal":
                float_val = float(value)
                # Check minimum/maximum
                if "minimum" in rules and float_val < rules["minimum"]:
                    return False
                if "maximum" in rules and float_val > rules["maximum"]:
                    return False
                    
            elif self.data_type == "boolean":
                # Boolean must be exactly "true" or "false" (lowercase)
                if value not in ["true", "false"]:
                    return False
                    
            elif self.data_type == "string":
                # Check enum constraint
                if "enum" in rules:
                    if value not in rules["enum"]:
                        return False
                # Check length constraints
                if "minLength" in rules and len(value) < rules["minLength"]:
                    return False
                if "maxLength" in rules and len(value) > rules["maxLength"]:
                    return False
                # Check pattern constraint
                if "pattern" in rules:
                    import re
                    if not re.match(rules["pattern"], value):
                        return False

            return True
            
        except (ValueError, json.JSONDecodeError, TypeError):
            return False

    def get_parsed_validation_rules(self) -> Dict[str, Any]:
        """Get validation rules as a parsed dictionary."""
        if self.validation_rules:
            try:
                result = json.loads(self.validation_rules)
                return dict(result)  # Ensure it's a dict
            except json.JSONDecodeError:
                return {}
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SettingType:
        """Create SettingType instance from dictionary."""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert SettingType to dictionary."""
        return self.model_dump()
