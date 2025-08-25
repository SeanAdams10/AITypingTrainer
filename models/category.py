"""Category data model.

Defines the structure and validation for a category.
"""

from __future__ import annotations

from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class Category(BaseModel):
    """Category data model with validation.

    Attributes:
        category_id: Unique identifier for the category (UUID string).
        category_name: Name of the category (must be ASCII, 1-64 chars).
    """

    category_id: str | None = None
    category_name: str = Field(...)
    description: str = Field("")

    model_config = {
        "validate_assignment": True,
    }

    @field_validator("category_name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate category name constraints (format, length, ASCII).

        Args:
            v: The category name to validate.

        Returns:
            str: The validated and stripped category name.

        Raises:
            ValueError: If validation fails (forwarded by Pydantic as ValidationError).
        """
        if not v or not v.strip():
            raise ValueError("Category name cannot be blank.")

        stripped_v = v.strip()

        if len(stripped_v) > 64:
            raise ValueError("Category name must be at most 64 characters.")
        if not all(ord(c) < 128 for c in stripped_v):
            raise ValueError("Category name must be ASCII-only.")
        return stripped_v

    @model_validator(mode="before")
    @classmethod
    def ensure_category_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure a category_id is present by generating a UUID if missing."""
        if not values.get("category_id"):
            values["category_id"] = str(uuid4())
        return values

    @field_validator("category_id")
    @classmethod
    def validate_category_id(cls, v: str) -> str:
        """Ensure category_id is a valid UUID string."""
        if not v:
            raise ValueError("category_id must not be empty")
        try:
            UUID(v)
        except Exception as err:
            raise ValueError("category_id must be a valid UUID string") from err
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Category instance to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the category.
        """
        # Explicitly cast the result to Dict[str, Any] to satisfy mypy
        return dict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Category:
        """Create a Category instance from a dictionary.

        Args:
            d: Dictionary containing category data.

        Returns:
            Category: An instance of the Category class.

        Raises:
            ValueError: If unexpected fields are present in the data.
        """
        allowed = set(cls.model_fields.keys())
        extra = set(d.keys()) - allowed
        if extra:
            raise ValueError(f"Extra fields not permitted: {extra}")
        return cls(**d)
