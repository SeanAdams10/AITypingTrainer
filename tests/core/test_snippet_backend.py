import pytest
from models.snippet import SnippetModel, SnippetManager
from models.category import CategoryManager
from db.database_manager import DatabaseManager

@pytest.fixture(autouse=True)
def setup_and_teardown_db(tmp_path, monkeypatch):
    # Use a temp DB for all tests
    db_file = tmp_path / "test_db.sqlite3"
    monkeypatch.setenv("AITR_DB_PATH", str(db_file))
    # No reset_instance since DatabaseManager is instantiated directly
    yield

@pytest.fixture
def db_manager(tmp_path):
    db_file = tmp_path / "test_db.sqlite3"
    db = DatabaseManager(str(db_file))
    db.init_tables()
    return db

@pytest.fixture
def category_manager(db_manager):
    return CategoryManager(db_manager)

@pytest.fixture
def snippet_manager(db_manager):
    return SnippetManager(db_manager)

@pytest.fixture
def snippet_category_fixture(category_manager):
    category = category_manager.create_category("TestCategory")
    return category.category_id

@pytest.mark.parametrize("name,content,expect_success", [
    ("Alpha", "Some content", True),
    ("", "Some content", False),
    ("A"*129, "Content", False),
    ("NonAsciié", "Content", False),
    ("Alpha", "", False),
])
def test_snippet_creation_validation(snippet_category_fixture, snippet_manager, name, content, expect_success):
    if expect_success:
        try:
            snippet_id = snippet_manager.create_snippet(category_id=snippet_category_fixture, snippet_name=name, content=content)
            loaded = snippet_manager.get_snippet(snippet_id)
            assert loaded is not None
            assert loaded.snippet_name == name
            assert loaded.content == content
        except Exception as e:
            pytest.fail(f"Should have succeeded but failed with: {e}")
    else:
        # Expect validation error during creation
        with pytest.raises(ValueError):
            snippet_manager.create_snippet(category_id=snippet_category_fixture, snippet_name=name, content=content)

@pytest.mark.parametrize("name1,name2,should_succeed", [
    ("Unique1", "Unique2", True),
    ("DupName", "DupName", False),
])
def test_snippet_name_uniqueness(snippet_category_fixture, snippet_manager, name1, name2, should_succeed):
    s1_id = snippet_manager.create_snippet(category_id=snippet_category_fixture, snippet_name=name1, content="abc")
    assert s1_id > 0
    
    if should_succeed:
        s2_id = snippet_manager.create_snippet(category_id=snippet_category_fixture, snippet_name=name2, content="def")
        assert s2_id > 0
    else:
        with pytest.raises(ValueError):
            snippet_manager.create_snippet(category_id=snippet_category_fixture, snippet_name=name2, content="def")

def test_snippet_deletion(snippet_category_fixture, snippet_manager):
    snippet_id = snippet_manager.create_snippet(category_id=snippet_category_fixture, snippet_name="ToDelete", content="abc")
    # Verify snippet exists
    loaded = snippet_manager.get_snippet(snippet_id)
    assert loaded is not None
    # Delete the snippet
    snippet_manager.delete_snippet(snippet_id)
    # Verify it no longer exists
    with pytest.raises(ValueError):
        snippet_manager.get_snippet(snippet_id)

def test_snippet_update(snippet_category_fixture, snippet_manager):
    snippet_id = snippet_manager.create_snippet(category_id=snippet_category_fixture, snippet_name="ToUpdate", content="abc")
    # Update the snippet
    snippet_manager.edit_snippet(snippet_id, snippet_name="UpdatedName", content="Updated content")
    # Verify changes
    loaded = snippet_manager.get_snippet(snippet_id)
    assert loaded.snippet_name == "UpdatedName"
    assert loaded.content == "Updated content"

def test_snippet_sql_injection(snippet_category_fixture, snippet_manager):
    inj = "Robert'); DROP TABLE text_snippets;--"
    # Expect validation error during object creation due to SQL injection attempt
    with pytest.raises(ValueError):
        snippet_manager.create_snippet(category_id=snippet_category_fixture, snippet_name=inj, content="abc")

def test_snippet_long_content(snippet_category_fixture, snippet_manager):
    long_content = "x" * 20000
    snippet_id = snippet_manager.create_snippet(category_id=snippet_category_fixture, snippet_name="LongContent", content=long_content)
    loaded = snippet_manager.get_snippet(snippet_id)
    assert loaded.content == long_content
