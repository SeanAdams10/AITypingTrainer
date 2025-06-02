"""
Unit tests for models.category_manager.CategoryManager.
Covers CRUD, validation (including DB uniqueness), cascade deletion, and error handling.
"""

import pytest
import uuid
from db.database_manager import DatabaseManager
from models.category import Category
from models.category_manager import CategoryManager, CategoryNotFound, CategoryValidationError


@pytest.fixture(scope="function")
def category_mgr(db_with_tables: DatabaseManager) -> CategoryManager:
    """
    Fixture: Provides a CategoryManager with a fresh, initialized database.
    """
    return CategoryManager(db_with_tables)


class TestCategoryManager:
    """Test suite for CategoryManager covering all CRUD and validation logic."""

    def test_create_category_valid(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Create a category with a valid name and verify persistence.
        """
        category = Category(category_name="Alpha")
        assert category_mgr.save_category(category)
        assert category.category_name == "Alpha"
        assert isinstance(category.category_id, str)
        # Verify it's in the DB
        retrieved_cat = category_mgr.get_category_by_id(category.category_id)
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
        self, category_mgr: CategoryManager, name: str, err_msg_part: str
    ) -> None:
        """
        Test objective: Attempt to create a category with an invalid name format.
        """
        with pytest.raises((ValueError, CategoryValidationError)) as e:
            category = Category(category_name=name)
            category_mgr.save_category(category)
        assert err_msg_part.lower() in str(e.value).lower()

    def test_create_category_duplicate_name(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to create a category with a duplicate name.
        """
        category1 = Category(category_name="UniqueName")
        category_mgr.save_category(category1)
        category2 = Category(category_name="UniqueName")
        with pytest.raises(CategoryValidationError) as e:
            category_mgr.save_category(category2)
        assert "must be unique" in str(e.value).lower()

    def test_get_category_by_id(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Retrieve a category by its ID.
        """
        category = Category(category_name="Test Category")
        category_mgr.save_category(category)
        retrieved_cat = category_mgr.get_category_by_id(category.category_id)
        assert retrieved_cat is not None
        assert retrieved_cat.category_id == category.category_id
        assert retrieved_cat.category_name == "Test Category"

    def test_get_category_by_id_not_found(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to retrieve a non-existent category by ID.
        """
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_id(str(uuid.uuid4()))

    def test_get_category_by_id_invalid_uuid(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to retrieve a category with an invalid (non-UUID) ID string.
        """
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_id("not-a-uuid")

    def test_get_category_by_name(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Retrieve a category by its name.
        """
        cat_name = "Named Category"
        category = Category(category_name=cat_name)
        category_mgr.save_category(category)
        retrieved_cat = category_mgr.get_category_by_name(cat_name)
        assert retrieved_cat is not None
        assert retrieved_cat.category_id == category.category_id
        assert retrieved_cat.category_name == cat_name

    def test_get_category_by_name_not_found(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to retrieve a non-existent category by name.
        """
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_name("NonExistent Name")

    def test_get_category_by_name_case_sensitive(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Verify category name retrieval is case-sensitive.
        """
        cat_name = "CaseSensitive"
        category = Category(category_name=cat_name)
        category_mgr.save_category(category)

        # Exact match should work
        assert category_mgr.get_category_by_name(cat_name) is not None

        # Different case should not work
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_name(cat_name.lower())
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_name(cat_name.upper())

    def test_list_all_categories_empty(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: List categories when none exist.
        """
        cats = category_mgr.list_all_categories()
        assert len(cats) == 0

    def test_list_all_categories_populated(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: List categories when multiple exist, ensuring order.
        """
        names = ["Charlie", "Alpha", "Beta"]
        for n in names:
            category_mgr.save_category(Category(category_name=n))
        cats = category_mgr.list_all_categories()
        assert len(cats) == 3
        sorted_names = [c.category_name for c in cats]
        assert sorted_names == sorted(sorted_names)  # Check for order by name

    def test_update_category_valid_name(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Update a category's name successfully.
        """
        category = Category(category_name="Original Name")
        category_mgr.save_category(category)
        updated_cat = category_mgr.update_category(category.category_id, "New Valid Name")
        assert updated_cat.category_name == "New Valid Name"
        assert updated_cat.category_id == category.category_id

        # Verify in DB
        retrieved_cat = category_mgr.get_category_by_id(category.category_id)
        assert retrieved_cat.category_name == "New Valid Name"

    @pytest.mark.parametrize(
        "new_name, err_msg_part",
        [
            ("", "blank"),
            ("A" * 65, "at most 64 characters"),
            ("Café Again", "ASCII-only"),
        ],
    )
    def test_update_category_invalid_format(
        self, category_mgr: CategoryManager, new_name: str, err_msg_part: str
    ) -> None:
        """
        Test objective: Attempt to update a category with an invalid new name format.
        """
        category = Category(category_name="ValidOriginal")
        category_mgr.save_category(category)
        with pytest.raises((ValueError, CategoryValidationError)) as e:
            category_mgr.update_category(category.category_id, new_name)
        assert err_msg_part.lower() in str(e.value).lower()

    def test_update_category_to_duplicate_name(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to update a category name to an existing different category's name.
        """
        category1 = Category(category_name="ExistingName")
        category2 = Category(category_name="ToBeUpdated")
        category_mgr.save_category(category1)
        category_mgr.save_category(category2)
        with pytest.raises(CategoryValidationError) as e:
            category_mgr.update_category(category2.category_id, "ExistingName")
        assert "must be unique" in str(e.value).lower()

    def test_update_category_to_case_variant_duplicate(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to update a category name to a case-variant of an
        existing name (should allow if case-sensitive, else fail).
        """
        category1 = Category(category_name="CaseName")
        category2 = Category(category_name="OtherName")
        category_mgr.save_category(category1)
        category_mgr.save_category(category2)
        # If uniqueness is case-sensitive, this should succeed; if not, should fail
        try:
            updated = category_mgr.update_category(category2.category_id, "casename")
            assert updated.category_name == "casename"
        except CategoryValidationError as e:
            assert "must be unique" in str(e).lower()

    def test_update_category_to_same_name(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Update a category to its current name (should be a no-op).
        """
        cat_name = "SameName"
        category = Category(category_name=cat_name)
        category_mgr.save_category(category)
        updated_cat = category_mgr.update_category(category.category_id, cat_name)
        assert updated_cat.category_name == cat_name

    def test_update_nonexistent_category(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to update a non-existent category.
        """
        with pytest.raises(CategoryNotFound):
            category_mgr.update_category(str(uuid.uuid4()), "New Name")

    def test_delete_category_by_id(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Delete an existing category.
        """
        category = Category(category_name="ToDelete")
        category_mgr.save_category(category)
        category_mgr.delete_category_by_id(category.category_id)
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_id(category.category_id)

    def test_delete_category_by_id_invalid_uuid(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to delete a category with an invalid (non-UUID) ID string.
        """
        with pytest.raises(CategoryNotFound):
            category_mgr.delete_category_by_id("not-a-uuid")

    def test_delete_nonexistent_category(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to delete a non-existent category.
        """
        with pytest.raises(CategoryNotFound):
            category_mgr.delete_category(str(uuid.uuid4()))

    def test_delete_all_categories(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Delete all categories and verify the action.
        """
        category_mgr.save_category(Category(category_name="A"))
        category_mgr.save_category(Category(category_name="B"))
        category_mgr.delete_all_categories()
        cats = category_mgr.list_all_categories()
        assert len(cats) == 0

    def test_delete_category_cascades(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Verify that deleting a category also deletes associated snippets and
        snippet_parts.
        """
        dbm = category_mgr.db_manager
        category = Category(category_name="CascadeTestCategory")
        category_mgr.save_category(category)

        # Create a snippet associated with this category
        snippet_id = str(uuid.uuid4())
        dbm.execute(
            "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            (snippet_id, category.category_id, "CascadeSnippet"),
        )
        # Create a snippet part associated with this snippet
        part_id = str(uuid.uuid4())
        dbm.execute(
            "INSERT INTO snippet_parts (part_id, snippet_id, part_number, content) "
            "VALUES (?, ?, ?, ?)",
            (part_id, snippet_id, 1, "Part 1 content"),
        )

        # Verify snippet and part exist
        snippet_row = dbm.execute(
            "SELECT snippet_id FROM snippets WHERE snippet_id = ?", (snippet_id,)
        ).fetchone()
        assert snippet_row is not None
        part_row = dbm.execute(
            "SELECT part_number FROM snippet_parts WHERE snippet_id = ?", (snippet_id,)
        ).fetchone()
        assert part_row is not None

        # Delete the category
        category_mgr.delete_category_by_id(category.category_id)

        # Verify category is deleted
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_id(category.category_id)

        # Verify associated snippet is deleted
        snippet_row_after_delete = dbm.execute(
            "SELECT snippet_id FROM snippets WHERE snippet_id = ?", (snippet_id,)
        ).fetchone()
        assert snippet_row_after_delete is None

        # Verify associated snippet part is deleted
        part_row_after_delete = dbm.execute(
            "SELECT part_number FROM snippet_parts WHERE snippet_id = ?", (snippet_id,)
        ).fetchone()
        assert part_row_after_delete is None

    def test_category_validation_blank_and_duplicate(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Destructively test blank and duplicate category names.
        """
        # Blank
        with pytest.raises((ValueError, CategoryValidationError)):
            category_mgr.save_category(Category(category_name="   "))
        # Duplicate
        category = Category(category_name="Unique")
        category_mgr.save_category(category)
        with pytest.raises(CategoryValidationError):
            category_mgr.save_category(Category(category_name="Unique"))

    def test_save_category_non_string_name(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to save a category with a non-string name (should
        raise ValueError or CategoryValidationError).
        """
        with pytest.raises((ValueError, CategoryValidationError)):
            category_mgr.save_category(Category(category_name=12345))

    def test_delete_category_alias(self, category_mgr: CategoryManager) -> None:
        """Test that delete_category (alias) works and raises on not found."""
        category = Category(category_name="AliasDelete")
        category_mgr.save_category(category)
        category_mgr.delete_category(category.category_id)
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_id(category.category_id)
        # Try deleting again, should raise
        with pytest.raises(CategoryNotFound):
            category_mgr.delete_category(category.category_id)

    def test_save_category_unexpected_db_error(
        self, category_mgr: CategoryManager, monkeypatch: object
    ) -> None:
        """Test save_category raises unexpected errors as-is (not ConstraintError)."""
        category = Category(category_name="DBErrorTest")
        def raise_db_error(*args: object, **kwargs: object) -> None:
            raise RuntimeError("Simulated DB error")
        monkeypatch.setattr(category_mgr.db_manager, "execute", raise_db_error)
        with pytest.raises(RuntimeError, match="Simulated DB error"):
            category_mgr.save_category(category)


if __name__ == "__main__":
    pytest.main([__file__])
