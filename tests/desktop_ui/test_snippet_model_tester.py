"""
Tests for SnippetModelTester functionality (validates SnippetManager and related logic).
"""

import pytest
from db.database_manager import DatabaseManager
from models.category_manager import CategoryManager
from models.snippet_manager import SnippetManager
from models.snippet import Snippet
from pydantic import ValidationError
from db.exceptions import ForeignKeyError
from typing import Generator


@pytest.fixture
def temp_db(tmp_path) -> Generator[DatabaseManager, None, None]:
    db_path = tmp_path / "test_snippet.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    yield db
    db.close()


@pytest.fixture
def snippet_mgr(temp_db: DatabaseManager) -> SnippetManager:
    return SnippetManager(temp_db)


@pytest.fixture
def category_mgr(temp_db: DatabaseManager) -> CategoryManager:
    return CategoryManager(temp_db)


def test_add_and_list_snippets(
    snippet_mgr: SnippetManager, category_mgr: CategoryManager
) -> None:
    cat = category_mgr.create_category("TestCat")
    snip = snippet_mgr.create_snippet(cat.category_id, "TestSnippet", "abc def")
    snippets = snippet_mgr.list_all_snippets()
    assert any(s.snippet_id == snip.snippet_id for s in snippets)
    assert any(s.snippet_name == "TestSnippet" for s in snippets)


def test_edit_snippet(snippet_mgr: SnippetManager, category_mgr: CategoryManager) -> None:
    cat = category_mgr.create_category("TestCat")
    snip = snippet_mgr.create_snippet(cat.category_id, "ToEdit", "original")
    snippet_mgr.update_snippet(snip.snippet_id, snippet_name="EditedName", content="new content")
    updated = snippet_mgr.get_snippet_by_id(snip.snippet_id)
    assert updated is not None
    assert updated.snippet_name == "EditedName"
    assert updated.content == "new content"


def test_delete_snippet(snippet_mgr: SnippetManager, category_mgr: CategoryManager) -> None:
    cat = category_mgr.create_category("TestCat")
    snip = snippet_mgr.create_snippet(cat.category_id, "ToDelete", "abc")
    snippet_mgr.delete_snippet_by_id(snip.snippet_id)
    all_snips = snippet_mgr.list_all_snippets()
    assert not any(s.snippet_id == snip.snippet_id for s in all_snips)


def test_snippet_validation(snippet_mgr: SnippetManager, category_mgr: CategoryManager) -> None:
    cat = category_mgr.create_category("Cat")
    # Name required
    with pytest.raises(ValidationError):
        snippet_mgr.create_snippet(cat.category_id, "", "content")
    # Content required
    with pytest.raises(ValidationError):
        snippet_mgr.create_snippet(cat.category_id, "Valid", "")
