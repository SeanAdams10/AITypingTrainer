import pytest
from models.snippet import Snippet
from models.category import Category
from db.database_manager import DatabaseManager
import string

@pytest.fixture(autouse=True)
def setup_and_teardown_db(tmp_path, monkeypatch):
    # Use a temp DB for all tests
    db_file = tmp_path / "test_db.sqlite3"
    monkeypatch.setenv("AITR_DB_PATH", str(db_file))
    DatabaseManager.reset_instance()
    db = DatabaseManager()
    db.set_db_path(str(db_file))
    db.initialize_database()
    yield

@pytest.fixture
def sample_category():
    cat = Category.create_category("TestCategory")
    return cat

@pytest.mark.parametrize("name,content,expect_success", [
    ("Alpha", "Some content", True),
    ("", "Some content", False),
    ("A"*129, "Content", False),
    ("NonAsciié", "Content", False),
    ("Alpha", "", False),
])
def test_snippet_creation_validation(sample_category, name, content, expect_success):
    if expect_success:
        snippet = Snippet(category_id=sample_category, snippet_name=name, content=content)
        assert snippet.save() is True
        loaded = Snippet.get_by_id(snippet.snippet_id)
        assert loaded is not None
        assert loaded.snippet_name == name
        assert loaded.content == content
    else:
        # Expect validation error during object creation
        with pytest.raises(ValueError):
            snippet = Snippet(category_id=sample_category, snippet_name=name, content=content)

@pytest.mark.parametrize("name1,name2,should_succeed", [
    ("Unique1", "Unique2", True),
    ("DupName", "DupName", False),
])
def test_snippet_name_uniqueness(sample_category, name1, name2, should_succeed):
    s1 = Snippet(category_id=sample_category, snippet_name=name1, content="abc")
    assert s1.save() is True
    s2 = Snippet(category_id=sample_category, snippet_name=name2, content="def")
    if should_succeed:
        assert s2.save() is True
    else:
        with pytest.raises(Exception):
            s2.save()

def test_snippet_deletion(sample_category):
    s = Snippet(category_id=sample_category, snippet_name="ToDelete", content="abc")
    s.save()
    sid = s.snippet_id
    assert Snippet.get_by_id(sid) is not None
    assert s.delete() is True
    assert Snippet.get_by_id(sid) is None

def test_snippet_update(sample_category):
    s = Snippet(category_id=sample_category, snippet_name="ToUpdate", content="abc")
    s.save()
    s.snippet_name = "UpdatedName"
    s.content = "Updated content"
    assert s.save() is True
    loaded = Snippet.get_by_id(s.snippet_id)
    assert loaded.snippet_name == "UpdatedName"
    assert loaded.content == "Updated content"

def test_snippet_sql_injection(sample_category):
    inj = "Robert'); DROP TABLE text_snippets;--"
    # Expect validation error during object creation due to SQL injection attempt
    with pytest.raises(ValueError):
        s = Snippet(category_id=sample_category, snippet_name=inj, content="abc")

def test_snippet_long_content(sample_category):
    long_content = "x" * 20000
    s = Snippet(category_id=sample_category, snippet_name="LongContent", content=long_content)
    assert s.save() is True
    loaded = Snippet.get_by_id(s.snippet_id)
    assert loaded.content == long_content
