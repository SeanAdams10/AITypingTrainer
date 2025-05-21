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
            session_id=test_practice_session.session_id,
            keystroke_time=now,
            keystroke_char="T",
            expected_char="T",
            is_correct=True,
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500  # 500ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_time=now + datetime.timedelta(milliseconds=1500),  # 1500 from start
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000  # 1000ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_time=now + datetime.timedelta(milliseconds=1800),  # 1800 from start
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300  # 300ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for i, keystroke in enumerate(keystrokes):
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                i,  # Use index as keystroke_id
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
    # Create four keystrokes with the session_id, first one has an error
    now = datetime.datetime.now()
    keystrokes = [
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_time=now,
            keystroke_char="G",  # Error: typed 'G' instead of 'T'
            expected_char="T",
            is_correct=False,    # Mark as incorrect
            time_since_previous=0  # First keystroke has 0 time_since_previous
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_time=now + datetime.timedelta(milliseconds=500),
            keystroke_char="h",
            expected_char="h",
            is_correct=True,
            time_since_previous=500  # 500ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_time=now + datetime.timedelta(milliseconds=1500),  # 1500 from start
            keystroke_char="e",
            expected_char="e",
            is_correct=True,
            time_since_previous=1000  # 1000ms since previous keystroke
        ),
        Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_time=now + datetime.timedelta(milliseconds=1800),  # 1800 from start
            keystroke_char="n",
            expected_char="n",
            is_correct=True,
            time_since_previous=300  # 300ms since previous keystroke
        )
    ]
    
    # Save keystrokes to the database
    for i, keystroke in enumerate(keystrokes):
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                i,  # Use index as keystroke_id
                keystroke.keystroke_time.isoformat(),
                keystroke.keystroke_char,
                keystroke.expected_char,
                keystroke.is_correct,
                keystroke.time_since_previous
            ),
            commit=True
        )
    
    return keystrokes

class TestNGramModelsExtended:
    """Extended test suite for NGram model and analyzer functionality with longer sequences."""
    
    def test_four_keystrokes_no_errors(self, temp_db, test_practice_session, four_keystrokes_no_errors):
        """
        Test objective: Verify that four keystrokes produce correct n-grams with proper timing.
        
        This test checks a scenario where:
        - Four keystrokes: T, h, e, n (expected: T, h, e, n)
        - No errors
        - Timing: 0ms, 500ms, 1000ms, 300ms between keystrokes
        
        Expected outcomes:
        - Three bigrams of length 2: 
          "Th" (500ms), "he" (1000ms), "en" (300ms)
        - Two trigrams of length 3:
          "The" (1500ms), "hen" (1300ms)
        - One quadgram of length 4:
          "Then" (1800ms)
        - In database: 6 rows in session_ngram_speed, 0 rows in session_ngram_errors
        """
        # Create an NGramAnalyzer instance with the keystrokes
        analyzer = NGramAnalyzer(test_practice_session, four_keystrokes_no_errors)
        
        # Check that all expected n-grams are identified
        # 1. Analyze the keystrokes to identify n-grams
        analyzer.analyze()
        
        # 2. Save n-grams to the database manually following the pattern in test_three_keystrokes_error_at_third
        # First ensure tables exist
        temp_db.init_tables()
        
        # Save to the database directly
        temp_db.begin_transaction()
        
        # Save speed n-grams manually
        for size, ngrams in analyzer.speed_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_speed (session_id, ngram_size, ngram, ngram_time_ms) VALUES (?, ?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text, ngram.avg_time_per_char_ms)
                )
        
        # Save error n-grams manually (none in this case)
        for size, ngrams in analyzer.error_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_errors (session_id, ngram_size, ngram) VALUES (?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text)
                )
        
        # Commit the transaction
        temp_db.commit_transaction()
        
        # 3. Validate that the expected n-grams are in the analyzer object
        # There should be 3 n-gram sizes present (bigrams, trigrams, and quadgrams)
        assert len(analyzer.speed_ngrams) == 3, f"Expected 3 n-gram sizes, got {len(analyzer.speed_ngrams)}"
        
        # Check that there are 3 bigrams, 2 trigrams, and 1 quadgram
        assert len(analyzer.speed_ngrams[2]) == 3, f"Expected 3 bigrams, got {len(analyzer.speed_ngrams[2])}"
        assert len(analyzer.speed_ngrams[3]) == 2, f"Expected 2 trigrams, got {len(analyzer.speed_ngrams[3])}"
        assert len(analyzer.speed_ngrams[4]) == 1, f"Expected 1 quadgram, got {len(analyzer.speed_ngrams[4])}"
        assert len(analyzer.error_ngrams) == 0, f"Expected 0 error n-grams, got {len(analyzer.error_ngrams)}"
        
        # Check specific n-grams and their timings
        # Bigrams
        th_ngram = _find_ngram_in_list(analyzer.speed_ngrams[2], "Th")
        assert th_ngram is not None, "Bigram 'Th' not found in speed n-grams"
        assert th_ngram.total_time_ms == 500, f"Expected 'Th' time to be 500ms, got {th_ngram.total_time_ms}ms"
        assert th_ngram.size == 2, f"Expected 'Th' size to be 2, got {th_ngram.size}"
        
        he_ngram = _find_ngram_in_list(analyzer.speed_ngrams[2], "he")
        assert he_ngram is not None, "Bigram 'he' not found in speed n-grams"
        assert he_ngram.total_time_ms == 1000, f"Expected 'he' time to be 1000ms, got {he_ngram.total_time_ms}ms"
        assert he_ngram.size == 2, f"Expected 'he' size to be 2, got {he_ngram.size}"
        
        en_ngram = _find_ngram_in_list(analyzer.speed_ngrams[2], "en")
        assert en_ngram is not None, "Bigram 'en' not found in speed n-grams"
        assert en_ngram.total_time_ms == 300, f"Expected 'en' time to be 300ms, got {en_ngram.total_time_ms}ms"
        assert en_ngram.size == 2, f"Expected 'en' size to be 2, got {en_ngram.size}"
        
        # Trigrams
        the_ngram = _find_ngram_in_list(analyzer.speed_ngrams[3], "The")
        assert the_ngram is not None, "Trigram 'The' not found in speed n-grams"
        assert the_ngram.total_time_ms == 1500, f"Expected 'The' time to be 1500ms, got {the_ngram.total_time_ms}ms"
        assert the_ngram.size == 3, f"Expected 'The' size to be 3, got {the_ngram.size}"
        
        hen_ngram = _find_ngram_in_list(analyzer.speed_ngrams[3], "hen")
        assert hen_ngram is not None, "Trigram 'hen' not found in speed n-grams"
        assert hen_ngram.total_time_ms == 1300, f"Expected 'hen' time to be 1300ms, got {hen_ngram.total_time_ms}ms"
        assert hen_ngram.size == 3, f"Expected 'hen' size to be 3, got {hen_ngram.size}"
        
        # Quadgram
        then_ngram = _find_ngram_in_list(analyzer.speed_ngrams[4], "Then")
        assert then_ngram is not None, "Quadgram 'Then' not found in speed n-grams"
        assert then_ngram.total_time_ms == 1800, f"Expected 'Then' time to be 1800ms, got {then_ngram.total_time_ms}ms"
        assert then_ngram.size == 4, f"Expected 'Then' size to be 4, got {then_ngram.size}"
        
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
        
        assert len(speed_ngrams_db) == 6, "Should be exactly six speed n-grams in the database"
        
        # Verify the content of each speed n-gram in the database
        # Each row should be a tuple of (ngram_size, ngram, ngram_time_ms)
        for row in speed_ngrams_db:
            size, ngram, time_ms = row
            if ngram == "Th":
                assert size == 2, "'Th' should be size 2"
                assert time_ms == 250, "'Th' average time should be 250ms (500/2)"
            elif ngram == "he":
                assert size == 2, "'he' should be size 2"
                assert time_ms == 500, "'he' average time should be 500ms (1000/2)"
            elif ngram == "en":
                assert size == 2, "'en' should be size 2"
                assert time_ms == 150, "'en' average time should be 150ms (300/2)"
            elif ngram == "The":
                assert size == 3, "'The' should be size 3"
                assert 495 <= time_ms <= 505, f"'The' average time should be ~500ms (1500/3), got {time_ms}"
            elif ngram == "hen":
                assert size == 3, "'hen' should be size 3"
                assert 430 <= time_ms <= 435, f"'hen' average time should be ~433.33ms (1300/3), got {time_ms}"
            elif ngram == "Then":
                assert size == 4, "'Then' should be size 4"
                assert 445 <= time_ms <= 455, f"'Then' average time should be ~450ms (1800/4), got {time_ms}"
            else:
                assert False, f"Unexpected n-gram in database: {ngram}"
        
        # Error n-grams - there should be none
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (test_practice_session.session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"
        
        # We've already verified all the n-grams above via the detailed loop
        
        # We've already verified all the n-gram timing above via the detailed loop
    
    def test_four_keystrokes_error_at_first(self, temp_db, test_practice_session, four_keystrokes_error_at_first):
        """
        Test objective: Verify that four keystrokes with an error on the first keystroke are analyzed correctly.
        
        This test checks a scenario where:
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
        temp_db.begin_transaction()
        
        # Save speed n-grams manually
        for size, ngrams in analyzer.speed_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_speed (session_id, ngram_size, ngram, ngram_time_ms) VALUES (?, ?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text, ngram.avg_time_per_char_ms)
                )
        
        # Save error n-grams manually (none in this case)
        for size, ngrams in analyzer.error_ngrams.items():
            for ngram in ngrams:
                temp_db.execute(
                    "INSERT INTO session_ngram_errors (session_id, ngram_size, ngram) VALUES (?, ?, ?)",
                    (test_practice_session.session_id, size, ngram.text)
                )
        
        # Commit the transaction
        temp_db.commit_transaction()
        
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
