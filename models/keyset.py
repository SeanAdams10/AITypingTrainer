"""Keyset and KeysetKey Pydantic models.

Implements validation, UUID auto-generation, and in_db state tracking
as specified in Prompts/Keysets.md.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


def _ensure_non_empty_str(value: object, field_name: str) -> str:
    """Validate that value is a non-empty string.

    Note: We intentionally do not enforce UUID format because tests and some
    tables use semantic IDs like 'kb1'.
    """
    if value is None:
        raise ValueError(f"{field_name} is required")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


class KeysetKey(BaseModel):
    """Represents a single key within a keyset.

    Attributes:
        key_id: UUID string, auto-generated when not provided
        keyset_id: Parent keyset id, may be None before persistence
        key_char: Exactly one unicode character
        is_new_key: Whether the key is emphasized as newly introduced in keyset
        in_db: Internal flag for DB state tracking
    """

    key_id: Optional[str] = None
    keyset_id: Optional[str] = None
    key_char: str
    is_new_key: bool = False
    in_db: bool = False

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }

    @model_validator(mode="before")
    @classmethod
    def ensure_key_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-generate key_id if not supplied."""
        if not values.get("key_id"):
            values["key_id"] = str(uuid4())
        return values

    @field_validator("key_id", mode="before")
    @classmethod
    def validate_key_id(cls, v: object) -> str:
        return _ensure_non_empty_str(v, "key_id")

    @field_validator("keyset_id", mode="before")
    @classmethod
    def validate_keyset_id(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        return _ensure_non_empty_str(v, "keyset_id")

    @field_validator("key_char", mode="before")
    @classmethod
    def validate_key_char(cls, v: object) -> str:
        if not isinstance(v, str):
            raise ValueError("key_char must be a string")
        if len(v) != 1:
            raise ValueError("key_char must be exactly one character")
        return v

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: Mapping[str, object]) -> "KeysetKey":
        return cls(**dict(d))  # type: ignore[arg-type]


class Keyset(BaseModel):
    """Represents a keyset for a keyboard.

    Attributes:
        keyset_id: UUID string, auto-generated when not provided
        keyboard_id: UUID string of owning keyboard
        keyset_name: 1..100 chars
        progression_order: integer >= 1
        keys: list of KeysetKey items
        in_db: internal flag tracking DB persistence state
    """

    keyset_id: Optional[str] = None
    keyboard_id: str
    keyset_name: str
    progression_order: int
    keys: List[KeysetKey] = Field(default_factory=list)
    in_db: bool = False

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }

    @model_validator(mode="before")
    @classmethod
    def ensure_keyset_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values.get("keyset_id"):
            values["keyset_id"] = str(uuid4())
        return values

    @field_validator("keyset_id", "keyboard_id", mode="before")
    @classmethod
    def validate_ids(cls, v: object, info) -> str:
        # info is available but not used besides signature
        field_name = str(info.field_name)
        return _ensure_non_empty_str(v, field_name)

    @field_validator("keyset_name", mode="before")
    @classmethod
    def validate_name(cls, v: object) -> str:
        if not isinstance(v, str):
            raise ValueError("keyset_name must be a string")
        name = v.strip()
        if not (1 <= len(name) <= 100):
            raise ValueError("keyset_name must be 1..100 characters")
        return name

    @field_validator("progression_order", mode="before")
    @classmethod
    def validate_order(cls, v: object) -> int:
        if isinstance(v, bool):  # bool is subclass of int
            raise ValueError("progression_order must be a positive integer")
        try:
            iv = int(v)  # type: ignore[arg-type]
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError("progression_order must be an integer") from exc
        if iv < 1:
            raise ValueError("progression_order must be >= 1")
        return iv

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: Mapping[str, object]) -> "Keyset":
        # Load nested keys if present
        data = dict(d)
        keys_val = data.get("keys")
        if isinstance(keys_val, list):
            data["keys"] = [KeysetKey.from_dict(k) if isinstance(k, Mapping) else k for k in keys_val]  # type: ignore[list-item]
        return cls(**data)  # type: ignore[arg-type]
