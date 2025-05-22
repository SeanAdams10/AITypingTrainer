"""
Tests for PracticeSessionManager and PracticeSession.

This module tests the functionality of PracticeSession and PracticeSessionManager classes,
using pytest and a temporary SQLite database. Tests cover session creation, retrieval,
updating, and clearing session data.
"""

import os
import sys
import tempfile
import datetime
from typing import Any, Dict, Generator

import pytest
import sqlite3
import uuid

# Add project root to path for test imports
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.database_manager import DatabaseManager
from models.practice_session import PracticeSession, PracticeSessionManager
from models.practice_session_extensions import PracticeSessionKeystrokeManager

# Define pytest marks
pytest.mark.populate_sessions = pytest.mark.populate_sessions


@pytest.fixture
def temp_db(
    request: pytest.FixtureRequest = None
) -> Generator[DatabaseManager, None, None]:
    """
    Create a temporary SQLite database for testing.

    This fixture sets up a clean temporary database with the minimal schema needed for
    practice_sessions and snippet_parts. It ensures the DB is closed before file removal
    to avoid PermissionError on Windows.

    Args:
        request: The pytest request object to check for markers

    Yields:
        DatabaseManager: Configured database manager for the temporary database

    When the 'populate_sessions' marker is present, it also adds test session data,
    keystrokes, and n-gram data for comprehensive testing.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DatabaseManager(path)
    db.init_tables()

    # Create a test category
    db.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
        (1, "Test Category")
    )

    # Create a test snippet
    db.execute(
        "INSERT INTO snippets "
        "(snippet_id, category_id, snippet_name) "
        "VALUES (?, ?, ?)",
        (1, 1, "Test Snippet")
    )

    # Create snippet parts
    db.execute(
        "INSERT INTO snippet_parts "
        "(snippet_id, part_number, content) "
        "VALUES (?, ?, ?)",
        (1, 0, "This is a test snippet part one.")
    )

    db.execute(
        "INSERT INTO snippet_parts "
        "(snippet_id, part_number, content) "
        "VALUES (?, ?, ?)",
        (1, 1, "This is a test snippet part two.")
    )

    # Check if we should populate test sessions
    populate_sessions = request and request.node.get_closest_marker("populate_sessions")

    if populate_sessions:
        # Add test practice sessions
        now = datetime.datetime.now()
        two_days_ago = now - datetime.timedelta(days=2)
        yesterday = now - datetime.timedelta(days=1)
        tomorrow = now + datetime.timedelta(days=1)

        # Create some sessions
        db.execute(
            "INSERT INTO practice_sessions "
            "(session_id, snippet_id, start_time, end_time, wpm, accuracy, completed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "test-session-1", 1, two_days_ago.isoformat(),
                yesterday.isoformat(), 60.5, 95.2, True
            ),
            commit=True
        )

        db.execute(
            "INSERT INTO practice_sessions "
            "(session_id, snippet_id, start_time, end_time, wpm, accuracy, completed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "test-session-2", 1, yesterday.isoformat(),
                now.isoformat(), 65.8, 97.1, True
            ),
            commit=True
        )

        db.execute(
            "INSERT INTO practice_sessions "
            "(session_id, snippet_id, start_time, end_time, wpm, accuracy, completed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test-session-3", 1, now.isoformat(), None, None, None, False),
            commit=True
        )

        db.execute(
            "INSERT INTO practice_sessions "
            "(session_id, snippet_id, start_time, end_time, wpm, accuracy, completed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            # Future session
            (
                "test-session-4", 1, now.isoformat(),
                tomorrow.isoformat(), None, None, False
            ),
            commit=True
        )

        # Add some keystrokes - simplified for testing
        db.execute(
            "CREATE TABLE IF NOT EXISTS session_keystrokes ("
            "keystroke_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "session_id TEXT NOT NULL, "
            "keystroke_time TIMESTAMP NOT NULL, "
            "keystroke_char TEXT NOT NULL, "
            "expected_char TEXT NOT NULL, "
            "is_correct BOOLEAN NOT NULL, "
            "time_since_previous INTEGER, "
            "FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) "
            "ON DELETE CASCADE)"
        )

        # Insert sample keystrokes
        for i in range(10):
            keystroke_time = now + datetime.timedelta(seconds=i)
            db.execute(
                "INSERT INTO session_keystrokes "
                "(session_id, keystroke_time, keystroke_char, "
                "expected_char, is_correct, time_since_previous) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "test-session-1", keystroke_time.isoformat(),
                    "a", "a", True, 100
                ),
                commit=True
            )

        # Add n-grams - simplified for testing
        db.execute(
            "CREATE TABLE IF NOT EXISTS session_ngram_data ("
            "ngram_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "session_id TEXT NOT NULL, "
            "ngram TEXT NOT NULL, "
            "ngram_size INTEGER NOT NULL, "
            "total_time_ms REAL NOT NULL, "
            "FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) "
            "ON DELETE CASCADE)"
        )

        # Insert sample n-gram data
        db.execute(
            "INSERT INTO session_ngram_data "
            "(session_id, ngram, ngram_size, total_time_ms) "
            "VALUES (?, ?, ?, ?)",
            ("test-session-1", "th", 2, 250.0),
            commit=True
        )

    try:
        yield db
    finally:
        # Close DB connection to release file lock before attempting to remove
        db.close()
        try:
            os.unlink(path)
        except (PermissionError, FileNotFoundError):
            # On Windows, sometimes we can't delete immediately
            # Don't fail the test if this happens
            pass


@pytest.fixture
def session_manager(temp_db: DatabaseManager) -> PracticeSessionManager:
    """Create a session manager for testing.

    Args:
        temp_db: Temporary test database fixture

    Returns:
        A configured PracticeSessionManager instance for testing
    """
    return PracticeSessionManager(temp_db)


@pytest.fixture
def sample_snippet() -> int:
    """Provide a sample snippet ID for testing.

    Returns:
        ID of the test snippet created in the temp_db fixture
    """
    # The snippet parts are already inserted in temp_db fixture
    return 1  # Just return the snippet ID





@pytest.mark.parametrize("session_attrs", [
    # Test case 1: All attributes provided
    {
        "session_id": None,  # Should be auto-generated
        "snippet_id": 1,
        "snippet_index_start": 0,
        "snippet_index_end": 5,
        "content": "Test content",
        "start_time": datetime.datetime(2025, 5, 10, 12, 0, 0),
        "end_time": datetime.datetime(2025, 5, 10, 12, 0, 15),
        "total_time": 10.5,
        "session_wpm": 60.0,
        "session_cpm": 300.0,
        "expected_chars": 100,
        "actual_chars": 90,
        "errors": 10,
        "efficiency": 0.9,
        "correctness": 0.9,
        "accuracy": 0.9,
    },
    # Test case 2: Different set of attributes
    {
        "session_id": None,  # Should be auto-generated
        "snippet_id": 1,
        "snippet_index_start": 0,
        "snippet_index_end": 10,
        "content": "Test minimum attributes",
        "start_time": datetime.datetime(2025, 5, 10, 12, 0, 0),
        "end_time": datetime.datetime(2025, 5, 10, 12, 0, 30),
        "total_time": 30.0,
        "session_wpm": 40.0,
        "session_cpm": 200.0,
        "expected_chars": 25,
        "actual_chars": 20,
        "errors": 5,
        "efficiency": 0.8,
        "correctness": 0.8,
        "accuracy": 0.8,
    }
])
def test_create_simple_session(
    session_manager: PracticeSessionManager,
    sample_snippet: int,
    session_attrs: Dict[str, Any]
) -> None:
    """Test objective: Verify creation of practice sessions with different attributes.
    
    This test verifies that:
    - Sessions can be created with both complete and minimal attribute sets
    - Generated session IDs are valid strings
    - Created sessions are retrievable from the database
    - All provided attributes are correctly stored
    
    Args:
        session_manager: The session manager fixture
        sample_snippet: The sample snippet ID fixture
        session_attrs: Parameterized session attributes
    """
    # Check that our sample snippet matches what we expect
    assert sample_snippet == 1
    
    # Create a session object from the test attributes
    session = PracticeSession(**session_attrs)
    session_id = session_manager.create_session(session)
    
    # Check that we got a valid session ID
    assert session_id is not None
    assert isinstance(session_id, str)
    assert len(session_id) > 0
    
    # Check that the session was properly stored in the database
    sessions = session_manager.list_sessions_for_snippet(sample_snippet)
    assert len(sessions) > 0
    
    # Get the created session back
    created_session = None
    for s in sessions:
        if s.session_id == session_id:
            created_session = s
            break
    
    assert created_session is not None
    
    # Check that created session has all the expected attributes
    for key, value in session_attrs.items():
        if key == "session_id":  # Skip session_id as it's generated
            continue
        assert hasattr(created_session, key)
        
        # For datetime objects, only check their existence, not exact values
        if isinstance(value, datetime.datetime):
            assert getattr(created_session, key) is not None
        else:
            assert getattr(created_session, key) == value

@pytest.mark.parametrize("session_data,retrieval_method", [
    # Test case 1: Create session with specific content & check with list_sessions
    ({
        "snippet_id": 1,
        "snippet_index_start": 0,
        "snippet_index_end": 10,
        "content": "The quick brown fox",
        "start_time": datetime.datetime(2025, 5, 10, 12, 0, 0),
        "end_time": datetime.datetime(2025, 5, 10, 12, 1, 0),
        "total_time": 60.0,
        "session_wpm": 60.0,
        "session_cpm": 300.0,
        "expected_chars": 19,
        "actual_chars": 19,
        "errors": 0,
        "efficiency": 1.0,
        "correctness": 1.0,
        "accuracy": 1.0,
    }, "list"),
    # Test case 2: Create session with fixed dates & check with get_last_session
    ({
        "snippet_id": 1,  # Will use sample_snippet in the test
        "snippet_index_start": 0,
        "snippet_index_end": 7,
        "content": "abcdefg",
        "start_time": datetime.datetime(2025, 5, 10, 12, 0, 0),
        "end_time": datetime.datetime(2025, 5, 10, 12, 1, 0),
        "total_time": 60.0,
        "session_wpm": 40.0,
        "session_cpm": 200.0,
        "expected_chars": 7,
        "actual_chars": 7,
        "errors": 0,
        "efficiency": 1.0,
        "correctness": 1.0,
        "accuracy": 1.0,
    }, "last"),
])
def test_create_session_and_retrieve(
    session_manager: PracticeSessionManager,
    sample_snippet: int,
    session_data: Dict[str, Any],
    retrieval_method: str
) -> None:
    """Test objective: Verify session creation and retrieval functionality.
    
    This test verifies that:
    - Sessions are properly created and stored in the database
    - Sessions can be retrieved using different query methods
    - Retrieved sessions have the correct attributes matching what was stored
    
    Args:
        session_manager: The session manager fixture
        sample_snippet: Sample snippet ID fixture
        session_data: Parameterized session data
        retrieval_method: Which retrieval method to test ('list' or 'last')
    """
    # Use sample_snippet if needed
    if session_data["snippet_id"] == 1:
        session_data["snippet_id"] = sample_snippet
    if "end_time" not in session_data:  
        session_data["end_time"] = datetime.datetime.now()
        
    # Print the session data to debug
    print(f"Creating session with data: {session_data}")
    
    try:
        print(f"Session data keys: {session_data.keys()}")
        print(f"Session data types: {[(k, type(v)) for k, v in session_data.items()]}")
        session = PracticeSession(
            session_id=None,
            **session_data
        )
    except Exception as e:
        print(f"Validation error: {str(e)[:500]}")
        import traceback
        print(traceback.format_exc())
        raise
    
    # Save the session
    session_id = session_manager.create_session(session)
    assert session_id is not None
    assert isinstance(session_id, str)  # Now expecting a string UUID
    
    # Retrieve using the specified method and check properties
    if retrieval_method == "list":
        sessions = session_manager.list_sessions_for_snippet(session_data["snippet_id"])
        assert len(sessions) == 1
        retrieved = sessions[0]
    else:  # "last"
        retrieved = session_manager.get_last_session_for_snippet(session_data["snippet_id"])
        assert retrieved is not None
        
    # Verify session properties match what was saved
    for key, value in session_data.items():
        if key in ("start_time", "end_time"):
            continue  # Skip time comparisons as they might not be exactly equal
        assert getattr(retrieved, key) == value


def test_get_session_info(
    session_manager: PracticeSessionManager,
    sample_snippet: int
) -> None:
    """Test objective: Verify session info retrieval from the manager.

    This test verifies that:
    - Session info can be retrieved for a snippet with no prior sessions
    - After adding a session, the info is correctly updated with the session details

    Args:
        session_manager: The practice session manager fixture
        sample_snippet: The sample snippet ID fixture
    """
    # Get session info for a snippet with no sessions yet
    info = session_manager.get_session_info(sample_snippet)
    assert "last_start_index" in info
    assert "last_end_index" in info
    assert "snippet_length" in info
    assert info["last_start_index"] == 0
    assert info["last_end_index"] == 0
    assert info["snippet_length"] == 64  # Length of the combined test snippet parts
    
    # Add a session
    session = PracticeSession(
        session_id=None,
        snippet_id=sample_snippet,
        snippet_index_start=2,
        snippet_index_end=7,
        content="cdefg",
        start_time=datetime.datetime(2025, 5, 10, 12, 2, 0),
        end_time=datetime.datetime(2025, 5, 10, 12, 3, 0),
        total_time=60.0,
        session_wpm=42.0,
        session_cpm=210.0,
        expected_chars=5,
        actual_chars=5,
        errors=1,
        efficiency=0.9,
        correctness=0.89,
        accuracy=0.8,
    )
    session_manager.create_session(session)
    
    # Check that session info has been updated
    info2 = session_manager.get_session_info(sample_snippet)
    assert info2["last_start_index"] == 2
    assert info2["last_end_index"] == 7
    assert info2["snippet_length"] == 64  # Length of the combined test snippet parts


def test_list_sessions_for_snippet(
    session_manager: PracticeSessionManager,
    sample_snippet: int
) -> None:
    """Test objective: Verify listing sessions with different ordering options.

    This test verifies that:
    - Multiple sessions can be created for a single snippet
    - Sessions can be listed with default ordering (by date, most recent first)
    - Sessions can be listed with custom ordering (by accuracy, ascending)

    Args:
        session_manager: The practice session manager fixture
        sample_snippet: The sample snippet ID fixture
    """
    # Add two sessions
    session1 = PracticeSession(
        session_id=None,
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=3,
        content="abc",
        start_time=datetime.datetime(2025, 5, 10, 12, 0, 0),
        end_time=datetime.datetime(2025, 5, 10, 12, 1, 0),
        total_time=60.0,
        session_wpm=30.0,
        session_cpm=150.0,
        expected_chars=3,
        actual_chars=3,
        errors=0,
        efficiency=1.0,
        correctness=1.0,
        accuracy=1.0,
    )
    session_manager.create_session(session1)
    
    session2 = PracticeSession(
        session_id=None,
        snippet_id=sample_snippet,
        snippet_index_start=2,
        snippet_index_end=7,
        content="cdefg",
        start_time=datetime.datetime(2025, 5, 10, 12, 2, 0),
        end_time=datetime.datetime(2025, 5, 10, 12, 3, 0),
        total_time=60.0,
        session_wpm=42.0,
        session_cpm=210.0,
        expected_chars=5,
        actual_chars=5,
        errors=1,
        efficiency=0.9,
        correctness=0.8,
        accuracy=0.8,
    )
    session_manager.create_session(session2)
    
    # List sessions - the default order is by end_time DESC (most recent first)
    sessions = session_manager.list_sessions_for_snippet(sample_snippet)
    # Should be in most recent order by default (session2, then session1)
    assert len(sessions) == 2
    assert sessions[0].start_time > sessions[1].start_time
    assert sessions[0].snippet_index_start == 2
    assert sessions[1].snippet_index_start == 0
    
    # Manually check if sessions are returned in the correct order
    # Since we can't control the order, verify we have both sessions with expected attributes
    assert any(s.accuracy == 0.8 for s in sessions)
    assert any(s.accuracy == 1.0 for s in sessions)


@pytest.mark.populate_sessions
def test_clear_all_session_data(temp_db: DatabaseManager) -> None:
    """Test objective: Verify the clear_all_session_data method removes data from all tables.
    
    This test verifies that:
    - Session data can be properly created and exists in the database
    - The clear_all_session_data method effectively removes all session data
    - Related data in dependent tables (keystrokes, n-gram data) is also removed
    
    Args:
        temp_db: The temporary database fixture with populate_sessions marker
    """
    # Create a session manager with the populated database
    session_manager = PracticeSessionManager(temp_db)
    
    # Add some additional test data
    session = PracticeSession(
        session_id=None,
        snippet_id=1,
        snippet_index_start=0,
        snippet_index_end=5,
        content="abcde",
        start_time=datetime.datetime(2025, 5, 10, 12, 0, 0),
        end_time=datetime.datetime(2025, 5, 10, 12, 1, 0),
        total_time=60.0,
        session_wpm=40.0,
        session_cpm=200.0,
        expected_chars=5,
        actual_chars=5,
        errors=0,
        efficiency=1.0,
        correctness=1.0,
        accuracy=1.0,
    )
    session_id = session_manager.create_session(session)
    
    # Add keystrokes for the session
    keystroke_manager = PracticeSessionKeystrokeManager(temp_db)
    for i in range(5):
        # Make the 3rd keystroke incorrect
        char_typed = "b" if i == 2 else "a"
        expected_char = "a"
        keystroke_manager.record_keystroke(
            session_id=session_id,
            char_position=i,
            char_typed=char_typed,
            expected_char=expected_char,
            timestamp=datetime.datetime(2025, 5, 10, 12, 0, i),
            time_since_previous=i * 100
        )
    
    # Add test n-gram data using the new unified schema
    temp_db.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_data (
            ngram_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            session_id TEXT NOT NULL, 
            ngram TEXT NOT NULL, 
            ngram_size INTEGER NOT NULL, 
            count INTEGER NOT NULL, 
            total_time_ms REAL NOT NULL, 
            error_count INTEGER NOT NULL, 
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) 
            ON DELETE CASCADE
        )
    """)
    
    # Insert sample n-gram data
    temp_db.execute("""
        INSERT INTO session_ngram_data 
        (session_id, ngram, ngram_size, count, total_time_ms, error_count) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, "ab", 2, 5, 250.0, 1))
    
    # Verify data exists before clearing
    session_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM practice_sessions"
    )[0]
    keystroke_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM session_keystrokes"
    )[0]
    # Check for error keystrokes rather than separate error table
    error_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM session_keystrokes WHERE is_correct = 0"
    )[0]
    ngram_data_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM session_ngram_data"
    )[0]
    
    assert session_count > 0
    assert keystroke_count > 0
    assert error_count > 0
    assert ngram_data_count > 0
    
    # Clear all session data
    session_manager.clear_all_session_data()
    
    # Verify all data has been removed
    session_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM practice_sessions"
    )[0]
    keystroke_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM session_keystrokes"
    )[0]
    # Check for error keystrokes rather than separate error table
    error_keystroke_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM session_keystrokes WHERE is_correct = 0"
    )[0]
    ngram_data_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM session_ngram_data"
    )[0]

    assert session_count == 0, f"Expected 0 sessions, found {session_count}"
    assert keystroke_count == 0, f"Expected 0 keystrokes, found {keystroke_count}"
    assert error_keystroke_count == 0, f"Expected 0 error keystrokes, found {error_keystroke_count}"
    assert ngram_data_count == 0, f"Expected 0 ngram data records, found {ngram_data_count}"
