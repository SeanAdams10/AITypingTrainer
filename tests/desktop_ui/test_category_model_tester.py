"""
Tests for CategoryModelTester functionality (validates CategoryManager logic).
"""

import pytest

from PyQt5.QtWidgets import QApplication, QMainWindow

from models.category import CategoryValidationError
from models.category_manager import CategoryManager
from db.database_manager import DatabaseManager


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_category.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    yield db
    db.close()


@pytest.fixture
def category_mgr(temp_db):
    return CategoryManager(temp_db)


def test_add_and_list_categories(category_mgr: CategoryManager):
    cat = category_mgr.create_category("TestCat")
    cats = category_mgr.list_categories()
    assert any(c.category_id == cat.category_id for c in cats)
    assert any(c.category_name == "TestCat" for c in cats)


def test_rename_category(category_mgr: CategoryManager):
    cat = category_mgr.create_category("ToRename")
    category_mgr.rename_category(cat.category_id, "RenamedCat")
    updated = next(
        c for c in category_mgr.list_categories() if c.category_id == cat.category_id
    )
    assert updated.category_name == "RenamedCat"


def test_delete_category(category_mgr: CategoryManager):
    cat = category_mgr.create_category("ToDelete")
    category_mgr.delete_category(cat.category_id)
    cats = category_mgr.list_categories()
    assert not any(c.category_id == cat.category_id for c in cats)


def test_category_validation(category_mgr: CategoryManager):
    # Name required
    with pytest.raises(CategoryValidationError):
        category_mgr.create_category("")
    # Duplicate name
    category_mgr.create_category("UniqueCat")
    with pytest.raises(CategoryValidationError):
        category_mgr.create_category("UniqueCat")
