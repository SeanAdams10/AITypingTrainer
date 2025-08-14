"""
Keyboard data model.
Defines the structure and validation for a keyboard.
"""

from __future__ import annotations

from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Keyboard(BaseModel):
    """Keyboard data model with validation.
    Attributes:
        keyboard_id: Unique identifier for the keyboard (UUID string).
        user_id: UUID string, foreign key to user table.
        keyboard_name: Name of the keyboard (ASCII, 1-64 chars).
        target_ms_per_keystroke: Target milliseconds per keystroke for speed goal
        (integer).
    """

    keyboard_id: str | None = None
    user_id: str = Field(...)
    keyboard_name: str = Field(...)
    target_ms_per_keystroke: int = Field(default=600)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("keyboard_name")
    @classmethod
    def validate_keyboard_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Keyboard name cannot be blank.")
        stripped_v = v.strip()
        if len(stripped_v) > 64:
            raise ValueError("Keyboard name must be at most 64 characters.")
        if not all(ord(c) < 128 for c in stripped_v):
            raise ValueError("Keyboard name must be ASCII-only.")
        return stripped_v

    @field_validator("target_ms_per_keystroke")
    @classmethod
    def validate_target_ms_per_keystroke(cls, v: int) -> int:
        if v is None:
            raise ValueError("Target milliseconds per keystroke cannot be None.")
        if not isinstance(v, int):
            raise ValueError("Target milliseconds per keystroke must be an integer.")
        if v < 50 or v > 5000:
            raise ValueError(
                "Target milliseconds per keystroke must be between 50 and 5000."
            )
        return v

    @model_validator(mode="before")
    @classmethod
    def ensure_keyboard_id(cls, values: dict) -> dict:
        if not values.get("keyboard_id"):
            values["keyboard_id"] = str(uuid4())
        return values

    @field_validator("keyboard_id")
    @classmethod
    def validate_keyboard_id(cls, v: str) -> str:
        if not v:
            raise ValueError("keyboard_id must not be empty")
        try:
            UUID(v)
        except Exception as err:
            raise ValueError("keyboard_id must be a valid UUID string") from err
        return v

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not v:
            raise ValueError("user_id must not be empty")
        try:
            UUID(v)
        except Exception as err:
            raise ValueError("user_id must be a valid UUID string") from err
        return v

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Keyboard":
        allowed = set(cls.model_fields.keys())
        extra = set(d.keys()) - allowed
        if extra:
            raise ValueError(f"Extra fields not permitted: {extra}")
        return cls(**d)
