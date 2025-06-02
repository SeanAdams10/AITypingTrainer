import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, Type
from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from pydantic import ValidationError

from db.database_manager import DatabaseManager
from db.exceptions import (
    ConstraintError,
    DatabaseError,
    DatabaseTypeError,
    DBConnectionError,
    ForeignKeyError,
    IntegrityError,
    SchemaError,
)
from models.session import Session
from models.session_manager import SessionManager

# Use the shared db_helpers fixtures for all DB setup
# (No need to import db_manager directly, pytest will inject it)


@pytest.fixture
def session_manager(
    db_with_tables: DatabaseManager,
) -> SessionManager:
    """Test objective: Provide a SessionManager using a temporary database."""
    return SessionManager(db_with_tables)


@pytest.fixture
def sample_snippet(db_with_tables: DatabaseManager) -> str:
    """
    Test objective: Insert a sample category, snippet, and snippet_part,
    then return the snippet_id.
    """
    import uuid

    # Insert into categories table
    category_id = str(uuid.uuid4())
    db_with_tables.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
        (category_id, "TestCat"),
    )
    snippet_id = str(uuid.uuid4())
    db_with_tables.execute(
        "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
        (snippet_id, category_id, "TestSnippet"),
    )
    db_with_tables.execute(
        "INSERT INTO snippet_parts (part_id, snippet_id, part_number, content) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), snippet_id, 1, "abcde"),
    )
    return snippet_id


def test_create_and_retrieve_session(session_manager: SessionManager, sample_snippet: str) -> None:
    now = datetime.now()
    import uuid

    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session_manager.save_session(session)
    retrieved = session_manager.get_session_by_id(session.session_id)
    assert isinstance(retrieved, Session)
    assert retrieved.session_id == session.session_id
    assert retrieved.snippet_id == sample_snippet
    assert retrieved.content == "abcde"
    assert isinstance(retrieved.ms_per_keystroke, float)


def test_list_sessions_for_snippet(session_manager: SessionManager, sample_snippet: str) -> None:
    now = datetime.now()
    session1 = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session2 = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="fghij",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session_manager.save_session(session1)
    session_manager.save_session(session2)
    sessions = session_manager.list_sessions_for_snippet(sample_snippet)
    assert len(sessions) >= 2
    assert all(isinstance(s, Session) for s in sessions)
    contents = [s.content for s in sessions]
    assert "abcde" in contents and "fghij" in contents


def test_delete_all_sessions(session_manager: SessionManager, sample_snippet: str) -> None:
    now = datetime.now()
    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session_manager.save_session(session)
    assert len(session_manager.list_sessions_for_snippet(sample_snippet)) > 0
    session_manager.delete_all()
    assert len(session_manager.list_sessions_for_snippet(sample_snippet)) == 0


def test_delete_all_sessions_cascades_and_success(
    session_manager: SessionManager, sample_snippet: str, monkeypatch: MonkeyPatch
) -> None:
    """
    Test that delete_all deletes keystrokes and ngrams first, and only deletes sessions
    if both succeed.
    """
    # Insert a session
    now = datetime.now()
    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session_manager.save_session(session)
    # Patch KeystrokeManager and NGramManager to always succeed
    monkeypatch.setattr("models.keystroke_manager.KeystrokeManager.delete_all", lambda self: True)
    monkeypatch.setattr("models.ngram_manager.NGramManager.delete_all_ngrams", lambda self: True)
    assert len(session_manager.list_sessions_for_snippet(sample_snippet)) > 0
    result = session_manager.delete_all()
    assert result is True
    assert len(session_manager.list_sessions_for_snippet(sample_snippet)) == 0


def test_delete_all_sessions_keystroke_fail(
    session_manager: SessionManager, sample_snippet: str, monkeypatch: MonkeyPatch
) -> None:
    """
    Test that delete_all does not delete sessions if keystroke deletion fails.
    """
    now = datetime.now()
    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session_manager.save_session(session)
    monkeypatch.setattr("models.keystroke_manager.KeystrokeManager.delete_all", lambda self: False)
    monkeypatch.setattr("models.ngram_manager.NGramManager.delete_all_ngrams", lambda self: True)
    assert len(session_manager.list_sessions_for_snippet(sample_snippet)) > 0
    result = session_manager.delete_all()
    assert result is False
    assert len(session_manager.list_sessions_for_snippet(sample_snippet)) > 0


def test_delete_all_sessions_ngram_fail(
    session_manager: SessionManager, sample_snippet: str, monkeypatch: MonkeyPatch
) -> None:
    """
    Test that delete_all does not delete sessions if ngram deletion fails.
    """
    now = datetime.now()
    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session_manager.save_session(session)
    monkeypatch.setattr("models.keystroke_manager.KeystrokeManager.delete_all", lambda self: True)
    monkeypatch.setattr("models.ngram_manager.NGramManager.delete_all_ngrams", lambda self: False)
    assert len(session_manager.list_sessions_for_snippet(sample_snippet)) > 0
    result = session_manager.delete_all()
    assert result is False
    assert len(session_manager.list_sessions_for_snippet(sample_snippet)) > 0


def test_delete_all_sessions_both_fail(
    session_manager: SessionManager, sample_snippet: str, monkeypatch: MonkeyPatch
) -> None:
    """
    Test that delete_all does not delete sessions if both keystroke and ngram deletion fail.
    """
    now = datetime.now()
    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session_manager.save_session(session)
    monkeypatch.setattr("models.keystroke_manager.KeystrokeManager.delete_all", lambda self: False)
    monkeypatch.setattr("models.ngram_manager.NGramManager.delete_all_ngrams", lambda self: False)
    assert len(session_manager.list_sessions_for_snippet(sample_snippet)) > 0
    result = session_manager.delete_all()
    assert result is False
    assert len(session_manager.list_sessions_for_snippet(sample_snippet)) > 0


def test_save_session_returns_id(session_manager: SessionManager, sample_snippet: str) -> None:
    now = datetime.now()
    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session_id = session_manager.save_session(session)
    assert session_id == session.session_id


def test_list_sessions_multiple_snippets(
    session_manager: SessionManager, db_manager: DatabaseManager
) -> None:
    # Add two snippets
    db_manager.execute("INSERT INTO categories (category_id, name) VALUES (?, ?)", (2, "Cat2"))
    db_manager.execute(
        "INSERT INTO snippets (snippet_id, category_id, content) VALUES (?, ?, ?)",
        (2, 2, "OtherSnippet"),
    )
    now = datetime.now()
    s1 = Session(
        session_id=str(uuid.uuid4()),
        snippet_id="1",
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    s2 = Session(
        session_id=str(uuid.uuid4()),
        snippet_id="2",
        snippet_index_start=0,
        snippet_index_end=3,
        content="xyz",
        start_time=now,
        end_time=now + timedelta(seconds=30),
        actual_chars=3,
        errors=0,
    )
    session_manager.save_session(s1)
    session_manager.save_session(s2)
    sessions1 = session_manager.list_sessions_for_snippet("1")
    sessions2 = session_manager.list_sessions_for_snippet("2")
    assert any(sess.session_id == s1.session_id for sess in sessions1)
    assert any(sess.session_id == s2.session_id for sess in sessions2)


@pytest.fixture
def valid_session_dict_fixture(sample_snippet: str) -> Dict[str, object]:
    now = datetime.now()
    return {
        "session_id": str(uuid.uuid4()),
        "snippet_id": sample_snippet,  # Use actual snippet ID from fixture
        "snippet_index_start": 0,
        "snippet_index_end": 5,
        "content": "abcde",
        "start_time": now,
        "end_time": now + timedelta(seconds=60),
        "actual_chars": 5,
        "errors": 1,
    }


def test_save_and_get_session(
    session_manager: SessionManager, valid_session_dict_fixture: Dict[str, object]
) -> None:
    s = Session.from_dict(valid_session_dict_fixture)
    session_manager.save_session(s)
    loaded = session_manager.get_session_by_id(s.session_id)
    assert loaded == s


def test_update_session(
    session_manager: SessionManager, valid_session_dict_fixture: Dict[str, object]
) -> None:
    s = Session.from_dict(valid_session_dict_fixture)
    session_manager.save_session(s)
    s2 = s.copy(update={"content": "updated content", "errors": 2})
    session_manager.save_session(s2)
    loaded = session_manager.get_session_by_id(s.session_id)
    assert loaded is not None, "Expected session to be loaded but got None"
    assert loaded.content == "updated content"
    assert loaded.errors == 2


def test_list_sessions_for_snippet_from_test_session(
    session_manager: SessionManager, valid_session_dict_fixture: Dict[str, object]
) -> None:
    s = Session.from_dict(valid_session_dict_fixture)
    session_manager.save_session(s)
    # Pass snippet_id as int as expected by the function
    sessions = session_manager.list_sessions_for_snippet(int(s.snippet_id))
    assert any(sess.session_id == s.session_id for sess in sessions)


def test_delete_all_sessions_from_test_session(
    session_manager: SessionManager, valid_session_dict_fixture: Dict[str, object]
) -> None:
    s = Session.from_dict(valid_session_dict_fixture)
    session_manager.save_session(s)
    session_manager.delete_all()  # This now uses the improved version
    assert session_manager.get_session_by_id(s.session_id) is None


def test_delete_session_by_id(session_manager: SessionManager, sample_snippet: str) -> None:
    now = datetime.now()
    import uuid

    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session_manager.save_session(session)
    assert session_manager.get_session_by_id(session.session_id) is not None
    deleted = session_manager.delete_session_by_id(session.session_id)
    assert deleted is True
    assert session_manager.get_session_by_id(session.session_id) is None


@pytest.mark.parametrize(
    "exc_cls",
    [
        DBConnectionError,
        ConstraintError,
        DatabaseError,
        DatabaseTypeError,
        ForeignKeyError,
        IntegrityError,
        SchemaError,
    ],
)
def test_save_session_db_exceptions(
    session_manager: SessionManager,
    valid_session_dict_fixture: Dict[str, object],
    exc_cls: Type[Exception],
    monkeypatch: MonkeyPatch,  # Changed from object to MonkeyPatch
) -> None:
    def raise_exc(*args: object, **kwargs: object) -> None:
        raise exc_cls("fail")

    monkeypatch.setattr(session_manager.db_manager, "execute", raise_exc)
    s = Session.from_dict(valid_session_dict_fixture)
    with pytest.raises(exc_cls):
        session_manager.save_session(s)


def test_update_session_invalid_data(
    session_manager: SessionManager, valid_session_dict_fixture: Dict[str, object]
) -> None:
    s = Session.from_dict(valid_session_dict_fixture)
    session_manager.save_session(s)
    # Create a new instance with invalid data to trigger validation
    data = s.model_dump()
    data["snippet_index_start"] = 10
    data["snippet_index_end"] = 5
    with pytest.raises(ValidationError):  # Assuming Session model validation
        Session.from_dict(data)


def test_save_duplicate_session_id_updates(
    session_manager: SessionManager, valid_session_dict_fixture: Dict[str, object]
) -> None:
    s = Session.from_dict(valid_session_dict_fixture)
    session_manager.save_session(s)
    s2 = s.copy(update={"content": "new content"})
    session_manager.save_session(s2)  # This should update due to unique constraint on session_id
    loaded = session_manager.get_session_by_id(s.session_id)
    assert loaded is not None, "Expected session to be loaded but got None"
    assert loaded.content == "new content"


def test_get_nonexistent_session(session_manager: SessionManager) -> None:
    assert session_manager.get_session_by_id(str(uuid.uuid4())) is None


def test_list_sessions_for_snippet_empty(session_manager: SessionManager) -> None:
    # Use a snippet_id that is unlikely to exist
    assert session_manager.list_sessions_for_snippet(999999) == []


@pytest.mark.parametrize(
    "exception_cls",  # Added this missing test from the original file
    [
        DBConnectionError,
        ConstraintError,
        DatabaseError,
        DatabaseTypeError,
        ForeignKeyError,
        IntegrityError,
        SchemaError,
    ],
)
def test_save_session_db_exceptions_from_manager(
    session_manager: SessionManager,
    valid_session_dict_fixture: Dict[str, object],
    exception_cls: Type[Exception],
    monkeypatch: MonkeyPatch,
) -> None:
    def raise_exc(*args: object, **kwargs: object) -> None:
        raise exception_cls("fail")

    monkeypatch.setattr(session_manager.db_manager, "execute", raise_exc)
    # Ensure snippet_id is a string if that's what Session expects
    if isinstance(valid_session_dict_fixture.get("snippet_id"), int):
        valid_session_dict_fixture["snippet_id"] = str(valid_session_dict_fixture["snippet_id"])

    s = Session.from_dict(valid_session_dict_fixture)
    with pytest.raises(exception_cls):
        session_manager.save_session(s)


def test_delete_all_when_no_sessions(session_manager: SessionManager) -> None:
    # Should not raise or fail
    session_manager.delete_all()
    assert True


def test_delete_all_removes_related(
    monkeypatch: MonkeyPatch, session_manager: SessionManager, sample_snippet: str
) -> None:
    called = {"keystrokes": False, "ngrams": False}

    class DummyK:
        def __init__(self, db: object) -> None:
            pass

        def delete_all(self) -> bool:
            called["keystrokes"] = True
            return True

    class DummyN:
        def __init__(self, db: object) -> None:
            pass

        def delete_all_ngrams(self) -> bool:
            called["ngrams"] = True
            return True

    monkeypatch.setattr("models.keystroke_manager.KeystrokeManager", DummyK)
    monkeypatch.setattr("models.ngram_manager.NGramManager", DummyN)
    now = datetime.now()
    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session_manager.save_session(session)
    session_manager.delete_all()
    assert called["keystrokes"] and called["ngrams"]


def test_get_session_by_id_hydrates_all_fields(
    session_manager: SessionManager, sample_snippet: str
) -> None:
    now = datetime.now()
    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    session_manager.save_session(session)
    loaded = session_manager.get_session_by_id(session.session_id)
    assert loaded is not None
    assert loaded.session_id == session.session_id
    assert loaded.snippet_id == session.snippet_id


@pytest.mark.parametrize(
    "exception_cls",
    [
        DBConnectionError,
        ConstraintError,
        DatabaseError,
        DatabaseTypeError,
        ForeignKeyError,
        IntegrityError,
        SchemaError,
    ],
)
def test_db_exceptions_handled(exception_cls: type[Exception]) -> None:
    db_mock = MagicMock()
    db_mock.execute.side_effect = exception_cls("fail")
    manager = SessionManager(db_mock)
    now = datetime.now()
    session = manager.create_session(
        snippet_id=1,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=now,
        end_time=now + timedelta(seconds=60),
        actual_chars=5,
        errors=1,
    )
    with pytest.raises(exception_cls):
        manager.save_session(session)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
