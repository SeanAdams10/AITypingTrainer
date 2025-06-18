"""
UserSetting data model.
Defines the structure and validation for user settings.
"""

from __future__ import annotations

from typing import Any, Dict, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class UserSetting(BaseModel):
    """UserSetting data model with validation.

    Attributes:
        user_setting_id: Unique identifier for the user setting (UUID string).
        user_id: ID of the user this setting belongs to.
        setting_key: Unique key/name for this setting (within a user's context).
        setting_value: The value of the setting (can be string, float, or integer).
        value_type: Type of the value ("str", "float", "int").
    """

    user_setting_id: str | None = None
    user_id: str = Field(...)
    setting_key: str = Field(...)
    setting_value: Union[str, float, int] = Field(...)
    value_type: str = Field(...)

    model_config = {
        "validate_assignment": True,
    }

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user_id is not empty.

        Args:
            v: The user_id to validate.

        Returns:
            str: The validated user_id.

        Raises:
            ValueError: If validation fails.
        """
        if not v or not v.strip():
            raise ValueError("user_id cannot be blank.")
        return v.strip()

    @field_validator("setting_key")
    @classmethod
    def validate_setting_key(cls, v: str) -> str:
        """Validate setting_key constraints (format, length).

        Args:
            v: The setting_key to validate.

        Returns:
            str: The validated and stripped setting_key.

        Raises:
            ValueError: If validation fails.
        """
        if not v or not v.strip():
            raise ValueError("setting_key cannot be blank.")

        stripped_v = v.strip()

        if len(stripped_v) > 64:
            raise ValueError("setting_key must be at most 64 characters.")
        return stripped_v

    @field_validator("value_type")
    @classmethod
    def validate_value_type(cls, v: str) -> str:
        """Validate value_type is one of the allowed types.

        Args:
            v: The value_type to validate.

        Returns:
            str: The validated value_type.

        Raises:
            ValueError: If validation fails.
        """
        allowed_types = ["str", "float", "int"]
        if v not in allowed_types:
            raise ValueError(f"value_type must be one of: {', '.join(allowed_types)}.")
        return v

    @model_validator(mode="before")
    @classmethod
    def ensure_user_setting_id(cls, values: dict) -> dict:
        """Ensure user_setting_id is set, generating a new one if necessary.

        Args:
            values: The values to validate.

        Returns:
            dict: The validated values.
        """
        if not values.get("user_setting_id"):
            values["user_setting_id"] = str(uuid4())
        return values

    @model_validator(mode="after")
    def validate_setting_value_type_match(self) -> "UserSetting":
        """Validate that setting_value matches the specified value_type.

        Returns:
            UserSetting: The validated UserSetting instance.

        Raises:
            ValueError: If value doesn't match the specified type.
        """
        if self.value_type == "str" and not isinstance(self.setting_value, str):
            raise ValueError("setting_value must be a string when value_type is 'str'.")
        elif self.value_type == "float" and not isinstance(self.setting_value, float):
            raise ValueError("setting_value must be a float when value_type is 'float'.")
        elif self.value_type == "int" and not isinstance(self.setting_value, int):
            raise ValueError("setting_value must be an integer when value_type is 'int'.")
        return self

    @field_validator("user_setting_id")
    @classmethod
    def validate_user_setting_id(cls, v: str) -> str:
        """Ensure user_setting_id is a valid UUID string.

        Args:
            v: The user_setting_id to validate.

        Returns:
            str: The validated user_setting_id.

        Raises:
            ValueError: If validation fails.
        """
        if not v:
            raise ValueError("user_setting_id must not be empty")
        try:
            UUID(v)
        except Exception as err:
            raise ValueError("user_setting_id must be a valid UUID string") from err
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert the UserSetting instance to a dictionary.

        Returns:
            Dict: A dictionary representation of the user setting.
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> UserSetting:
        """Create a UserSetting instance from a dictionary.

        Args:
            d: Dictionary containing user setting data.

        Returns:
            UserSetting: An instance of the UserSetting class.

        Raises:
            ValueError: If unexpected fields are present in the data.
        """
        allowed = set(cls.model_fields.keys())
        extra = set(d.keys()) - allowed
        if extra:
            raise ValueError(f"Extra fields not permitted: {extra}")
        return cls(**d)
