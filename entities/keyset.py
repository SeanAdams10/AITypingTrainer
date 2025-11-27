"""Keyset entity - Pure Pydantic model with no external dependencies.

This is the Entities layer of Clean Architecture. It contains only business logic
and validation rules. No imports from repositories, services, UI, or frameworks.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, cast
from uuid import uuid4

from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator

from entities.keyset_key import KeysetKey


class Keyset(BaseModel):
    """Represents a keyset for a keyboard.

    This is a pure domain entity with no database or UI dependencies.
    All validation rules and business logic are enforced at the model level.

    Attributes:
        keyset_id: UUID string, auto-generated when not provided
        keyboard_id: UUID string of owning keyboard
        keyset_name: 1..100 chars, whitespace stripped
        progression_order: Integer >= 1 indicating learning sequence
        keys: List of KeysetKey items in this keyset
        in_db: Internal flag tracking database persistence state (managed by repositories)
        is_dirty: Flag indicating model has diverged from database copy
    """

    keyset_id: Optional[str] = None
    keyboard_id: str
    keyset_name: str
    progression_order: int
    keys: List[KeysetKey] = Field(default_factory=list)
    in_db: bool = False
    is_dirty: bool = False

    # Internal guard to avoid marking dirty during model initialization
    _initializing: bool = PrivateAttr(default=True)

    model_config = {
        "extra": "forbid",  # Reject unknown fields
        "validate_assignment": True,  # Validate on field updates
    }

    @model_validator(mode="before")
    @classmethod
    def ensure_keyset_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-generate keyset_id if not supplied."""
        if not values.get("keyset_id"):
            values["keyset_id"] = str(uuid4())
        return values

    @field_validator("keyset_id", "keyboard_id", mode="before")
    @classmethod
    def validate_ids(cls, v: object, info: Any) -> str:
        """Validate ID fields are non-empty strings.

        Note: We intentionally do not enforce UUID format because tests and some
        tables use semantic IDs like 'kb1'.
        """
        field_name = str(info.field_name)
        if v is None:
            raise ValueError(f"{field_name} is required")
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"{field_name} must be a non-empty string")
        return v

    @field_validator("keyset_name", mode="before")
    @classmethod
    def validate_name(cls, v: object) -> str:
        """Validate keyset_name is 1-100 characters after stripping whitespace."""
        if not isinstance(v, str):
            raise ValueError("keyset_name must be a string")
        name = v.strip()
        if not (1 <= len(name) <= 100):
            raise ValueError("keyset_name must be 1..100 characters")
        return name

    @field_validator("progression_order", mode="before")
    @classmethod
    def validate_order(cls, v: object) -> int:
        """Validate progression_order is a positive integer >= 1."""
        if isinstance(v, bool):  # bool is subclass of int, reject explicitly
            raise ValueError("progression_order must be a positive integer")
        if not isinstance(v, (int, str)):
            raise ValueError("progression_order must be an integer")
        try:
            iv = int(v)
        except (ValueError, TypeError) as exc:
            raise ValueError("progression_order must be an integer") from exc
        if iv < 1:
            raise ValueError("progression_order must be >= 1")
        return iv

    def model_post_init(self, __context: Any) -> None:
        """Mark end of initialization so subsequent assignments can mark dirty."""
        self._initializing = False

    def __setattr__(self, name: str, value: Any) -> None:
        """Override setattr to mark model as dirty when business fields change.

        Only marks dirty for user-editable business fields (keyset_name,
        progression_order, keys), and only after initialization is complete.

        Does NOT mark dirty when:
        - Setting is_dirty itself (avoid recursion)
        - Setting in_db (state tracking field)
        - Setting keyset_id or keyboard_id (immutable identifiers)
        - During model initialization (_initializing=True)
        """
        # Check if we should mark dirty BEFORE calling super().__setattr__
        # This prevents issues with Pydantic's validate_assignment triggering recursive calls
        should_mark_dirty = False

        # Only mark dirty for business fields, and only after initialization
        if name not in {"is_dirty", "in_db", "_initializing", "keyset_id", "keyboard_id"}:
            try:
                # Access private attributes through __pydantic_private__
                private_attrs = object.__getattribute__(self, "__pydantic_private__")
                if private_attrs and "_initializing" in private_attrs:
                    init_val = private_attrs["_initializing"]
                    if not init_val:
                        should_mark_dirty = True
            except (AttributeError, KeyError):
                # During initial object construction, private attrs may not be set up yet
                pass

        # Delegate to BaseModel to handle the actual assignment and validation
        super().__setattr__(name, value)

        # Now mark as dirty if needed
        if should_mark_dirty:
            super().__setattr__("is_dirty", True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary.

        Returns:
            Dictionary representation of all fields including nested keys
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: Mapping[str, object]) -> Keyset:
        """Create entity from dictionary.

        Args:
            d: Dictionary with entity data, may contain nested key dictionaries

        Returns:
            New Keyset instance with nested KeysetKey objects

        Raises:
            ValidationError: If data doesn't meet validation rules
        """
        # Load nested keys if present
        data: Dict[str, Any] = dict(d)
        keys_val = data.get("keys")
        if isinstance(keys_val, list):
            data["keys"] = [
                KeysetKey.from_dict(k) if isinstance(k, Mapping) else k
                for k in keys_val
            ]
        # Cast to Any to satisfy mypy for unpacking dict into Pydantic model
        return cls(**cast(Any, data))
