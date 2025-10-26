"""Tests for session manager functionality.

Tests for session management, persistence, and lifecycle operations.
"""

import datetime
import uuid
from typing import Any, Generator

import pytest

from db.database_manager import DatabaseManager
from models.category import Category
from models.category_manager import CategoryManager
from models.keyboard import Keyboard
from models.session import Session
from models.session_manager import SessionManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager
from models.user import User


def make_session(snippet_id: str, user_id: str, keyboard_id: str, **overrides: object) -> Session:
    now = datetime.datetime(2023, 1, 1, 12, 0, 0)
    data: dict[str, Any] = {
        "session_id": str(uuid.uuid4()),
        "snippet_id": snippet_id,
        "user_id": user_id,
        "keyboard_id": keyboard_id,
        "snippet_index_start": 0,
        "snippet_index_end": 5,
        "content": "abcde",
        "start_time": now,
        "end_time": now + datetime.timedelta(seconds=60),
        "actual_chars": 5,
        "errors": 1,
    }
    data.update(overrides)
    return Session(**data)


@pytest.fixture
def category_mgr(db_with_tables: DatabaseManager) -> Generator[CategoryManager, None, None]:
    manager = CategoryManager(db_manager=db_with_tables)
    yield manager


@pytest.fixture
def snippet_mgr(db_with_tables: DatabaseManager) -> Generator[SnippetManager, None, None]:
    manager = SnippetManager(db_manager=db_with_tables)
    yield manager


@pytest.fixture
def session_mgr(db_with_tables: DatabaseManager) -> Generator[SessionManager, None, None]:
    manager = SessionManager(db_manager=db_with_tables)
    yield manager


@pytest.fixture
def sample_category(category_mgr: CategoryManager) -> Category:
    category = Category(category_name="Test Category", description="A category for testing")
    category_mgr.save_category(category=category)
    return category


@pytest.fixture
def sample_snippet(
    snippet_mgr: SnippetManager, sample_category: Category, test_user: User
) -> Snippet:
    snippet = Snippet(
        category_id=str(sample_category.category_id),
        snippet_name="Test Snippet",
        content="This is a test snippet.",
        description="",
    )
    snippet_mgr.save_snippet(snippet=snippet)
    return snippet


def test_save_and_get_session(
    session_mgr: SessionManager,
    sample_snippet: Snippet,
    test_user: User,
    test_keyboard: Keyboard,
) -> None:
    session = make_session(
        snippet_id=str(sample_snippet.snippet_id),
        user_id=str(test_user.user_id),
        keyboard_id=str(test_keyboard.keyboard_id),
    )
    session_mgr.save_session(session)
    loaded = session_mgr.get_session_by_id(str(session.session_id))
    assert loaded == session


def test_update_session(
    session_mgr: SessionManager,
    sample_snippet: Snippet,
    test_user: User,
    test_keyboard: Keyboard,
) -> None:
    session = make_session(
        snippet_id=str(sample_snippet.snippet_id),
        user_id=str(test_user.user_id),
        keyboard_id=str(test_keyboard.keyboard_id),
    )
    session_mgr.save_session(session)
    session.errors = 3
    session_mgr.save_session(session)
    loaded = session_mgr.get_session_by_id(str(session.session_id))
    assert loaded is not None
    assert loaded.errors == 3


def test_list_sessions_for_snippet(
    session_mgr: SessionManager,
    sample_snippet: Snippet,
    test_user: User,
    test_keyboard: Keyboard,
) -> None:
    s1 = make_session(
        snippet_id=str(sample_snippet.snippet_id),
        user_id=str(test_user.user_id),
        keyboard_id=str(test_keyboard.keyboard_id),
    )
    s2 = make_session(
        snippet_id=str(sample_snippet.snippet_id),
        user_id=str(test_user.user_id),
        keyboard_id=str(test_keyboard.keyboard_id),
    )
    session_mgr.save_session(s1)
    session_mgr.save_session(s2)
    sessions = session_mgr.list_sessions_for_snippet(str(sample_snippet.snippet_id))
    assert len(sessions) == 2
    assert all(isinstance(s, Session) for s in sessions)


def test_delete_session_by_id(
    session_mgr: SessionManager,
    sample_snippet: Snippet,
    test_user: User,
    test_keyboard: Keyboard,
) -> None:
    session = make_session(
        snippet_id=str(sample_snippet.snippet_id),
        user_id=str(test_user.user_id),
        keyboard_id=str(test_keyboard.keyboard_id),
    )
    session_mgr.save_session(session)
    assert session_mgr.get_session_by_id(str(session.session_id)) is not None
    session_mgr.delete_session_by_id(str(session.session_id))
    assert session_mgr.get_session_by_id(str(session.session_id)) is None


def test_delete_all(
    session_mgr: SessionManager,
    snippet_mgr: SnippetManager,
    sample_category: Category,
    test_user: User,
    test_keyboard: Keyboard,
) -> None:
    snippet1 = Snippet(
        category_id=str(sample_category.category_id),
        snippet_name="Snippet 1",
        content="Content 1",
        description="",
    )
    snippet_mgr.save_snippet(snippet=snippet1)
    snippet2 = Snippet(
        category_id=str(sample_category.category_id),
        snippet_name="Snippet 2",
        content="Content 2",
        description="",
    )
    snippet_mgr.save_snippet(snippet=snippet2)

    s1 = make_session(
        snippet_id=str(snippet1.snippet_id),
        user_id=str(test_user.user_id),
        keyboard_id=str(test_keyboard.keyboard_id),
    )
    s2 = make_session(
        snippet_id=str(snippet2.snippet_id),
        user_id=str(test_user.user_id),
        keyboard_id=str(test_keyboard.keyboard_id),
    )
    session_mgr.save_session(s1)
    session_mgr.save_session(s2)
    assert len(session_mgr.list_sessions_for_snippet(str(s1.snippet_id))) == 1
    assert len(session_mgr.list_sessions_for_snippet(str(s2.snippet_id))) == 1
    session_mgr.delete_all()
    assert session_mgr.get_session_by_id(str(s1.session_id)) is None
    assert session_mgr.get_session_by_id(str(s2.session_id)) is None


def test_save_session_returns_id(
    session_mgr: SessionManager,
    sample_snippet: Snippet,
    test_user: User,
    test_keyboard: Keyboard,
) -> None:
    session = make_session(
        snippet_id=str(sample_snippet.snippet_id),
        user_id=str(test_user.user_id),
        keyboard_id=str(test_keyboard.keyboard_id),
    )
    session_id = session_mgr.save_session(session)
    assert session_id == str(session.session_id)


def test_get_nonexistent_session(session_mgr: SessionManager) -> None:
    assert session_mgr.get_session_by_id(str(uuid.uuid4())) is None


def test_list_sessions_for_snippet_empty(session_mgr: SessionManager) -> None:
    assert session_mgr.list_sessions_for_snippet(str(uuid.uuid4())) == []


if __name__ == "__main__":
    pytest.main([__file__])
