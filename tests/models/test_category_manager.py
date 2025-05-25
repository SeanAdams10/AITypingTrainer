"""
Unit tests for models.category_manager.CategoryManager.
Covers CRUD, validation (including DB uniqueness), cascade deletion, and error handling.
"""
# Standard library imports
import sys
from pathlib import Path
from typing import Generator

# Third-party imports
import pytest

# Add project root to path BEFORE importing any local modules
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Local application imports
from db.database_manager import DatabaseManager  # noqa: E402
from models.category import Category, CategoryNotFound, CategoryValidationError  # noqa: E402
from models.category_manager import CategoryManager  # noqa: E402


@pytest.fixture(scope="function")
def db_manager_for_category(tmp_path: Path) -> Generator[DatabaseManager, None, None]:
    """
    Provides a DatabaseManager instance with an initialized, temporary database
    for category manager tests.
    """
    db_path = str(tmp_path / "test_category_manager.db")
    dbm = DatabaseManager(db_path)
    dbm.init_tables()  # Ensures all tables, including dependencies, are created
    yield dbm
    dbm.close()


class TestCategoryManager:
    """Test cases for CategoryManager."""

    def test_create_category_valid(self, db_manager_for_category: DatabaseManager) -> None:
        """Test objective: Create a category with a valid name."""
        cat_mgr = CategoryManager(db_manager_for_category)
        category_name = "Alpha"
        cat = cat_mgr.create_category(category_name)
        assert cat.category_name == category_name
        assert isinstance(cat.category_id, int)
        assert cat.category_id > 0

        # Verify it's in the DB
        retrieved_cat = cat_mgr.get_category_by_id(cat.category_id)
        assert retrieved_cat.category_name == category_name

    @pytest.mark.parametrize(
        "name, err_msg_part",
        [
            ("", "blank"),
            ("  ", "blank"),  # Should be stripped by model, but manager might re-check
            ("A" * 65, "at most 64 characters"),
            ("Café NonASCII", "ASCII-only"),
        ],
    )
    def test_create_category_invalid_format(
        self, db_manager_for_category: DatabaseManager, name: str, err_msg_part: str
    ) -> None:
        """Test objective: Attempt to create a category with an invalid name format."""
        cat_mgr = CategoryManager(db_manager_for_category)
        # Pydantic's ValidationError is raised by the Category model if format is wrong
        # CategoryManager's _validate_name_uniqueness raises CategoryValidationError for uniqueness
        with pytest.raises((ValueError, CategoryValidationError)) as e:  # ValueError from Pydantic
            cat_mgr.create_category(name)
        assert err_msg_part.lower() in str(e.value).lower()

    def test_create_category_duplicate_name(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """Test objective: Attempt to create a category with a duplicate name."""
        cat_mgr = CategoryManager(db_manager_for_category)
        cat_mgr.create_category("UniqueName")
        with pytest.raises(CategoryValidationError) as e:
            cat_mgr.create_category("UniqueName")
        assert "must be unique" in str(e.value).lower()

    def test_get_category_by_id(self, db_manager_for_category: DatabaseManager) -> None:
        """Test objective: Retrieve a category by its ID."""
        cat_mgr = CategoryManager(db_manager_for_category)
        cat = cat_mgr.create_category("Test Category")
        retrieved_cat = cat_mgr.get_category_by_id(cat.category_id)
        assert retrieved_cat is not None
        assert retrieved_cat.category_id == cat.category_id
        assert retrieved_cat.category_name == "Test Category"

    def test_get_category_by_id_not_found(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """Test objective: Attempt to retrieve a non-existent category by ID."""
        cat_mgr = CategoryManager(db_manager_for_category)
        with pytest.raises(CategoryNotFound):
            cat_mgr.get_category_by_id(99999)

    def test_get_category_by_name(self, db_manager_for_category: DatabaseManager) -> None:
        """Test objective: Retrieve a category by its name."""
        cat_mgr = CategoryManager(db_manager_for_category)
        cat_name = "Named Category"
        created_cat = cat_mgr.create_category(cat_name)
        retrieved_cat = cat_mgr.get_category_by_name(cat_name)
        assert retrieved_cat is not None
        assert retrieved_cat.category_id == created_cat.category_id
        assert retrieved_cat.category_name == cat_name

    def test_get_category_by_name_not_found(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """Test objective: Attempt to retrieve a non-existent category by name."""
        cat_mgr = CategoryManager(db_manager_for_category)
        with pytest.raises(CategoryNotFound):
            cat_mgr.get_category_by_name("NonExistent Name")

    def test_get_category_by_name_case_sensitive(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """Test objective: Verify category name retrieval is case-sensitive."""
        cat_mgr = CategoryManager(db_manager_for_category)
        cat_name = "CaseSensitive"
        cat_mgr.create_category(cat_name)

        # Exact match should work
        assert cat_mgr.get_category_by_name(cat_name) is not None

        # Different case should not work
        with pytest.raises(CategoryNotFound):
            cat_mgr.get_category_by_name(cat_name.lower())
        with pytest.raises(CategoryNotFound):
            cat_mgr.get_category_by_name(cat_name.upper())

    def test_list_categories_empty(self, db_manager_for_category: DatabaseManager) -> None:
        """Test objective: List categories when none exist."""
        cat_mgr = CategoryManager(db_manager_for_category)
        cats = cat_mgr.list_categories()
        assert len(cats) == 0

    def test_list_categories_populated(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """Test objective: List categories when multiple exist, ensuring order."""
        cat_mgr = CategoryManager(db_manager_for_category)
        cat_mgr.create_category("Charlie")
        cat_mgr.create_category("Alpha")
        cat_mgr.create_category("Beta")
        cats = cat_mgr.list_categories()
        assert len(cats) == 3
        names = [c.category_name for c in cats]
        assert names == ["Alpha", "Beta", "Charlie"]  # Check for order by name

    def test_update_category_valid_name(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """Test objective: Update a category's name successfully."""
        cat_mgr = CategoryManager(db_manager_for_category)
        cat = cat_mgr.create_category("Original Name")
        updated_cat = cat_mgr.update_category(cat.category_id, "New Valid Name")
        assert updated_cat.category_name == "New Valid Name"
        assert updated_cat.category_id == cat.category_id

        # Verify in DB
        retrieved_cat = cat_mgr.get_category_by_id(cat.category_id)
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
        self, db_manager_for_category: DatabaseManager, new_name: str, err_msg_part: str
    ) -> None:
        """Test objective: Attempt to update a category with an invalid new name format."""
        cat_mgr = CategoryManager(db_manager_for_category)
        cat = cat_mgr.create_category("ValidOriginal")
        with pytest.raises((ValueError, CategoryValidationError)) as e:  # ValueError from Pydantic
            cat_mgr.update_category(cat.category_id, new_name)
        assert err_msg_part.lower() in str(e.value).lower()

    def test_update_category_to_duplicate_name(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """Test objective: Attempt to update a category name to an existing different category's name."""
        cat_mgr = CategoryManager(db_manager_for_category)
        cat_mgr.create_category("ExistingName")
        cat_to_update = cat_mgr.create_category("ToBeUpdated")
        with pytest.raises(CategoryValidationError) as e:
            cat_mgr.update_category(cat_to_update.category_id, "ExistingName")
        assert "must be unique" in str(e.value).lower()

    def test_update_category_to_same_name(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """Test objective: Update a category to its current name (should be a no-op)."""
        cat_mgr = CategoryManager(db_manager_for_category)
        cat_name = "SameName"
        cat = cat_mgr.create_category(cat_name)
        updated_cat = cat_mgr.update_category(cat.category_id, cat_name)
        assert updated_cat.category_name == cat_name
        # Further check if any actual DB update was avoided (implementation dependent)

    def test_update_nonexistent_category(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """Test objective: Attempt to update a non-existent category."""
        cat_mgr = CategoryManager(db_manager_for_category)
        with pytest.raises(CategoryNotFound):
            cat_mgr.update_category(88888, "New Name")

    def test_delete_category_existing(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """Test objective: Delete an existing category."""
        cat_mgr = CategoryManager(db_manager_for_category)
        cat = cat_mgr.create_category("ToDelete")
        cat_mgr.delete_category(cat.category_id)
        with pytest.raises(CategoryNotFound):
            cat_mgr.get_category_by_id(cat.category_id)

    def test_delete_nonexistent_category(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """Test objective: Attempt to delete a non-existent category."""
        cat_mgr = CategoryManager(db_manager_for_category)
        with pytest.raises(CategoryNotFound):
            cat_mgr.delete_category(77777)

    def test_delete_category_cascades(
        self, db_manager_for_category: DatabaseManager
    ) -> None:
        """
        Test objective: Verify that deleting a category also deletes associated snippets
        and snippet_parts.
        """
        cat_mgr = CategoryManager(db_manager_for_category)
        category = cat_mgr.create_category("CascadeTestCategory")

        # Create a snippet associated with this category
        snippet_cursor = db_manager_for_category.execute(
            "INSERT INTO snippets (category_id, snippet_name, difficulty_level) "
            "VALUES (?, ?, ?)",
            (category.category_id, "CascadeSnippet", 1),
        )
        snippet_id = snippet_cursor.lastrowid
        assert snippet_id is not None

        # Create a snippet part associated with this snippet
        db_manager_for_category.execute(
            "INSERT INTO snippet_parts (snippet_id, part_number, content) "
            "VALUES (?, ?, ?)",
            (snippet_id, 1, "Part 1 content"),
        )

        # Verify snippet and part exist
        snippet_row = db_manager_for_category.execute(
            "SELECT snippet_id FROM snippets WHERE snippet_id = ?", (snippet_id,)
        ).fetchone()
        assert snippet_row is not None
        part_row = db_manager_for_category.execute(
            "SELECT part_id FROM snippet_parts WHERE snippet_id = ?", (snippet_id,)
        ).fetchone()
        assert part_row is not None

        # Delete the category
        cat_mgr.delete_category(category.category_id)

        # Verify category is deleted
        with pytest.raises(CategoryNotFound):
            cat_mgr.get_category_by_id(category.category_id)

        # Verify associated snippet is deleted
        snippet_row_after_delete = db_manager_for_category.execute(
            "SELECT snippet_id FROM snippets WHERE snippet_id = ?", (snippet_id,)
        ).fetchone()
        assert snippet_row_after_delete is None

        # Verify associated snippet part is deleted
        part_row_after_delete = db_manager_for_category.execute(
            "SELECT part_id FROM snippet_parts WHERE snippet_id = ?", (snippet_id,)
        ).fetchone()
        assert part_row_after_delete is None


if __name__ == "__main__":
    pytest.main([__file__])
