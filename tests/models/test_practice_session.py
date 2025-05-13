"""
Tests for PracticeSessionManager and PracticeSession.
Uses pytest and a temporary SQLite database.
Includes tests for clearing session data.
"""

import os
import sys
import tempfile
import pytest

# Define pytest marks in conftest.py or use this approach
pytest.mark.populate_sessions = pytest.mark.populate_sessions
import datetime
from typing import Any, Dict, Generator, List, Optional

# Add project root to path for test imports
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.database_manager import DatabaseManager
from models.practice_session import PracticeSession, PracticeSessionManager
from models.practice_session_extensions import (
    PracticeSessionKeystrokeManager,
    NgramAnalyzer
)


@pytest.fixture
def temp_db(request: pytest.FixtureRequest = None) -> Generator[DatabaseManager, None, None]:
    """
    Pytest fixture for a temporary SQLite database with minimal schema for practice_sessions and snippet_parts.
    Ensures DB is closed before file removal to avoid PermissionError on Windows.
    
    If the 'populate_sessions' marker is present, also adds test session data, keystrokes, errors, and n-gram data.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DatabaseManager(path)
    db.init_tables()
    
    # Create a test category
    db.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
        (1, "Test Category"),
        commit=True
    )
    
    # Create a test snippet
    db.execute(
        "INSERT INTO snippets (snippet_name, category_id) VALUES (?, ?)",
        ("Test Snippet", 1),
        commit=True
    )
    
    # Insert snippet parts that we use in our tests
    db.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (1, 0, "abc"),
        commit=True
    )
    db.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (1, 1, "defg"),
        commit=True
    )
    
    # Check if this test needs populated session data
    has_populate_marker = request and hasattr(request, "node") and request.node.get_closest_marker("populate_sessions")
    
    # For test_clear_all_session_data, always populate session data
    # This is a temporary solution until we properly fix the pytest marker
    if request and hasattr(request, "node") and request.node.name == "test_clear_all_session_data":
        has_populate_marker = True
    
    if has_populate_marker:
        # Add test session data for tests that need it
        session_manager = PracticeSessionManager(db)
        
        session = PracticeSession(
            session_id=None,
            snippet_id=1,
            snippet_index_start=0,
            snippet_index_end=100,
            content="Test content",
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now(),
            total_time=10.5,
            session_wpm=50.0,
            session_cpm=250.0,
            expected_chars=100,
            actual_chars=100,
            errors=0,
            accuracy=100.0
        )
        
        session_id = session_manager.create_session(session)
        
        # Add test keystroke data
        keystroke_manager = PracticeSessionKeystrokeManager(db)
        for i in range(5):
            keystroke_manager.record_keystroke(
                session_id=session_id,
                char_position=i,
                char_typed="a",
                expected_char="a",
                timestamp=datetime.datetime.now(),
                time_since_start=i * 100
            )
        
        # Error data is now tracked directly in the keystroke data
        # Adding an incorrect keystroke for error tracking
        keystroke_manager = PracticeSessionKeystrokeManager(db)
        keystroke_manager.record_keystroke(
            session_id=session_id,
            char_position=5,
            char_typed="c", 
            expected_char="b",
            timestamp=datetime.datetime.now(),
            time_since_start=500
        )
        
        # Add test n-gram data
        db.execute("""
            INSERT INTO session_ngram_speed
            (session_id, ngram, ngram_size, avg_time, occurrences) 
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, "ab", 2, 150.0, 1), commit=True)
        
        db.execute("""
            INSERT INTO session_ngram_errors
            (session_id, ngram, ngram_size, error_count, occurrences) 
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, "bc", 2, 1, 3), commit=True)
    
    yield db
    db.close()
    try:
        os.remove(path)
    except PermissionError:
        # On Windows, sometimes we need to wait for the file to be released
        pass


@pytest.fixture
def session_manager(temp_db: DatabaseManager) -> PracticeSessionManager:
    return PracticeSessionManager(temp_db)


@pytest.fixture
def sample_snippet(temp_db):
    # The snippet parts are already inserted in temp_db fixture
    # Just return the snippet ID
    return 1





@pytest.mark.parametrize("session_data,retrieval_method", [
    # Test case 1: Create session with specific content & check with list_sessions
    ({
        "snippet_id": 1,
        "snippet_index_start": 0,
        "snippet_index_end": 10,
        "content": "The quick brown fox",
        "total_time": 30,
        "session_wpm": 60.0,
        "session_cpm": 300.0,
        "expected_chars": 19,
        "actual_chars": 19,
        "errors": 0,
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
        "total_time": 60,
        "session_wpm": 40.0,
        "session_cpm": 200.0,
        "expected_chars": 7,
        "actual_chars": 7,
        "errors": 0,
        "accuracy": 1.0,
    }, "last"),
])
def test_create_session_and_retrieve(session_manager: PracticeSessionManager, 
                                   sample_snippet: int,
                                   session_data: Dict[str, Any],
                                   retrieval_method: str) -> None:
    """Test creating practice sessions and retrieving them using different methods.
    
    Args:
        session_manager: The session manager fixture
        sample_snippet: Sample snippet ID fixture
        session_data: Parameterized session data
        retrieval_method: Which retrieval method to test ('list' or 'last')
    """
    # Use sample_snippet if needed
    if session_data["snippet_id"] == 1:
        session_data["snippet_id"] = sample_snippet
    
    # Create the session with provided data
    if "start_time" not in session_data:
        session_data["start_time"] = datetime.datetime.now()
    if "end_time" not in session_data:  
        session_data["end_time"] = datetime.datetime.now()
        
    session = PracticeSession(
        session_id=None,
        **session_data
    )
    
    # Save the session
    session_id = session_manager.create_session(session)
    assert session_id is not None
    assert session_id > 0
    
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


def test_get_session_info(session_manager, sample_snippet):
    # No session yet
    info = session_manager.get_session_info(sample_snippet)
    assert info["last_start_index"] == 0
    assert info["last_end_index"] == 0
    assert info["snippet_length"] == 7
    # Add a session
    session = PracticeSession(
        session_id=None,
        snippet_id=sample_snippet,
        snippet_index_start=2,
        snippet_index_end=7,
        content="cdefg",  # Adding the missing required content field
        start_time=datetime.datetime(2025, 5, 10, 12, 2, 0),
        end_time=datetime.datetime(2025, 5, 10, 12, 3, 0),
        total_time=60,
        session_wpm=42.0,
        session_cpm=210.0,
        expected_chars=5,
        actual_chars=5,
        errors=1,
        accuracy=0.8,
    )
    session_manager.create_session(session)
    info2 = session_manager.get_session_info(sample_snippet)
    assert info2["last_start_index"] == 2
    assert info2["last_end_index"] == 7
    assert info2["snippet_length"] == 7


def test_list_sessions_for_snippet(session_manager, sample_snippet):
    # Add two sessions
    session1 = PracticeSession(
        session_id=None,
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=3,
        content="abc",  # Adding the missing required content field
        start_time=datetime.datetime(2025, 5, 10, 12, 0, 0),
        end_time=datetime.datetime(2025, 5, 10, 12, 1, 0),
        total_time=60,
        session_wpm=30.0,
        session_cpm=150.0,
        expected_chars=3,
        actual_chars=3,
        errors=0,
        accuracy=1.0,
    )
    session2 = PracticeSession(
        session_id=None,
        snippet_id=sample_snippet,
        snippet_index_start=3,
        snippet_index_end=7,
        content="defg",  # Adding the missing required content field
        start_time=datetime.datetime(2025, 5, 10, 12, 1, 0),
        end_time=datetime.datetime(2025, 5, 10, 12, 2, 0),
        total_time=60,
        session_wpm=50.0,
        session_cpm=250.0,
        expected_chars=4,
        actual_chars=4,
        errors=0,
        accuracy=1.0,
    )
    session_manager.create_session(session1)
    session_manager.create_session(session2)
    sessions = session_manager.list_sessions_for_snippet(sample_snippet)
    assert len(sessions) == 2
    assert sessions[0].snippet_index_start == 3
    assert sessions[1].snippet_index_start == 0


def test_clear_all_session_data(temp_db):
    """Test the clear_all_session_data method removes data from all tables."""
    # Create test data manually
    session_manager = PracticeSessionManager(temp_db)
    
    session = PracticeSession(
        session_id=None,
        snippet_id=1,
        snippet_index_start=0,
        snippet_index_end=100,
        content="Test content",
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now(),
        total_time=10.5,
        session_wpm=50.0,
        session_cpm=250.0,
        expected_chars=100,
        actual_chars=100,
        errors=0,
        accuracy=100.0
    )
    
    session_id = session_manager.create_session(session)
    
    # Add test keystroke data to match updated schema
    timestamp = datetime.datetime.now()
    for i in range(5):
        # Make the 3rd keystroke incorrect to ensure we have error data
        is_correct = 0 if i == 2 else 1
        expected = "b" if i == 2 else "a"
        temp_db.execute("""
            INSERT INTO session_keystrokes (
                session_id, keystroke_id, keystroke_time, keystroke_char,
                expected_char, is_correct, time_since_previous
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(session_id), i, timestamp.isoformat(), "a", expected, is_correct, i * 100
        ), commit=True)
    
    # Error data is now tracked directly in keystroke data, no separate error table needed
    
    # Add test n-gram data
    temp_db.execute("""
        INSERT INTO session_ngram_speed
        (session_id, ngram, speed) 
        VALUES (?, ?, ?)
    """, (session_id, "ab", 150.0), commit=True)
    
    temp_db.execute("""
        INSERT INTO session_ngram_errors
        (session_id, ngram, ngram_size, error_count, occurrences) 
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, "bc", 2, 1, 3), commit=True)
    
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
    ngram_speed_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM session_ngram_speed"
    )[0]
    ngram_error_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM session_ngram_errors"
    )[0]
    
    assert session_count > 0
    assert keystroke_count > 0
    assert error_count > 0
    assert ngram_speed_count > 0
    assert ngram_error_count > 0
    
    # Clear all session data
    session_manager = PracticeSessionManager(temp_db)
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
    ngram_speed_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM session_ngram_speed"
    )[0]
    ngram_error_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM session_ngram_errors"
    )[0]

    assert session_count == 0, f"Expected 0 sessions, found {session_count}"
    assert keystroke_count == 0, f"Expected 0 keystrokes, found {keystroke_count}"
    assert error_keystroke_count == 0, f"Expected 0 error keystrokes, found {error_keystroke_count}"
    assert ngram_speed_count == 0, f"Expected 0 ngram speed records, found {ngram_speed_count}"
    assert ngram_error_count == 0, f"Expected 0 ngram error records, found {ngram_error_count}"
