"""
Unit tests for models.category_manager.CategoryManager.
Covers CRUD, validation (including DB uniqueness), cascade deletion, and error handling.
"""

import pytest

from db.database_manager import DatabaseManager
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
        category_name = "Alpha"
        cat = category_mgr.create_category(category_name)
        assert cat.category_name == category_name
        assert isinstance(cat.category_id, int)
        assert cat.category_id > 0

        # Verify it's in the DB
        retrieved_cat = category_mgr.get_category_by_id(cat.category_id)
        assert retrieved_cat.category_name == category_name

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
            category_mgr.create_category(name)
        assert err_msg_part.lower() in str(e.value).lower()

    def test_create_category_duplicate_name(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to create a category with a duplicate name.
        """
        category_mgr.create_category("UniqueName")
        with pytest.raises(CategoryValidationError) as e:
            category_mgr.create_category("UniqueName")
        assert "must be unique" in str(e.value).lower()

    def test_get_category_by_id(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Retrieve a category by its ID.
        """
        cat = category_mgr.create_category("Test Category")
        retrieved_cat = category_mgr.get_category_by_id(cat.category_id)
        assert retrieved_cat is not None
        assert retrieved_cat.category_id == cat.category_id
        assert retrieved_cat.category_name == "Test Category"

    def test_get_category_by_id_not_found(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to retrieve a non-existent category by ID.
        """
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_id(99999)

    def test_get_category_by_name(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Retrieve a category by its name.
        """
        cat_name = "Named Category"
        created_cat = category_mgr.create_category(cat_name)
        retrieved_cat = category_mgr.get_category_by_name(cat_name)
        assert retrieved_cat is not None
        assert retrieved_cat.category_id == created_cat.category_id
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
        category_mgr.create_category(cat_name)

        # Exact match should work
        assert category_mgr.get_category_by_name(cat_name) is not None

        # Different case should not work
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_name(cat_name.lower())
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_name(cat_name.upper())

    def test_list_categories_empty(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: List categories when none exist.
        """
        cats = category_mgr.list_categories()
        assert len(cats) == 0

    def test_list_categories_populated(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: List categories when multiple exist, ensuring order.
        """
        category_mgr.create_category("Charlie")
        category_mgr.create_category("Alpha")
        category_mgr.create_category("Beta")
        cats = category_mgr.list_categories()
        assert len(cats) == 3
        names = [c.category_name for c in cats]
        assert names == ["Alpha", "Beta", "Charlie"]  # Check for order by name

    def test_update_category_valid_name(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Update a category's name successfully.
        """
        cat = category_mgr.create_category("Original Name")
        updated_cat = category_mgr.update_category(cat.category_id, "New Valid Name")
        assert updated_cat.category_name == "New Valid Name"
        assert updated_cat.category_id == cat.category_id

        # Verify in DB
        retrieved_cat = category_mgr.get_category_by_id(cat.category_id)
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
        cat = category_mgr.create_category("ValidOriginal")
        with pytest.raises((ValueError, CategoryValidationError)) as e:
            category_mgr.update_category(cat.category_id, new_name)
        assert err_msg_part.lower() in str(e.value).lower()

    def test_update_category_to_duplicate_name(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to update a category name to an existing different category's name.
        """
        category_mgr.create_category("ExistingName")
        cat_to_update = category_mgr.create_category("ToBeUpdated")
        with pytest.raises(CategoryValidationError) as e:
            category_mgr.update_category(cat_to_update.category_id, "ExistingName")
        assert "must be unique" in str(e.value).lower()

    def test_update_category_to_same_name(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Update a category to its current name (should be a no-op).
        """
        cat_name = "SameName"
        cat = category_mgr.create_category(cat_name)
        updated_cat = category_mgr.update_category(cat.category_id, cat_name)
        assert updated_cat.category_name == cat_name

    def test_update_nonexistent_category(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to update a non-existent category.
        """
        with pytest.raises(CategoryNotFound):
            category_mgr.update_category(88888, "New Name")

    def test_delete_category_existing(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Delete an existing category.
        """
        cat = category_mgr.create_category("ToDelete")
        category_mgr.delete_category(cat.category_id)
        with pytest.raises(CategoryNotFound):
            category_mgr.get_category_by_id(cat.category_id)

    def test_delete_nonexistent_category(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Attempt to delete a non-existent category.
        """
        with pytest.raises(CategoryNotFound):
            category_mgr.delete_category(77777)

    def test_delete_category_cascades(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Verify that deleting a category also deletes associated snippets and
        snippet_parts.
        """
        dbm = category_mgr.db_manager
        category = category_mgr.create_category("CascadeTestCategory")

        # Create a snippet associated with this category
        dbm.execute(
            "INSERT INTO snippets (category_id, content) VALUES (?, ?)",
            (category.category_id, "CascadeSnippet"),
        )
        snippet_id = dbm.execute(
            "SELECT snippet_id FROM snippets WHERE category_id = ?", (category.category_id,)
        ).fetchone()[0]

        # Create a snippet part associated with this snippet
        dbm.execute(
            "INSERT INTO snippet_parts (snippet_id, part_index, part_content) VALUES (?, ?, ?)",
            (snippet_id, 1, "Part 1 content"),
        )

        # Verify snippet and part exist
        snippet_row = dbm.execute(
            "SELECT snippet_id FROM snippets WHERE snippet_id = ?", (snippet_id,)
        ).fetchone()
        assert snippet_row is not None
        part_row = dbm.execute(
            "SELECT part_id FROM snippet_parts WHERE snippet_id = ?", (snippet_id,)
        ).fetchone()
        assert part_row is not None

        # Delete the category
        category_mgr.delete_category(category.category_id)

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
            "SELECT part_id FROM snippet_parts WHERE snippet_id = ?", (snippet_id,)
        ).fetchone()
        assert part_row_after_delete is None

    def test_category_validation_blank_and_duplicate(self, category_mgr: CategoryManager) -> None:
        """
        Test objective: Ensure blank names and duplicate names are rejected.
        """
        # Pydantic ValidationError is raised for blank name
        with pytest.raises((ValueError, CategoryValidationError)):
            category_mgr.create_category("")
        # Unique name is accepted
        category_mgr.create_category("UniqueCat")
        # CategoryValidationError is raised for duplicate name
        with pytest.raises(CategoryValidationError):
            category_mgr.create_category("UniqueCat")


if __name__ == "__main__":
    pytest.main([__file__])
