"""Setting data model.

Defines the structure and validation for a setting.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class SettingValidationError(Exception):
    """Exception raised when setting validation fails.

    This exception is raised for validation errors such as invalid format
    or if a setting type ID that is not unique for a given entity is attempted to be used.
    """

    def __init__(self, message: str = "Setting validation failed") -> None:
        """Initialize the exception with a message."""
        self.message = message
        super().__init__(self.message)


class SettingNotFound(Exception):
    """Exception raised when a requested setting cannot be found.

    This exception is raised when attempting to access, modify or delete
    a setting that does not exist in the database.
    """

    def __init__(self, message: str = "Setting not found") -> None:
        """Initialize the exception with a message."""
        self.message = message
        super().__init__(self.message)


class Setting(BaseModel):
    """Setting data model with validation.

    Attributes:
        setting_id: Unique identifier for the setting (UUID string).
        setting_type_id: 6-character key identifying the setting type.
        setting_value: The setting value stored as text.
        related_entity_id: UUID string identifying the related entity (user, keyboard, etc.).
        created_user_id: User who created this setting.
        updated_user_id: User who last updated this setting.
        created_at: When setting was first created.
        updated_at: When setting was last updated.
        row_checksum: SHA-256 hash of business columns for no-op detection.
    """

    setting_id: Optional[str] = None
    setting_type_id: str = Field(..., min_length=6, max_length=6)
    setting_value: str = Field(..., min_length=0)
    related_entity_id: str = Field(..., min_length=1)
    created_user_id: str = Field(..., min_length=1)
    updated_user_id: str = Field(..., min_length=1)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    row_checksum: Optional[str] = None

    model_config = {
        "validate_assignment": True,
    }

    @field_validator("setting_type_id")
    @classmethod
    def validate_setting_type_id(cls, v: str) -> str:
        """Validate setting_type_id constraints (length, format).

        Args:
            v: The setting_type_id to validate.

        Returns:
            str: The validated setting_type_id.

        Raises:
            ValueError: If validation fails.
        """
        if len(v) != 6:
            raise ValueError("setting_type_id must be exactly 6 characters")
        
        # Check if ASCII-only
        try:
            v.encode("ascii")
        except UnicodeEncodeError as err:
            raise ValueError("setting_type_id must be ASCII-only") from err
        
        if not v.isupper():
            raise ValueError("setting_type_id must be uppercase")
        
        return v

    @field_validator("related_entity_id")
    @classmethod
    def validate_related_entity_id(cls, v: str) -> str:
        """Ensure related_entity_id is a valid UUID string."""
        if not v:
            raise ValueError("related_entity_id must not be empty")
        try:
            UUID(v)
        except Exception as err:
            raise ValueError("related_entity_id must be a valid UUID string") from err
        return v

    @model_validator(mode="before")
    @classmethod
    def ensure_setting_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a UUID for setting_id if not provided."""
        if not values.get("setting_id"):
            values["setting_id"] = str(uuid4())
        return values

    @field_validator("setting_id")
    @classmethod
    def validate_setting_id(cls, v: Optional[str]) -> str:
        """Ensure setting_id is a valid UUID string."""
        if not v:
            return str(uuid4())
        try:
            UUID(v)
        except Exception as err:
            raise ValueError("setting_id must be a valid UUID string") from err
        return v

    @field_validator("updated_at")
    @classmethod
    def validate_updated_at(cls, v: Optional[datetime]) -> datetime:
        """Ensure updated_at is a valid datetime."""
        if not v:
            return datetime.now(timezone.utc)
        return v

    def model_post_init(self, __context: object) -> None:
        """Set default values after initialization."""
        if self.setting_id is None:
            self.setting_id = str(uuid4())
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)
        if self.row_checksum is None:
            self.row_checksum = self.calculate_checksum()

    def calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum of business columns."""
        business_data = "|".join([
            self.setting_type_id,
            self.setting_value,
            self.related_entity_id,
        ])
        return hashlib.sha256(business_data.encode("utf-8")).hexdigest()

    def validate_value(self, setting_type: object) -> bool:
        """Validate setting value against setting type rules.
        
        Args:
            setting_type: The setting type object to validate against.
            
        Returns:
            bool: True if valid, False otherwise.
        """
        if hasattr(setting_type, "validate_setting_value"):
            result = setting_type.validate_setting_value(self.setting_value)
            return bool(result)
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Setting instance to a dictionary.

        Returns:
            Dict: A dictionary representation of the setting.
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Setting:
        """Create a Setting instance from a dictionary.

        Args:
            d: Dictionary containing setting data.

        Returns:
            Setting: An instance of the Setting class.

        Raises:
            ValueError: If unexpected fields are present in the data.
        """
        allowed = set(cls.model_fields.keys())
        extra = set(d.keys()) - allowed
        if extra:
            raise ValueError(f"Extra fields not permitted: {extra}")
        return cls(**d)
