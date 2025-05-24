import datetime

import pytest

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke
from models.keystroke_manager import KeystrokeManager


@pytest.fixture
def db_manager(tmp_path):
    db_path = tmp_path / "test_keystrokes.db"
    db = DatabaseManager(str(db_path))
    db.init_db()
    return db

@pytest.fixture
def keystroke_manager(db_manager):
    return KeystrokeManager(db_manager)

@pytest.fixture
def sample_keystroke():
    return Keystroke(
        session_id=1,
        keystroke_id=0,
        keystroke_time=datetime.datetime.now(),
        keystroke_char="a",
        expected_char="a",
        is_correct=True,
        error_type=None,
        time_since_previous=100,
    )

def test_add_keystroke(keystroke_manager, sample_keystroke):
    assert keystroke_manager.add_keystroke(sample_keystroke) is True
    

def test_save_keystrokes(keystroke_manager):
    keystrokes = [
        {
            "session_id": 2,
            "keystroke_id": 0,
            "keystroke_time": datetime.datetime.now().isoformat(),
            "keystroke_char": "b",
            "expected_char": "b",
            "is_correct": True,
            "time_since_previous": 120,
        },
        {
            "session_id": 2,
            "keystroke_id": 1,
            "keystroke_time": datetime.datetime.now().isoformat(),
            "keystroke_char": "c",
            "expected_char": "c",
            "is_correct": False,
            "time_since_previous": 110,
        },
    ]
    assert keystroke_manager.save_keystrokes(2, keystrokes) is True

def test_delete_keystrokes_by_session(keystroke_manager, sample_keystroke):
    # Add a keystroke first
    keystroke_manager.add_keystroke(sample_keystroke)
    # Now delete
    assert keystroke_manager.delete_keystrokes_by_session(sample_keystroke.session_id) is True
