"""
Test module for NGram models and analyzer functionality.

This test suite covers the NGram model and NGramAnalyzer class functionality
as specified in the ngram.md requirements.
"""

import os
import uuid
import datetime
import tempfile
import pytest
from typing import List, Optional
from db.database_manager import DatabaseManager
from models.keystroke import Keystroke
from models.practice_session import PracticeSession, PracticeSessionManager
from models.ngram_analyzer import NGram, NGramAnalyzer
import json

# Helper function to find an NGram by text in a list of NGrams
def _find_ngram_in_list(ngram_list: List[NGram], text: str) -> Optional[NGram]:
    """Finds the first occurrence of an NGram with the given text in a list."""
    for ngram_obj in ngram_list:
        if ngram_obj.text == text:
            return ngram_obj
    return None

# Define BACKSPACE_CHAR for use in tests
BACKSPACE_CHAR = "\x08"  # Standard ASCII for backspace

@pytest.fixture
def temp_db():
    """
    Test objective: Create a temporary database for testing.
    
    This fixture provides a temporary, isolated SQLite database for testing.
    It initializes the schema and yields the database manager, then
    ensures cleanup after the test.
    """
    # Create a temporary file for the database
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_file.close()
    
    # Initialize database with full schema
    db = DatabaseManager(db_file.name)
    db.init_tables()
    
    yield db
    
    # Clean up after the test
    db.close()
    os.unlink(db_file.name)


@pytest.fixture
def test_practice_session(temp_db) -> PracticeSession:
    """
    Test objective: Create a test practice session for NGram analysis.
    
    This fixture creates a minimal practice session suitable for testing.
    It sets up all required database dependencies (category and snippet).
    """
    # Create a category first (required for foreign key constraint)
    temp_db.execute(
        "INSERT INTO categories (category_name) VALUES (?)",
        ("Test Category",),
        commit=True
    )
    
    # Get the category ID
    category_row = temp_db.fetchone("SELECT category_id FROM categories WHERE category_name = ?", ("Test Category",))
    category_id = category_row[0]
    
    # Create a snippet (required for foreign key constraint)
    temp_db.execute(
        "INSERT INTO snippets (category_id, snippet_name) VALUES (?, ?)",
        (category_id, "Test Snippet"),
        commit=True
    )
    
    # Get the snippet ID
    snippet_row = temp_db.fetchone("SELECT snippet_id FROM snippets WHERE snippet_name = ?", ("Test Snippet",))
    snippet_id = snippet_row[0]
    
    # Add content to the snippet
    temp_db.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (snippet_id, 1, "test typing content"),
        commit=True
    )
    
    # Create a simple session with basic information
    session_id = str(uuid.uuid4())
    session = PracticeSession(
        session_id=session_id,
        snippet_id=snippet_id,  # Use the actual snippet ID
        snippet_index_start=0,
        snippet_index_end=10,
        content="test typing",
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now() + datetime.timedelta(minutes=1),
        total_time=60.0,  # 60 seconds
        session_wpm=30.0,  # 30 words per minute
        session_cpm=150.0,  # 150 chars per minute
        expected_chars=10,
        actual_chars=10,
        errors=0,
        efficiency=100.0,
        correctness=100.0,
        accuracy=100.0
    )
    
    # Save the session to the database
    session_manager = PracticeSessionManager(temp_db)
    session_manager.create_session(session)
    
    return session


@pytest.fixture
def test_keystrokes(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create test keystrokes for NGram analysis.
    
    This fixture creates two keystrokes associated with the test session.
    """
    # Create two keystrokes with the session_id
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=0,
            keystroke_time=now,
            keystroke_char="t",
            expected_char="t",
            is_correct=True,
            time_since_previous=None  # First keystroke has no previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=1,
            keystroke_time=now + datetime.timedelta(milliseconds=100),
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=100  # 100ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for keystroke in keystrokes:
        # Use the database manager directly to insert the keystrokes
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes


@pytest.fixture
def single_keystroke(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create a single keystroke for testing no n-gram scenario.
    
    This fixture creates just one keystroke ('T') associated with the test session.
    """
    # Create a single keystroke with the session_id
    now = datetime.datetime.now()
    keystroke = Keystroke(
        session_id=test_practice_session.session_id,
        keystroke_id=0,
        keystroke_time=now,
        keystroke_char="T",
        expected_char="T",
        is_correct=True,
        time_since_previous=None  # First keystroke has no previous
    )
    
    # Save keystroke to the database
    temp_db.execute(
        """
        INSERT INTO session_keystrokes 
        (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            keystroke.session_id,
            keystroke.keystroke_id,
            keystroke.keystroke_time.isoformat(),
            keystroke.keystroke_char,
            keystroke.expected_char,
            keystroke.is_correct,
            keystroke.time_since_previous
        ),
        commit=True
    )
    
    return [keystroke]


@pytest.fixture
def two_keystrokes_no_errors(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create two correct keystrokes for testing basic bigram formation.
    
    This fixture creates two keystrokes ('T' and 'h') with no errors and a
    specific timing (500ms between keystrokes).
    """
    # Create two keystrokes with the session_id
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=0,
            keystroke_time=now,
            keystroke_char="T",
            expected_char="T",
            is_correct=True,
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=1,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500  # 500ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for keystroke in keystrokes:
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes


@pytest.fixture
def two_keystrokes_error_at_first(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create two keystrokes with an error on the first keystroke.
    
    This fixture creates two keystrokes where:
    - First keystroke is incorrect: 'G' instead of 'T'
    - Second keystroke is correct: 'h'
    - Timing: 0ms, 500ms
    """
    # Create two keystrokes with the session_id, first one has an error
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=0,
            keystroke_time=now,
            keystroke_char="G",  # Error: typed 'G' instead of 'T'
            expected_char="T",
            is_correct=False,    # Mark as incorrect
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=1,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500  # 500ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for keystroke in keystrokes:
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes


@pytest.fixture
def two_keystrokes_error_at_second(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create two keystrokes with an error on the second keystroke.
    
    This fixture creates two keystrokes where:
    - First keystroke is correct: 'T'
    - Second keystroke is incorrect: 'b' instead of 'h'
    - Timing: 0ms, 500ms
    """
    # Create two keystrokes with the session_id, second one has an error
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=0,
            keystroke_time=now,
            keystroke_char="T",
            expected_char="T",
            is_correct=True,
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=1,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="b",  # Error: typed 'b' instead of 'h'
            expected_char="h",
            is_correct=False,    # Mark as incorrect
            time_since_previous=500  # 500ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for keystroke in keystrokes:
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes


@pytest.fixture
def three_keystrokes_no_errors(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create three correct keystrokes for testing multiple n-gram formation.
    
    This fixture creates three keystrokes ('T', 'h', and 'e') with no errors and
    specific timing (500ms between first and second, 1000ms between second and third).
    """
    # Create three keystrokes with the session_id
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=0,
            keystroke_time=now,
            keystroke_char="T",
            expected_char="T",
            is_correct=True,
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=1,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500  # 500ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=2,
            keystroke_time=now + datetime.timedelta(milliseconds=1500),  # 1500 from start
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000  # 1000ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for keystroke in keystrokes:
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes


@pytest.fixture
def three_keystrokes_error_at_first(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create three keystrokes with an error on the first keystroke.
    
    This fixture creates three keystrokes where:
    - First keystroke is incorrect: 'G' instead of 'T'
    - Second keystroke is correct: 'h'
    - Third keystroke is correct: 'e'
    - Timing: 0ms, 500ms, 1000ms
    """
    # Create three keystrokes with the session_id, first one has an error
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=0,
            keystroke_time=now,
            keystroke_char="G",  # Error: typed 'G' instead of 'T'
            expected_char="T",
            is_correct=False,    # Mark as incorrect
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=1,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500  # 500ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=2,
            keystroke_time=now + datetime.timedelta(milliseconds=1500),  # 1500 from start
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000  # 1000ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for keystroke in keystrokes:
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes


@pytest.fixture
def three_keystrokes_error_at_second(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create three keystrokes with an error on the second keystroke.
    
    This fixture creates three keystrokes where:
    - First keystroke is correct: 'T'
    - Second keystroke is incorrect: 'b' instead of 'h'
    - Third keystroke is correct: 'e'
    - Timing: 0ms, 500ms, 1000ms
    """
    # Create three keystrokes with the session_id, second one has an error
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=0,
            keystroke_time=now,
            keystroke_char="T",
            expected_char="T",
            is_correct=True,
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=1,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="b",  # Error: typed 'b' instead of 'h'
            expected_char="h",
            is_correct=False,    # Mark as incorrect
            time_since_previous=500  # 500ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=2,
            keystroke_time=now + datetime.timedelta(milliseconds=1500),  # 1500 from start
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000  # 1000ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for keystroke in keystrokes:
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes


@pytest.fixture
def three_keystrokes_error_at_third(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create three keystrokes with an error on the third keystroke.
    
    This fixture creates three keystrokes where:
    - First keystroke is correct: 'T'
    - Second keystroke is correct: 'h'
    - Third keystroke is incorrect: 'd' instead of 'e'
    - Timing: 0ms, 500ms, 1000ms
    """
    # Create three keystrokes with the session_id, third one has an error
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=0,
            keystroke_time=now,
            keystroke_char="T",
            expected_char="T",
            is_correct=True,
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=1,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500  # 500ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=2,
            keystroke_time=now + datetime.timedelta(milliseconds=1500),  # 1500 from start
            keystroke_char="d",  # Error: typed 'd' instead of 'e'
            expected_char="e",
            is_correct=False,    # Mark as incorrect
            time_since_previous=1000  # 1000ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for keystroke in keystrokes:
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes


@pytest.fixture
def four_keystrokes_no_errors(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create four correct keystrokes for testing multiple n-gram formation.
    
    This fixture creates four keystrokes ('T', 'h', 'e', 'n') with no errors and
    specific timing (500ms between first and second, 1000ms between second and third,
    300ms between third and fourth).
    """
    # Create four keystrokes with the session_id, all correct
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=0,
            keystroke_time=now,
            keystroke_char="T",
            expected_char="T",
            is_correct=True,
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=1,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500  # 500ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=2,
            keystroke_time=now + datetime.timedelta(milliseconds=1500),  # 1500 from start
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000  # 1000ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=3,
            keystroke_time=now + datetime.timedelta(milliseconds=1800),  # 1800 from start
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300  # 300ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for keystroke in keystrokes:
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes


@pytest.fixture
def four_keystrokes_error_at_first(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create four keystrokes with an error on the first keystroke.
    
    This fixture creates four keystrokes where:
    - First keystroke is incorrect: 'G' instead of 'T'
    - Second keystroke is correct: 'h'
    - Third keystroke is correct: 'e'
    - Fourth keystroke is correct: 'n'
    - Timing: 0ms, 500ms, 1000ms, 300ms
    """
    # Create four keystrokes with the session_id, first has error
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=0,
            keystroke_time=now,
            keystroke_char="G",  # Error: typed 'G' instead of 'T'
            expected_char="T",
            is_correct=False,    # Mark as incorrect
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=1,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500  # 500ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=2,
            keystroke_time=now + datetime.timedelta(milliseconds=1500),  # 1500 from start
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000  # 1000ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=3,
            keystroke_time=now + datetime.timedelta(milliseconds=1800),  # 1800 from start
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300  # 300ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for keystroke in keystrokes:
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes


@pytest.fixture
def four_keystrokes_error_at_second(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create four keystrokes with an error on the second keystroke.
    
    This fixture creates four keystrokes where:
    - First keystroke is correct: 'T'
    - Second keystroke is incorrect: 'g' instead of 'h'
    - Third keystroke is correct: 'e'
    - Fourth keystroke is correct: 'n'
    - Timing: 0ms, 500ms, 1000ms, 300ms
    """
    # Create four keystrokes with the session_id, second has error
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=0,
            keystroke_time=now,
            keystroke_char="T",
            expected_char="T",
            is_correct=True,
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=1,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="g",  # Error: typed 'g' instead of 'h'
            expected_char="h",
            is_correct=False,    # Mark as incorrect
            time_since_previous=500  # 500ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=2,
            keystroke_time=now + datetime.timedelta(milliseconds=1500),  # 1500 from start
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000  # 1000ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=3,
            keystroke_time=now + datetime.timedelta(milliseconds=1800),  # 1800 from start
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300  # 300ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for keystroke in keystrokes:
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes


@pytest.fixture
def three_keystrokes_backspace_at_first(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create keystrokes for 'The' with a correction at the first char (G-<BS>-T-h-e).
    Target: "The"
    Typed: G, <BACKSPACE>, T, h, e
    Timings: G (0ms), <BS> (500ms after G), T (300ms after <BS>), h (500ms after T), e (500ms after h)
    """
    now = datetime.datetime.now()
    session_id = test_practice_session.session_id
    keystrokes_data = [
        {'id': 0, 'char': 'G', 'expected': 'T', 'correct': False, 'tsp': 0},
        {'id': 1, 'char': BACKSPACE_CHAR, 'expected': BACKSPACE_CHAR, 'correct': True, 'tsp': 500},
        {'id': 2, 'char': 'T', 'expected': 'T', 'correct': True, 'tsp': 300},
        {'id': 3, 'char': 'h', 'expected': 'h', 'correct': True, 'tsp': 500},
        {'id': 4, 'char': 'e', 'expected': 'e', 'correct': True, 'tsp': 500},
    ]
    
    keystrokes: List[Keystroke] = []
    current_time = now
    for i, kd in enumerate(keystrokes_data):
        if i > 0:
            current_time += datetime.timedelta(milliseconds=kd['tsp'])
        k = Keystroke(
            session_id=session_id,
            keystroke_id=kd['id'],
            keystroke_time=current_time,
            keystroke_char=kd['char'],
            expected_char=kd['expected'],
            is_correct=kd['correct'],
            time_since_previous=kd['tsp']
        )
        keystrokes.append(k)
        temp_db.execute(
            """INSERT INTO session_keystrokes (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (k.session_id, k.keystroke_id, k.keystroke_time.isoformat(), k.keystroke_char, k.expected_char, k.is_correct, k.time_since_previous),
            commit=True
        )
    return keystrokes


@pytest.fixture
def three_keystrokes_backspace_at_second(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create keystrokes for 'The' with a correction at the second char (T-g-<BS>-h-e).
    Target: "The"
    Typed: T, g, <BACKSPACE>, h, e
    Timings: T (0ms), g (500ms after T), <BS> (300ms after g), h (500ms after <BS>), e (500ms after h)
    """
    now = datetime.datetime.now()
    session_id = test_practice_session.session_id
    keystrokes_data = [
        {'id': 0, 'char': 'T', 'expected': 'T', 'correct': True, 'tsp': 0},
        {'id': 1, 'char': 'g', 'expected': 'h', 'correct': False, 'tsp': 500},
        {'id': 2, 'char': BACKSPACE_CHAR, 'expected': BACKSPACE_CHAR, 'correct': True, 'tsp': 300},
        {'id': 3, 'char': 'h', 'expected': 'h', 'correct': True, 'tsp': 500},
        {'id': 4, 'char': 'e', 'expected': 'e', 'correct': True, 'tsp': 500},
    ]
    
    keystrokes: List[Keystroke] = []
    current_time = now
    for i, kd in enumerate(keystrokes_data):
        if i > 0:
            current_time += datetime.timedelta(milliseconds=kd['tsp'])
        k = Keystroke(
            session_id=session_id,
            keystroke_id=kd['id'],
            keystroke_time=current_time,
            keystroke_char=kd['char'],
            expected_char=kd['expected'],
            is_correct=kd['correct'],
            time_since_previous=kd['tsp']
        )
        keystrokes.append(k)
        temp_db.execute(
            """INSERT INTO session_keystrokes (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (k.session_id, k.keystroke_id, k.keystroke_time.isoformat(), k.keystroke_char, k.expected_char, k.is_correct, k.time_since_previous),
            commit=True
        )
    return keystrokes


@pytest.fixture
def three_keystrokes_backspace_at_first_and_second(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create keystrokes for 'The' with corrections at first and second chars (G-<BS>-T-g-<BS>-h-e).
    Target: "The"
    Typed: G, <BS>, T, g, <BS>, h, e
    Timings: G(0), <BS1>(500), T(300), g(500), <BS2>(300), h(500), e(500)
    """
    now = datetime.datetime.now()
    session_id = test_practice_session.session_id
    keystrokes_data = [
        {'id': 0, 'char': 'G', 'expected': 'T', 'correct': False, 'tsp': 0}, 
        {'id': 1, 'char': BACKSPACE_CHAR, 'expected': BACKSPACE_CHAR, 'correct': True, 'tsp': 500},
        {'id': 2, 'char': 'T', 'expected': 'T', 'correct': True, 'tsp': 300},
        {'id': 3, 'char': 'g', 'expected': 'h', 'correct': False, 'tsp': 500},
        {'id': 4, 'char': BACKSPACE_CHAR, 'expected': BACKSPACE_CHAR, 'correct': True, 'tsp': 300},
        {'id': 5, 'char': 'h', 'expected': 'h', 'correct': True, 'tsp': 500},
        {'id': 6, 'char': 'e', 'expected': 'e', 'correct': True, 'tsp': 500},
    ]

    keystrokes: List[Keystroke] = []
    current_time = now
    for i, kd in enumerate(keystrokes_data):
        if i > 0:
            current_time += datetime.timedelta(milliseconds=kd['tsp'])
        k = Keystroke(
            session_id=session_id,
            keystroke_id=kd['id'],
            keystroke_time=current_time,
            keystroke_char=kd['char'],
            expected_char=kd['expected'],
            is_correct=kd['correct'],
            time_since_previous=kd['tsp']
        )
        keystrokes.append(k)
        temp_db.execute(
            """INSERT INTO session_keystrokes (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (k.session_id, k.keystroke_id, k.keystroke_time.isoformat(), k.keystroke_char, k.expected_char, k.is_correct, k.time_since_previous),
            commit=True
        )
    return keystrokes


class TestNGramModels:
    """Test suite for NGram model and analyzer functionality."""
    
    def test_basic_ngram_analyzer_initialization(self, temp_db, test_practice_session, test_keystrokes):
        """
        Test objective: Verify basic NGram analyzer initialization.
        
        This test checks that:
        1. The NGramAnalyzer can be initialized with a session and keystrokes
        2. The session has a valid session ID
        3. The keystroke list contains exactly 2 entries
        """
        # Create NGramAnalyzer instance
        analyzer = NGramAnalyzer(test_practice_session, test_keystrokes, temp_db)
        
        # Assert session and keystroke setup
        assert analyzer.session.session_id is not None, "Session ID should not be None"
        assert len(analyzer.keystrokes) == 2, "Should have exactly 2 keystrokes"
        
        # Verify keystrokes have correct properties
        assert analyzer.keystrokes[0].keystroke_char == "t", "First keystroke should be 't'"
        assert analyzer.keystrokes[1].keystroke_char == "e", "Second keystroke should be 'e'"
    
    def test_single_keystroke_no_ngrams(self, temp_db, test_practice_session, single_keystroke):
        """
        Test objective: Verify that a single keystroke produces no n-grams.
        
        This test checks that:
        1. The analyzer properly handles a single keystroke scenario
        2. No n-grams are identified in the analyzer object
        3. No n-grams are saved to the database
        """
        # Define the session ID constant for better readability in assertions
        session_id = test_practice_session.session_id
        
        # Create NGramAnalyzer instance with a single keystroke
        analyzer = NGramAnalyzer(test_practice_session, single_keystroke, temp_db)
        
        # Run the analyzer
        analyzer.analyze()  # Analyze n-grams of sizes 2-5
        
        # Verify analysis was completed
        assert analyzer.analysis_complete is True, "Analysis should be marked as complete"
        
        # Verify no valid n-grams were identified in memory
        # Note: The single keystroke is insufficient to form any n-gram of size >= 2
        for size in range(2, 6):  # Check for n-grams of sizes 2-5
            # The dictionaries might not have keys for all sizes since we only have one keystroke
            # We just check that there are no valid n-grams identified
            if size in analyzer.speed_ngrams:
                assert len(analyzer.speed_ngrams[size]) == 0, f"Should be no speed n-grams of size {size}"
            
            if size in analyzer.error_ngrams:
                assert len(analyzer.error_ngrams[size]) == 0, f"Should be no error n-grams of size {size}"
        
        # Try to save to database - should succeed but not actually save anything
        save_result = analyzer.save_to_database()
        assert save_result is True, "Save operation should succeed even with no n-grams"
        
        # Verify no n-grams were saved to the database
        speed_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert speed_ngrams_count == 0, "No speed n-grams should be saved to the database"
        
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"
        
        # Get slowest n-grams - should return empty list
        slowest_ngrams = analyzer.get_slowest_ngrams(size=2)
        assert len(slowest_ngrams) == 0, "Should be no slowest n-grams"
        
        # Get error-prone n-grams - should return empty list
        error_ngrams = analyzer.get_most_error_prone_ngrams(size=2)
        assert len(error_ngrams) == 0, "Should be no error-prone n-grams"
    
    def test_two_keystrokes_no_errors(self, temp_db, test_practice_session, two_keystrokes_no_errors):
        """
        Test objective: Verify that two keystrokes produce a single bigram with correct timing.
        
        This test checks that:
        1. The analyzer properly handles two keystrokes scenario
        2. Exactly one bigram is identified in memory
        3. The bigram has the correct timing (500ms)
        4. The bigram is correctly saved to the database
        """
        # Define the session ID constant for better readability in assertions
        session_id = test_practice_session.session_id
        
        # Create NGramAnalyzer instance with two keystrokes
        analyzer = NGramAnalyzer(test_practice_session, two_keystrokes_no_errors, temp_db)
        
        # Run the analyzer for bigrams only
        analyzer.analyze()  # Analyze only bigrams (size 2)
        
        # Verify analysis was completed
        assert analyzer.analysis_complete is True, "Analysis should be marked as complete"
        
        # Verify exactly one bigram was identified in memory
        assert 2 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for bigrams"
        assert len(analyzer.speed_ngrams[2]) == 1, "Should be exactly one speed bigram"
        
        # Retrieve the single bigram
        bigram_text = "Th"  # The expected bigram text
        
        # Validate its properties
        bigram = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram_text)
        assert bigram is not None, f"Bigram '{bigram_text}' not found in speed_ngrams[2]"
        assert bigram.text == bigram_text, f"Bigram text should be '{bigram_text}'"
        assert bigram.size == 2, "Bigram size should be 2"
        assert len(bigram.keystrokes) == 2, "Bigram should have 2 keystrokes"
        
        # Check that the bigram timing is correct - should be 500ms (from the second keystroke)
        assert bigram.total_time_ms == 500, "Bigram total time should be 500ms"
        # Check that the bigram is clean (no errors)
        assert bigram.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram.is_error is False, "Bigram should not be an error bigram"
        assert bigram.is_valid is True, "Bigram should be valid"
        
        # Check error n-grams - should be empty
        assert len(analyzer.error_ngrams.get(2, [])) == 0, "Should be no error bigrams of size 2"
        
        # Save to database
        save_result = analyzer.save_to_database()
        assert save_result is True, "Save operation should succeed"
        
        # Verify the bigram was saved to the database correctly
        speed_ngrams = temp_db.fetchall(
            """SELECT ngram_size, ngram, ngram_time_ms 
               FROM session_ngram_speed 
               WHERE session_id = ?""", 
            (session_id,)
        )
        
        assert len(speed_ngrams) == 1, "Should be exactly one speed n-gram in the database"
        db_bigram = speed_ngrams[0]
        assert db_bigram[0] == 2, "Database bigram size should be 2"
        assert db_bigram[1] == bigram_text, f"Database bigram text should be '{bigram_text}'"
        # Check that the saved time value is the average time per character (500ms / 2 chars = 250ms)
        # This matches the NGram.avg_time_per_char_ms property formula
        assert db_bigram[2] == 250, "Database bigram time should be 250ms (avg per character)"
        
        # Verify no error n-grams were saved
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"
        
        # Get slowest n-grams - should return our bigram
        slowest_ngrams = analyzer.get_slowest_ngrams(size=2)
        assert len(slowest_ngrams) == 1, "Should be one slowest bigram"
        assert slowest_ngrams[0].text == bigram_text, f"Slowest bigram should be '{bigram_text}'"
        
        # Get error-prone n-grams - should return empty list
        error_ngrams = analyzer.get_most_error_prone_ngrams(size=2)
        assert len(error_ngrams) == 0, "Should be no error-prone bigrams"


    def test_two_keystrokes_error_at_first(self, temp_db, test_practice_session, two_keystrokes_error_at_first):
        """
        Test objective: Verify that two keystrokes with an error on the first keystroke are analyzed correctly.
        
        This test checks that:
        1. The analyzer properly handles a scenario with an error on the first keystroke
        2. No n-grams are identified (as the error is on the first keystroke)
        3. No n-grams are saved to the database
        """
        # Define the session ID constant for better readability in assertions
        session_id = test_practice_session.session_id
        
        # Create NGramAnalyzer instance with two keystrokes, first has error
        analyzer = NGramAnalyzer(test_practice_session, two_keystrokes_error_at_first, temp_db)
        
        # Run the analyzer for bigrams
        analyzer.analyze()  # Analyze bigrams
        
        # Verify analysis was completed
        assert analyzer.analysis_complete is True, "Analysis should be marked as complete"
        
        # Verify no speed bigrams were identified (due to error on first keystroke)       
        assert (2 not in analyzer.speed_ngrams) or (len(analyzer.speed_ngrams[2]) == 0), "Should be no speed bigrams due to error on first keystroke"  
        
        # Verify no error bigrams were identified
        # (errors at the beginning don't create error n-grams)
        assert (2 not in analyzer.error_ngrams) or (len(analyzer.error_ngrams[2]) == 0), "Should be no error bigrams"
        
        # Save to database
        save_result = analyzer.save_to_database()
        assert save_result is True, "Save operation should succeed"
        
        # Verify no n-grams were saved to the speed table
        speed_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert speed_ngrams_count == 0, "No speed n-grams should be saved to the database"
        
        # Verify no n-grams were saved to the errors table
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"
        
        # Get slowest n-grams - should return empty list since there are no speed n-grams
        slowest_bigrams = analyzer.get_slowest_ngrams(size=2)
        assert len(slowest_bigrams) == 0, "Should be no slowest bigrams"
        
        # Get error-prone n-grams - should return empty list since there are no error n-grams
        error_bigrams = analyzer.get_most_error_prone_ngrams(size=2)
        assert len(error_bigrams) == 0, "Should be no error-prone bigrams"
        
    def test_two_keystrokes_error_at_second(self, temp_db, test_practice_session, two_keystrokes_error_at_second):
        """
        Test objective: Verify that two keystrokes with an error on the second keystroke are analyzed correctly.
        
        This test checks that:
        1. The analyzer properly handles a scenario with an error on the second keystroke
        2. One bigram (Tb) is identified as an error n-gram
        3. No speed n-grams are identified (due to the error)
        4. The error n-gram has correct timing (500ms)
        5. The n-gram is correctly saved to the database error table
        """
        # Define the session ID constant for better readability in assertions
        session_id = test_practice_session.session_id
        
        # Create NGramAnalyzer instance with two keystrokes, second has error
        analyzer = NGramAnalyzer(test_practice_session, two_keystrokes_error_at_second, temp_db)
        
        # Run the analyzer for bigrams
        analyzer.analyze()  # Analyze bigrams
        
        # Verify analysis was completed
        assert analyzer.analysis_complete is True, "Analysis should be marked as complete"
        
        # Verify no speed bigrams were identified (due to error)
        assert (2 not in analyzer.speed_ngrams) or (len(analyzer.speed_ngrams[2]) == 0), "Should be no speed bigrams due to error on second keystroke"
        
        # Verify error n-grams were identified correctly
        assert 2 in analyzer.error_ngrams, "Error n-grams dictionary should have key for bigrams"
        assert len(analyzer.error_ngrams[2]) == 1, "Should be exactly one error bigram"
        
        # Validate the error bigram 'Tb'
        bigram_text_to_find = "Tb"
        error_bigrams_list = analyzer.error_ngrams.get(2, [])
        bigram = _find_ngram_in_list(error_bigrams_list, bigram_text_to_find)
        assert bigram is not None, f"Error bigram '{bigram_text_to_find}' not found in analyzer.error_ngrams"
        assert bigram.text == bigram_text_to_find, f"Bigram text should be '{bigram_text_to_find}'"
        assert bigram.size == 2, "Bigram size should be 2"
        assert len(bigram.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram.total_time_ms == 500, "Bigram 'Tb' time should be 500ms"
        
        # Check that the bigram is flagged as an error bigram
        assert bigram.is_clean is False, "Bigram should not be clean (has errors)"
        assert bigram.error_on_last is True, "Bigram should have error on last character"
        assert bigram.other_errors is False, "Bigram should not have other errors"
        assert bigram.is_error is True, "Bigram should be an error bigram"
        assert bigram.is_valid is True, "Bigram should be valid for tracking"
        
        # Save to database
        save_result = analyzer.save_to_database()
        assert save_result is True, "Save operation should succeed"
        
        # Verify no n-grams were saved to the speed table
        speed_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert speed_ngrams_count == 0, "No speed n-grams should be saved to the database"
        
        # Verify the error n-gram was saved to the database correctly
        error_ngrams = temp_db.fetchall(
            """SELECT ngram_size, ngram 
               FROM session_ngram_errors 
               WHERE session_id = ?
               ORDER BY ngram_size, ngram""", 
            (session_id,)
        )
        
        assert len(error_ngrams) == 1, "Should be exactly one error n-gram in the database"
        
        # Verify the error bigram (Tb)
        db_bigram = error_ngrams[0]
        assert db_bigram[0] == 2, "Database error bigram size should be 2"
        assert db_bigram[1] == bigram_text_to_find, f"Database error bigram text should be '{bigram_text_to_find}'"
        
        # Get slowest n-grams - should return empty list since there are no speed n-grams
        slowest_bigrams = analyzer.get_slowest_ngrams(size=2)
        assert len(slowest_bigrams) == 0, "Should be no slowest bigrams"
        
        # Get error-prone n-grams - should return our error bigram
        error_bigrams = analyzer.get_most_error_prone_ngrams(size=2)
        assert len(error_bigrams) == 1, "Should be one error-prone bigram"
        assert error_bigrams[0].text == bigram_text_to_find, f"Error-prone bigram should be '{bigram_text_to_find}'"
    
    def test_three_keystrokes_no_errors(self, temp_db, test_practice_session, three_keystrokes_no_errors):
        """
        Test objective: Verify that three keystrokes produce correct bigrams and trigram with proper timing.
        
        This test checks that:
        1. The analyzer properly handles three keystrokes scenario
        2. Two bigrams and one trigram are identified with correct timing:
           - Bigram 'Th': 500ms
           - Bigram 'he': 1000ms
           - Trigram 'The': 1500ms total
        3. All identified n-grams are clean (no errors).
        4. N-grams are correctly saved to the database.
        5. Slowest n-grams are correctly identified.
        6. No error-prone n-grams are identified.
        """
        # Define the session ID constant for better readability in assertions
        session_id = test_practice_session.session_id
        
        # Create NGramAnalyzer instance with three keystrokes
        analyzer = NGramAnalyzer(test_practice_session, three_keystrokes_no_errors, temp_db)
        
        # Run the analyzer for n-grams of default sizes (2-5)
        analyzer.analyze()
        
        # Verify analysis was completed
        assert analyzer.analysis_complete is True, "Analysis should be marked as complete"
        
        # Verify bigrams (size 2) were identified correctly
        assert 2 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for bigrams"
        assert len(analyzer.speed_ngrams[2]) == 2, "Should be exactly two speed bigrams"
        
        # Validate the first bigram 'Th'
        bigram1_text = "Th"  # The expected first bigram text
        
        # Retrieve the bigram using the helper function
        bigram1 = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram1_text)
        assert bigram1 is not None, f"Bigram '{bigram1_text}' not found in speed_ngrams[2]"
        assert bigram1.text == bigram1_text, f"Bigram text should be '{bigram1_text}'"
        assert bigram1.size == 2, "Bigram size should be 2"
        assert len(bigram1.keystrokes) == 2, "Bigram should have 2 keystrokes"
        
        # Check that the bigram timing is correct - should be 500ms (from the second keystroke)
        assert bigram1.total_time_ms == 500, "Bigram 'Th' time should be 500ms"
        assert bigram1.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram1.is_error is False, "Bigram should not be an error bigram"
        assert bigram1.is_valid is True, "Bigram should be valid"
        
        # Validate the second bigram 'he'
        bigram2_text = "he"  # The expected second bigram text
        
        # Retrieve the bigram from the dictionary
        bigram2 = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram2_text)
        assert bigram2 is not None, f"Bigram '{bigram2_text}' not found in speed_ngrams[2]"
        assert bigram2.text == bigram2_text, f"Bigram text should be '{bigram2_text}'"
        assert bigram2.size == 2, "Bigram size should be 2"
        assert len(bigram2.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram2.total_time_ms == 1000, "Bigram 'he' time should be 1000ms"
        assert bigram2.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram2.is_error is False, "Bigram should not be an error bigram"
        assert bigram2.is_valid is True, "Bigram should be valid"
        
        # Verify trigram (size 3) was identified correctly
        assert 3 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for trigrams"
        assert len(analyzer.speed_ngrams[3]) == 1, "Should be exactly one speed trigram"
        
        # Validate the trigram 'The'
        trigram_text = "The"  # The expected trigram text
        
        # Retrieve the trigram from the dictionary
        trigram = _find_ngram_in_list(analyzer.speed_ngrams[3], trigram_text)
        assert trigram is not None, f"Trigram '{trigram_text}' not found in speed_ngrams[3]"
        assert trigram.text == trigram_text, f"Trigram text should be '{trigram_text}'"
        assert trigram.size == 3, "Trigram size should be 3"
        assert len(trigram.keystrokes) == 3, "Trigram should have 3 keystrokes"
        
        # For the trigram, we expect the total time to be 500ms + 1000ms = 1500ms
        # This is because we don't count the first keystroke's time in our calculation,
        # only the time_since_previous of subsequent keystrokes
        assert trigram.total_time_ms == 1500, "Trigram 'The' total time should be 1500ms"
        assert trigram.is_clean is True, "Trigram should be clean (no errors)"
        assert trigram.is_error is False, "Trigram should not be an error trigram"
        assert trigram.is_valid is True, "Trigram should be valid"
        
        # Verify no error n-grams were identified
        assert len(analyzer.error_ngrams[2]) == 0, "Should be no error bigrams"
        assert len(analyzer.error_ngrams[3]) == 0, "Should be no error trigrams"
        
        # Save to database
        save_result = analyzer.save_to_database()
        assert save_result is True, "Save operation should succeed"
        
        # Verify n-grams were saved to the database correctly
        speed_ngrams = temp_db.fetchall(
            """SELECT ngram_size, ngram, ngram_time_ms 
               FROM session_ngram_speed 
               WHERE session_id = ?
               ORDER BY ngram_size, ngram""", 
            (session_id,)
        )
        
        assert len(speed_ngrams) == 3, "Should be exactly three speed n-grams in the database"
        
        # Verify first bigram (Th)
        db_bigram1 = next((row for row in speed_ngrams if row[0] == 2 and row[1] == "Th"), None)
        assert db_bigram1 is not None, "Bigram 'Th' should be in database"
        assert db_bigram1[0] == 2, "Database bigram size should be 2"
        # Check that the saved time value is the average time per character (500ms / 2 chars = 250ms)
        assert db_bigram1[2] == 250, "Database bigram 'Th' time should be 250ms (avg per character)"
        
        # Verify second bigram (he)
        db_bigram2 = next((row for row in speed_ngrams if row[0] == 2 and row[1] == "he"), None)
        assert db_bigram2 is not None, "Bigram 'he' should be in database"
        assert db_bigram2[0] == 2, "Database bigram size should be 2"
        # Check that the saved time value is the average time per character (1000ms / 2 chars = 500ms)
        assert db_bigram2[2] == 500, "Database bigram 'he' time should be 500ms (avg per character)"
        
        # Verify trigram (The)
        db_trigram = next((row for row in speed_ngrams if row[0] == 3 and row[1] == "The"), None)
        assert db_trigram is not None, "Trigram 'The' should be in database"
        assert db_trigram[0] == 3, "Database trigram size should be 3"
        # Check that the saved time value is the average time per character (1500ms / 3 chars = 500ms)
        assert db_trigram[2] == 500, "Database trigram time should be 500ms (avg per character)"
        
        # Verify no error n-grams were saved
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"
        
        # Get slowest n-grams for each size - should return our n-grams
        slowest_bigrams = analyzer.get_slowest_ngrams(size=2)
        assert len(slowest_bigrams) == 2, "Should be two slowest bigrams"
        # The 'he' bigram should be the slowest since it has 1000ms vs 500ms for 'Th'
        assert slowest_bigrams[0].text == "he", "Slowest bigram should be 'he'"
        # Second one should be 'Th' (500ms)
        assert slowest_bigrams[1].text == "Th", "Second slowest bigram should be 'Th'"
        
        slowest_trigrams = analyzer.get_slowest_ngrams(size=3)
        assert len(slowest_trigrams) == 1, "Should be one slowest trigram"
        assert slowest_trigrams[0].text == "The", "Slowest trigram should be 'The'"
        
        # Get error-prone n-grams - should return empty lists
        error_prone_bigrams = analyzer.get_most_error_prone_ngrams(size=2)
        assert len(error_prone_bigrams) == 0, "Should be no error-prone bigrams"
        
        error_prone_trigrams = analyzer.get_most_error_prone_ngrams(size=3)
        assert len(error_prone_trigrams) == 0, "Should be no error-prone trigrams"
        
    
    def test_three_keystrokes_error_at_first(self, temp_db, test_practice_session, three_keystrokes_error_at_first):
        """
        Test objective: Verify that three keystrokes with an error on the first keystroke are analyzed correctly.
        
        This test checks that:
        1. The analyzer properly handles a scenario with an error on the first keystroke
        2. Only one bigram (he) should be valid, as the first keystroke has an error
        3. No trigrams should be valid due to the error
        4. The bigram has correct timing (1000ms)
        5. The n-gram is correctly saved to the database
        """
        # Define the session ID constant for better readability in assertions
        session_id = test_practice_session.session_id
        
        # Create NGramAnalyzer instance with three keystrokes, first has error
        analyzer = NGramAnalyzer(test_practice_session, three_keystrokes_error_at_first, temp_db)
        
        # Run the analyzer for both bigrams and trigrams
        analyzer.analyze()  # Analyze bigrams and trigrams
        
        # Verify analysis was completed
        assert analyzer.analysis_complete is True, "Analysis should be marked as complete"
        
        # Verify bigrams (size 2) were identified correctly
        assert 2 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for bigrams"
        
        # Should only have one valid bigram ('he'), since 'Gh' has an error
        assert len(analyzer.speed_ngrams[2]) == 1, "Should be exactly one speed bigram"
        
        # Validate the bigram 'he'
        bigram_text = "he"  # The expected bigram text
        
        # Retrieve the bigram from the dictionary using the helper function
        bigram = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram_text)
        assert bigram is not None, f"Bigram '{bigram_text}' not found in speed_ngrams[2]"
        assert bigram.text == bigram_text, f"Bigram text should be '{bigram_text}'"
        assert bigram.size == 2, "Bigram size should be 2"
        assert len(bigram.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram.total_time_ms == 1000, "Bigram 'he' time should be 1000ms"
        assert bigram.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram.is_error is False, "Bigram should not be an error bigram"
        assert bigram.is_valid is True, "Bigram should be valid"
        
        # The first bigram 'Gh' should not be in speed_ngrams since it has an error
        first_bigram_text = "Gh"
        first_bigram = _find_ngram_in_list(analyzer.speed_ngrams[2], first_bigram_text)
        assert first_bigram is None, f"Bigram '{first_bigram_text}' should not be in speed_ngrams due to error"
        
        # Verify no trigrams were identified (since first char has error)
        # When accessing analyzer.speed_ngrams[3], defaultdict automatically creates the key if needed
        assert len(analyzer.speed_ngrams[3]) == 0, "Should be no speed trigrams due to error"
        
        # Verify no error n-grams were identified for bigrams
        # Note: The error is on the first keystroke, not the last character of any bigram
        assert len(analyzer.error_ngrams[2]) == 0, "Should be no error bigrams"
        
        # Verify no error n-grams were identified for trigrams
        assert len(analyzer.error_ngrams[3]) == 0, "Should be no error trigrams"
        
        # Save to database
        save_result = analyzer.save_to_database()
        assert save_result is True, "Save operation should succeed"
        
        # Verify only one n-gram was saved to the database correctly
        speed_ngrams = temp_db.fetchall(
            """SELECT ngram_size, ngram, ngram_time_ms 
               FROM session_ngram_speed 
               WHERE session_id = ?
               ORDER BY ngram_size, ngram""", 
            (session_id,)
        )
        
        assert len(speed_ngrams) == 1, "Should be exactly one speed n-gram in the database"
        
        # Verify the bigram (he)
        db_bigram = speed_ngrams[0]
        assert db_bigram[0] == 2, "Database bigram size should be 2"
        assert db_bigram[1] == bigram_text, f"Database bigram text should be '{bigram_text}'"
        # Check that the saved time value is the average time per character (1000ms / 2 chars = 500ms)
        assert db_bigram[2] == 500, "Database bigram time should be 500ms (avg per character)"
        
        # Verify no error n-grams were saved
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"
        
        # Get slowest n-grams - should return our bigram
        slowest_bigrams = analyzer.get_slowest_ngrams(size=2)
        assert len(slowest_bigrams) == 1, "Should be one slowest bigram"
        assert slowest_bigrams[0].text == bigram_text, f"Slowest bigram should be '{bigram_text}'"
        
        # Get error-prone n-grams - should return empty list
        error_prone_bigrams = analyzer.get_most_error_prone_ngrams(size=2)
        assert len(error_prone_bigrams) == 0, "Should be no error-prone bigrams"
        
        # Also verify for trigrams
        slowest_trigrams = analyzer.get_slowest_ngrams(size=3)
        assert len(slowest_trigrams) == 0, "Should be no slowest trigrams"
        
        error_prone_trigrams = analyzer.get_most_error_prone_ngrams(size=3)
        assert len(error_prone_trigrams) == 0, "Should be no error-prone trigrams"
        
    
    def test_three_keystrokes_error_at_second(self, temp_db, test_practice_session, three_keystrokes_error_at_second):
        """
        Test objective: Verify that three keystrokes with an error on the second keystroke are analyzed correctly.
        
        This test checks that:
        1. The analyzer properly handles a scenario with an error on the second keystroke
        2. One bigram (Tb) is identified as an error n-gram
        3. One trigram (Tbe) is identified as an error n-gram
        4. No speed n-grams should be identified due to the error
        5. The error n-grams have correct timing (500ms for bigram, 1500ms for trigram)
        6. The n-grams are correctly saved to the database error table
        """
        # Define the session ID constant for better readability in assertions
        session_id = test_practice_session.session_id
        
        # Create NGramAnalyzer instance with three keystrokes, second has error
        analyzer = NGramAnalyzer(test_practice_session, three_keystrokes_error_at_second, temp_db)
        
        # Run the analyzer for both bigrams and trigrams
        analyzer.analyze()  # Analyze bigrams and trigrams
        
        # Verify analysis was completed
        assert analyzer.analysis_complete is True, "Analysis should be marked as complete"
        
        # Verify no speed bigrams were identified (due to error)
        assert len(analyzer.speed_ngrams.get(2, [])) == 0, "Should be no speed bigrams due to error on second keystroke"
        
        # Verify no speed trigrams were identified (due to error)
        assert len(analyzer.speed_ngrams.get(3, [])) == 0, "Should be no speed trigrams due to error"
        
        # Verify error n-grams were identified correctly
        assert len(analyzer.error_ngrams.get(2, [])) == 1, "Should be exactly one error bigram"
        
        # Validate the error bigram 'Tb'
        error_bigram_text = "Tb"  # Expected error bigram: T (correct) then b (error)
        error_bigram = _find_ngram_in_list(analyzer.error_ngrams[2], error_bigram_text)
        
        assert error_bigram is not None, f"Error bigram '{error_bigram_text}' not found"
        assert error_bigram.text == error_bigram_text, f"Bigram text should be '{error_bigram_text}'"
        assert error_bigram.size == 2, "Bigram size should be 2"
        assert len(error_bigram.keystrokes) == 2, "Bigram should have 2 keystrokes"
        # Keystrokes: T (0ms), b (500ms, error). Error bigram 'Tb' time is from the second keystroke 'b'.
        assert error_bigram.total_time_ms == 500, f"Bigram '{error_bigram_text}' time should be 500ms"
        
        assert error_bigram.is_clean is False, "Error bigram should not be clean"
        assert error_bigram.error_on_last is True, "Error bigram 'Tb' should have error on last character ('b')"
        assert error_bigram.other_errors is False, "Error bigram 'Tb' should not have other errors"
        assert error_bigram.is_error is True, "Bigram should be marked as an error n-gram"
        assert error_bigram.is_valid is True, "Error bigram should be valid for tracking"

        # Error Trigram ('Tbe')
        assert len(analyzer.error_ngrams.get(3, [])) == 1, "Should be exactly one error trigram"
        error_trigram_text = "Tbe"  # Expected error trigram: T (correct), b (error), e (correct)
        error_trigram = _find_ngram_in_list(analyzer.error_ngrams[3], error_trigram_text)

        assert error_trigram is not None, f"Error trigram '{error_trigram_text}' not found"
        assert error_trigram.text == error_trigram_text, f"Trigram text should be '{error_trigram_text}'"
        assert error_trigram.size == 3, "Trigram size should be 3"
        assert len(error_trigram.keystrokes) == 3, "Trigram should have 3 keystrokes"
        # Keystrokes: T (0ms), b (500ms, error), e (1000ms). Total time = 500 + 1000 = 1500ms.
        assert error_trigram.total_time_ms == 1500, f"Trigram '{error_trigram_text}' time should be 1500ms"

        assert error_trigram.is_clean is False, "Error trigram should not be clean"
        assert error_trigram.error_on_last is False, "Error trigram 'Tbe' has error on 'b', not on 'e' (last)"
        assert error_trigram.other_errors is True, "Error trigram 'Tbe' has error on 'b' (not last)"
        assert error_trigram.is_error is False, "Trigram should not be marked as an error n-gram since error is not on last keystroke"
        assert error_trigram.is_valid is False, "Error trigram should not be valid for tracking since it's neither clean nor an error on the last keystroke"
        
        # Save to database
        save_result = analyzer.save_to_database()
        assert save_result is True, "Save operation should succeed"
        
        # Verify no speed n-grams were saved to the database
        speed_ngrams_count_db = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert speed_ngrams_count_db == 0, "No speed n-grams should be saved to the database"
        
        # Verify the error n-grams were saved to the database
        error_ngrams_db = temp_db.fetchall(
            """SELECT ngram_size, ngram 
               FROM session_ngram_errors 
               WHERE session_id = ?
               ORDER BY ngram_size, ngram""", 
            (session_id,)
        )
        
        assert len(error_ngrams_db) == 2, "Should be two error n-grams in the database (bigram 'Tb', trigram 'Tbe')"
        
        # Verify the error bigram (Tb)
        db_error_bigram = error_ngrams_db[0]
        assert db_error_bigram[0] == 2, "Database error bigram size should be 2"
        assert db_error_bigram[1] == error_bigram_text, f"Database error bigram text should be '{error_bigram_text}'"
        
        # Verify the error trigram (Tbe)
        db_error_trigram = error_ngrams_db[1]
        assert db_error_trigram[0] == 3, "Database error trigram size should be 3"
        assert db_error_trigram[1] == error_trigram_text, f"Database error trigram text should be '{error_trigram_text}'"
        
        # Get slowest n-grams - should be empty since there are no speed n-grams
        slowest_bigrams = analyzer.get_slowest_ngrams(size=2)
        assert len(slowest_bigrams) == 0, "Should be no slowest bigrams as no speed n-grams were recorded"
        
        slowest_trigrams = analyzer.get_slowest_ngrams(size=3)
        assert len(slowest_trigrams) == 0, "Should be no slowest trigrams as no speed n-grams were recorded"
        
        # Get error-prone n-grams - should return our error n-grams
        error_prone_bigrams = analyzer.get_most_error_prone_ngrams(size=2)
        assert len(error_prone_bigrams) == 1, "Should be one error-prone bigram"
        assert error_prone_bigrams[0].text == error_bigram_text, f"Error-prone bigram should be '{error_bigram_text}'"
        
        error_prone_trigrams = analyzer.get_most_error_prone_ngrams(size=3)
        assert len(error_prone_trigrams) == 0, "Should be no error-prone trigrams"
        
        
    def test_four_keystrokes_no_errors(self, temp_db, test_practice_session, four_keystrokes_no_errors):
        """
        Test objective: Verify that four keystrokes with no errors produce all possible n-grams with correct timing.
        
        This test checks that:
        1. The analyzer properly handles four correct keystrokes
        2. Three bigrams, two trigrams, and one 4-gram are identified with correct timing
        3. All n-grams are correctly saved to the database
        4. No error n-grams are identified or saved
        """
        # Define the session ID constant for better readability in assertions
        session_id = test_practice_session.session_id
        
        # Create NGramAnalyzer instance with four keystrokes, all correct
        analyzer = NGramAnalyzer(test_practice_session, four_keystrokes_no_errors, temp_db)
        
        # Run the analyzer for n-gram sizes 2 to 4
        analyzer.analyze()  # Analyze bigrams, trigrams, and 4-grams
        
        # Verify analysis was completed
        assert analyzer.analysis_complete is True, "Analysis should be marked as complete"
        
        # === VERIFY BIGRAMS ===
        assert 2 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for bigrams"
        assert len(analyzer.speed_ngrams[2]) == 3, "Should be exactly three speed bigrams"
        
        # Validate the first bigram 'Th'
        bigram1_text = "Th"  # First bigram
        
        # Retrieve the bigram from the dictionary
        bigram1 = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram1_text)
        assert bigram1 is not None, f"Bigram '{bigram1_text}' not found in speed_ngrams[2]"
        assert bigram1.text == bigram1_text, f"Bigram text should be '{bigram1_text}'"
        assert bigram1.size == 2, "Bigram size should be 2"
        assert len(bigram1.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram1.total_time_ms == 500, "Bigram 'Th' time should be 500ms"
        assert bigram1.is_clean is True, "Bigram should be clean (no errors)"
        
        # Validate the second bigram 'he'
        bigram2_text = "he"  # Second bigram
        
        # Retrieve the bigram from the dictionary
        bigram2 = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram2_text)
        assert bigram2 is not None, f"Bigram '{bigram2_text}' not found in speed_ngrams[2]"
        assert bigram2.text == bigram2_text, f"Bigram text should be '{bigram2_text}'"
        assert bigram2.size == 2, "Bigram size should be 2"
        assert len(bigram2.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram2.total_time_ms == 1000, "Bigram 'he' time should be 1000ms"
        assert bigram2.is_clean is True, "Bigram should be clean (no errors)"
        
        # Validate the third bigram 'en'
        bigram3_text = "en"  # Third bigram
        
        # Retrieve the bigram from the dictionary
        bigram3 = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram3_text)
        assert bigram3 is not None, f"Bigram '{bigram3_text}' not found in speed_ngrams[2]"
        assert bigram3.text == bigram3_text, f"Bigram text should be '{bigram3_text}'"
        assert bigram3.size == 2, "Bigram size should be 2"
        assert len(bigram3.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram3.total_time_ms == 300, "Bigram 'en' time should be 300ms"
        assert bigram3.is_clean is True, "Bigram should be clean (no errors)"
        
        # === VERIFY TRIGRAMS ===
        assert 3 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for trigrams"
        assert len(analyzer.speed_ngrams[3]) == 2, "Should be exactly two speed trigrams"
        
        # Validate the first trigram 'The'
        trigram1_text = "The"  # First trigram
        
        # Retrieve the trigram from the dictionary
        trigram1 = _find_ngram_in_list(analyzer.speed_ngrams[3], trigram1_text)
        assert trigram1 is not None, f"Trigram '{trigram1_text}' not found in speed_ngrams[3]"
        assert trigram1.text == trigram1_text, f"Trigram text should be '{trigram1_text}'"
        assert trigram1.size == 3, "Trigram size should be 3"
        assert len(trigram1.keystrokes) == 3, "Trigram should have 3 keystrokes"
        assert trigram1.total_time_ms == 1500, "Trigram 'The' total time should be 1500ms"
        assert trigram1.avg_time_per_char_ms == pytest.approx(500), "Trigram 'The' avg time should be ~500ms per char"
        assert trigram1.is_clean is True, "Trigram should be clean (no errors)"
        
        # Validate the second trigram 'hen'
        trigram2_text = "hen"  # Second trigram
        
        # Retrieve the trigram from the dictionary
        trigram2 = _find_ngram_in_list(analyzer.speed_ngrams[3], trigram2_text)
        assert trigram2 is not None, f"Trigram '{trigram2_text}' not found in speed_ngrams[3]"
        assert trigram2.text == trigram2_text, f"Trigram text should be '{trigram2_text}'"
        assert trigram2.size == 3, "Trigram size should be 3"
        assert len(trigram2.keystrokes) == 3, "Trigram should have 3 keystrokes"
        assert trigram2.total_time_ms == 1300, "Trigram 'hen' total time should be 1300ms"
        assert trigram2.avg_time_per_char_ms == pytest.approx(433.33, abs=0.1), "Trigram 'hen' avg time should be ~433.33ms per char"
        assert trigram2.is_clean is True, "Trigram should be clean (no errors)"
        
        # === VERIFY 4-GRAM ===
        assert 4 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for 4-grams"
        assert len(analyzer.speed_ngrams[4]) == 1, "Should be exactly one speed 4-gram"
        
        # Validate the 4-gram 'Then'
        fourgram_text = "Then"  # 4-gram
        
        # Retrieve the 4-gram from the dictionary
        fourgram = _find_ngram_in_list(analyzer.speed_ngrams[4], fourgram_text)
        assert fourgram is not None, f"4-gram '{fourgram_text}' not found in speed_ngrams[4]"
        assert fourgram.text == fourgram_text, f"4-gram text should be '{fourgram_text}'"
        assert fourgram.size == 4, "4-gram size should be 4"
        assert len(fourgram.keystrokes) == 4, "4-gram should have 4 keystrokes"
        assert fourgram.total_time_ms == 1800, "4-gram 'Then' total time should be 1800ms"
        assert fourgram.avg_time_per_char_ms == pytest.approx(450), "4-gram 'Then' avg time should be ~450ms per char"
        assert fourgram.is_clean is True, "4-gram should be clean (no errors)"
        
        # === VERIFY NO ERROR N-GRAMS ===
        assert 2 in analyzer.error_ngrams, "Error n-grams dictionary should have key for bigrams"
        assert len(analyzer.error_ngrams[2]) == 0, "Should be no error bigrams"
        
        assert 3 in analyzer.error_ngrams, "Error n-grams dictionary should have key for trigrams"
        assert len(analyzer.error_ngrams[3]) == 0, "Should be no error trigrams"
        
        assert 4 in analyzer.error_ngrams, "Error n-grams dictionary should have key for 4-grams"
        assert len(analyzer.error_ngrams[4]) == 0, "Should be no error 4-grams"
        
        # === SAVE TO DATABASE AND VERIFY ===
        save_result = analyzer.save_to_database()
        assert save_result is True, "Save operation should succeed"
        
        # Verify speed n-grams were saved to the database correctly
        speed_ngrams = temp_db.fetchall(
            """SELECT ngram_size, ngram, ngram_time_ms 
               FROM session_ngram_speed 
               WHERE session_id = ?
               ORDER BY ngram_size, ngram""", 
            (session_id,)
        )
        
        assert len(speed_ngrams) == 6, "Should be exactly six speed n-grams in the database"
        
        # Verify the bigrams in the database
        # Note: We sort the results by ngram_size and then by ngram text
        db_bigram1 = speed_ngrams[0]  # 'Th'
        assert db_bigram1[0] == 2, "Database bigram1 size should be 2"
        assert db_bigram1[1] == "Th", f"Database bigram1 text should be 'Th'"
        assert db_bigram1[2] == 250, "Database bigram1 avg time should be 250ms per char"
        
        db_bigram2 = speed_ngrams[1]  # 'en'
        assert db_bigram2[0] == 2, "Database bigram2 size should be 2"
        assert db_bigram2[1] == "en", f"Database bigram2 text should be 'en'"
        assert db_bigram2[2] == 150, "Database bigram2 avg time should be 150ms per char"
        
        db_bigram3 = speed_ngrams[2]  # 'he'
        assert db_bigram3[0] == 2, "Database bigram3 size should be 2"
        assert db_bigram3[1] == "he", f"Database bigram3 text should be 'he'"
        assert db_bigram3[2] == 500, "Database bigram3 avg time should be 500ms per char"
        
        # Verify the trigrams in the database
        db_trigram1 = speed_ngrams[3]  # 'The'
        assert db_trigram1[0] == 3, "Database trigram1 size should be 3"
        assert db_trigram1[1] == "The", f"Database trigram1 text should be 'The'"
        assert db_trigram1[2] == 500, "Database trigram1 avg time should be 500ms per char"
        
        db_trigram2 = speed_ngrams[4]  # 'hen'
        assert db_trigram2[0] == 3, "Database trigram2 size should be 3"
        assert db_trigram2[1] == "hen", f"Database trigram2 text should be 'hen'"
        assert db_trigram2[2] == pytest.approx(433.33, abs=0.1), "Database trigram2 avg time should be ~433.33ms per char"
        
        # Verify the 4-gram in the database
        db_fourgram = speed_ngrams[5]  # 'Then'
        assert db_fourgram[0] == 4, "Database 4-gram size should be 4"
        assert db_fourgram[1] == "Then", f"Database 4-gram text should be 'Then'"
        assert db_fourgram[2] == 450, "Database 4-gram avg time should be 450ms per char"
        
        # Verify no error n-grams were saved to the database
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "Should be no error n-grams in the database"
        
        # Verify retrieval of slowest n-grams
        slowest_bigrams = analyzer.get_slowest_ngrams(size=2)
        assert len(slowest_bigrams) == 3, "Should be three slowest bigrams"
        # The 'he' bigram should be the slowest since it has 1000ms vs 500ms for 'Th'
        assert slowest_bigrams[0].text == "he", "Slowest bigram should be 'he'"
        # Second one should be 'Th' (500ms)
        assert slowest_bigrams[1].text == "Th", "Second slowest bigram should be 'Th'"
        # Third one should be 'en' (300ms)
        assert slowest_bigrams[2].text == "en", "Third slowest bigram should be 'en'"
        
        # Verify no error-prone n-grams
        error_prone_bigrams = analyzer.get_most_error_prone_ngrams(size=2)
        assert len(error_prone_bigrams) == 0, "Should be no error-prone bigrams"
        
    def test_four_keystrokes_error_at_first(self, temp_db, test_practice_session, four_keystrokes_error_at_first):
        """
        Test objective: Verify that four keystrokes with an error on the first keystroke are analyzed correctly.
        
        This test checks that:
        1. The analyzer properly handles four keystrokes with an error at the first position
        2. Two bigrams ('he', 'en') and one trigram ('hen') are identified as clean n-grams
        3. No n-grams involving the first erroneous keystroke are identified
        4. No error n-grams are identified (since errors at the start don't create error n-grams)
        5. The n-grams are correctly saved to the database
        """
        # Define the session ID constant for better readability in assertions
        session_id = test_practice_session.session_id
        
        # Create NGramAnalyzer instance with four keystrokes, first has error
        analyzer = NGramAnalyzer(test_practice_session, four_keystrokes_error_at_first, temp_db)
        
        # Run the analyzer for n-gram sizes 2 to 4
        analyzer.analyze()  # Analyze bigrams, trigrams, and 4-grams
        
        # Verify analysis was completed
        assert analyzer.analysis_complete is True, "Analysis should be marked as complete"
        
        # === VERIFY BIGRAMS ===
        assert 2 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for bigrams"
        assert len(analyzer.speed_ngrams[2]) == 2, "Should be exactly two speed bigrams"
        
        # Validate the first bigram 'he'
        bigram1_text = "he"  # First valid bigram
        
        # Retrieve the bigram from the dictionary
        bigram1 = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram1_text)
        assert bigram1 is not None, f"Bigram '{bigram1_text}' not found in speed_ngrams[2]"
        assert bigram1.text == bigram1_text, f"Bigram text should be '{bigram1_text}'"
        assert bigram1.size == 2, "Bigram size should be 2"
        assert len(bigram1.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram1.total_time_ms == 1000, "Bigram 'he' time should be 1000ms"
        assert bigram1.is_clean is True, "Bigram should be clean (no errors)"
        
        # Validate the second bigram 'en'
        bigram2_text = "en"  # Second valid bigram
        
        # Retrieve the bigram from the dictionary
        bigram2 = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram2_text)
        assert bigram2 is not None, f"Bigram '{bigram2_text}' not found in speed_ngrams[2]"
        assert bigram2.text == bigram2_text, f"Bigram text should be '{bigram2_text}'"
        assert bigram2.size == 2, "Bigram size should be 2"
        assert len(bigram2.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram2.total_time_ms == 300, "Bigram 'en' time should be 300ms"
        assert bigram2.is_clean is True, "Bigram should be clean (no errors)"
        
        # Verify 'Gh' is not in the speed bigrams (it has an error at the beginning)
        assert "Gh" not in analyzer.speed_ngrams[2], "Bigram 'Gh' should not be in speed_ngrams due to error"
        
        # === VERIFY TRIGRAMS ===
        assert 3 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for trigrams"
        assert len(analyzer.speed_ngrams[3]) == 1, "Should be exactly one speed trigram"
        
        # Validate the trigram 'hen'
        trigram_text = "hen"  # Only valid trigram
        
        # Retrieve the trigram from the dictionary
        trigram = _find_ngram_in_list(analyzer.speed_ngrams[3], trigram_text)
        assert trigram is not None, f"Trigram '{trigram_text}' not found in speed_ngrams[3]"
        assert trigram.text == trigram_text, f"Trigram text should be '{trigram_text}'"
        assert trigram.size == 3, "Trigram size should be 3"
        assert len(trigram.keystrokes) == 3, "Trigram should have 3 keystrokes"
        assert trigram.total_time_ms == 1300, "Trigram 'hen' total time should be 1300ms"
        assert trigram.avg_time_per_char_ms == pytest.approx(433.33, abs=0.1), "Trigram 'hen' avg time should be ~433.33ms per char"
        assert trigram.is_clean is True, "Trigram should be clean (no errors)"
        
        # Verify 'Ghe' is not in the speed trigrams (it has an error at the beginning)
        assert "Ghe" not in analyzer.speed_ngrams[3], "Trigram 'Ghe' should not be in speed_ngrams due to error"
        
        # === VERIFY 4-GRAMS ===
        assert 4 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for 4-grams"
        assert len(analyzer.speed_ngrams[4]) == 0, "Should be no speed 4-grams due to error in first keystroke"
        
        # === VERIFY NO ERROR N-GRAMS ===
        # An error at the beginning of a keystroke sequence doesn't create error n-grams,
        # since error n-grams require the error to be on the last keystroke
        assert 2 in analyzer.error_ngrams, "Error n-grams dictionary should have key for bigrams"
        assert len(analyzer.error_ngrams[2]) == 0, "Should be no error bigrams"
        
        assert 3 in analyzer.error_ngrams, "Error n-grams dictionary should have key for trigrams"
        assert len(analyzer.error_ngrams[3]) == 0, "Should be no error trigrams"
        
        assert 4 in analyzer.error_ngrams, "Error n-grams dictionary should have key for 4-grams"
        assert len(analyzer.error_ngrams[4]) == 0, "Should be no error 4-grams"
        
        # === SAVE TO DATABASE AND VERIFY ===
        save_result = analyzer.save_to_database()
        assert save_result is True, "Save operation should succeed"
        
        # Verify speed n-grams were saved to the database correctly
        speed_ngrams = temp_db.fetchall(
            """SELECT ngram_size, ngram, ngram_time_ms 
               FROM session_ngram_speed 
               WHERE session_id = ?
               ORDER BY ngram_size, ngram""", 
            (session_id,)
        )
        
        assert len(speed_ngrams) == 3, "Should be exactly three speed n-grams in the database"
        
        # Verify the bigrams in the database
        # Note: We sort the results by ngram_size and then by ngram text
        db_bigram1 = speed_ngrams[0]  # 'en'
        assert db_bigram1[0] == 2, "Database bigram1 size should be 2"
        assert db_bigram1[1] == "en", f"Database bigram1 text should be 'en'"
        assert db_bigram1[2] == 150, "Database bigram1 avg time should be 150ms per char"
        
        db_bigram2 = speed_ngrams[1]  # 'he'
        assert db_bigram2[0] == 2, "Database bigram2 size should be 2"
        assert db_bigram2[1] == "he", f"Database bigram2 text should be 'he'"
        assert db_bigram2[2] == 500, "Database bigram2 avg time should be 500ms per char"
        
        # Verify the trigram in the database
        db_trigram = speed_ngrams[2]  # 'hen'
        assert db_trigram[0] == 3, "Database trigram size should be 3"
        assert db_trigram[1] == "hen", f"Database trigram text should be 'hen'"
        assert db_trigram[2] == pytest.approx(433.33, abs=0.1), "Database trigram avg time should be ~433.33ms per char"
        
        # Verify no error n-grams were saved to the database
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "Should be no error n-grams in the database"
        
        # Verify retrieval of slowest n-grams
        slowest_bigrams = analyzer.get_slowest_ngrams(size=2)
        assert len(slowest_bigrams) == 2, "Should be two slowest bigrams"
        # First one should be 'he' as it's slowest (1000ms)
        assert slowest_bigrams[0].text == "he", "Slowest bigram should be 'he'"
        # Second one should be 'en' (300ms)
        assert slowest_bigrams[1].text == "en", "Second slowest bigram should be 'en'"
        
        # Verify no error-prone n-grams
        error_prone_bigrams = analyzer.get_most_error_prone_ngrams(size=2)
        assert len(error_prone_bigrams) == 0, "Should be no error-prone bigrams"
        
    def test_four_keystrokes_error_at_second(self, temp_db, test_practice_session, four_keystrokes_error_at_second):
        """
        Test objective: Verify that four keystrokes with an error on the second keystroke are analyzed correctly.
        
        This test checks that:
        1. The analyzer properly handles four keystrokes with an error at the second position.
        2. Speed N-grams: 'en' (bigram).
        3. Error N-grams: 'Tg' (bigram), 'Tge' (trigram), 'Tgen' (4-gram).
        4. The n-grams are correctly saved to the database.
        """
        session_id = test_practice_session.session_id
        analyzer = NGramAnalyzer(test_practice_session, four_keystrokes_error_at_second, temp_db)
        analyzer.analyze()
        
        assert analyzer.analysis_complete is True, "Analysis should be marked as complete"
        
        # === VERIFY BIGRAMS ===
        speed_bigrams = analyzer.speed_ngrams.get(2, [])
        error_bigrams = analyzer.error_ngrams.get(2, [])

        assert len(speed_bigrams) == 1, f"Should be 1 speed bigram, got {len(speed_bigrams)}"
        assert len(error_bigrams) == 1, f"Should be 1 error bigram, got {len(error_bigrams)}"

        # Validate the clean bigram 'en'
        bigram1_text = "en"
        bigram1 = _find_ngram_in_list(speed_bigrams, bigram1_text)
        assert bigram1 is not None, f"Speed bigram '{bigram1_text}' not found"
        assert bigram1.text == bigram1_text, f"Bigram text should be '{bigram1_text}'"
        assert bigram1.size == 2, "Bigram size should be 2"
        assert len(bigram1.keystrokes) == 2, "Bigram should have 2 keystrokes"
        # Keystrokes: T(0) g(500, error) e(800) n(1100). 'en' is e(800) -> n(1100), time = 300ms.
        assert bigram1.total_time_ms == 300, f"Bigram '{bigram1_text}' time should be 300ms, got {bigram1.total_time_ms}"
        assert bigram1.is_clean is True, "Bigram should be clean (no errors)"
        
        # Validate the error bigram 'Tg'
        error_bigram_text = "Tg"
        error_bigram1 = _find_ngram_in_list(error_bigrams, error_bigram_text)
        assert error_bigram1 is not None, f"Error bigram '{error_bigram_text}' not found"
        assert error_bigram1.text == error_bigram_text, f"Error bigram text should be '{error_bigram_text}'"
        assert error_bigram1.size == 2, "Error bigram size should be 2"
        assert len(error_bigram1.keystrokes) == 2, "Error bigram should have 2 keystrokes"
        # Keystrokes: T(0) g(500, error). 'Tg' is T(0) -> g(500), time = 500ms.
        assert error_bigram1.total_time_ms == 500, f"Error bigram '{error_bigram_text}' time should be 500ms, got {error_bigram1.total_time_ms}"
        assert error_bigram1.is_clean is False, "Error bigram should not be clean (has errors)"
        assert error_bigram1.error_on_last is True, "Error bigram should have error on last character"
        assert error_bigram1.is_error is True, "Error bigram should be an error bigram"
        
        # Verify 'ge' is not in any n-grams (due to error in the previous key 'g')
        assert _find_ngram_in_list(speed_bigrams, "ge") is None, "Bigram 'ge' should not be in speed_ngrams"
        assert _find_ngram_in_list(error_bigrams, "ge") is None, "Bigram 'ge' should not be in error_ngrams"
        
        # === VERIFY TRIGRAMS ===
        speed_trigrams = analyzer.speed_ngrams.get(3, [])
        error_trigrams = analyzer.error_ngrams.get(3, [])

        assert len(speed_trigrams) == 0, f"Should be no speed trigrams, got {len(speed_trigrams)}"
        assert len(error_trigrams) == 1, f"Should be 1 error trigram, got {len(error_trigrams)}"

        # Validate error trigram 'Tge'
        error_trigram_text = "Tge"
        error_trigram1 = _find_ngram_in_list(error_trigrams, error_trigram_text)
        assert error_trigram1 is not None, f"Error trigram '{error_trigram_text}' not found"
        assert error_trigram1.text == error_trigram_text
        assert error_trigram1.size == 3
        assert len(error_trigram1.keystrokes) == 3
        # T(0) g(500, error) e(800). Time = 800ms.
        assert error_trigram1.total_time_ms == 1500, f"Error trigram '{error_trigram_text}' time, got {error_trigram1.total_time_ms}"
        assert error_trigram1.is_error is True
        assert error_trigram1.error_indices == [1] # Error on 'g' which is at index 1 of 'Tge'

        # === VERIFY 4-GRAMS ===
        speed_4grams = analyzer.speed_ngrams.get(4, [])
        error_4grams = analyzer.error_ngrams.get(4, [])

        assert len(speed_4grams) == 0, f"Should be no speed 4-grams, got {len(speed_4grams)}"
        assert len(error_4grams) == 1, f"Should be 1 error 4-gram, got {len(error_4grams)}"

        # Validate error 4-gram 'Tgen'
        error_4gram_text = "Tgen"
        error_4gram1 = _find_ngram_in_list(error_4grams, error_4gram_text)
        assert error_4gram1 is not None, f"Error 4-gram '{error_4gram_text}' not found"
        assert error_4gram1.text == error_4gram_text
        assert error_4gram1.size == 4
        assert len(error_4gram1.keystrokes) == 4
        # T(0) g(500, error) e(800) n(1100). Time = 1100ms.
        assert error_4gram1.total_time_ms == 1100, f"Error 4-gram '{error_4gram_text}' time, got {error_4gram1.total_time_ms}"
        assert error_4gram1.is_error is True
        assert error_4gram1.error_indices == [1] # Error on 'g' which is at index 1 of 'Tgen'

        # === VERIFY 5-GRAMS (default max size) ===
        speed_5grams = analyzer.speed_ngrams.get(5, [])
        error_5grams = analyzer.error_ngrams.get(5, [])
        assert len(speed_5grams) == 0, f"Should be no speed 5-grams, got {len(speed_5grams)}"
        assert len(error_5grams) == 0, f"Should be no error 5-grams, got {len(error_5grams)}"

        # === SAVE TO DATABASE AND VERIFY ===
        save_result = analyzer.save_to_database()
        assert save_result is True, "Save operation should succeed"

        # Verify speed n-grams were saved to the database correctly
        # Expected: 'en' (bigram)
        speed_ngrams_from_db = temp_db.fetchall(
            """SELECT ngram_size, ngram, total_time_ms, avg_time_per_char_ms, occurrences
               FROM session_ngram_speed 
               WHERE session_id = ? AND ngram_size = ? AND ngram = ?""", 
            (session_id, 2, bigram1_text) # bigram1_text is 'en'
        )
        assert len(speed_ngrams_from_db) == 1, f"Should be 1 speed n-gram '{bigram1_text}' in DB, found {len(speed_ngrams_from_db)}"
        db_speed_bigram = speed_ngrams_from_db[0]
        assert db_speed_bigram[0] == 2  # ngram_size
        assert db_speed_bigram[1] == bigram1_text  # ngram
        assert db_speed_bigram[2] == 300  # total_time_ms for 'en'
        assert db_speed_bigram[3] == 150  # avg_time_per_char_ms for 'en'
        assert db_speed_bigram[4] == 1  # occurrences for 'en'

        # Verify error n-grams were saved to the database correctly
        # Expected: 'Tg' (bigram), 'Tge' (trigram), 'Tgen' (4-gram)
        error_ngrams_from_db = temp_db.fetchall(
            """SELECT ngram_size, ngram, error_indices, error_on_last, occurrences
               FROM session_ngram_errors 
               WHERE session_id = ? ORDER BY ngram_size, ngram""", 
            (session_id,)
        )
        assert len(error_ngrams_from_db) == 3, f"Should be 3 error n-grams in DB, found {len(error_ngrams_from_db)}"

        # Validate 'Tg'
        db_error_tg = error_ngrams_from_db[0]
        assert db_error_tg[0] == 2 # size
        assert db_error_tg[1] == error_bigram_text # 'Tg'
        assert json.loads(db_error_tg[2]) == [1] # error_indices
        assert db_error_tg[3] is True # error_on_last
        assert db_error_tg[4] == 1 # occurrences

        # Validate 'Tge'
        db_error_tge = error_ngrams_from_db[1]
        assert db_error_tge[0] == 3 # size
        assert db_error_tge[1] == error_trigram_text # 'Tge'
        assert json.loads(db_error_tge[2]) == [1] # error_indices
        assert db_error_tge[3] is False # error_on_last for 'Tge' (error is not on 'e')
        assert db_error_tge[4] == 1 # occurrences

        # Validate 'Tgen'
        db_error_tgen = error_ngrams_from_db[2]
        assert db_error_tgen[0] == 4 # size
        assert db_error_tgen[1] == error_4gram_text # 'Tgen'
        assert json.loads(db_error_tgen[2]) == [1] # error_indices
        assert db_error_tgen[3] is False # error_on_last for 'Tgen' (error is not on 'n')
        assert db_error_tgen[4] == 1 # occurrences

        # Verify retrieval of slowest n-grams
        slowest_bigrams = analyzer.get_slowest_ngrams(size=2)
        assert len(slowest_bigrams) == 1, "Should be one slowest bigram"
        assert slowest_bigrams[0].text == bigram1_text, f"Slowest bigram should be '{bigram1_text}' ('en')"

        # Verify retrieval of error-prone n-grams
        error_prone_bigrams = analyzer.get_most_error_prone_ngrams(size=2)
        assert len(error_prone_bigrams) == 1, "Should be one error-prone bigram"
        assert error_prone_bigrams[0].text == error_bigram_text, f"Error-prone bigram should be '{error_bigram_text}' ('Tg')"

        error_prone_trigrams = analyzer.get_most_error_prone_ngrams(size=3)
        assert len(error_prone_trigrams) == 0, "Should be no error-prone trigrams"
        assert error_prone_trigrams[0].text == error_trigram_text, f"Error-prone trigram should be '{error_trigram_text}' ('Tge')"

        error_prone_4grams = analyzer.get_most_error_prone_ngrams(size=4)
        assert len(error_prone_4grams) == 1, "Should be one error-prone 4-gram"
        assert error_prone_4grams[0].text == error_4gram_text, f"Error-prone 4-gram should be '{error_4gram_text}' ('Tgen')"
        
    # endregion

    # region: Tests for three_keystrokes_no_errors fixture
