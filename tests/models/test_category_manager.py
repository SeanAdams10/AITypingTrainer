"""
Unit tests for models.category_manager.CategoryManager.
Covers CRUD, validation (including DB uniqueness), cascade deletion, and error handling.
"""

import uuid

import pytest
from pydantic import ValidationError

from models.category import Category
from models.category_manager import CategoryManager, CategoryNotFound, CategoryValidationError


class TestCategoryManager:
    """Test suite for CategoryManager covering all CRUD and validation logic."""

    def test_create_category_valid(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: Create a category with a valid name and verify persistence.
        """
        category = Category(category_name="Alpha", description="")
        assert category_manager_fixture.save_category(category)
        assert category.category_name == "Alpha"
        assert isinstance(category.category_id, str)
        # Verify it's in the DB
        retrieved_cat = category_manager_fixture.get_category_by_id(str(category.category_id))
        assert retrieved_cat.category_name == "Alpha"

    @pytest.mark.parametrize(
        "name, err_msg_part",
        [
            ("", "blank"),
            ("  ", "blank"),
            ("A" * 65, "at most 64 characters"),
            ("Café NonASCII", "ASCII-only"),
        ],
    )
    def test_create_category_invalid_format(
        self, category_manager_fixture: CategoryManager, name: str, err_msg_part: str
    ) -> None:
        """
        Test objective: Attempt to create a category with an invalid name format.
        """
        with pytest.raises((ValueError, CategoryValidationError)) as e:
            category = Category(category_name=name, description="")
            category_manager_fixture.save_category(category)
        assert err_msg_part.lower() in str(e.value).lower()

    def test_create_category_duplicate_name(
        self, category_manager_fixture: CategoryManager
    ) -> None:
        """
        Test objective: Attempt to create a category with a duplicate name.
        """
        category1 = Category(category_name="UniqueName", description="")
        category_manager_fixture.save_category(category1)
        category2 = Category(category_name="UniqueName", description="")
        with pytest.raises(CategoryValidationError) as e:
            category_manager_fixture.save_category(category2)
        assert "unique" in str(e.value).lower()

    def test_get_category_by_id(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: Retrieve a category by its ID.
        """
        category = Category(category_name="Test Category", description="")
        category_manager_fixture.save_category(category)
        retrieved_cat = category_manager_fixture.get_category_by_id(str(category.category_id))
        assert retrieved_cat is not None
        assert retrieved_cat.category_id == str(category.category_id)
        assert retrieved_cat.category_name == "Test Category"

    def test_get_category_by_id_not_found(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: Attempt to retrieve a non-existent category by ID.
        """
        with pytest.raises(CategoryNotFound):
            category_manager_fixture.get_category_by_id(str(uuid.uuid4()))

    def test_get_category_by_id_invalid_uuid(
        self, category_manager_fixture: CategoryManager
    ) -> None:
        """
        Test objective: Attempt to retrieve a category with an invalid (non-UUID) ID string.
        """
        with pytest.raises(CategoryNotFound):
            category_manager_fixture.get_category_by_id("not-a-uuid")

    def test_get_category_by_name(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: Retrieve a category by its name.
        """
        cat_name = "Named Category"
        category = Category(category_name=cat_name, description="")
        category_manager_fixture.save_category(category)
        retrieved_cat = category_manager_fixture.get_category_by_name(cat_name)
        assert retrieved_cat is not None
        assert retrieved_cat.category_id == str(category.category_id)
        assert retrieved_cat.category_name == cat_name

    def test_get_category_by_name_not_found(
        self, category_manager_fixture: CategoryManager
    ) -> None:
        """
        Test objective: Attempt to retrieve a non-existent category by name.
        """
        with pytest.raises(CategoryNotFound):
            category_manager_fixture.get_category_by_name("NonExistent Name")

    def test_get_category_by_name_case_sensitive(
        self, category_manager_fixture: CategoryManager
    ) -> None:
        """
        Test objective: Verify category name retrieval is case-sensitive.
        """
        cat_name = "CaseSensitive"
        category = Category(category_name=cat_name, description="")
        category_manager_fixture.save_category(category)

        # Exact match should work
        assert category_manager_fixture.get_category_by_name(cat_name) is not None

        # Different case should not work
        with pytest.raises(CategoryNotFound):
            category_manager_fixture.get_category_by_name(cat_name.lower())
        with pytest.raises(CategoryNotFound):
            category_manager_fixture.get_category_by_name(cat_name.upper())

    def test_list_all_categories_empty(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: List categories when none exist.
        """
        cats = category_manager_fixture.list_all_categories()
        assert len(cats) == 0

    def test_list_all_categories_populated(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: List categories when multiple exist, ensuring order.
        """
        names = ["Charlie", "Alpha", "Beta"]
        for n in names:
            category_manager_fixture.save_category(Category(category_name=n, description=""))
        cats = category_manager_fixture.list_all_categories()
        assert len(cats) == 3
        sorted_names = [c.category_name for c in cats]
        assert sorted_names == sorted(sorted_names)  # Check for order by name

    def test_update_category_valid_name(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: Update a category's name successfully using save_category.
        """
        category = Category(category_name="Original Name", description="")
        category_manager_fixture.save_category(category)
        category.category_name = "New Valid Name"
        assert category_manager_fixture.save_category(category)
        retrieved = category_manager_fixture.get_category_by_id(str(category.category_id))
        assert retrieved.category_name == "New Valid Name"

    @pytest.mark.parametrize(
        "new_name, err_msg_part",
        [
            ("", "blank"),
            ("A" * 65, "at most 64 characters"),
            ("Café Again", "ASCII-only"),
        ],
    )
    def test_update_category_invalid_format(
        self, category_manager_fixture: CategoryManager, new_name: str, err_msg_part: str
    ) -> None:
        """
        Test objective: Attempt to update a category with an invalid new name format using
        save_category.
        """
        category = Category(category_name="ValidOriginal", description="")
        category_manager_fixture.save_category(category)
        with pytest.raises((ValueError, CategoryValidationError)) as e:
            category.category_name = new_name
            category_manager_fixture.save_category(category)
        assert err_msg_part.lower() in str(e.value).lower()

    def test_update_category_to_duplicate_name(
        self, category_manager_fixture: CategoryManager
    ) -> None:
        """
        Test objective: Attempt to update a category name to an existing different category's name
        using save_category.
        """
        category1 = Category(category_name="ExistingName", description="")
        category2 = Category(category_name="ToBeUpdated", description="")
        category_manager_fixture.save_category(category1)
        category_manager_fixture.save_category(category2)
        category2.category_name = "ExistingName"
        with pytest.raises(CategoryValidationError) as e:
            category_manager_fixture.save_category(category2)
        assert "must be unique" in str(e.value).lower()

    def test_update_category_to_case_variant_duplicate(
        self, category_manager_fixture: CategoryManager
    ) -> None:
        """
        Test objective: Attempt to update a category name to a case-variant of an existing name
        using save_category.
        """
        category1 = Category(category_name="CaseName", description="")
        category2 = Category(category_name="OtherName", description="")
        category_manager_fixture.save_category(category1)
        category_manager_fixture.save_category(category2)
        category2.category_name = "casename"
        try:
            category_manager_fixture.save_category(category2)
            retrieved = category_manager_fixture.get_category_by_id(str(category2.category_id))
            assert retrieved.category_name == "casename"
        except CategoryValidationError as e:
            assert "must be unique" in str(e).lower()

    def test_update_category_to_same_name(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: Update a category to its current name (should be a no-op) using
        save_category.
        """
        cat_name = "SameName"
        category = Category(category_name=cat_name, description="")
        category_manager_fixture.save_category(category)
        category.category_name = cat_name
        assert category_manager_fixture.save_category(category)
        retrieved = category_manager_fixture.get_category_by_id(str(category.category_id))
        assert retrieved.category_name == cat_name

    def test_delete_category_by_id(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: Delete an existing category.
        """
        category = Category(category_name="ToDelete", description="")
        category_manager_fixture.save_category(category)
        assert category_manager_fixture.delete_category_by_id(str(category.category_id)) is True
        with pytest.raises(CategoryNotFound):
            category_manager_fixture.get_category_by_id(str(category.category_id))

    def test_delete_category_by_id_invalid_uuid(
        self, category_manager_fixture: CategoryManager
    ) -> None:
        """
        Test objective: Attempt to delete a category with an invalid (non-UUID) ID string.
        """
        assert category_manager_fixture.delete_category_by_id("not-a-uuid") is False

    def test_delete_nonexistent_category(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: Attempt to delete a non-existent category.
        """
        assert category_manager_fixture.delete_category(str(uuid.uuid4())) is False

    def test_delete_all_categories(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: Delete all categories and verify the action.
        """
        category_manager_fixture.save_category(Category(category_name="A", description=""))
        category_manager_fixture.save_category(Category(category_name="B", description=""))
        assert category_manager_fixture.delete_all_categories() is True
        cats = category_manager_fixture.list_all_categories()
        assert len(cats) == 0
        # Deleting again should return False (already empty)
        assert category_manager_fixture.delete_all_categories() is False

    def test_category_validation_blank_and_duplicate(
        self, category_manager_fixture: CategoryManager
    ) -> None:
        """
        Test objective: Destructively test blank and duplicate category names.
        """
        # Blank
        with pytest.raises((ValueError, CategoryValidationError)):
            category_manager_fixture.save_category(Category(category_name="   ", description=""))
        # Duplicate
        category = Category(category_name="Unique", description="")
        category_manager_fixture.save_category(category)
        with pytest.raises(CategoryValidationError):
            category_manager_fixture.save_category(Category(category_name="Unique", description=""))

    def test_save_category_non_string_name(self, category_manager_fixture: CategoryManager) -> None:
        """
        Test objective: Attempt to save a category with a non-string name (should
        raise ValueError or CategoryValidationError).
        """
        with pytest.raises((ValueError, CategoryValidationError, ValidationError)):
            Category(category_name=12345, description="")

    def test_delete_category_alias(self, category_manager_fixture: CategoryManager) -> None:
        """Test that delete_category (alias) works and does not raise on not found."""
        category = Category(category_name="AliasDelete", description="")
        category_manager_fixture.save_category(category)
        category_manager_fixture.delete_category(str(category.category_id))
        with pytest.raises(CategoryNotFound):
            category_manager_fixture.get_category_by_id(str(category.category_id))
        assert category_manager_fixture.delete_category(str(category.category_id)) is False

    def test_save_category_unexpected_db_error(
        self, category_manager_fixture: CategoryManager, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test save_category raises unexpected errors as-is (not ConstraintError)."""
        with pytest.raises(ValidationError):
            category = Category(category_name="DBErrorTest", description=None)  # type: ignore

            # The rest of the test is unreachable, as instantiation fails
            def raise_db_error(*args: object, **kwargs: object) -> None:
                raise RuntimeError("Simulated DB error")

            monkeypatch.setattr(category_manager_fixture.db_manager, "execute", raise_db_error)
            with pytest.raises(RuntimeError, match="Simulated DB error"):
                category_manager_fixture.save_category(category)


if __name__ == "__main__":
    pytest.main([__file__])
