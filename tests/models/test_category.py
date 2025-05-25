"""
Unit tests for the Category Pydantic model in models.category.
Focuses on validation logic within the Category model itself.
"""
# Standard library imports
import sys
from pathlib import Path

# Third-party imports
import pytest
from pydantic import ValidationError

# Add project root to path BEFORE importing any local modules
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Local application imports
from models.category import Category, CategoryNotFound, CategoryValidationError


class TestCategoryModel:
    """Test cases for the Category Pydantic model."""

    def test_category_creation_valid(self) -> None:
        """Test objective: Create a Category instance with valid data."""
        cat = Category(category_id=1, category_name="Valid Name")
        assert cat.category_id == 1
        assert cat.category_name == "Valid Name"

        cat_stripped = Category(category_id=2, category_name="  Spaced Name  ")
        assert cat_stripped.category_name == "Spaced Name"

    @pytest.mark.parametrize(
        "name, expected_error_message_part",
        [
            ("", "Category name cannot be blank."),
            ("   ", "Category name cannot be blank."),
            ("A" * 65, "Category name must be at most 64 characters."),
            ("NonASCIIÑame", "Category name must be ASCII-only."),
        ],
    )
    def test_category_name_validation(
        self, name: str, expected_error_message_part: str
    ) -> None:
        """
        Test objective: Verify Category model's name validation for format, length, and ASCII.
        """
        with pytest.raises(ValidationError) as exc_info:
            Category(category_id=1, category_name=name)
        
        assert expected_error_message_part in str(exc_info.value)

    def test_category_exceptions_instantiable(self) -> None:
        """Test objective: Ensure custom exceptions can be instantiated."""
        try:
            raise CategoryValidationError("Test validation error")
        except CategoryValidationError as e:
            assert "Test validation error" in str(e)

        try:
            raise CategoryNotFound("Test not found error")
        except CategoryNotFound as e:
            assert "Test not found error" in str(e)

if __name__ == "__main__":
    pytest.main([__file__])
