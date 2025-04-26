"""
Unit tests for models.category.CategoryManager and related logic.
Covers CRUD, validation, cascade deletion, and error handling as per Prompts/Category.md.
"""
import pytest
import sqlite3
from models.category import CategoryManager, Category, CategoryValidationError, CategoryNotFound
from typing import List

@pytest.fixture(scope="function")
def temp_db(tmp_path):
    db_path = str(tmp_path / "test_core_category.db")
    # Patch the CategoryManager DB_PATH
    CategoryManager.DB_PATH = db_path
    # Create schema
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snippets (
            snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            snippet_name TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(category_id) ON DELETE CASCADE
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snippet_parts (
            part_id INTEGER PRIMARY KEY AUTOINCREMENT,
            snippet_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY(snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()
    yield db_path

class TestCategoryManager:
    def test_create_category_valid(self, temp_db):
        cat = CategoryManager.create_category("Alpha")
        assert cat.category_name == "Alpha"
        assert isinstance(cat.category_id, int)

    @pytest.mark.parametrize("name,err", [
        ("", "blank"),
        (" ", "blank"),
        ("A"*65, "at most 64"),
        ("Café", "ASCII"),
    ])
    def test_create_category_invalid(self, temp_db, name, err):
        with pytest.raises(CategoryValidationError) as e:
            CategoryManager.create_category(name)
        assert err.lower() in str(e.value).lower()

    def test_create_category_duplicate(self, temp_db):
        CategoryManager.create_category("Alpha")
        with pytest.raises(CategoryValidationError) as e:
            CategoryManager.create_category("Alpha")
        assert "unique" in str(e.value).lower()

    def test_list_categories(self, temp_db):
        CategoryManager.create_category("Alpha")
        CategoryManager.create_category("Beta")
        cats = CategoryManager.list_categories()
        names = [c.category_name for c in cats]
        assert set(names) == {"Alpha", "Beta"}

    def test_rename_category_valid(self, temp_db):
        cat = CategoryManager.create_category("Alpha")
        cat2 = CategoryManager.rename_category(cat.category_id, "Bravo")
        assert cat2.category_name == "Bravo"
        assert cat2.category_id == cat.category_id

    @pytest.mark.parametrize("new_name,err", [
        ("", "blank"),
        ("B"*65, "at most 64"),
        ("Tést", "ASCII"),
    ])
    def test_rename_category_invalid(self, temp_db, new_name, err):
        cat = CategoryManager.create_category("Alpha")
        with pytest.raises(CategoryValidationError) as e:
            CategoryManager.rename_category(cat.category_id, new_name)
        assert err.lower() in str(e.value).lower()

    def test_rename_category_to_duplicate(self, temp_db):
        c1 = CategoryManager.create_category("Alpha")
        c2 = CategoryManager.create_category("Beta")
        with pytest.raises(CategoryValidationError) as e:
            CategoryManager.rename_category(c2.category_id, "Alpha")
        assert "unique" in str(e.value).lower()

    def test_rename_nonexistent_category(self, temp_db):
        with pytest.raises(CategoryNotFound):
            CategoryManager.rename_category(99999, "Gamma")

    def test_delete_category(self, temp_db):
        cat = CategoryManager.create_category("Alpha")
        # Add snippet to category
        conn = sqlite3.connect(CategoryManager.DB_PATH)
        conn.execute("INSERT INTO snippets (category_id, snippet_name, content) VALUES (?, ?, ?)", (cat.category_id, "S1", "abc"))
        conn.commit()
        # Delete category
        CategoryManager.delete_category(cat.category_id)
        # Confirm deleted
        cats = CategoryManager.list_categories()
        assert all(c.category_id != cat.category_id for c in cats)
        # Confirm snippet deleted
        snips = conn.execute("SELECT * FROM snippets WHERE category_id = ?", (cat.category_id,)).fetchall()
        assert len(snips) == 0
        conn.close()

    def test_delete_nonexistent_category(self, temp_db):
        with pytest.raises(CategoryNotFound):
            CategoryManager.delete_category(99999)
