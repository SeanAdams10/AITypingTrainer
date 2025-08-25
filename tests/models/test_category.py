"""Unit tests for the Category Pydantic model in models.category.
Focuses on validation logic within the Category model itself.
"""

# Standard library imports
import uuid

# Third-party imports
import pytest
from pydantic import ValidationError

# Local application imports
from models.category import Category
from models.category_manager import CategoryNotFound, CategoryValidationError


class TestCategoryModel:
    """Test cases for the Category Pydantic model."""

    def test_category_creation_valid(self) -> None:
        """Test objective: Create a Category instance with valid data."""
        cat = Category(category_id=str(uuid.uuid4()), category_name="Valid Name")
        assert isinstance(cat.category_id, str)
        assert cat.category_name == "Valid Name"

        cat_stripped = Category(category_id=str(uuid.uuid4()), category_name="  Spaced Name  ")
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
    def test_category_name_validation(self, name: str, expected_error_message_part: str) -> None:
        """Test objective: Verify Category model's name validation for format, length, and ASCII."""
        with pytest.raises(ValidationError) as exc_info:
            Category(category_id=str(uuid.uuid4()), category_name=name)
        assert expected_error_message_part in str(exc_info.value)

    def test_category_exceptions_instantiable(self) -> None:
        """Test objective: Ensure custom exceptions can be instantiated."""
        with pytest.raises(CategoryValidationError) as e_val:
            raise CategoryValidationError("Test validation error")
        assert "Test validation error" in str(e_val.value)

        with pytest.raises(CategoryNotFound) as e_nf:
            raise CategoryNotFound("Test not found error")
        assert "Test not found error" in str(e_nf.value)

    def test_category_init_autogenerates_id(self) -> None:
        """Test that __init__ auto-generates a UUID if not provided."""
        cat = Category(category_name="AutoID")
        assert isinstance(cat.category_id, str)
        uuid_obj = uuid.UUID(cat.category_id)
        assert str(uuid_obj) == cat.category_id

    def test_category_from_dict_valid_and_extra_fields(self) -> None:
        """Test from_dict with valid and extra fields."""
        data = {"category_name": "FromDictTest"}
        cat = Category.from_dict(data)
        assert cat.category_name == "FromDictTest"
        assert isinstance(cat.category_id, str)
        # Extra fields should raise ValueError
        data_extra = {"category_name": "X", "foo": 123}
        with pytest.raises(ValueError) as e:
            Category.from_dict(data_extra)
        assert "Extra fields not permitted" in str(e.value)

    def test_category_to_dict(self) -> None:
        """Test to_dict returns correct dictionary."""
        cat = Category(category_name="DictTest")
        d = cat.to_dict()
        assert d["category_id"] == cat.category_id
        assert d["category_name"] == cat.category_name

    @pytest.mark.parametrize(
        "field, value, expected_error",
        [
            # category_id=None should auto-generate a UUID, not error
            ("category_id", 123, "Input should be a valid string"),
            ("category_id", "not-a-uuid", "category_id must be a valid UUID string"),
            ("category_name", None, "Input should be a valid string"),
            ("category_name", "", "Category name cannot be blank"),
            ("category_name", " ", "Category name cannot be blank"),
            ("category_name", "A" * 65, "Category name must be at most 64 characters"),
            ("category_name", "NonASCIIÑame", "Category name must be ASCII-only"),
        ],
    )
    def test_category_field_type_and_value_errors(
        self, field: str, value: object, expected_error: str
    ) -> None:
        """Test wrong types and bad values for category fields."""
        data = {"category_id": str(uuid.uuid4()), "category_name": "Valid"}
        if field == "category_id" and value is None:
            cat = Category(category_id=None, category_name="Valid")
            uuid_obj = uuid.UUID(cat.category_id)
            assert str(uuid_obj) == cat.category_id
            return
        data[field] = value  # type: ignore
        with pytest.raises(Exception) as e:
            Category(**data)
        assert expected_error in str(e.value)

    def test_category_db_rows_fail_validation(self) -> None:
        """Test that current DB rows would fail Pydantic validation (simulate DB load)."""
        # These are the actual rows from the current categories table
        db_rows = [
            (1, "Test Category", None),
            (2, "Python", None),
            (3, "PySpark", None),
            (5, "Test", None),
            (6, "PracticeText", None),
            (9, "Poetry", None),
            (14, "Great Speeches", None),
            (15, "Important Texts", None),
        ]
        for row in db_rows:
            cat_id = row[0]  # This is an int, but should be a UUID string
            cat_name = row[1]
            # Simulate what happens when loading from DB
            with pytest.raises(Exception) as exc_info:
                Category(category_id=cat_id, category_name=cat_name)
            assert "category_id" in str(exc_info.value) and (
                "string" in str(exc_info.value) or "UUID" in str(exc_info.value)
            )


if __name__ == "__main__":
    pytest.main([__file__])
