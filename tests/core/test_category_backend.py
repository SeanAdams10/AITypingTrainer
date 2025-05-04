import pytest
from models.category import Category, CategoryManager
from db.database_manager import DatabaseManager

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_category.db"
    db = DatabaseManager.get_instance()
    db.set_db_path(str(db_path))
    db.initialize_database()
    yield db

@pytest.fixture
def manager(temp_db):
    return CategoryManager(db=temp_db)

# --- Security ---
def test_category_sql_injection_attempt(manager):
    with pytest.raises(ValueError):
        manager.add_category("Robert'); DROP TABLE text_category;--")
