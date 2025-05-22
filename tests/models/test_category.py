"""
Unit tests for models.category.CategoryManager and related logic.
Covers CRUD, validation, cascade deletion, and error handling.
"""

"""
Unit tests for models.category.CategoryManager and related logic.
Covers CRUD, validation, cascade deletion, and error handling.
"""

import sys
from pathlib import Path

# Add project root to path before importing any local modules
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
from db.database_manager import DatabaseManager
from models.category import (
    CategoryManager,
    CategoryValidationError,
    CategoryNotFound,
)


@pytest.fixture(scope="function")
def db_manager(tmp_path):
    db_path = str(tmp_path / "test_core_category.db")
    dbm = DatabaseManager(db_path)
    dbm.init_tables()
    # Create dependent tables for cascade delete tests
    # We'll already created all tables with init_tables
    # This ensures tests use the same schema as the production code
    yield dbm
    dbm.close()


class TestDatabaseManager:
    """Test cases for database initialization and category management."""
    
    def test_init_tables(self, tmp_path: Path) -> None:
        """Test that database tables are properly initialized.
        
        Verifies that the categories table can be created and used.
        """
        db_path = str(tmp_path / "test_init_category.db")
        dbm = DatabaseManager(db_path)
        dbm.init_tables()
        # Table should exist, insert should succeed
        dbm.execute(
            "INSERT INTO categories (category_name) VALUES (?)",
            ("TestCat",)
        )
        row = dbm.execute(
            "SELECT category_name FROM categories WHERE category_name = ?",
            ("TestCat",)
        ).fetchone()
        assert row[0] == "TestCat"
        dbm.close()

    def test_create_category_valid(self, db_manager: DatabaseManager) -> None:
        """Test creating a category with valid data.
        
        Verifies that a category can be created with a valid name.
        """
        cat_mgr = CategoryManager(db_manager)
        cat = cat_mgr.create_category("Alpha")
        assert cat.category_name == "Alpha"
        assert isinstance(cat.category_id, int)

    @pytest.mark.parametrize(
        "name,err",
        [
            ("", "blank"),
            (" ", "blank"),
            ("A" * 65, "at most 64"),
            ("Café", "ASCII"),
        ],
    )
    def test_create_category_invalid(
        self,
        db_manager: DatabaseManager,
        name: str,
        err: str
    ) -> None:
        """Test creating a category with invalid data.
        
        Verifies that appropriate validation errors are raised for invalid names.
        """
        cat_mgr = CategoryManager(db_manager)
        with pytest.raises(CategoryValidationError) as e:
            cat_mgr.create_category(name)
        assert err.lower() in str(e.value).lower()

    def test_create_category_duplicate(self, db_manager: DatabaseManager) -> None:
        """Test creating a duplicate category.
        
        Verifies that duplicate category names are not allowed.
        """
        cat_mgr = CategoryManager(db_manager)
        cat_mgr.create_category("Alpha")
        with pytest.raises(CategoryValidationError) as e:
            cat_mgr.create_category("Alpha")
        assert "unique" in str(e.value).lower()

    def test_list_categories(self, db_manager: DatabaseManager) -> None:
        """Test listing all categories.
        
        Verifies that all created categories are returned.
        """
        cat_mgr = CategoryManager(db_manager)
        cat_mgr.create_category("Alpha")
        cat_mgr.create_category("Beta")
        cats = cat_mgr.list_categories()
        names = [c.category_name for c in cats]
        assert set(names) == {"Alpha", "Beta"}

    def test_rename_category_valid(self, db_manager: DatabaseManager) -> None:
        """Test renaming a category with valid data.
        
        Verifies that a category can be renamed with a valid new name.
        """
        cat_mgr = CategoryManager(db_manager)
        cat = cat_mgr.create_category("Alpha")
        cat2 = cat_mgr.rename_category(cat.category_id, "Bravo")
        assert cat2.category_name == "Bravo"
        assert cat2.category_id == cat.category_id

    @pytest.mark.parametrize(
        "new_name,err",
        [
            ("", "blank"),
            ("B" * 65, "at most 64"),
            ("Tést", "ASCII"),
        ],
    )
    def test_rename_category_invalid(
        self,
        db_manager: DatabaseManager,
        new_name: str,
        err: str
    ) -> None:
        """Test renaming a category with invalid data.
        
        Verifies that appropriate validation errors are raised for invalid names.
        """
        cat_mgr = CategoryManager(db_manager)
        cat = cat_mgr.create_category("Alpha")
        with pytest.raises(CategoryValidationError) as e:
            cat_mgr.rename_category(cat.category_id, new_name)
        assert err.lower() in str(e.value).lower()

    def test_rename_category_to_duplicate(self, db_manager: DatabaseManager) -> None:
        """Test renaming a category to a duplicate name.
        
        Verifies that a category cannot be renamed to an existing category name.
        """
        cat_mgr = CategoryManager(db_manager)
        # Create first category
        cat_mgr.create_category("Alpha")
        # Create second category to test duplicate name validation
        c2 = cat_mgr.create_category("Beta")
        with pytest.raises(CategoryValidationError) as e:
            cat_mgr.rename_category(c2.category_id, "Alpha")
        assert "unique" in str(e.value).lower()

    def test_rename_nonexistent_category(self, db_manager: DatabaseManager) -> None:
        """Test renaming a non-existent category.
        
        Verifies that attempting to rename a non-existent category raises an error.
        """
        cat_mgr = CategoryManager(db_manager)
        with pytest.raises(CategoryNotFound):
            cat_mgr.rename_category(99999, "Gamma")

    def test_delete_category(self, db_manager: DatabaseManager) -> None:
        """Test deleting a category.
        
        Verifies that a category and its associated snippets are properly deleted.
        """
        cat_mgr = CategoryManager(db_manager)
        cat = cat_mgr.create_category("Alpha")
        # Add snippet to category
        cursor = db_manager.execute(
            ("INSERT INTO snippets (category_id, snippet_name) "
             "VALUES (?, ?)"),
            (cat.category_id, "S1")
        )
        # Add content to snippet_parts
        snippet_id = cursor.lastrowid
        db_manager.execute(
            ("INSERT INTO snippet_parts (snippet_id, part_number, content) "
             "VALUES (?, ?, ?)"),
            (snippet_id, 1, "abc")
        )
        # Delete category
        cat_mgr.delete_category(cat.category_id)
        # Confirm deleted
        cats = cat_mgr.list_categories()
        assert all(c.category_id != cat.category_id for c in cats)
        # Confirm snippet deleted
        snips = db_manager.execute(
            "SELECT * FROM snippets WHERE category_id = ?", (cat.category_id,)
        ).fetchall()
        assert len(snips) == 0

    def test_delete_nonexistent_category(self, db_manager: DatabaseManager) -> None:
        """Test deleting a non-existent category.
        
        Verifies that attempting to delete a non-existent category raises an error.
        """
        cat_mgr = CategoryManager(db_manager)
        with pytest.raises(CategoryNotFound):
            cat_mgr.delete_category(99999)


if __name__ == "__main__":
    pytest.main([__file__])
