import datetime
import uuid

import pytest

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke
from models.keystroke_manager import KeystrokeManager


@pytest.fixture
def db_manager(tmp_path):
    db_path = tmp_path / "test_keystrokes.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    return db


@pytest.fixture
def keystroke_manager(db_manager):
    return KeystrokeManager(db_manager)


@pytest.fixture
def sample_keystroke() -> Keystroke:
    return Keystroke(
        session_id=str(uuid.uuid4()),
        keystroke_char="a",
        expected_char="a",
        is_error=False,
        time_since_previous=0,
    )


@pytest.fixture
def sample_session_id() -> str:
    return str(uuid.uuid4())


def test_add_and_save_keystroke(keystroke_manager, sample_keystroke):
    keystroke_manager.add_keystroke(sample_keystroke)
    assert len(keystroke_manager.keystroke_list) == 1
    assert keystroke_manager.keystroke_list[0] == sample_keystroke
    assert keystroke_manager.save_keystrokes() is True


def test_get_keystrokes_for_session(keystroke_manager, sample_session_id):
    # Add and save multiple keystrokes
    for i in range(3):
        ks = Keystroke(
            session_id=sample_session_id,
            keystroke_char=chr(97 + i),
            expected_char=chr(97 + i),
            is_error=(i == 2),
            time_since_previous=100 * i,
        )
        keystroke_manager.add_keystroke(ks)
    keystroke_manager.save_keystrokes()
    # Clear in-memory list and repopulate from DB
    keystroke_manager.keystroke_list = []
    result = keystroke_manager.get_keystrokes_for_session(sample_session_id)
    assert len(result) == 3
    assert all(isinstance(ks, Keystroke) for ks in result)


def test_delete_keystrokes_by_session(keystroke_manager, sample_session_id):
    ks = Keystroke(
        session_id=sample_session_id,
        keystroke_char="x",
        expected_char="x",
        is_error=False,
        time_since_previous=0,
    )
    keystroke_manager.add_keystroke(ks)
    keystroke_manager.save_keystrokes()
    assert keystroke_manager.delete_keystrokes_by_session(sample_session_id) is True
    # Should be empty after deletion
    result = keystroke_manager.get_keystrokes_for_session(sample_session_id)
    assert result == []


def test_delete_all_keystrokes(keystroke_manager, sample_session_id):
    for i in range(2):
        ks = Keystroke(
            session_id=sample_session_id,
            keystroke_char=chr(97 + i),
            expected_char=chr(97 + i),
            is_error=False,
            time_since_previous=0,
        )
        keystroke_manager.add_keystroke(ks)
    keystroke_manager.save_keystrokes()
    assert keystroke_manager.delete_all_keystrokes() is True
    # Should be empty for any session
    result = keystroke_manager.get_keystrokes_for_session(sample_session_id)
    assert result == []


def test_count_keystrokes_per_session(keystroke_manager, sample_session_id):
    for i in range(5):
        ks = Keystroke(
            session_id=sample_session_id,
            keystroke_char=chr(97 + i),
            expected_char=chr(97 + i),
            is_error=False,
            time_since_previous=0,
        )
        keystroke_manager.add_keystroke(ks)
    keystroke_manager.save_keystrokes()
    count = keystroke_manager.count_keystrokes_per_session(sample_session_id)
    assert count == 5


def test_keystroke_to_dict_and_from_dict():
    data = {
        "session_id": str(uuid.uuid4()),
        "keystroke_char": "z",
        "expected_char": "z",
        "is_error": True,
        "time_since_previous": 123,
        "keystroke_time": datetime.datetime.now().isoformat(),
    }
    ks = Keystroke.from_dict(data)
    d = ks.to_dict()
    assert d["session_id"] == data["session_id"]
    assert d["keystroke_char"] == "z"
    assert d["expected_char"] == "z"
    assert d["is_error"] is True
    assert d["time_since_previous"] == 123


def test_get_errors_for_session(keystroke_manager, sample_session_id):
    for i in range(4):
        ks = Keystroke(
            session_id=sample_session_id,
            keystroke_char=chr(97 + i),
            expected_char=chr(97 + i),
            is_error=(i % 2 == 0),
            time_since_previous=0,
        )
        keystroke_manager.add_keystroke(ks)
    keystroke_manager.save_keystrokes()
    errors = Keystroke.get_errors_for_session(sample_session_id)
    assert len(errors) == 2
    assert all(ks.is_error for ks in errors)


def test_delete_all_keystrokes_classmethod(db_manager):
    # Add a keystroke via direct DB insert
    db_manager.execute(
        "INSERT INTO session_keystrokes (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_error, time_since_previous) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            datetime.datetime.now().isoformat(),
            "a",
            "a",
            0,
            0,
        ),
    )
    assert Keystroke.delete_all_keystrokes(db_manager) is True
    # Table should be empty
    db_manager.execute("DELETE FROM session_keystrokes")
