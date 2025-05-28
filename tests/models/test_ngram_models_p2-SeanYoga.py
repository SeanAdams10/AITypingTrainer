"""
Additional test module for NGram models and analyzer functionality.

This test suite covers advanced NGram model and NGramAnalyzer class functionality
with longer keystroke sequences and different error patterns.
"""

import datetime
import os
import tempfile
import uuid
from typing import List, Optional

import pytest

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke
from models.ngram_analyzer import NGram, NGramAnalyzer
from models.session import Session
from models.session_manager import SessionManager


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
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_file.close()

    # Initialize database with full schema
    db = DatabaseManager(db_file.name)
    db.init_tables()

    yield db

    # Clean up after the test
    db.close()
    os.unlink(db_file.name)


@pytest.fixture
def test_practice_session(temp_db) -> Session:
    """
    Test objective: Create a test practice session for NGram analysis.

    This fixture creates a minimal practice session suitable for testing.
    It sets up all required database dependencies (category and snippet).
    """
    # Create a category first (required for foreign key constraint)
    temp_db.execute("INSERT INTO categories (category_name) VALUES (?)", ("Test Category",))

    # Get the category ID
    category_row = temp_db.fetchone(
        "SELECT category_id FROM categories WHERE category_name = ?", ("Test Category",)
    )
    category_id = category_row[0]

    # Create a snippet (required for foreign key constraint)
    temp_db.execute(
        "INSERT INTO snippets (category_id, snippet_name) VALUES (?, ?)",
        (category_id, "Test Snippet"),
    )

    # Get the snippet ID
    snippet_row = temp_db.fetchone(
        "SELECT snippet_id FROM snippets WHERE snippet_name = ?", ("Test Snippet",)
    )
    snippet_id = snippet_row[0]

    # Add content to the snippet
    temp_db.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (snippet_id, 1, "test typing content"),
    )

    # Create a simple session with basic information
    session_id = str(uuid.uuid4())
    session = Session(
        session_id=session_id,
        snippet_id=snippet_id,  # Use the actual snippet ID
        snippet_index_start=0,
        snippet_index_end=10,
        content="test typing",
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now() + datetime.timedelta(minutes=1),
        actual_chars=10,
        errors=0,
    )

    # Save the session to the database
    session_manager = SessionManager(temp_db)
    session_manager.create_session(session.to_dict())

    return session


@pytest.fixture
def four_keystrokes_no_errors(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create four correct keystrokes for testing n-gram formation.

    This fixture creates four keystrokes ('T', 'h', 'e', 'n') with no errors and
    specific timing (500ms between first and second, 1000ms between second and third,
    300ms between third and fourth).
    """
    # Create four keystrokes with the session_id
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            keystroke_id=0,
            session_id=test_practice_session.session_id,
            keystroke_time=now,
            keystroke_char="T",
            expected_char="T",
            is_correct=True,
            time_since_previous=0,  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            keystroke_id=1,
            session_id=test_practice_session.session_id,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500,  # 500ms since previous keystroke
        ),
        Keystroke(
            keystroke_id=2,
            session_id=test_practice_session.session_id,
            keystroke_time=now + datetime.timedelta(milliseconds=1500),  # 1500 from start
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000,  # 1000ms since previous keystroke
        ),
        Keystroke(
            keystroke_id=3,
            session_id=test_practice_session.session_id,
            keystroke_time=now + datetime.timedelta(milliseconds=1800),  # 1800 from start
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300,  # 300ms since previous keystroke
        ),
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
                keystroke.time_since_previous,
            ),
        )

    return keystrokes


@pytest.fixture
def four_keystrokes_error_at_first(temp_db, test_practice_session):
    """
    Test objective: Create four keystrokes with an error on the first keystroke.

    This fixture creates four keystrokes where:
    - First keystroke is incorrect: 'G' instead of 'T'
    - Second keystroke is correct: 'h'
    - Third keystroke is correct: 'e'
    - Fourth keystroke is correct: 'n'
    - Timing: 0ms, 500ms, 1000ms, 300ms
    """
    session_id = test_practice_session.session_id
    dt_base = datetime.datetime(2023, 1, 1, 12, 0, 0)

    keystrokes = [
        # First keystroke (incorrect - 'G' instead of 'T')
        Keystroke(
            keystroke_id=0,
            session_id=session_id,
            keystroke_time=dt_base,
            keystroke_char="G",  # Actual keystroke
            expected_char="T",  # Expected keystroke
            is_correct=False,  # Is incorrect
            time_since_previous=0,
        ),
        # Second keystroke (correct - 'h')
        Keystroke(
            keystroke_id=1,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500,
        ),
        # Third keystroke (correct - 'e')
        Keystroke(
            keystroke_id=2,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1500),
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000,
        ),
        # Fourth keystroke (correct - 'n')
        Keystroke(
            keystroke_id=3,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1800),
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300,
        ),
    ]

    # Create all keystrokes in the database
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
                keystroke.time_since_previous,
            ),
        )

    return keystrokes


@pytest.fixture
def four_keystrokes_error_at_second(temp_db, test_practice_session):
    """
    Test objective: Create four keystrokes with an error on the second keystroke.

    This fixture creates four keystrokes where:
    - First keystroke is correct: 'T'
    - Second keystroke is incorrect: 'g' instead of 'h'
    - Third keystroke is correct: 'e'
    - Fourth keystroke is correct: 'n'
    - Timing: 0ms, 500ms, 1000ms, 300ms
    """
    session_id = test_practice_session.session_id
    dt_base = datetime.datetime(2023, 1, 1, 12, 0, 0)

    keystrokes = [
        # First keystroke (correct - 'T')
        Keystroke(
            keystroke_id=0,
            session_id=session_id,
            keystroke_time=dt_base,
            keystroke_char="T",  # Actual keystroke
            expected_char="T",  # Expected keystroke
            is_correct=True,  # Is correct
            time_since_previous=0,
        ),
        # Second keystroke (incorrect - 'g' instead of 'h')
        Keystroke(
            keystroke_id=1,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=500),
            keystroke_char="g",
            expected_char="h",
            is_correct=False,
            time_since_previous=500,
        ),
        # Third keystroke (correct - 'e')
        Keystroke(
            keystroke_id=2,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1500),
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000,
        ),
        # Fourth keystroke (correct - 'n')
        Keystroke(
            keystroke_id=3,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1800),
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300,
        ),
    ]

    # Create all keystrokes in the database
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
                keystroke.time_since_previous,
            ),
        )

    return keystrokes


@pytest.fixture
def four_keystrokes_error_at_third(temp_db, test_practice_session):
    """
    Test objective: Create four keystrokes with an error on the third keystroke.

    This fixture creates four keystrokes where:
    - First keystroke is correct: 'T'
    - Second keystroke is correct: 'h'
    - Third keystroke is incorrect: 'g' instead of 'e'
    - Fourth keystroke is correct: 'n'
    - Timing: 0ms, 500ms, 1000ms, 300ms
    """
    session_id = test_practice_session.session_id
    dt_base = datetime.datetime(2023, 1, 1, 12, 0, 0)

    keystrokes = [
        # First keystroke (correct - 'T')
        Keystroke(
            keystroke_id=0,
            session_id=session_id,
            keystroke_time=dt_base,
            keystroke_char="T",  # Actual keystroke
            expected_char="T",  # Expected keystroke
            is_correct=True,  # Is correct
            time_since_previous=0,
        ),
        # Second keystroke (correct - 'h')
        Keystroke(
            keystroke_id=1,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500,
        ),
        # Third keystroke (incorrect - 'g' instead of 'e')
        Keystroke(
            keystroke_id=2,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1500),
            keystroke_char="g",
            expected_char="e",
            is_correct=False,
            time_since_previous=1000,
        ),
        # Fourth keystroke (correct - 'n')
        Keystroke(
            keystroke_id=3,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1800),
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300,
        ),
    ]

    # Create all keystrokes in the database
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
                keystroke.time_since_previous,
            ),
        )

    return keystrokes


@pytest.fixture
def four_keystrokes_error_at_fourth(temp_db, test_practice_session):
    """
    Test objective: Create four keystrokes with an error on the fourth keystroke.

    This fixture creates four keystrokes where:
    - First keystroke is correct: 'T'
    - Second keystroke is correct: 'h'
    - Third keystroke is correct: 'e'
    - Fourth keystroke is incorrect: 'b' instead of 'n'
    - Timing: 0ms, 500ms, 1000ms, 300ms
    """
    session_id = test_practice_session.session_id
    dt_base = datetime.datetime(2023, 1, 1, 12, 0, 0)

    keystrokes = [
        # First keystroke (correct - 'T')
        Keystroke(
            keystroke_id=0,
            session_id=session_id,
            keystroke_time=dt_base,
            keystroke_char="T",  # Actual keystroke
            expected_char="T",  # Expected keystroke
            is_correct=True,  # Is correct
            time_since_previous=0,
        ),
        # Second keystroke (correct - 'h')
        Keystroke(
            keystroke_id=1,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500,
        ),
        # Third keystroke (correct - 'e')
        Keystroke(
            keystroke_id=2,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1500),
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000,
        ),
        # Fourth keystroke (incorrect - 'b' instead of 'n')
        Keystroke(
            keystroke_id=3,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1800),
            keystroke_char="b",
            expected_char="n",
            is_correct=False,
            time_since_previous=300,
        ),
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
                keystroke.time_since_previous,
            ),
        )

    return keystrokes


class TestNGramModelsExtended:
    """Extended test suite for NGram model and analyzer functionality with longer sequences."""

    def test_four_keystrokes_no_errors(
        self, temp_db, test_practice_session, four_keystrokes_no_errors
    ):
        analyzer = NGramAnalyzer()
        generated_ngrams = analyzer.generate_ngrams_from_keystrokes(
            four_keystrokes_no_errors, n_min=2, n_max=4
        )

        assert len(generated_ngrams) == 6

        # Bigrams
        ngram_th = _find_ngram_in_list(generated_ngrams, "Th")
        assert ngram_th is not None
        assert ngram_th.count == 1
        assert ngram_th.avg_time_ms == (0 + 500) / 2
        assert not ngram_th.is_error
        assert ngram_th.error_details == []

        ngram_he = _find_ngram_in_list(generated_ngrams, "he")
        assert ngram_he is not None
        assert ngram_he.count == 1
        assert ngram_he.avg_time_ms == (500 + 1000) / 2
        assert not ngram_he.is_error
        assert ngram_he.error_details == []

        ngram_en = _find_ngram_in_list(generated_ngrams, "en")
        assert ngram_en is not None
        assert ngram_en.count == 1
        assert ngram_en.avg_time_ms == (1000 + 300) / 2
        assert not ngram_en.is_error
        assert ngram_en.error_details == []

        # Trigrams
        ngram_the = _find_ngram_in_list(generated_ngrams, "The")
        assert ngram_the is not None
        assert ngram_the.count == 1
        assert ngram_the.avg_time_ms == (0 + 500 + 1000) / 3
        assert not ngram_the.is_error
        assert ngram_the.error_details == []

        ngram_hen = _find_ngram_in_list(generated_ngrams, "hen")
        assert ngram_hen is not None
        assert ngram_hen.count == 1
        assert ngram_hen.avg_time_ms == (500 + 1000 + 300) / 3
        assert not ngram_hen.is_error
        assert ngram_hen.error_details == []

        # Quadrigrams
        ngram_then = _find_ngram_in_list(generated_ngrams, "Then")
        assert ngram_then is not None
        assert ngram_then.count == 1
        assert ngram_then.avg_time_ms == (0 + 500 + 1000 + 300) / 4
        assert not ngram_then.is_error
        assert ngram_then.error_details == []

    def test_four_keystrokes_error_at_first(
        self, temp_db, test_practice_session, four_keystrokes_error_at_first
    ):
        analyzer = NGramAnalyzer()
        generated_ngrams = analyzer.generate_ngrams_from_keystrokes(
            four_keystrokes_error_at_first, n_min=2, n_max=4
        )
        assert len(generated_ngrams) == 6

        # Keystrokes: G(T), h, e, n. Times: 0, 500, 1000, 300
        # Bigrams
        ngram_gh = _find_ngram_in_list(generated_ngrams, "Gh")
        assert ngram_gh is not None
        assert ngram_gh.count == 1
        assert ngram_gh.avg_time_ms == (0 + 500) / 2
        assert ngram_gh.is_error
        assert ngram_gh.error_details == [("G", "T", 0)]

        ngram_he = _find_ngram_in_list(generated_ngrams, "he")
        assert ngram_he is not None
        assert ngram_he.count == 1
        assert ngram_he.avg_time_ms == (500 + 1000) / 2
        assert not ngram_he.is_error
        assert ngram_he.error_details == []

        ngram_en = _find_ngram_in_list(generated_ngrams, "en")
        assert ngram_en is not None
        assert ngram_en.count == 1
        assert ngram_en.avg_time_ms == (1000 + 300) / 2
        assert not ngram_en.is_error
        assert ngram_en.error_details == []

        # Trigrams
        ngram_ghe = _find_ngram_in_list(generated_ngrams, "Ghe")
        assert ngram_ghe is not None
        assert ngram_ghe.count == 1
        assert ngram_ghe.avg_time_ms == (0 + 500 + 1000) / 3
        assert ngram_ghe.is_error
        assert ngram_ghe.error_details == [("G", "T", 0)]

        ngram_hen = _find_ngram_in_list(generated_ngrams, "hen")
        assert ngram_hen is not None
        assert ngram_hen.count == 1
        assert ngram_hen.avg_time_ms == (500 + 1000 + 300) / 3
        assert not ngram_hen.is_error
        assert ngram_hen.error_details == []

        # Quadrigrams
        ngram_ghen = _find_ngram_in_list(generated_ngrams, "Ghen")
        assert ngram_ghen is not None
        assert ngram_ghen.count == 1
        assert ngram_ghen.avg_time_ms == (0 + 500 + 1000 + 300) / 4
        assert ngram_ghen.is_error
        assert ngram_ghen.error_details == [("G", "T", 0)]

    def test_four_keystrokes_error_at_second(
        self, temp_db, test_practice_session, four_keystrokes_error_at_second
    ):
        analyzer = NGramAnalyzer()
        generated_ngrams = analyzer.generate_ngrams_from_keystrokes(
            four_keystrokes_error_at_second, n_min=2, n_max=4
        )
        assert len(generated_ngrams) == 6

        # Keystrokes: T, g(h), e, n. Times: 0, 500, 1000, 300
        # Bigrams
        ngram_tg = _find_ngram_in_list(generated_ngrams, "Tg")
        assert ngram_tg is not None
        assert ngram_tg.count == 1
        assert ngram_tg.avg_time_ms == (0 + 500) / 2
        assert ngram_tg.is_error
        assert ngram_tg.error_details == [("g", "h", 1)]

        ngram_ge = _find_ngram_in_list(generated_ngrams, "ge")  # Starts with error
        assert ngram_ge is not None
        assert ngram_ge.count == 1
        assert ngram_ge.avg_time_ms == (500 + 1000) / 2
        assert ngram_ge.is_error
        assert ngram_ge.error_details == [("g", "h", 0)]

        ngram_en = _find_ngram_in_list(generated_ngrams, "en")
        assert ngram_en is not None
        assert ngram_en.count == 1
        assert ngram_en.avg_time_ms == (1000 + 300) / 2
        assert not ngram_en.is_error
        assert ngram_en.error_details == []

        # Trigrams
        ngram_tge = _find_ngram_in_list(generated_ngrams, "Tge")
        assert ngram_tge is not None
        assert ngram_tge.count == 1
        assert ngram_tge.avg_time_ms == (0 + 500 + 1000) / 3
        assert ngram_tge.is_error
        assert ngram_tge.error_details == [("g", "h", 1)]

        ngram_gen = _find_ngram_in_list(generated_ngrams, "gen")  # Starts with error
        assert ngram_gen is not None
        assert ngram_gen.count == 1
        assert ngram_gen.avg_time_ms == (500 + 1000 + 300) / 3
        assert ngram_gen.is_error
        assert ngram_gen.error_details == [("g", "h", 0)]

        # Quadrigrams
        ngram_tgen = _find_ngram_in_list(generated_ngrams, "Tgen")
        assert ngram_tgen is not None
        assert ngram_tgen.count == 1
        assert ngram_tgen.avg_time_ms == (0 + 500 + 1000 + 300) / 4
        assert ngram_tgen.is_error
        assert ngram_tgen.error_details == [("g", "h", 1)]

    def test_four_keystrokes_error_at_third(
        self, temp_db, test_practice_session, four_keystrokes_error_at_third
    ):
        analyzer = NGramAnalyzer()
        generated_ngrams = analyzer.generate_ngrams_from_keystrokes(
            four_keystrokes_error_at_third, n_min=2, n_max=4
        )
        assert len(generated_ngrams) == 6

        # Keystrokes: T, h, g(e), n. Times: 0, 500, 1000, 300
        # Bigrams
        ngram_th = _find_ngram_in_list(generated_ngrams, "Th")
        assert ngram_th is not None
        assert ngram_th.count == 1
        assert ngram_th.avg_time_ms == (0 + 500) / 2
        assert not ngram_th.is_error
        assert ngram_th.error_details == []

        ngram_hg = _find_ngram_in_list(generated_ngrams, "hg")
        assert ngram_hg is not None
        assert ngram_hg.count == 1
        assert ngram_hg.avg_time_ms == (500 + 1000) / 2
        assert ngram_hg.is_error
        assert ngram_hg.error_details == [("g", "e", 1)]

        ngram_gn = _find_ngram_in_list(generated_ngrams, "gn")  # Starts with error
        assert ngram_gn is not None
        assert ngram_gn.count == 1
        assert ngram_gn.avg_time_ms == (1000 + 300) / 2
        assert ngram_gn.is_error
        assert ngram_gn.error_details == [("g", "e", 0)]

        # Trigrams
        ngram_tge = _find_ngram_in_list(generated_ngrams, "Tge")
        assert ngram_tge is not None
        assert ngram_tge.count == 1
        assert ngram_tge.avg_time_ms == (0 + 500 + 1000) / 3
        assert ngram_tge.is_error
        assert ngram_tge.error_details == [("g", "e", 1)]

        ngram_gen = _find_ngram_in_list(generated_ngrams, "gen")  # Starts with error
        assert ngram_gen is not None
        assert ngram_gen.count == 1
        assert ngram_gen.avg_time_ms == (500 + 1000 + 300) / 3
        assert ngram_gen.is_error
        assert ngram_gen.error_details == [("g", "e", 0)]

        # Quadrigrams
        ngram_tgen = _find_ngram_in_list(generated_ngrams, "Tgen")
        assert ngram_tgen is not None
        assert ngram_tgen.count == 1
        assert ngram_tgen.avg_time_ms == (0 + 500 + 1000 + 300) / 4
        assert ngram_tgen.is_error
        assert ngram_tgen.error_details == [("g", "e", 1)]

    def test_four_keystrokes_error_at_fourth(
        self, temp_db, test_practice_session, four_keystrokes_error_at_fourth
    ):
        analyzer = NGramAnalyzer()
        generated_ngrams = analyzer.generate_ngrams_from_keystrokes(
            four_keystrokes_error_at_fourth, n_min=2, n_max=4
        )
        assert len(generated_ngrams) == 6

        # Keystrokes: T, h, e, b. Times: 0, 500, 1000, 300
        # Bigrams
        ngram_th = _find_ngram_in_list(generated_ngrams, "Th")
        assert ngram_th is not None
        assert ngram_th.count == 1
        assert ngram_th.avg_time_ms == (0 + 500) / 2
        assert not ngram_th.is_error
        assert ngram_th.error_details == []

        ngram_he = _find_ngram_in_list(generated_ngrams, "he")
        assert ngram_he is not None
        assert ngram_he.count == 1
        assert ngram_he.avg_time_ms == (500 + 1000) / 2
        assert not ngram_he.is_error
        assert ngram_he.error_details == []

        ngram_en = _find_ngram_in_list(generated_ngrams, "en")
        assert ngram_en is not None
        assert ngram_en.count == 1
        assert ngram_en.avg_time_ms == (1000 + 300) / 2
        assert ngram_en.is_error
        assert ngram_en.error_details == [("b", "n", 0)]

        # Trigrams
        ngram_the = _find_ngram_in_list(generated_ngrams, "The")
        assert ngram_the is not None
        assert ngram_the.count == 1
        assert ngram_the.avg_time_ms == (0 + 500 + 1000) / 3
        assert not ngram_the.is_error
        assert ngram_the.error_details == []

        ngram_hen = _find_ngram_in_list(generated_ngrams, "hen")
        assert ngram_hen is not None
        assert ngram_hen.count == 1
        assert ngram_hen.avg_time_ms == (500 + 1000 + 300) / 3
        assert ngram_hen.is_error
        assert ngram_hen.error_details == [("b", "n", 0)]

        # Quadrigrams
        ngram_then = _find_ngram_in_list(generated_ngrams, "Then")
        assert ngram_then is not None
        assert ngram_then.count == 1
        assert ngram_then.avg_time_ms == (0 + 500 + 1000 + 300) / 4
        assert ngram_then.is_error
        assert ngram_then.error_details == [("b", "n", 0)]
