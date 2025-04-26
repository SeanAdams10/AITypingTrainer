"""
Unit tests for models.category.CategoryManager and related logic.
Covers CRUD, validation, cascade deletion, and error handling as per Prompts/Category.md.
"""
import pytest
import sqlite3
from models.category import CategoryManager, Category, CategoryValidationError, CategoryNotFound
from models.database_manager import DatabaseManager
from typing import List

@pytest.fixture(scope="function")
def db_manager(tmp_path):
    db_path = str(tmp_path / "test_core_category.db")
    dbm = DatabaseManager(db_path)
    dbm.initialize_category_table()
    # Create dependent tables for cascade delete tests
    dbm.execute("""
        CREATE TABLE IF NOT EXISTS snippets (
            snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            snippet_name TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(category_id) ON DELETE CASCADE
        );
    """, commit=True)
    dbm.execute("""
        CREATE TABLE IF NOT EXISTS snippet_parts (
            part_id INTEGER PRIMARY KEY AUTOINCREMENT,
            snippet_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY(snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE
        );
    """, commit=True)
    yield dbm
    dbm.close()

class TestDatabaseManager:
    def test_initialize_category_table(self, tmp_path):
        db_path = str(tmp_path / "test_init_category.db")
        dbm = DatabaseManager(db_path)
        dbm.initialize_category_table()
        # Table should exist, insert should succeed
        dbm.execute("INSERT INTO categories (category_name) VALUES (?)", ("TestCat",), commit=True)
        row = dbm.execute("SELECT category_name FROM categories WHERE category_name = ?", ("TestCat",)).fetchone()
        assert row[0] == "TestCat"
        dbm.close()

    def test_create_category_valid(self, db_manager):
        cat_mgr = CategoryManager(db_manager)
        cat = cat_mgr.create_category("Alpha")
        assert cat.category_name == "Alpha"
        assert isinstance(cat.category_id, int)

    @pytest.mark.parametrize("name,err", [
        ("", "blank"),
        (" ", "blank"),
        ("A"*65, "at most 64"),
        ("Café", "ASCII"),
    ])
    def test_create_category_invalid(self, db_manager, name, err):
        cat_mgr = CategoryManager(db_manager)
        with pytest.raises(CategoryValidationError) as e:
            cat_mgr.create_category(name)
        assert err.lower() in str(e.value).lower()

    def test_create_category_duplicate(self, db_manager):
        cat_mgr = CategoryManager(db_manager)
        cat_mgr.create_category("Alpha")
        with pytest.raises(CategoryValidationError) as e:
            cat_mgr.create_category("Alpha")
        assert "unique" in str(e.value).lower()

    def test_list_categories(self, db_manager):
        cat_mgr = CategoryManager(db_manager)
        cat_mgr.create_category("Alpha")
        cat_mgr.create_category("Beta")
        cats = cat_mgr.list_categories()
        names = [c.category_name for c in cats]
        assert set(names) == {"Alpha", "Beta"}

    def test_rename_category_valid(self, db_manager):
        cat_mgr = CategoryManager(db_manager)
        cat = cat_mgr.create_category("Alpha")
        cat2 = cat_mgr.rename_category(cat.category_id, "Bravo")
        assert cat2.category_name == "Bravo"
        assert cat2.category_id == cat.category_id

    @pytest.mark.parametrize("new_name,err", [
        ("", "blank"),
        ("B"*65, "at most 64"),
        ("Tést", "ASCII"),
    ])
    def test_rename_category_invalid(self, db_manager, new_name, err):
        cat_mgr = CategoryManager(db_manager)
        cat = cat_mgr.create_category("Alpha")
        with pytest.raises(CategoryValidationError) as e:
            cat_mgr.rename_category(cat.category_id, new_name)
        assert err.lower() in str(e.value).lower()

    def test_rename_category_to_duplicate(self, db_manager):
        cat_mgr = CategoryManager(db_manager)
        c1 = cat_mgr.create_category("Alpha")
        c2 = cat_mgr.create_category("Beta")
        with pytest.raises(CategoryValidationError) as e:
            cat_mgr.rename_category(c2.category_id, "Alpha")
        assert "unique" in str(e.value).lower()

    def test_rename_nonexistent_category(self, db_manager):
        cat_mgr = CategoryManager(db_manager)
        with pytest.raises(CategoryNotFound):
            cat_mgr.rename_category(99999, "Gamma")

    def test_delete_category(self, db_manager):
        cat_mgr = CategoryManager(db_manager)
        cat = cat_mgr.create_category("Alpha")
        # Add snippet to category
        db_manager.execute("INSERT INTO snippets (category_id, snippet_name, content) VALUES (?, ?, ?)", (cat.category_id, "S1", "abc"), commit=True)
        # Delete category
        cat_mgr.delete_category(cat.category_id)
        # Confirm deleted
        cats = cat_mgr.list_categories()
        assert all(c.category_id != cat.category_id for c in cats)
        # Confirm snippet deleted
        snips = db_manager.execute("SELECT * FROM snippets WHERE category_id = ?", (cat.category_id,)).fetchall()
        assert len(snips) == 0

    def test_delete_nonexistent_category(self, db_manager):
        cat_mgr = CategoryManager(db_manager)
        with pytest.raises(CategoryNotFound):
            cat_mgr.delete_category(99999)
