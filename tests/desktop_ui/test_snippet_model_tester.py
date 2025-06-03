"""
Tests for SnippetModelTester functionality (validates SnippetManager and related logic).
"""

from pathlib import Path
from typing import Generator

import pytest
from pydantic import ValidationError

from db.database_manager import DatabaseManager
from models.category import Category
from models.category_manager import CategoryManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager


@pytest.fixture
def temp_db(tmp_path: Path) -> Generator[DatabaseManager, None, None]:
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
    cat = Category(category_name="TestCat")
    category_mgr.save_category(cat)
    snip = Snippet(category_id=cat.category_id, snippet_name="TestSnippet", content="abc def")
    snippet_mgr.save_snippet(snip)
    snippets = snippet_mgr.list_all_snippets()
    assert any(s.snippet_id == snip.snippet_id for s in snippets)
    assert any(s.snippet_name == "TestSnippet" for s in snippets)


def test_edit_snippet(snippet_mgr: SnippetManager, category_mgr: CategoryManager) -> None:
    cat = Category(category_name="TestCat")
    category_mgr.save_category(cat)
    snip = Snippet(category_id=cat.category_id, snippet_name="ToEdit", content="original")
    snippet_mgr.save_snippet(snip)
    # Update: change name and content, then save again
    snip.snippet_name = "EditedName"
    snip.content = "new content"
    snippet_mgr.save_snippet(snip)
    updated = snippet_mgr.get_snippet_by_id(snip.snippet_id)
    assert updated is not None
    assert updated.snippet_name == "EditedName"
    assert updated.content == "new content"


def test_delete_snippet(
    snippet_mgr: SnippetManager, category_mgr: CategoryManager
) -> None:
    cat = Category(category_name="TestCat")
    category_mgr.save_category(cat)
    snip = Snippet(category_id=cat.category_id, snippet_name="ToDelete", content="abc")
    snippet_mgr.save_snippet(snip)
    snippet_mgr.delete_snippet(snip.snippet_id)
    all_snips = snippet_mgr.list_all_snippets()
    assert not any(s.snippet_id == snip.snippet_id for s in all_snips)


def test_snippet_validation(
    snippet_mgr: SnippetManager, category_mgr: CategoryManager
) -> None:
    cat = Category(category_name="Cat")
    category_mgr.save_category(cat)
    # Name required
    with pytest.raises(ValidationError):
        snip = Snippet(category_id=cat.category_id, snippet_name="", content="content")
        snippet_mgr.save_snippet(snip)
    # Content required
    with pytest.raises(ValidationError):
        snip = Snippet(category_id=cat.category_id, snippet_name="Valid", content="")
        snippet_mgr.save_snippet(snip)
