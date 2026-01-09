"""KeysetKey entity - Pure Pydantic model with no external dependencies.

This is the Entities layer of Clean Architecture. It contains only business logic
and validation rules. No imports from repositories, services, UI, or frameworks.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, cast
from uuid import uuid4

from pydantic import BaseModel, field_validator, model_validator


class KeysetKey(BaseModel):
    """Represents a single key within a keyset.

    This is a pure domain entity with no database or UI dependencies.
    All validation rules are enforced at the model level.

    Attributes:
        key_id: UUID string, auto-generated when not provided
        keyset_id: Parent keyset id, may be None before persistence
        key_char: Exactly one unicode character (supports ASCII, emojis, CJK, symbols)
        is_new_key: Whether the key is emphasized as newly introduced in keyset
        in_db: Internal flag for database state tracking (managed by repositories)
    """

    key_id: Optional[str] = None
    keyset_id: Optional[str] = None
    key_char: str
    is_new_key: bool = False
    in_db: bool = False

    model_config = {
        "extra": "forbid",  # Reject unknown fields
        "validate_assignment": True,  # Validate on field updates
    }

    @model_validator(mode="before")
    @classmethod
    def ensure_key_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-generate key_id if not supplied."""
        if "key_id" not in values or values.get("key_id") is None:
            values["key_id"] = str(uuid4())
        else:
            provided = values.get("key_id")
            if isinstance(provided, str) and not provided.strip():
                raise ValueError("key_id must be a non-empty string")
        return values

    @field_validator("key_id", mode="before")
    @classmethod
    def validate_key_id(cls, v: object) -> str:
        """Validate key_id is a non-empty string.

        Note: We intentionally do not enforce UUID format because tests and some
        tables use semantic IDs like 'key1'.
        """
        if v is None:
            raise ValueError("key_id is required")
        if not isinstance(v, str) or not v.strip():
            raise ValueError("key_id must be a non-empty string")
        return v

    @field_validator("keyset_id", mode="before")
    @classmethod
    def validate_keyset_id(cls, v: object) -> Optional[str]:
        """Validate keyset_id if provided (can be None before persistence)."""
        if v is None:
            return None
        if not isinstance(v, str) or not v.strip():
            raise ValueError("keyset_id must be a non-empty string")
        return v

    @field_validator("key_char", mode="before")
    @classmethod
    def validate_key_char(cls, v: object) -> str:
        """Validate key_char is exactly one Unicode character.

        Supports full Unicode range:
        - ASCII letters and digits (a-z, A-Z, 0-9)
        - Punctuation (!, ?, @, #, etc.)
        - Symbols ($, %, &, *, etc.)
        - Whitespace (space, tab)
        - Non-ASCII letters (é, ñ, ü)
        - CJK characters (中, 日, 한)
        - Emojis (😀, 🎉, 🔥)
        """
        if not isinstance(v, str):
            raise ValueError("key_char must be a string")
        if len(v) != 1:
            raise ValueError("key_char must be exactly one character")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary.

        Returns:
            Dictionary representation of all fields
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: Mapping[str, object]) -> KeysetKey:
        """Create entity from dictionary.

        Args:
            d: Dictionary with entity data

        Returns:
            New KeysetKey instance

        Raises:
            ValidationError: If data doesn't meet validation rules
        """
        # Cast to Any to satisfy mypy for unpacking dict into Pydantic model
        return cls(**cast(Any, dict(d)))
