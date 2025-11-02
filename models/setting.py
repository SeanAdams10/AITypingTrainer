"""Setting data model.

Defines the structure and validation for a setting.
"""

from __future__ import annotations

import datetime
import hashlib
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
        row_checksum: SHA-256 hash of business columns for no-op detection.
        created_dt: ISO datetime indicating when the setting was created.
        updated_dt: ISO datetime indicating when the setting was last updated.
        created_user_id: UUID string identifying the user who created the setting.
        updated_user_id: UUID string identifying the user who last updated the setting.
    """

    setting_id: str | None = None
    setting_type_id: str = Field(...)
    setting_value: str = Field(...)
    related_entity_id: str = Field(...)
    row_checksum: bytes = Field(...)
    created_dt: str = Field(...)
    updated_dt: str = Field(...)
    created_user_id: str = Field(...)
    updated_user_id: str = Field(...)

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
        stripped_v = v.strip() if v else v

        if len(stripped_v) != 6:
            raise ValueError("setting_type_id must be exactly 6 characters.")
        if not all(ord(c) < 128 for c in stripped_v):
            raise ValueError("setting_type_id must be ASCII-only.")
        return stripped_v

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

    @field_validator("created_dt")
    @classmethod
    def validate_created_dt(cls, v: str) -> str:
        """Ensure created_dt is a valid ISO datetime string."""
        if not v:
            raise ValueError("created_dt must be explicitly provided")
        try:
            datetime.datetime.fromisoformat(v)
        except Exception as err:
            raise ValueError("created_dt must be a valid ISO datetime string") from err
        return v

    @field_validator("updated_dt")
    @classmethod
    def validate_updated_dt(cls, v: str) -> str:
        """Ensure updated_dt is a valid ISO datetime string."""
        if not v:
            raise ValueError("updated_dt must be explicitly provided")
        try:
            datetime.datetime.fromisoformat(v)
        except Exception as err:
            raise ValueError("updated_dt must be a valid ISO datetime string") from err
        return v

    @field_validator("created_user_id")
    @classmethod
    def validate_created_user_id(cls, v: str) -> str:
        """Ensure created_user_id is a valid UUID string."""
        if not v:
            raise ValueError("created_user_id must be explicitly provided")
        try:
            UUID(v)
        except Exception as err:
            raise ValueError("created_user_id must be a valid UUID string") from err
        return v

    @field_validator("updated_user_id")
    @classmethod
    def validate_updated_user_id(cls, v: str) -> str:
        """Ensure updated_user_id is a valid UUID string."""
        if not v:
            raise ValueError("updated_user_id must be explicitly provided")
        try:
            UUID(v)
        except Exception as err:
            raise ValueError("updated_user_id must be a valid UUID string") from err
        return v

    def calculate_checksum(self) -> bytes:
        """Calculate SHA-256 checksum of business columns.
        
        Business columns are: setting_type_id, setting_value, related_entity_id.
        Excludes audit columns: row_checksum, created_dt, updated_dt,
        created_user_id, updated_user_id.
        
        Returns:
            bytes: SHA-256 hash of business columns.
        """
        business_data = "|".join([
            self.setting_type_id or "",
            self.setting_value or "",
            self.related_entity_id or "",
        ])
        return hashlib.sha256(business_data.encode("utf-8")).digest()

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
