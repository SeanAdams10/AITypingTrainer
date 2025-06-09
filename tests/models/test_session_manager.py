import datetime
import uuid

import pytest

from db.database_manager import DatabaseManager
from models.session import Session
from models.session_manager import SessionManager


def make_session(snippet_id: str = None, **overrides: object) -> Session:
    now = datetime.datetime(2023, 1, 1, 12, 0, 0)
    sid = snippet_id or str(uuid.uuid4())
    data = {
        "session_id": str(uuid.uuid4()),
        "snippet_id": sid,
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


def create_category_and_snippet(db: DatabaseManager, snippet_id: str) -> None:
    """Insert a valid category and snippet for the given snippet_id."""
    category_id = str(uuid.uuid4())
    category_name = f"Test Category {snippet_id}"
    db.execute(
        """
        INSERT INTO categories (category_id, category_name) VALUES (?, ?)
        """,
        (category_id, category_name),
    )
    db.execute(
        """
        INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)
        """,
        (snippet_id, category_id, "Test Snippet"),
    )


def test_save_and_get_session(tmp_path: str) -> None:
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    manager = SessionManager(db)
    session = make_session()
    create_category_and_snippet(db, session.snippet_id)
    manager.save_session(session)
    loaded = manager.get_session_by_id(session.session_id)
    assert loaded == session


def test_update_session(tmp_path: str) -> None:
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    manager = SessionManager(db)
    session = make_session()
    create_category_and_snippet(db, session.snippet_id)
    manager.save_session(session)
    session.errors = 3
    manager.save_session(session)
    loaded = manager.get_session_by_id(session.session_id)
    assert loaded.errors == 3


def test_list_sessions_for_snippet(tmp_path: str) -> None:
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    manager = SessionManager(db)
    snippet_id = str(uuid.uuid4())
    create_category_and_snippet(db, snippet_id)
    s1 = make_session(snippet_id=snippet_id)
    s2 = make_session(snippet_id=snippet_id)
    manager.save_session(s1)
    manager.save_session(s2)
    sessions = manager.list_sessions_for_snippet(snippet_id)
    assert len(sessions) == 2
    assert all(isinstance(s, Session) for s in sessions)


def test_delete_session_by_id(tmp_path: str) -> None:
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    manager = SessionManager(db)
    session = make_session()
    create_category_and_snippet(db, session.snippet_id)
    manager.save_session(session)
    assert manager.get_session_by_id(session.session_id) is not None
    manager.delete_session_by_id(session.session_id)
    assert manager.get_session_by_id(session.session_id) is None


def test_delete_all(tmp_path: str) -> None:
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    manager = SessionManager(db)
    s1 = make_session()
    s2 = make_session()
    create_category_and_snippet(db, s1.snippet_id)
    create_category_and_snippet(db, s2.snippet_id)
    manager.save_session(s1)
    manager.save_session(s2)
    assert len(manager.list_sessions_for_snippet(s1.snippet_id)) == 1
    assert len(manager.list_sessions_for_snippet(s2.snippet_id)) == 1
    manager.delete_all()
    assert manager.get_session_by_id(s1.session_id) is None
    assert manager.get_session_by_id(s2.session_id) is None


def test_save_session_returns_id(tmp_path: str) -> None:
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    manager = SessionManager(db)
    session = make_session()
    create_category_and_snippet(db, session.snippet_id)
    session_id = manager.save_session(session)
    assert session_id == session.session_id


def test_get_nonexistent_session(tmp_path: str) -> None:
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    manager = SessionManager(db)
    assert manager.get_session_by_id(str(uuid.uuid4())) is None


def test_list_sessions_for_snippet_empty(tmp_path: str) -> None:
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    manager = SessionManager(db)
    assert manager.list_sessions_for_snippet(str(uuid.uuid4())) == []


if __name__ == "__main__":
    pytest.main([__file__])
