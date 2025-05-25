import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke
from models.keystroke_manager import KeystrokeManager


@pytest.fixture
def db_manager(tmp_path: Path) -> DatabaseManager:
    """Create a test database with tables initialized."""
    db_path = tmp_path / "test_keystrokes.db"
    db = DatabaseManager(str(db_path))
    db.init_tables()
    return db


@pytest.fixture
def keystroke_manager(db_manager: DatabaseManager) -> KeystrokeManager:
    """Create a KeystrokeManager instance for testing."""
    return KeystrokeManager(db_manager)


@pytest.fixture
def sample_keystroke() -> Keystroke:
    """Create a sample keystroke for testing."""
    return Keystroke(
        session_id="test-session-1",  # Using string session ID to match database schema
        keystroke_id=None,  # Let DB assign ID
        keystroke_time=datetime.datetime.now(),
        keystroke_char="a",
        expected_char="a",
        is_correct=True,
        error_type=None,
        time_since_previous=100,
    )


@pytest.fixture
def test_session() -> str:
    """Return a test session ID."""
    return "test-session-2"


def test_add_keystroke(keystroke_manager: KeystrokeManager, sample_keystroke: Keystroke) -> None:
    """Test that a single keystroke can be added."""
    import sys
    print(f"\nTest adding keystroke: {sample_keystroke}", file=sys.stderr)
    
    try:
        print(f"Calling add_keystroke with keystroke: {sample_keystroke}", file=sys.stderr)
        result = keystroke_manager.add_keystroke(sample_keystroke)
        print(f"Add result: {result}", file=sys.stderr)
        assert result is True, "Failed to add keystroke"
    except Exception as e:
        import traceback
        print(f"Error in test_add_keystroke: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise


def test_save_keystrokes(keystroke_manager: KeystrokeManager, test_session: str) -> None:
    """Test that multiple keystrokes can be saved for a session."""
    import sys
    print(f"\nTest session ID: {test_session}", file=sys.stderr)
    
    now = datetime.datetime.now()
    keystrokes: List[Dict[str, Any]] = [
        {
            "session_id": test_session,  # Use the fixture session ID
            "keystroke_id": None,
            "keystroke_time": now.isoformat(),
            "keystroke_char": "b",
            "expected_char": "b",
            "is_correct": True,
            "time_since_previous": 120,
        },
        {
            "session_id": test_session,  # Use the fixture session ID
            "keystroke_id": None,
            "keystroke_time": (now + datetime.timedelta(milliseconds=120)).isoformat(),
            "keystroke_char": "c",
            "expected_char": "c",
            "is_correct": False,
            "time_since_previous": 110,
        },
    ]
    
    print(f"Keystrokes to save: {keystrokes}", file=sys.stderr)
    
    try:
        print(f"Calling save_keystrokes with session_id: {test_session}", file=sys.stderr)
        result = keystroke_manager.save_keystrokes(test_session, keystrokes)
        print(f"Save result: {result}", file=sys.stderr)
        assert result is True, "Failed to save keystrokes"
    except Exception as e:
        import traceback
        print(f"Error in test_save_keystrokes: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise


def test_delete_keystrokes_by_session(
    keystroke_manager: KeystrokeManager, sample_keystroke: Keystroke
) -> None:
    """Test that keystrokes can be deleted by session."""
    import sys
    session_id = str(sample_keystroke.session_id)  # Ensure it's a string
    print(f"\nTest deleting keystrokes for session: {session_id}", file=sys.stderr)
    
    # Add a keystroke first
    keystroke_manager.add_keystroke(sample_keystroke)
    
    try:
        print(f"Calling delete_keystrokes_by_session with ID: {session_id}", 
              file=sys.stderr)
        result = keystroke_manager.delete_keystrokes_by_session(session_id)
        print(f"Delete result: {result}", file=sys.stderr)
        assert result is True, "Failed to delete keystrokes"
    except Exception as e:
        import traceback
        print(f"Error in test_delete_keystrokes_by_session: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise
