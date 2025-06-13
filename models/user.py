"""
User data model.
Defines the structure and validation for a user.
"""

from __future__ import annotations

from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class User(BaseModel):
    """User data model with validation.

    Attributes:
        user_id: Unique identifier for the user (UUID string).
        first_name: User's first name (ASCII, 1-64 chars).
        surname: User's surname (ASCII, 1-64 chars).
        email_address: User's email address (ASCII, 5-128 chars).
    """

    user_id: str | None = None
    first_name: str = Field(...)
    surname: str = Field(...)
    email_address: str = Field(...)

    model_config = {
        "validate_assignment": True,
    }

    @field_validator("first_name", "surname")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be blank.")
        stripped_v = v.strip()
        if len(stripped_v) > 64:
            raise ValueError("Name must be at most 64 characters.")
        if not all(ord(c) < 128 for c in stripped_v):
            raise ValueError("Name must be ASCII-only.")
        return stripped_v

    @field_validator("email_address")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Email address cannot be blank.")
        stripped_v = v.strip()
        if len(stripped_v) < 5 or len(stripped_v) > 128:
            raise ValueError("Email address must be 5-128 characters.")
        if not all(ord(c) < 128 for c in stripped_v):
            raise ValueError("Email address must be ASCII-only.")
        if "@" not in stripped_v or "." not in stripped_v:
            raise ValueError("Email address must contain '@' and '.'")
        return stripped_v

    @model_validator(mode="before")
    @classmethod
    def ensure_user_id(cls, values: dict) -> dict:
        if not values.get("user_id"):
            values["user_id"] = str(uuid4())
        return values

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
    def from_dict(cls, d: Dict[str, Any]) -> "User":
        allowed = set(cls.model_fields.keys())
        extra = set(d.keys()) - allowed
        if extra:
            raise ValueError(f"Extra fields not permitted: {extra}")
        return cls(**d)
