"""
Tests for SnippetModelTester functionality (validates SnippetManager and related logic).
"""

import pytest

from db.database_manager import DatabaseManager
from models.category import CategoryManager
from models.snippet import SnippetManager


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_snippet.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    yield db
    db.close()


@pytest.fixture
def snippet_mgr(temp_db):
    return SnippetManager(temp_db)


@pytest.fixture
def category_mgr(temp_db):
    return CategoryManager(temp_db)


def test_add_and_list_snippets(
    snippet_mgr: SnippetManager, category_mgr: CategoryManager
):
    cat = category_mgr.create_category("TestCat")
    snip_id = snippet_mgr.create_snippet(cat.category_id, "TestSnippet", "abc def")
    snip = snippet_mgr.get_snippet(snip_id)
    snippets = snippet_mgr.list_snippets(cat.category_id)
    assert any(s.snippet_id == snip_id for s in snippets)
    assert any(s.snippet_name == "TestSnippet" for s in snippets)


def test_edit_snippet(snippet_mgr: SnippetManager, category_mgr: CategoryManager):
    cat = category_mgr.create_category("TestCat")
    snip_id = snippet_mgr.create_snippet(cat.category_id, "ToEdit", "original")
    snippet_mgr.edit_snippet(snip_id, "EditedName", "new content", cat.category_id)
    updated = snippet_mgr.get_snippet(snip_id)
    assert updated.snippet_name == "EditedName"
    assert updated.content == "new content"


def test_delete_snippet(snippet_mgr: SnippetManager, category_mgr: CategoryManager):
    cat = category_mgr.create_category("TestCat")
    snip_id = snippet_mgr.create_snippet(cat.category_id, "ToDelete", "abc")
    snippet_mgr.delete_snippet(snip_id)
    all_snips = snippet_mgr.list_snippets(cat.category_id)
    assert not any(s.snippet_id == snip_id for s in all_snips)


def test_snippet_validation(snippet_mgr: SnippetManager, category_mgr: CategoryManager):
    cat = category_mgr.create_category("Cat")
    # Name required
    with pytest.raises(Exception):
        snippet_mgr.create_snippet(cat.category_id, "", "content")
    # Content required
    with pytest.raises(Exception):
        snippet_mgr.create_snippet(cat.category_id, "Valid", "")
