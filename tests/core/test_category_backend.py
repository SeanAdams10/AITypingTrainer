import pytest
from models.category import Category
from db.database_manager import DatabaseManager
import string

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_category.db"
    db = DatabaseManager.get_instance()
    db.set_db_path(str(db_path))
    db.init_db()
    yield db

@pytest.fixture
def category_service(temp_db):
    return Category()

# --- Category Creation ---
def test_create_valid_category(category_service):
    cat_id = category_service.create_category("Alpha")
    assert isinstance(cat_id, int)
    cats = category_service.list_categories()
    assert any(c[1] == "Alpha" for c in cats)

def test_create_category_ascii_required(category_service):
    with pytest.raises(ValueError):
        category_service.create_category("Café")  # Non-ASCII

    with pytest.raises(ValueError):
        category_service.create_category("")  # Empty

    long_name = "A" * 65
    with pytest.raises(ValueError):
        category_service.create_category(long_name)

def test_create_duplicate_category(category_service):
    category_service.create_category("Beta")
    with pytest.raises(ValueError):
        category_service.create_category("Beta")

# --- Category Retrieval ---
def test_list_categories_empty(category_service):
    cats = category_service.list_categories()
    assert cats == []

def test_list_categories_multiple(category_service):
    names = ["A", "B", "C"]
    for n in names:
        category_service.create_category(n)
    cats = category_service.list_categories()
    assert set(c[1] for c in cats) == set(names)

# --- Category Rename ---
def test_rename_category_valid(category_service):
    cat_id = category_service.create_category("Old")
    category_service.rename_category(cat_id, "New")
    cats = category_service.list_categories()
    assert any(c[1] == "New" for c in cats)
    assert not any(c[1] == "Old" for c in cats)

def test_rename_category_duplicate(category_service):
    id1 = category_service.create_category("X")
    id2 = category_service.create_category("Y")
    with pytest.raises(ValueError):
        category_service.rename_category(id2, "X")

def test_rename_category_invalid(category_service):
    cat_id = category_service.create_category("Z")
    with pytest.raises(ValueError):
        category_service.rename_category(cat_id, "")
    with pytest.raises(ValueError):
        category_service.rename_category(cat_id, "Çategory")
    with pytest.raises(ValueError):
        category_service.rename_category(cat_id, "A" * 65)

# --- Category Deletion ---
def test_delete_category(category_service):
    cat_id = category_service.create_category("DelMe")
    category_service.delete_category(cat_id)
    cats = category_service.list_categories()
    assert not any(c[0] == cat_id for c in cats)

def test_delete_category_cascades(category_service, temp_db):
    # Create category, snippet, and snippet_part
    cat_id = category_service.create_category("Cascade")
    db = temp_db
    db.execute_non_query("INSERT INTO text_snippets (category_id, snippet_name) VALUES (?, ?)", (cat_id, "S1"))
    snip_id = db.execute_query("SELECT snippet_id FROM text_snippets WHERE category_id = ?", (cat_id,))[0]["snippet_id"]
    db.execute_non_query("INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)", (snip_id, 0, "abc"))
    # Delete category
    category_service.delete_category(cat_id)
    # Ensure snippets and snippet_parts are deleted
    snips = db.execute_query("SELECT * FROM text_snippets WHERE category_id = ?", (cat_id,))
    assert snips == []
    parts = db.execute_query("SELECT * FROM snippet_parts WHERE snippet_id = ?", (snip_id,))
    assert parts == []

# --- Error Handling ---
def test_rename_nonexistent_category(category_service):
    with pytest.raises(ValueError):
        category_service.rename_category(9999, "Nope")

def test_delete_nonexistent_category(category_service):
    # Should not raise, just be a no-op
    category_service.delete_category(9999)

# --- Security ---
def test_category_sql_injection_attempt(category_service):
    # Should not allow SQL injection via name
    bad_name = "Robert'); DROP TABLE text_category;--"
    with pytest.raises(ValueError):
        category_service.create_category(bad_name)
