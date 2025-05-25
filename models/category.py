"""
Category data model.
Defines the structure and validation for a category.
"""
from typing import Dict

from pydantic import BaseModel, field_validator


class CategoryValidationError(Exception):
    """Exception raised when category validation fails.

    This exception is raised for validation errors such as invalid name format
    or if a name that is not unique is attempted to be used.
    """

    def __init__(self, message: str = "Category validation failed") -> None:
        self.message = message
        super().__init__(self.message)


class CategoryNotFound(Exception):
    """Exception raised when a requested category cannot be found.

    This exception is raised when attempting to access, modify or delete
    a category that does not exist in the database.
    """

    def __init__(self, message: str = "Category not found") -> None:
        self.message = message
        super().__init__(self.message)


class Category(BaseModel):
    """Category data model with validation.

    Attributes:
        category_id: Unique identifier for the category.
                     Can be a placeholder (e.g., -1) if the category is not yet persisted.
        category_name: Name of the category (must be ASCII, 1-64 chars).
                       Uniqueness is handled by CategoryManager.
    """

    category_id: int
    category_name: str

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

    # Note: Uniqueness validation (checking against other category names in the DB)
    # is handled by the CategoryManager before database operations, as it requires DB access.

    @classmethod
    def from_dict(cls, data: Dict) -> "Category":
        """Create a Category instance from a dictionary.

        Args:
            data: Dictionary containing category data.

        Returns:
            Category: An instance of the Category class.

        Raises:
            ValueError: If unexpected fields are present in the data.
        """
        allowed_fields = {"category_id", "category_name"}
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}

        if len(filtered_data) != len(data):
            extra_keys = [k for k in data if k not in allowed_fields]
            raise ValueError(f"Extra fields not permitted: {extra_keys}")

        return cls(**filtered_data)

    def to_dict(self) -> Dict:
        """Convert the Category instance to a dictionary.

        Returns:
            Dict: A dictionary representation of the category.
        """
        return {
            "category_id": self.category_id,
            "category_name": self.category_name,
        }
