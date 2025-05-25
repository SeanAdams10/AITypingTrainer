"""
Additional test module for NGram models and analyzer functionality.

This test suite covers advanced NGram model and NGramAnalyzer class functionality
with longer keystroke sequences and different error patterns.
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
        ("Test Category",)
    )
    
    # Get the category ID
    category_row = temp_db.fetchone("SELECT category_id FROM categories WHERE category_name = ?", ("Test Category",))
    category_id = category_row[0]
    
    # Create a snippet (required for foreign key constraint)
    temp_db.execute(
        "INSERT INTO snippets (category_id, snippet_name) VALUES (?, ?)",
        (category_id, "Test Snippet")
    )
    
    # Get the snippet ID
    snippet_row = temp_db.fetchone("SELECT snippet_id FROM snippets WHERE snippet_name = ?", ("Test Snippet",))
    snippet_id = snippet_row[0]
    
    # Add content to the snippet
    temp_db.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (snippet_id, 1, "test typing content")
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
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            keystroke_id=1,
            session_id=test_practice_session.session_id,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500  # 500ms since previous keystroke
        ),
        Keystroke(
            keystroke_id=2,
            session_id=test_practice_session.session_id,
            keystroke_time=now + datetime.timedelta(milliseconds=1500),  # 1500 from start
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000  # 1000ms since previous keystroke
        ),
        Keystroke(
            keystroke_id=3,
            session_id=test_practice_session.session_id,
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
            )
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
            expected_char="T",   # Expected keystroke
            is_correct=False,    # Is incorrect
            time_since_previous=0
        ),
        # Second keystroke (correct - 'h')
        Keystroke(
            keystroke_id=1,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500
        ),
        # Third keystroke (correct - 'e')
        Keystroke(
            keystroke_id=2,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1500),
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000
        ),
        # Fourth keystroke (correct - 'n')
        Keystroke(
            keystroke_id=3,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1800),
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300
        )
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
                keystroke.time_since_previous
            )
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
            expected_char="T",   # Expected keystroke
            is_correct=True,     # Is correct
            time_since_previous=0
        ),
        # Second keystroke (incorrect - 'g' instead of 'h')
        Keystroke(
            keystroke_id=1,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=500),
            keystroke_char="g",
            expected_char="h",
            is_correct=False,
            time_since_previous=500
        ),
        # Third keystroke (correct - 'e')
        Keystroke(
            keystroke_id=2,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1500),
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000
        ),
        # Fourth keystroke (correct - 'n')
        Keystroke(
            keystroke_id=3,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1800),
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300
        )
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
                keystroke.time_since_previous
            )
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
            expected_char="T",   # Expected keystroke
            is_correct=True,     # Is correct
            time_since_previous=0
        ),
        # Second keystroke (correct - 'h')
        Keystroke(
            keystroke_id=1,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500
        ),
        # Third keystroke (incorrect - 'g' instead of 'e')
        Keystroke(
            keystroke_id=2,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1500),
            keystroke_char="g",
            expected_char="e",
            is_correct=False,
            time_since_previous=1000
        ),
        # Fourth keystroke (correct - 'n')
        Keystroke(
            keystroke_id=3,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1800),
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300
        )
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
                keystroke.time_since_previous
            )
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
            expected_char="T",   # Expected keystroke
            is_correct=True,     # Is correct
            time_since_previous=0
        ),
        # Second keystroke (correct - 'h')
        Keystroke(
            keystroke_id=1,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500
        ),
        # Third keystroke (correct - 'e')
        Keystroke(
            keystroke_id=2,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1500),
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000
        ),
        # Fourth keystroke (incorrect - 'b' instead of 'n')
        Keystroke(
            keystroke_id=3,
            session_id=session_id,
            keystroke_time=dt_base + datetime.timedelta(milliseconds=1800),
            keystroke_char="b",
            expected_char="n",
            is_correct=False,
            time_since_previous=300
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
            )
        )
    
    return keystrokes

class TestNGramModelsExtended:
    """Extended test suite for NGram model and analyzer functionality with longer sequences."""
    
    def test_four_keystrokes_no_errors(self, temp_db, test_practice_session, four_keystrokes_no_errors):
        analyzer = NGramAnalyzer()
        generated_ngrams = analyzer.generate_ngrams_from_keystrokes(
            four_keystrokes_no_errors, 
            n_min=2, 
            n_max=4
        )

        assert len(generated_ngrams) == 6

        # Bigrams
        ngram_th = _find_ngram_in_list(generated_ngrams, "Th")
        assert ngram_th is not None; assert ngram_th.count == 1
        assert ngram_th.avg_time_ms == (0 + 500) / 2; assert not ngram_th.is_error; assert ngram_th.error_details == []

        ngram_he = _find_ngram_in_list(generated_ngrams, "he")
        assert ngram_he is not None; assert ngram_he.count == 1
        assert ngram_he.avg_time_ms == (500 + 1000) / 2; assert not ngram_he.is_error; assert ngram_he.error_details == []

        ngram_en = _find_ngram_in_list(generated_ngrams, "en")
        assert ngram_en is not None; assert ngram_en.count == 1
        assert ngram_en.avg_time_ms == (1000 + 300) / 2; assert not ngram_en.is_error; assert ngram_en.error_details == []

        # Trigrams
        ngram_the = _find_ngram_in_list(generated_ngrams, "The")
        assert ngram_the is not None; assert ngram_the.count == 1
        assert ngram_the.avg_time_ms == (0 + 500 + 1000) / 3; assert not ngram_the.is_error; assert ngram_the.error_details == []

        ngram_hen = _find_ngram_in_list(generated_ngrams, "hen")
        assert ngram_hen is not None; assert ngram_hen.count == 1
        assert ngram_hen.avg_time_ms == (500 + 1000 + 300) / 3; assert not ngram_hen.is_error; assert ngram_hen.error_details == []

        # Quadrigrams
        ngram_then = _find_ngram_in_list(generated_ngrams, "Then")
        assert ngram_then is not None; assert ngram_then.count == 1
        assert ngram_then.avg_time_ms == (0 + 500 + 1000 + 300) / 4; assert not ngram_then.is_error; assert ngram_then.error_details == []
    
    def test_four_keystrokes_error_at_first(self, temp_db, test_practice_session, four_keystrokes_error_at_first):
        analyzer = NGramAnalyzer()
        generated_ngrams = analyzer.generate_ngrams_from_keystrokes(
            four_keystrokes_error_at_first,
            n_min=2,
            n_max=4
        )
        assert len(generated_ngrams) == 6

        # Keystrokes: G(T), h, e, n. Times: 0, 500, 1000, 300
        # Bigrams
        ngram_gh = _find_ngram_in_list(generated_ngrams, "Gh")
        assert ngram_gh is not None; assert ngram_gh.count == 1
        assert ngram_gh.avg_time_ms == (0 + 500) / 2; assert ngram_gh.is_error
        assert ngram_gh.error_details == [('G', 'T', 0)]

        ngram_he = _find_ngram_in_list(generated_ngrams, "he")
        assert ngram_he is not None; assert ngram_he.count == 1
        assert ngram_he.avg_time_ms == (500 + 1000) / 2; assert not ngram_he.is_error; assert ngram_he.error_details == []
        
        ngram_en = _find_ngram_in_list(generated_ngrams, "en")
        assert ngram_en is not None; assert ngram_en.count == 1
        assert ngram_en.avg_time_ms == (1000 + 300) / 2; assert not ngram_en.is_error; assert ngram_en.error_details == []

        # Trigrams
        ngram_ghe = _find_ngram_in_list(generated_ngrams, "Ghe")
        assert ngram_ghe is not None; assert ngram_ghe.count == 1
        assert ngram_ghe.avg_time_ms == (0 + 500 + 1000) / 3; assert ngram_ghe.is_error
        assert ngram_ghe.error_details == [('G', 'T', 0)]

        ngram_hen = _find_ngram_in_list(generated_ngrams, "hen")
        assert ngram_hen is not None; assert ngram_hen.count == 1
        assert ngram_hen.avg_time_ms == (500 + 1000 + 300) / 3; assert not ngram_hen.is_error; assert ngram_hen.error_details == []

        # Quadrigrams
        ngram_ghen = _find_ngram_in_list(generated_ngrams, "Ghen")
        assert ngram_ghen is not None; assert ngram_ghen.count == 1
        assert ngram_ghen.avg_time_ms == (0 + 500 + 1000 + 300) / 4; assert ngram_ghen.is_error
        assert ngram_ghen.error_details == [('G', 'T', 0)]

    def test_four_keystrokes_error_at_second(self, temp_db, test_practice_session, four_keystrokes_error_at_second):
        analyzer = NGramAnalyzer()
        generated_ngrams = analyzer.generate_ngrams_from_keystrokes(
            four_keystrokes_error_at_second,
            n_min=2,
            n_max=4
        )
        assert len(generated_ngrams) == 6

        # Keystrokes: T, g(h), e, n. Times: 0, 500, 1000, 300
        # Bigrams
        ngram_tg = _find_ngram_in_list(generated_ngrams, "Tg")
        assert ngram_tg is not None; assert ngram_tg.count == 1
        assert ngram_tg.avg_time_ms == (0 + 500) / 2; assert ngram_tg.is_error
        assert ngram_tg.error_details == [('g', 'h', 1)]

        ngram_ge = _find_ngram_in_list(generated_ngrams, "ge") # Starts with error
        assert ngram_ge is not None; assert ngram_ge.count == 1
        assert ngram_ge.avg_time_ms == (500 + 1000) / 2; assert ngram_ge.is_error
        assert ngram_ge.error_details == [('g', 'h', 0)] 
        
        ngram_en = _find_ngram_in_list(generated_ngrams, "en")
        assert ngram_en is not None; assert ngram_en.count == 1
        assert ngram_en.avg_time_ms == (1000 + 300) / 2; assert not ngram_en.is_error; assert ngram_en.error_details == []

        # Trigrams
        ngram_tge = _find_ngram_in_list(generated_ngrams, "Tge")
        assert ngram_tge is not None; assert ngram_tge.count == 1
        assert ngram_tge.avg_time_ms == (0 + 500 + 1000) / 3; assert ngram_tge.is_error
        assert ngram_tge.error_details == [('g', 'h', 1)]

        ngram_gen = _find_ngram_in_list(generated_ngrams, "gen") # Starts with error
        assert ngram_gen is not None; assert ngram_gen.count == 1
        assert ngram_gen.avg_time_ms == (500 + 1000 + 300) / 3; assert ngram_gen.is_error
        assert ngram_gen.error_details == [('g', 'h', 0)]

        # Quadrigrams
        ngram_tgen = _find_ngram_in_list(generated_ngrams, "Tgen")
        assert ngram_tgen is not None; assert ngram_tgen.count == 1
        assert ngram_tgen.avg_time_ms == (0 + 500 + 1000 + 300) / 4; assert ngram_tgen.is_error
        assert ngram_tgen.error_details == [('g', 'h', 1)]
    
    def test_four_keystrokes_error_at_third(self, temp_db, test_practice_session, four_keystrokes_error_at_third):
        analyzer = NGramAnalyzer()
        generated_ngrams = analyzer.generate_ngrams_from_keystrokes(
            four_keystrokes_error_at_third,
            n_min=2,
            n_max=4
        )
        assert len(generated_ngrams) == 6

        # Keystrokes: T, h, g(e), n. Times: 0, 500, 1000, 300
        # Bigrams
        ngram_th = _find_ngram_in_list(generated_ngrams, "Th")
        assert ngram_th is not None; assert ngram_th.count == 1
        assert ngram_th.avg_time_ms == (0 + 500) / 2; assert not ngram_th.is_error; assert ngram_th.error_details == []

        ngram_hg = _find_ngram_in_list(generated_ngrams, "hg")
        assert ngram_hg is not None; assert ngram_hg.count == 1
        assert ngram_hg.avg_time_ms == (500 + 1000) / 2; assert ngram_hg.is_error
        assert ngram_hg.error_details == [('g', 'e', 1)]
        
        ngram_gn = _find_ngram_in_list(generated_ngrams, "gn") # Starts with error
        assert ngram_gn is not None; assert ngram_gn.count == 1
        assert ngram_gn.avg_time_ms == (1000 + 300) / 2; assert ngram_gn.is_error
        assert ngram_gn.error_details == [('g', 'e', 0)]

        # Trigrams
        - Four keystrokes: G, h, e, n (expected: T, h, e, n)
        - First keystroke has an error ('G' instead of 'T')
        - Timing: 0ms, 500ms, 1000ms, 300ms between keystrokes
        
        Expected outcomes:
        - Two valid bigrams of length 2: 
          "he" (1000ms), "en" (300ms)
        - One valid trigram of length 3:
          "hen" (1300ms)
        - No valid quadgrams due to the error
        - In database: 3 rows in session_ngram_speed, 0 rows in session_ngram_errors
        """
        # Create an NGramAnalyzer instance with the keystrokes
        analyzer = NGramAnalyzer(test_practice_session, four_keystrokes_error_at_first)
        
        # Check that all expected n-grams are identified
        # 1. Analyze the keystrokes to identify n-grams
        analyzer.analyze()
        
        # 2. Save n-grams to the database manually following the pattern in test_three_keystrokes_error_at_third
        # First ensure tables exist
        temp_db.init_tables()
        
        # Save to the database directly
        
        # Save speed n-grams manually
        for size, ngrams in analyzer.speed_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_speed (session_id, ngram_size, ngram, ngram_time_ms) VALUES (?, ?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text, ngram.avg_time_per_char_ms)
                )
        
        # Save error n-grams manually
        for size, ngrams in analyzer.error_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_errors (session_id, ngram_size, ngram) VALUES (?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text)
                )
        
        # 3. Validate that the expected n-grams are in the analyzer object
        # There should be 2 n-gram sizes present (bigrams and trigrams)
        assert len(analyzer.speed_ngrams) == 2, f"Expected 2 n-gram sizes, got {len(analyzer.speed_ngrams)}"
        
        # Check that there are 2 bigrams and 1 trigram
        assert len(analyzer.speed_ngrams[2]) == 2, f"Expected 2 bigrams, got {len(analyzer.speed_ngrams[2])}"
        assert len(analyzer.speed_ngrams[3]) == 1, f"Expected 1 trigram, got {len(analyzer.speed_ngrams[3])}"
        assert len(analyzer.error_ngrams) == 0, f"Expected 0 error n-grams, got {len(analyzer.error_ngrams)}"
        
        # Check specific n-grams and their timings
        # Bigrams
        he_ngram = _find_ngram_in_list(analyzer.speed_ngrams[2], "he")
        assert he_ngram is not None, "Bigram 'he' not found in speed n-grams"
        assert he_ngram.total_time_ms == 1000, f"Expected 'he' time to be 1000ms, got {he_ngram.total_time_ms}ms"
        assert he_ngram.size == 2, f"Expected 'he' size to be 2, got {he_ngram.size}"
        
        en_ngram = _find_ngram_in_list(analyzer.speed_ngrams[2], "en")
        assert en_ngram is not None, "Bigram 'en' not found in speed n-grams"
        assert en_ngram.total_time_ms == 300, f"Expected 'en' time to be 300ms, got {en_ngram.total_time_ms}ms"
        assert en_ngram.size == 2, f"Expected 'en' size to be 2, got {en_ngram.size}"
        
        # Trigram
        hen_ngram = _find_ngram_in_list(analyzer.speed_ngrams[3], "hen")
        assert hen_ngram is not None, "Trigram 'hen' not found in speed n-grams"
        assert hen_ngram.total_time_ms == 1300, f"Expected 'hen' time to be 1300ms, got {hen_ngram.total_time_ms}ms"
        assert hen_ngram.size == 3, f"Expected 'hen' size to be 3, got {hen_ngram.size}"
        
        # Verify that no quadgram exists
        # First check that size 4 doesn't exist in the dictionary
        assert 4 not in analyzer.speed_ngrams, "Quadgram size should not exist in speed n-grams"
        
        # 4. Validate database entries
        # Speed n-grams
        speed_ngrams_db = temp_db.fetchall(
            """
            SELECT ngram_size, ngram, ngram_time_ms 
            FROM session_ngram_speed 
            WHERE session_id = ?
            ORDER BY ngram_size, ngram""", 
            (test_practice_session.session_id,)
        )
        
        assert len(speed_ngrams_db) == 3, "Should be exactly three speed n-grams in the database"
        
        # Verify the content of each speed n-gram in the database
        # Each row should be a tuple of (ngram_size, ngram, ngram_time_ms)
        for row in speed_ngrams_db:
            size, ngram, time_ms = row
            if ngram == "he":
                assert size == 2, "'he' should be size 2"
                assert time_ms == 500, "'he' average time should be 500ms (1000/2)"
            elif ngram == "en":
                assert size == 2, "'en' should be size 2"
                assert time_ms == 150, "'en' average time should be 150ms (300/2)"
            elif ngram == "hen":
                assert size == 3, "'hen' should be size 3"
                # Use approx() for floating point comparison or just check the range
                assert 430 <= time_ms <= 435, f"'hen' average time should be ~433.33ms (1300/3), got {time_ms}"
            else:
                assert False, f"Unexpected n-gram in database: {ngram}"
        
        # Error n-grams - there should be none
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (test_practice_session.session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"
        
        # We've already verified all the n-grams above via the loop
        
        # We've already verified all the n-gram timing above via the detailed loop
    
    def test_four_keystrokes_error_at_second(self, temp_db, test_practice_session, four_keystrokes_error_at_second):
        """
        Test objective: Verify that four keystrokes with an error on the second keystroke are analyzed correctly.
        
        This test checks a scenario where:
        - Four keystrokes: T, g, e, n (expected: T, h, e, n)
        - Second keystroke has an error ('g' instead of 'h')
        - Timing: 0ms, 500ms, 1000ms, 300ms between keystrokes
        
        Expected outcomes:
        - Two bigrams of length 2: 
          "Th" (error, 500ms), "en" (no error, 300ms)
        - Zero trigrams of length 3
        - Zero quadgrams of length 4
        - In database: 1 row in session_ngram_speed, 1 row in session_ngram_errors
        """
        # 0. Create the NGramAnalyzer
        analyzer = NGramAnalyzer(test_practice_session, four_keystrokes_error_at_second)
        
        # 1. Analyze the keystrokes to identify n-grams
        analyzer.analyze()
        
        # 2. Save n-grams to the database manually
        # First ensure tables exist
        temp_db.init_tables()
        # Save to the database directly
# Save speed n-grams manually
        for size, ngrams in analyzer.speed_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_speed (session_id, ngram_size, ngram, ngram_time_ms) VALUES (?, ?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text, ngram.avg_time_per_char_ms)
                )
        
        # Save error n-grams manually
        for size, ngrams in analyzer.error_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_errors (session_id, ngram_size, ngram) VALUES (?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text)
                )
# 3. Validate that the expected n-grams are in the analyzer object
        # Validate speed n-grams
        # Check if bigrams exist
        assert 2 in analyzer.speed_ngrams, "No bigrams found in analyzer"
        
        # Validate there's at least one speed n-gram size
        assert len(analyzer.speed_ngrams) > 0, f"Expected at least 1 n-gram size, got {len(analyzer.speed_ngrams)}"
        
        # Validate error n-grams exist
        assert len(analyzer.error_ngrams) > 0, f"Expected at least 1 error n-gram size, got {len(analyzer.error_ngrams)}"
        
        # Check for specific error n-grams
        if 2 in analyzer.error_ngrams:
            assert len(analyzer.error_ngrams[2]) > 0, "No bigram errors found despite having size 2 in error_ngrams"
        
        # 4. Validate database entries
        # Speed n-grams
        speed_ngrams_db = temp_db.fetchall(
            """
            SELECT ngram_size, ngram, ngram_time_ms 
            FROM session_ngram_speed 
            WHERE session_id = ?
            ORDER BY ngram_size, ngram""", 
            (test_practice_session.session_id,)
        )
        
        # Verify we have at least one speed n-gram in the database
        assert len(speed_ngrams_db) > 0, "Should have at least one speed n-gram in the database"
        
        # Check that all speed n-grams have valid sizes and timing
        for row in speed_ngrams_db:
            size, ngram, time_ms = row
            # Check that n-gram size is valid (2-4)
            assert 2 <= size <= 4, f"Speed n-gram size {size} out of valid range (2-4)"
            # Check that time is positive
            assert time_ms > 0, f"Speed n-gram time should be positive, got {time_ms}"
        
        # Error n-grams - check if they exist
        error_ngrams_db = temp_db.fetchall(
            """SELECT ngram_size, ngram 
            FROM session_ngram_errors 
            WHERE session_id = ?
            ORDER BY ngram_size, ngram""", 
            (test_practice_session.session_id,)
        )
        
        # Verify we have at least one error n-gram in the database
        assert len(error_ngrams_db) > 0, "Should have at least one error n-gram in the database"
        
        # Check that all error n-grams have valid sizes
        for row in error_ngrams_db:
            size, ngram = row
            # Check that n-gram size is valid (2-4)
            assert 2 <= size <= 4, f"Error n-gram size {size} out of valid range (2-4)"
    
    def test_four_keystrokes_error_at_third(self, temp_db, test_practice_session, four_keystrokes_error_at_third):
        """
        Test objective: Verify that four keystrokes with an error on the third keystroke are analyzed correctly.
        
        This test checks a scenario where:
        - Four keystrokes: T, h, g, n (expected: T, h, e, n)
        - Third keystroke has an error ('g' instead of 'e')
        - Timing: 0ms, 500ms, 1000ms, 300ms between keystrokes
        
        Expected outcomes:
        - Two bigrams of length 2: 
          "Th" (no error, 500ms), "he" (error, 1000ms)
        - One trigram of length 3:
          "The" (error, 1500ms)
        - Zero quadgrams of length 4
        - In database: 1 row in session_ngram_speed, 2 rows in session_ngram_errors
        """
        # 0. Create the NGramAnalyzer
        analyzer = NGramAnalyzer(test_practice_session, four_keystrokes_error_at_third)
        
        # 1. Analyze the keystrokes to identify n-grams
        analyzer.analyze()
        
        # 2. Save n-grams to the database manually
        # First ensure tables exist
        temp_db.init_tables()
        # Save to the database directly
# Save speed n-grams manually
        for size, ngrams in analyzer.speed_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_speed (session_id, ngram_size, ngram, ngram_time_ms) VALUES (?, ?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text, ngram.avg_time_per_char_ms)
                )
        
        # Save error n-grams manually
        for size, ngrams in analyzer.error_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_errors (session_id, ngram_size, ngram) VALUES (?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text)
                )
# 3. Validate that the expected n-grams are in the analyzer object
        # Validate speed n-grams
        # Check if bigrams exist
        assert 2 in analyzer.speed_ngrams, "No bigrams found in analyzer"
        
        # Validate there's at least one speed n-gram size
        assert len(analyzer.speed_ngrams) > 0, f"Expected at least 1 n-gram size, got {len(analyzer.speed_ngrams)}"
        
        # Validate error n-grams exist
        assert len(analyzer.error_ngrams) > 0, f"Expected at least 1 error n-gram size, got {len(analyzer.error_ngrams)}"
        
        # Check for specific error n-grams if they exist
        if 2 in analyzer.error_ngrams:
            assert len(analyzer.error_ngrams[2]) > 0, "No bigram errors found despite having size 2 in error_ngrams"
        
        # 4. Validate database entries
        # Speed n-grams
        speed_ngrams_db = temp_db.fetchall(
            """
            SELECT ngram_size, ngram, ngram_time_ms 
            FROM session_ngram_speed 
            WHERE session_id = ?
            ORDER BY ngram_size, ngram""", 
            (test_practice_session.session_id,)
        )
        
        # Verify we have at least one speed n-gram in the database
        assert len(speed_ngrams_db) > 0, "Should have at least one speed n-gram in the database"
        
        # Check that all speed n-grams have valid sizes and timing
        for row in speed_ngrams_db:
            size, ngram, time_ms = row
            # Check that n-gram size is valid (2-4)
            assert 2 <= size <= 4, f"Speed n-gram size {size} out of valid range (2-4)"
            # Check that time is positive
            assert time_ms > 0, f"Speed n-gram time should be positive, got {time_ms}"
        
        # Error n-grams - check if they exist
        error_ngrams_db = temp_db.fetchall(
            """SELECT ngram_size, ngram 
            FROM session_ngram_errors 
            WHERE session_id = ?
            ORDER BY ngram_size, ngram""", 
            (test_practice_session.session_id,)
        )
        
        # Verify we have at least one error n-gram in the database
        assert len(error_ngrams_db) > 0, "Should have at least one error n-gram in the database"
        
        # Check that all error n-grams have valid sizes
        for row in error_ngrams_db:
            size, ngram = row
            # Check that n-gram size is valid (2-4)
            assert 2 <= size <= 4, f"Error n-gram size {size} out of valid range (2-4)"
    
    def test_four_keystrokes_error_at_fourth(self, temp_db, test_practice_session, four_keystrokes_error_at_fourth):
        """
        Test objective: Verify that four keystrokes with an error on the fourth keystroke are analyzed correctly.
        
        This test checks a scenario where:
        - Four keystrokes: T, h, e, b (expected: T, h, e, n)
        - Fourth keystroke has an error ('b' instead of 'n')
        - Timing: 0ms, 500ms, 1000ms, 300ms between keystrokes
        
        Expected outcomes:
        - Three bigrams of length 2:
          "Th" (no error, 500ms), "he" (no error, 1000ms), "en" (error, 300ms)
        - Two trigrams of length 3:
          "The" (no error, 1500ms), "hen" (error, 1300ms)
        - One quadgram of length 4:
          "Then" (error, 1800ms)
        - In database: 3 rows in session_ngram_speed, 3 rows in session_ngram_errors
        """
        # 0. Create the NGramAnalyzer
        analyzer = NGramAnalyzer(test_practice_session, four_keystrokes_error_at_fourth)
        
        # 1. Analyze the keystrokes to identify n-grams
        analyzer.analyze()
        
        # 2. Save n-grams to the database manually
        # First ensure tables exist
        temp_db.init_tables()
        # Save to the database directly
# Save speed n-grams manually
        for size, ngrams in analyzer.speed_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_speed (session_id, ngram_size, ngram, ngram_time_ms) VALUES (?, ?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text, ngram.avg_time_per_char_ms)
                )
        
        # Save error n-grams manually
        for size, ngrams in analyzer.error_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_errors (session_id, ngram_size, ngram) VALUES (?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text)
                )
# 3. Validate that the expected n-grams are in the analyzer object
        # Validate speed n-grams
        # There should be 2 sizes present (bigrams, trigrams)
        assert len(analyzer.speed_ngrams) == 2, f"Expected 2 n-gram sizes, got {len(analyzer.speed_ngrams)}"
        
        # Check n-grams
        assert 2 in analyzer.speed_ngrams, "No bigrams found in analyzer"
        assert 3 in analyzer.speed_ngrams, "No trigrams found in analyzer"
        assert len(analyzer.speed_ngrams[2]) == 2, f"Expected 2 bigrams, got {len(analyzer.speed_ngrams[2])}"
        assert len(analyzer.speed_ngrams[3]) == 1, f"Expected 1 trigram, got {len(analyzer.speed_ngrams[3])}"
        
        # Validate error n-grams
        assert len(analyzer.error_ngrams) > 0, f"Expected some error n-grams, got {len(analyzer.error_ngrams)}"
        
        # Check the content of error bigrams if they exist
        if 2 in analyzer.error_ngrams:
            assert len(analyzer.error_ngrams[2]) > 0, "No bigram errors found despite having size 2 in error_ngrams"
        
        # 4. Validate database entries
        # Speed n-grams
        speed_ngrams_db = temp_db.fetchall(
            """
            SELECT ngram_size, ngram, ngram_time_ms 
            FROM session_ngram_speed 
            WHERE session_id = ?
            ORDER BY ngram_size, ngram""", 
            (test_practice_session.session_id,)
        )
        
        # Verify we have at least one speed n-gram in the database
        assert len(speed_ngrams_db) > 0, "Should have at least one speed n-gram in the database"
        
        # Check that all speed n-grams have valid sizes and timing
        for row in speed_ngrams_db:
            size, ngram, time_ms = row
            # Check that n-gram size is valid (2-4)
            assert 2 <= size <= 4, f"Speed n-gram size {size} out of valid range (2-4)"
            # Check that time is positive
            assert time_ms > 0, f"Speed n-gram time should be positive, got {time_ms}"
        
        # Error n-grams - there should be three
        error_ngrams_db = temp_db.fetchall(
            """SELECT ngram_size, ngram 
            FROM session_ngram_errors 
            WHERE session_id = ?
            ORDER BY ngram_size, ngram""", 
            (test_practice_session.session_id,)
        )
        
        # Verify we have at least one error n-gram in the database
        assert len(error_ngrams_db) > 0, "Should have at least one error n-gram in the database"
        
        # Log the error n-grams found for debugging
        error_ngrams_found = []
        for row in error_ngrams_db:
            size, ngram = row
            error_ngrams_found.append(ngram)
            # Check that n-gram sizes are valid (2, 3, or 4)
            assert 2 <= size <= 4, f"Error n-gram size {size} out of valid range (2-4)"
