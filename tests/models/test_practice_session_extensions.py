"""
Tests for PracticeSession extension functionality.

Tests keystrokes, errors, and n-gram analysis for typing sessions.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional, cast

import pytest

# Add project root to path for test imports
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.database_manager import DatabaseManager
from models.practice_session import PracticeSession, PracticeSessionManager
from models.practice_session_extensions import (
    NgramAnalyzer,
    PracticeSessionKeystrokeManager,
    save_session_data,
)

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(name="temp_db")
def temp_db_fixture() -> Generator[DatabaseManager, None, None]:
    """Create a temporary in-memory database for testing.
    
    Yields:
        DatabaseManager: A database manager connected to an in-memory SQLite database.
    """
    db_manager = DatabaseManager(":memory:")
    db_manager.init_tables()
    
    # Create tables needed for extensions
    PracticeSessionKeystrokeManager(db_manager)
    NgramAnalyzer(db_manager)
    
    # Create a sample snippet that we can reference
    # Create a category first
    db_manager.execute(
        """
        INSERT INTO categories (category_id, category_name) 
        VALUES (?, ?)
        """,
        (1, "Test Category")
    )
    
    # Insert a snippet with the correct column names
    db_manager.execute(
        """
        INSERT INTO snippets (snippet_id, category_id, snippet_name) 
        VALUES (?, ?, ?)
        """,
        (1, 1, "Test Snippet")
    )
    
    # Add snippet parts
    db_manager.execute(
        """
        INSERT INTO snippet_parts (snippet_id, part_number, content) 
        VALUES (?, ?, ?)
        """,
        (1, 1, "Hello, world!")
    )
    
    try:
        yield db_manager
    finally:
        db_manager.close()


@pytest.fixture
def sample_session(
    temp_db: DatabaseManager
) -> Dict[str, Any]:
    """Create a sample practice session for testing.
    
    Args:
        temp_db: Database manager fixture.
        
    Returns:
        Dict containing session information including ID, content, and managers.
    """
    session = PracticeSession(
        session_id=None,
        snippet_id=1,
        snippet_index_start=0,
        snippet_index_end=12,
        content="Hello, world!",
        start_time=datetime.now() - timedelta(minutes=1),
        end_time=datetime.now(),
        total_time=60,
        session_wpm=60.0,
        session_cpm=300.0,
        expected_chars=12,
        actual_chars=12,
        errors=1,
        efficiency=0.96,
        correctness=0.955,
        accuracy=91.7 / 100
    )
    
    session_manager = PracticeSessionManager(temp_db)
    session_id = session_manager.create_session(session)
    
    return {
        "session_id": session_id,
        "content": "Hello, world!",
        "db_manager": temp_db,
        "session_manager": session_manager,
    }


def test_keystroke_manager_creation(temp_db: DatabaseManager) -> None:
    """Test that keystroke manager creates required tables.
    
    Args:
        temp_db: Database manager fixture.
    """
    # Initialize keystroke manager
    PracticeSessionKeystrokeManager(temp_db)
    
    # Check if table exists
    result = temp_db.execute(
        """
        SELECT name 
        FROM sqlite_master 
        WHERE type='table' AND name='session_keystrokes'
        """
    ).fetchone()
    
    assert result is not None
    assert result[0] == 'session_keystrokes'


def test_error_tracking_in_keystrokes(temp_db: DatabaseManager) -> None:
    """Test that errors are tracked in the keystrokes table.
    
    Args:
        temp_db: Database manager fixture.
    """
    # Initialize keystroke manager
    PracticeSessionKeystrokeManager(temp_db)
    
    # Check if keystroke table exists and has is_correct field for error tracking
    keystroke_table = temp_db.execute(
        "PRAGMA table_info(session_keystrokes)"
    ).fetchall()
    
    # Verify the is_correct column exists in the keystroke table
    is_correct_column = next(
        (col for col in keystroke_table if col[1] == 'is_correct'),
        None
    )
    
    assert is_correct_column is not None, \
        "is_correct column should exist in session_keystrokes table"


def test_ngram_analyzer_creation(temp_db: DatabaseManager) -> None:
    """Test that ngram analyzer creates required tables.
    
    Args:
        temp_db: Database manager fixture.
    """
    # Initialize ngram analyzer
    NgramAnalyzer(temp_db)
    
    # Check if tables exist
    speed_table = temp_db.execute(
        """
        SELECT name 
        FROM sqlite_master 
        WHERE type='table' AND name='session_ngram_speed'
        """
    ).fetchone()
    
    error_table = temp_db.execute(
        """
        SELECT name 
        FROM sqlite_master 
        WHERE type='table' AND name='session_ngram_errors'
        """
    ).fetchone()
    
    assert speed_table is not None
    assert speed_table[0] == 'session_ngram_speed'
    assert error_table is not None
    assert error_table[0] == 'session_ngram_errors'


def test_record_keystroke(sample_session: Dict[str, Any]) -> None:
    """Test recording keystrokes for a session.
    
    Args:
        sample_session: Fixture providing a sample session for testing.
    """
    # Initialize keystroke manager
    keystroke_manager = PracticeSessionKeystrokeManager(sample_session["db_manager"])
    
    # Record a keystroke
    timestamp = datetime.now()
    keystroke_id = keystroke_manager.record_keystroke(
        session_id=str(sample_session["session_id"]),
        char_position=0,
        char_typed="H",
        expected_char="H",
        timestamp=timestamp,
        time_since_previous=100.0
    )
    
    # Verify keystroke was recorded
    assert keystroke_id is not None
    assert keystroke_id > 0
    
    # Get keystroke from database
    result = sample_session["db_manager"].execute(
        """
        SELECT * 
        FROM session_keystrokes 
        WHERE keystroke_id = ?
        """,
        (keystroke_id,)
    ).fetchone()
    
    assert result is not None
    # session_id is now a string
    assert result[0] == str(sample_session["session_id"])
    assert result[1] == keystroke_id  # keystroke_id
    # result[2] is keystroke_time (datetime)
    assert result[3] == "H"  # keystroke_char
    assert result[4] == "H"  # expected_char
    assert result[5] == 1  # is_correct (1 for correct keystroke)
    # time_since_previous as float
    assert abs(cast(float, result[6]) - 100.0) < 0.001


def test_record_error_in_keystrokes(sample_session: Dict[str, Any]) -> None:
    """Test recording errors as keystrokes with is_correct=0.
    
    Args:
        sample_session: Fixture providing a sample session for testing.
    """
    # Initialize keystroke manager
    keystroke_manager = PracticeSessionKeystrokeManager(sample_session["db_manager"])
    
    # Record an error as a keystroke with is_correct=0
    keystroke_id = keystroke_manager.record_keystroke(
        session_id=str(sample_session["session_id"]),
        char_position=5,
        char_typed=".",
        expected_char=",",
        timestamp=datetime.now(),
        time_since_previous=500.0
    )
    
    # Verify keystroke was recorded
    assert keystroke_id is not None
    
    # Get keystroke from database
    result = sample_session["db_manager"].execute(
        """
        SELECT * 
        FROM session_keystrokes 
        WHERE session_id = ? 
        AND keystroke_id = ? 
        AND is_correct = 0
        """,
        (str(sample_session["session_id"]), keystroke_id)
    ).fetchone()
    
    # Verify error data is in the keystroke record
    assert result is not None
    assert result[0] == str(sample_session["session_id"])  # session_id
    assert result[3] == "."  # keystroke_char
    assert result[4] == ","  # expected_char
    assert result[5] == 0  # is_correct (0 = error)
    
    # Count errors (incorrect keystrokes) for this session
    error_count_result = sample_session["db_manager"].execute(
        """
        SELECT COUNT(*) 
        FROM session_keystrokes 
        WHERE session_id = ? 
        AND is_correct = 0
        """,
        (str(sample_session["session_id"]),)
    ).fetchone()
    
    assert error_count_result is not None
    assert error_count_result[0] >= 1  # type: ignore


def test_save_session_data(sample_session: Dict[str, Any]) -> None:
    """Test saving complete session data with keystrokes, errors, and n-gram analysis.
    
    Args:
        sample_session: Fixture providing a sample session for testing.
    """
    # Create sample keystrokes with consistent timing
    keystrokes: List[Dict[str, Any]] = []
    now = datetime.now()
    content = "Hello, world!"
    
    # Create keystroke data matching the schema
    for i, char in enumerate(content):
        keystroke = {
            "timestamp": now + timedelta(milliseconds=i * 100),
            "keystroke_char": "." if i == 5 else char,  # Add error at position 5
            "expected_char": char,
            "is_correct": 0 if i == 5 else 1,  # Mark error at position 5
            "time_since_previous": 100.0 if i > 0 else 0.0,
            "char_position": i
        }
        keystrokes.append(keystroke)
    
    logger.info("Starting test with content: %s", content)
    
    # First, ensure the session has the correct content in the database
    sample_session["db_manager"].execute(
        """
        UPDATE practice_sessions 
        SET content = ? 
        WHERE session_id = ?
        """,
        (content, str(sample_session["session_id"]))
    )
    
    # Verify the session exists in the database
    session_exists = sample_session["db_manager"].fetchone(
        """
        SELECT 1 
        FROM practice_sessions 
        WHERE session_id = ?
        """,
        (str(sample_session["session_id"]),)
    )
    assert session_exists is not None, \
        f"Session {sample_session['session_id']} not found in database"
    
    # Save session data
    save_session_data(
        session_manager=sample_session["session_manager"],
        session_id=str(sample_session["session_id"]),
        keystrokes=keystrokes,
        errors=[]  # Empty list since errors are now tracked in keystrokes
    )
    
    # Verify keystrokes were saved
    saved_keystrokes = sample_session["db_manager"].execute(
        """
        SELECT keystroke_char, expected_char, is_correct 
        FROM session_keystrokes 
        WHERE session_id = ? 
        ORDER BY keystroke_time
        """,
        (str(sample_session["session_id"]),)
    ).fetchall()
    
    logger.debug("Keystrokes in database: %s", saved_keystrokes)
    
    # Verify we have the expected number of keystrokes
    assert len(saved_keystrokes) == len(keystrokes)
    
    # Verify at least one keystroke is marked as incorrect
    has_errors = any(not k[2] for k in saved_keystrokes)  # Check is_correct flag
    assert has_errors, "Expected at least one incorrect keystroke"


def test_analyze_ngrams(sample_session: Dict[str, Any]) -> None:
    """Test analyzing n-grams for a session.
    
    Args:
        sample_session: Fixture providing a sample session for testing.
    """
    # Create sample keystrokes with consistent timing
    keystrokes: List[Dict[str, Any]] = []
    now = datetime.now()
    test_text = "ababcabcabc"  # Text with repeating patterns
    
    for i, char in enumerate(test_text):
        is_error = (i == 5)  # Error at position 5
        keystrokes.append({
            "timestamp": now + timedelta(milliseconds=i * 100),
            "keystroke_char": "d" if is_error else char,
            "expected_char": char,
            "is_correct": 0 if is_error else 1,
            "time_since_previous": 100.0 if i > 0 else 0.0,
            "char_position": i
        })

    # Initialize ngram analyzer
    ngram_analyzer = NgramAnalyzer(sample_session["db_manager"])

    # Save the keystrokes to the database first
    keystroke_manager = PracticeSessionKeystrokeManager(sample_session["db_manager"])
    for k in keystrokes:
        keystroke_manager.record_keystroke(
            session_id=str(sample_session["session_id"]),
            char_position=cast(int, k["char_position"]),
            char_typed=cast(str, k["keystroke_char"]),
            expected_char=cast(str, k["expected_char"]),
            timestamp=cast(datetime, k["timestamp"]),
            time_since_previous=cast(float, k["time_since_previous"])
        )

    # Update session content
    sample_session["db_manager"].execute(
        """
        UPDATE practice_sessions 
        SET content = ? 
        WHERE session_id = ?
        """,
        (test_text, str(sample_session["session_id"]))
    )

    # Now analyze n-grams using the method's actual signature
    ngram_analyzer.analyze_session_ngrams(
        session_id=str(sample_session["session_id"]),
        min_size=2,
        max_size=3
    )

    # Get speed results for bigrams (n=2)
    bigram_speeds = sample_session["db_manager"].execute(
        """
        SELECT ngram, ngram_time_ms 
        FROM session_ngram_speed 
        WHERE session_id = ? AND ngram_size = 2
        """,
        (str(sample_session["session_id"]),)
    ).fetchall()
    
    # Verify we got some n-gram results
    # Note: The test content is 'ababcabcabc' which should generate several bigrams
    # Even with the error at position 5, we should still get some valid bigrams
    assert len(bigram_speeds) > 0, f"Expected some n-gram speed results, got {bigram_speeds}"
    
    # Check that we have timing data for some n-grams
    found_ngrams = {row[0] for row in bigram_speeds}
    # These are the possible bigrams in 'ababcabcabc' (with error at position 5)
    expected_ngrams = {'ab', 'ba', 'bc', 'ca', 'cb'}
    assert any(ngram in found_ngrams for ngram in expected_ngrams), \
        f"Expected to find some of {expected_ngrams} in {found_ngrams}"


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main(["-v", "-s", __file__]))
