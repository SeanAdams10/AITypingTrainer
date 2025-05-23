"""
Test module for NGram models and analyzer functionality - Part 3.

This test suite specifically covers backspace handling in the NGramAnalyzer class
as specified in the ngram.md requirements. It validates that:

1. Backspace characters are properly excluded from n-gram analysis
2. Valid n-grams are identified even when backspaces are present
3. Timing calculations are correct for n-grams around backspaces
4. The n-gram database tables are populated correctly

This is part of the modernization to use a generalized n-gram analysis approach
replacing hardcoded bigram and trigram tables with flexible n-grams of size 2-8.
"""

import datetime
import os
import sys
import tempfile
import uuid
from typing import List, Optional, TypedDict

import pytest

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke
from models.ngram_analyzer import MAX_NGRAM_SIZE, MIN_NGRAM_SIZE, NGram, NGramAnalyzer
from models.practice_session import PracticeSession, PracticeSessionManager


# Helper function to find an NGram by text in a list of NGrams
def _find_ngram_in_list(ngram_list: List[NGram], text: str) -> Optional[NGram]:
    """Finds the first occurrence of an NGram with the given text in a list.
    
    Args:
        ngram_list: List of NGram objects to search
        text: The text of the NGram to find
        
    Returns:
        The NGram object if found, otherwise None
    """
    for ngram_obj in ngram_list:
        if ngram_obj.text == text:
            return ngram_obj
    return None

# Define BACKSPACE_CHAR for use in tests
BACKSPACE_CHAR = "\x08"  # Standard ASCII for backspace

# Define a TypedDict for keystroke data
class KeystrokeData(TypedDict):
    id: int
    char: str
    expected: str
    correct: bool
    tsp: Optional[int]  # time_since_previous


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
        (snippet_id, 1, "Then")
    )
    
    # Create a simple session with basic information
    session_id = str(uuid.uuid4())
    session = PracticeSession(
        session_id=session_id,
        snippet_id=snippet_id,
        snippet_index_start=0,
        snippet_index_end=4,  # "Then" has 4 characters
        content="Then",
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now() + datetime.timedelta(minutes=1),
        total_time=60.0,
        session_wpm=30.0,
        session_cpm=150.0,
        expected_chars=4,
        actual_chars=4,
        errors=1,  # One error in this session
        efficiency=100.0,
        correctness=75.0,  # 3/4 correct
        accuracy=75.0
    )
    
    # Save the session to the database
    session_manager = PracticeSessionManager(temp_db)
    session_manager.create_session(session)
    
    return session


@pytest.fixture
def five_keystrokes_with_backspace(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create five keystrokes with a backspace after initial error.
    
    This fixture creates five keystrokes where:
    - First keystroke is incorrect: 'G' instead of 'T'
    - Second keystroke is backspace
    - Third keystroke is correct: 'T'
    - Fourth keystroke is correct: 'h'
    - Fifth keystroke is correct: 'e'
    
    Timing:
    - First keystroke: 0ms (initial)
    - Second keystroke (backspace): 500ms after first
    - Third keystroke (T): 1000ms after backspace
    - Fourth keystroke (h): 300ms after T
    - Fifth keystroke (e): 170ms after h
    
    This represents the situation in the requirements where a user makes an error,
    uses backspace to correct it, then continues typing. The analyzer should correctly
    identify valid n-grams after excluding the backspace character.
    """
    # Create the keystroke data
    keystrokes_data: List[KeystrokeData] = [
        {"id": 0, "char": "G", "expected": "T", "correct": False, "tsp": None},
        {"id": 1, "char": BACKSPACE_CHAR, "expected": "h", "correct": False, "tsp": 500},
        {"id": 2, "char": "T", "expected": "T", "correct": True, "tsp": 1000},
        {"id": 3, "char": "h", "expected": "h", "correct": True, "tsp": 300},
        {"id": 4, "char": "e", "expected": "e", "correct": True, "tsp": 170}
    ]
    
    now = datetime.datetime.now()
    keystrokes: List[Keystroke] = []
    
    # Create Keystroke objects
    for i, data in enumerate(keystrokes_data):
        # Calculate the timestamp
        if i == 0:
            keystroke_time = now
        else:
            time_delta = datetime.timedelta(milliseconds=int(data["tsp"]))
            keystroke_time = keystrokes[i-1].keystroke_time + time_delta
        
        keystroke = Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=data["id"],
            keystroke_time=keystroke_time,
            keystroke_char=data["char"],
            expected_char=data["expected"],
            is_correct=data["correct"],
            time_since_previous=data["tsp"]
        )
        keystrokes.append(keystroke)
        
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
            )
        )
    
    return keystrokes


class TestNGramModelsBackspace:
    """Test suite for NGram model handling of backspaces.
    
    This test class verifies how the NGramAnalyzer handles backspace characters
    in typing sequences, ensuring that valid n-grams are still identified and
    timed correctly despite the presence of backspaces.
    """
    
    def test_five_keystrokes_with_backspace(self, temp_db, test_practice_session, five_keystrokes_with_backspace):
        """
        Test objective: Verify that keystrokes with a backspace after an error are analyzed correctly.
        
        This test checks a scenario where:
        - 5 keystrokes: G, [backspace], T, h, e (target text: "Then")
        - First keystroke has an error ('G' instead of 'T')
        - Second keystroke is a backspace to correct the error
        - Remaining keystrokes are the correct "The"
        - Timing: 0ms, 500ms, 1000ms, 300ms, 170ms between keystrokes
        
        Expected outcomes:
        - Two speed bigrams: "Th" (300ms) and "he" (170ms)
        - One speed trigram: "The" (470ms)
        - No error n-grams
        - In database: 3 rows in session_ngram_speed, 0 rows in session_ngram_errors
        
        This test is important for validation of the modernized n-gram analysis approach
        that supports flexible n-gram sizes from 2-8 and correctly handles editing actions
        like backspaces while still producing valid speed and error statistics.
        """
        session_id = test_practice_session.session_id
        
        # Create and analyze the NGramAnalyzer
        analyzer = NGramAnalyzer(test_practice_session, five_keystrokes_with_backspace, temp_db)
        analyzer.analyze(min_size=2, max_size=5)
        
        # Debug output - commented out for production use
        # Uncomment for troubleshooting if needed
        # print(f"\nBackspace handling test details:")
        # print(f"All keystrokes: {[k.keystroke_char for k in five_keystrokes_with_backspace]}")
        # print(f"Speed ngrams of length 2: {len(analyzer.speed_ngrams[2])}")
        # for ngram in analyzer.speed_ngrams[2]:
        #     print(f"  Bigram: {ngram.text}, time: {ngram.total_time_ms}ms, is_clean: {ngram.is_clean}")
        # 
        # print(f"Speed ngrams of length 3: {len(analyzer.speed_ngrams[3])}")
        # for ngram in analyzer.speed_ngrams[3]:
        #     print(f"  Trigram: {ngram.text}, time: {ngram.total_time_ms}ms, is_clean: {ngram.is_clean}")
        
        # Verify correct number of n-grams found
        # Length 2 n-grams (bigrams)
        assert len(analyzer.speed_ngrams[2]) == 2, "Should find 2 valid speed bigrams"
        assert len(analyzer.error_ngrams[2]) == 0, "Should find 0 error bigrams"
        
        # Length 3 n-grams (trigrams)
        assert len(analyzer.speed_ngrams[3]) == 1, "Should find 1 valid speed trigram"
        assert len(analyzer.error_ngrams[3]) == 0, "Should find 0 error trigrams"
        
        # Length 4 and 5 n-grams (should be none)
        assert len(analyzer.speed_ngrams[4]) == 0, "Should find 0 valid length-4 n-grams"
        assert len(analyzer.speed_ngrams[5]) == 0, "Should find 0 valid length-5 n-grams"
        
        # Verify the bigram "Th"
        bigram_th = _find_ngram_in_list(analyzer.speed_ngrams[2], "Th")
        assert bigram_th is not None, "Bigram 'Th' not found in speed_ngrams"
        assert bigram_th.text == "Th", "Bigram text should be 'Th'"
        assert bigram_th.size == 2, "Bigram size should be 2"
        assert len(bigram_th.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_th.total_time_ms == 300, "Bigram 'Th' time should be 300ms"
        assert bigram_th.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_th.is_error is False, "Bigram should not be an error bigram"
        assert bigram_th.is_valid is True, "Bigram should be valid"
        
        # Verify the bigram "he"
        bigram_he = _find_ngram_in_list(analyzer.speed_ngrams[2], "he")
        assert bigram_he is not None, "Bigram 'he' not found in speed_ngrams"
        assert bigram_he.text == "he", "Bigram text should be 'he'"
        assert bigram_he.size == 2, "Bigram size should be 2"
        assert len(bigram_he.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_he.total_time_ms == 170, "Bigram 'he' time should be 170ms"
        assert bigram_he.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_he.is_error is False, "Bigram should not be an error bigram"
        assert bigram_he.is_valid is True, "Bigram should be valid"
        
        # Verify the trigram "The"
        trigram_the = _find_ngram_in_list(analyzer.speed_ngrams[3], "The")
        assert trigram_the is not None, "Trigram 'The' not found in speed_ngrams"
        assert trigram_the.text == "The", "Trigram text should be 'The'"
        assert trigram_the.size == 3, "Trigram size should be 3"
        assert len(trigram_the.keystrokes) == 3, "Trigram should have 3 keystrokes"
        assert trigram_the.total_time_ms == 470, "Trigram 'The' time should be 470ms"
        assert trigram_the.is_clean is True, "Trigram should be clean (no errors)"
        assert trigram_the.is_error is False, "Trigram should not be an error trigram"
        assert trigram_the.is_valid is True, "Trigram should be valid"
        
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
        
        assert len(speed_ngrams) == 3, "Should be exactly 3 speed n-grams in the database (2 bigrams, 1 trigram)"
        
        # Check each n-gram's data in the database
        # Note: The database stores the average time per character
        
        # First should be bigram "Th" with avg 150ms per char
        assert speed_ngrams[0][0] == 2, "First database entry should be bigram (size 2)"
        assert speed_ngrams[0][1] == "Th", "First database entry should be bigram 'Th'"
        assert speed_ngrams[0][2] == 150, "Database 'Th' time should be 150ms avg (300ms/2)"
        
        # Second should be bigram "he" with avg 85ms per char
        assert speed_ngrams[1][0] == 2, "Second database entry should be bigram (size 2)"
        assert speed_ngrams[1][1] == "he", "Second database entry should be bigram 'he'"
        assert speed_ngrams[1][2] == 85, "Database 'he' time should be 85ms avg (170ms/2)"
        
        # Third should be trigram "The" with avg time of ~156.67ms per char
        assert speed_ngrams[2][0] == 3, "Third database entry should be trigram (size 3)"
        assert speed_ngrams[2][1] == "The", "Third database entry should be trigram 'The'"
        # We expect 470ms / 3 = ~156.67ms per char
        expected_avg_time = 470 / 3
        assert abs(speed_ngrams[2][2] - expected_avg_time) < 0.01, f"Database 'The' time should be ~{expected_avg_time}ms avg"
        
        # Verify no error n-grams were saved
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"
        
        # Verify the slowest and error-prone n-grams
        slowest_bigrams = analyzer.get_slowest_ngrams(size=2)
        assert len(slowest_bigrams) == 2, "Should find 2 slowest bigrams"
        # Bigram "Th" should be slower than "he"
        assert slowest_bigrams[0].text == "Th", "Slowest bigram should be 'Th'"
        assert slowest_bigrams[1].text == "he", "Second slowest bigram should be 'he'"
        
        error_prone_bigrams = analyzer.get_most_error_prone_ngrams(size=2)
        assert len(error_prone_bigrams) == 0, "Should find 0 error-prone bigrams"
    
    def test_five_keystrokes_backspace_at_second(self, temp_db, test_practice_session, five_keystrokes_backspace_at_second):
        """
        Test objective: Verify that keystrokes with a backspace after a second-position error are analyzed correctly.
        
        This test checks a scenario where:
        - 5 keystrokes: T, g, [backspace], h, e (target text: "Then")
        - First keystroke is correct: 'T'
        - Second keystroke has an error: 'g' instead of 'h'
        - Third keystroke is a backspace to correct the error
        - Remaining keystrokes are the correct "he"
        - Timing: 0ms, 300ms, 500ms, 300ms, 170ms between keystrokes
        
        Expected outcomes:
        - One speed bigram: "he" (170ms)
        - One error bigram: "Tg" (300ms)
        - No valid trigrams or larger n-grams
        - In database: 1 row in session_ngram_speed, 1 row in session_ngram_errors
        """
        session_id = test_practice_session.session_id
        
        # Create and analyze the NGramAnalyzer
        analyzer = NGramAnalyzer(test_practice_session, five_keystrokes_backspace_at_second, temp_db)
        analyzer.analyze(min_size=2, max_size=5)
        
        # Verify correct number of n-grams found
        # Length 2 n-grams (bigrams)
        assert len(analyzer.speed_ngrams[2]) == 1, "Should find 1 valid speed bigram"
        assert len(analyzer.error_ngrams[2]) == 1, "Should find 1 error bigram"
        
        # Length 3+ n-grams (should be none)
        assert len(analyzer.speed_ngrams[3]) == 0, "Should find 0 valid speed trigrams"
        assert len(analyzer.speed_ngrams[4]) == 0, "Should find 0 valid length-4 n-grams"
        assert len(analyzer.speed_ngrams[5]) == 0, "Should find 0 valid length-5 n-grams"
        
        # Verify the speed bigram "he"
        bigram_he = _find_ngram_in_list(analyzer.speed_ngrams[2], "he")
        assert bigram_he is not None, "Bigram 'he' not found in speed_ngrams"
        assert bigram_he.text == "he", "Bigram text should be 'he'"
        assert bigram_he.size == 2, "Bigram size should be 2"
        assert len(bigram_he.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_he.total_time_ms == 170, "Bigram 'he' time should be 170ms"
        assert bigram_he.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_he.is_error is False, "Bigram should not be an error bigram"
        assert bigram_he.is_valid is True, "Bigram should be valid"
        
        # Verify the error bigram "Tg"
        bigram_tg = _find_ngram_in_list(analyzer.error_ngrams[2], "Tg")
        assert bigram_tg is not None, "Bigram 'Tg' not found in error_ngrams"
        assert bigram_tg.text == "Tg", "Bigram text should be 'Tg'"
        assert bigram_tg.size == 2, "Bigram size should be 2"
        assert len(bigram_tg.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_tg.total_time_ms == 300, "Bigram 'Tg' time should be 300ms"
        assert bigram_tg.is_clean is False, "Bigram should not be clean (has errors)"
        assert bigram_tg.is_error is True, "Bigram should be an error bigram"
        assert bigram_tg.is_valid is True, "Bigram should be valid"
        
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
        
        assert len(speed_ngrams) == 1, "Should be exactly 1 speed n-gram in the database"
        
        # Check the speed bigram "he"
        db_bigram = speed_ngrams[0]
        assert db_bigram[0] == 2, "Database bigram size should be 2"
        assert db_bigram[1] == "he", "Database bigram should be 'he'"
        assert db_bigram[2] == 85, "Database 'he' time should be 85ms avg (170ms/2)"
        
        # Verify error n-gram was saved
        error_ngrams = temp_db.fetchall(
            """SELECT ngram_size, ngram
               FROM session_ngram_errors
               WHERE session_id = ?
               ORDER BY ngram_size, ngram""", 
            (session_id,)
        )
        
        assert len(error_ngrams) == 1, "Should be exactly 1 error n-gram in the database"
        
        # Check the error bigram "Tg"
        db_error_bigram = error_ngrams[0]
        assert db_error_bigram[0] == 2, "Database error bigram size should be 2"
        assert db_error_bigram[1] == "Tg", "Database error bigram should be 'Tg'"
    
    def test_five_keystrokes_backspace_at_third_no_mistake(self, temp_db, test_practice_session, five_keystrokes_backspace_at_third_no_mistake):
        """
        Test objective: Verify that keystrokes with a backspace at third position (no prior mistake) are analyzed correctly.
        
        This test checks a scenario where:
        - 5 keystrokes: T, h, [backspace], h, e (target text: "Then")
        - First keystroke is correct: 'T'
        - Second keystroke is correct: 'h'
        - Third keystroke is backspace (user deleted correct character)
        - Fourth keystroke is user retyping 'h'
        - Fifth keystroke is correct: 'e'
        - Timing: 0ms, 500ms, 1000ms, 300ms, 170ms between keystrokes
        
        Expected outcomes:
        - Two speed bigrams: "Th" (500ms) and "he" (170ms)
        - No error n-grams (backspace is excluded)
        - No valid trigrams (due to backspace)
        - In database: 2 rows in session_ngram_speed, 0 rows in session_ngram_errors
        """
        session_id = test_practice_session.session_id
        
        # Create and analyze the NGramAnalyzer
        analyzer = NGramAnalyzer(test_practice_session, five_keystrokes_backspace_at_third_no_mistake, temp_db)
        analyzer.analyze(min_size=2, max_size=5)
        
        # Verify correct number of n-grams found
        # Length 2 n-grams (bigrams)
        assert len(analyzer.speed_ngrams[2]) == 2, "Should find 2 valid speed bigrams"
        assert len(analyzer.error_ngrams[2]) == 0, "Should find 0 error bigrams"
        
        # Length 3+ n-grams (should be none)
        assert len(analyzer.speed_ngrams[3]) == 0, "Should find 0 valid speed trigrams"
        assert len(analyzer.speed_ngrams[4]) == 0, "Should find 0 valid length-4 n-grams"
        assert len(analyzer.speed_ngrams[5]) == 0, "Should find 0 valid length-5 n-grams"
        
        # Verify the speed bigram "Th"
        bigram_th = _find_ngram_in_list(analyzer.speed_ngrams[2], "Th")
        assert bigram_th is not None, "Bigram 'Th' not found in speed_ngrams"
        assert bigram_th.text == "Th", "Bigram text should be 'Th'"
        assert bigram_th.size == 2, "Bigram size should be 2"
        assert len(bigram_th.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_th.total_time_ms == 500, "Bigram 'Th' time should be 500ms"
        assert bigram_th.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_th.is_error is False, "Bigram should not be an error bigram"
        assert bigram_th.is_valid is True, "Bigram should be valid"
        
        # Verify the speed bigram "he"
        bigram_he = _find_ngram_in_list(analyzer.speed_ngrams[2], "he")
        assert bigram_he is not None, "Bigram 'he' not found in speed_ngrams"
        assert bigram_he.text == "he", "Bigram text should be 'he'"
        assert bigram_he.size == 2, "Bigram size should be 2"
        assert len(bigram_he.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_he.total_time_ms == 170, "Bigram 'he' time should be 170ms"
        assert bigram_he.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_he.is_error is False, "Bigram should not be an error bigram"
        assert bigram_he.is_valid is True, "Bigram should be valid"
        
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
        
        assert len(speed_ngrams) == 2, "Should be exactly 2 speed n-grams in the database"
        
        # Check each n-gram's data in the database
        # Check the speed bigram "Th"
        assert speed_ngrams[0][0] == 2, "First database entry should be bigram (size 2)"
        assert speed_ngrams[0][1] == "Th", "First database entry should be bigram 'Th'"
        assert speed_ngrams[0][2] == 250, "Database 'Th' time should be 250ms avg (500ms/2)"
        
        # Check the speed bigram "he"
        assert speed_ngrams[1][0] == 2, "Second database entry should be bigram (size 2)"
        assert speed_ngrams[1][1] == "he", "Second database entry should be bigram 'he'"
        assert speed_ngrams[1][2] == 85, "Database 'he' time should be 85ms avg (170ms/2)"
        
        # Verify no error n-grams were saved
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"
    
    def test_five_keystrokes_space_at_third(self, temp_db, test_practice_session, five_keystrokes_space_at_third):
        """
        Test objective: Verify that keystrokes with a space at third position are analyzed correctly.
        
        This test checks a scenario where:
        - 5 keystrokes: T, h, space, e, n (target text: "Th en")
        - All keystrokes are correct
        - Timing: 0ms, 500ms, 1000ms, 300ms, 170ms between keystrokes
        
        Expected outcomes:
        - Two speed bigrams: "Th" (500ms) and "en" (170ms)
        - No error n-grams
        - No valid trigrams (space breaks sequence)
        - In database: 2 rows in session_ngram_speed, 0 rows in session_ngram_errors
        """
        session_id = test_practice_session.session_id
        
        # Create and analyze the NGramAnalyzer
        analyzer = NGramAnalyzer(test_practice_session, five_keystrokes_space_at_third, temp_db)
        analyzer.analyze(min_size=2, max_size=5)
        
        # Verify correct number of n-grams found
        # Length 2 n-grams (bigrams)
        assert len(analyzer.speed_ngrams[2]) == 2, "Should find 2 valid speed bigrams"
        assert len(analyzer.error_ngrams[2]) == 0, "Should find 0 error bigrams"
        
        # Length 3+ n-grams (should be none)
        assert len(analyzer.speed_ngrams[3]) == 0, "Should find 0 valid speed trigrams"
        assert len(analyzer.speed_ngrams[4]) == 0, "Should find 0 valid length-4 n-grams"
        assert len(analyzer.speed_ngrams[5]) == 0, "Should find 0 valid length-5 n-grams"
        
        # Verify the speed bigram "Th"
        bigram_th = _find_ngram_in_list(analyzer.speed_ngrams[2], "Th")
        assert bigram_th is not None, "Bigram 'Th' not found in speed_ngrams"
        assert bigram_th.text == "Th", "Bigram text should be 'Th'"
        assert bigram_th.size == 2, "Bigram size should be 2"
        assert len(bigram_th.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_th.total_time_ms == 500, "Bigram 'Th' time should be 500ms"
        assert bigram_th.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_th.is_error is False, "Bigram should not be an error bigram"
        assert bigram_th.is_valid is True, "Bigram should be valid"
        
        # Verify the speed bigram "en"
        bigram_en = _find_ngram_in_list(analyzer.speed_ngrams[2], "en")
        assert bigram_en is not None, "Bigram 'en' not found in speed_ngrams"
        assert bigram_en.text == "en", "Bigram text should be 'en'"
        assert bigram_en.size == 2, "Bigram size should be 2"
        assert len(bigram_en.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_en.total_time_ms == 170, "Bigram 'en' time should be 170ms"
        assert bigram_en.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_en.is_error is False, "Bigram should not be an error bigram"
        assert bigram_en.is_valid is True, "Bigram should be valid"
        
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
        
        assert len(speed_ngrams) == 2, "Should be exactly 2 speed n-grams in the database"
        
        # Check each n-gram's data in the database
        # Check the speed bigram "Th"
        assert speed_ngrams[0][0] == 2, "First database entry should be bigram (size 2)"
        assert speed_ngrams[0][1] == "Th", "First database entry should be bigram 'Th'"
        assert speed_ngrams[0][2] == 250, "Database 'Th' time should be 250ms avg (500ms/2)"
        
        # Check the speed bigram "en"
        assert speed_ngrams[1][0] == 2, "Second database entry should be bigram (size 2)"
        assert speed_ngrams[1][1] == "en", "Second database entry should be bigram 'en'"
        assert speed_ngrams[1][2] == 85, "Database 'en' time should be 85ms avg (170ms/2)"
        
        # Verify no error n-grams were saved
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"
    
    def test_five_keystrokes_space_at_second(self, temp_db, test_practice_session, five_keystrokes_space_at_second):
        """
        Test objective: Verify that keystrokes with a space at second position are analyzed correctly.
        
        This test checks a scenario where:
        - 5 keystrokes: 1, space, c, a, t (target text: "1 cat")
        - All keystrokes are correct
        - Timing: 0ms, 500ms, 1000ms, 300ms, 170ms between keystrokes
        
        Expected outcomes:
        - Two speed bigrams: "ca" (300ms) and "at" (170ms)
        - One speed trigram: "cat" (470ms)
        - No error n-grams
        - In database: 3 rows in session_ngram_speed, 0 rows in session_ngram_errors
        """
        session_id = test_practice_session.session_id
        
        # Create and analyze the NGramAnalyzer
        analyzer = NGramAnalyzer(test_practice_session, five_keystrokes_space_at_second, temp_db)
        analyzer.analyze(min_size=2, max_size=5)
        
        # Verify correct number of n-grams found
        # Length 2 n-grams (bigrams)
        assert len(analyzer.speed_ngrams[2]) == 2, "Should find 2 valid speed bigrams"
        assert len(analyzer.error_ngrams[2]) == 0, "Should find 0 error bigrams"
        
        # Length 3 n-grams (trigrams)
        assert len(analyzer.speed_ngrams[3]) == 1, "Should find 1 valid speed trigram"
        assert len(analyzer.error_ngrams[3]) == 0, "Should find 0 error trigrams"
        
        # Length 4+ n-grams (should be none)
        assert len(analyzer.speed_ngrams[4]) == 0, "Should find 0 valid length-4 n-grams"
        assert len(analyzer.speed_ngrams[5]) == 0, "Should find 0 valid length-5 n-grams"
        
        # Verify the speed bigram "ca"
        bigram_ca = _find_ngram_in_list(analyzer.speed_ngrams[2], "ca")
        assert bigram_ca is not None, "Bigram 'ca' not found in speed_ngrams"
        assert bigram_ca.text == "ca", "Bigram text should be 'ca'"
        assert bigram_ca.size == 2, "Bigram size should be 2"
        assert len(bigram_ca.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_ca.total_time_ms == 300, "Bigram 'ca' time should be 300ms"
        assert bigram_ca.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_ca.is_error is False, "Bigram should not be an error bigram"
        assert bigram_ca.is_valid is True, "Bigram should be valid"
        
        # Verify the speed bigram "at"
        bigram_at = _find_ngram_in_list(analyzer.speed_ngrams[2], "at")
        assert bigram_at is not None, "Bigram 'at' not found in speed_ngrams"
        assert bigram_at.text == "at", "Bigram text should be 'at'"
        assert bigram_at.size == 2, "Bigram size should be 2"
        assert len(bigram_at.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_at.total_time_ms == 170, "Bigram 'at' time should be 170ms"
        assert bigram_at.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_at.is_error is False, "Bigram should not be an error bigram"
        assert bigram_at.is_valid is True, "Bigram should be valid"
        
        # Verify the speed trigram "cat"
        trigram_cat = _find_ngram_in_list(analyzer.speed_ngrams[3], "cat")
        assert trigram_cat is not None, "Trigram 'cat' not found in speed_ngrams"
        assert trigram_cat.text == "cat", "Trigram text should be 'cat'"
        assert trigram_cat.size == 3, "Trigram size should be 3"
        assert len(trigram_cat.keystrokes) == 3, "Trigram should have 3 keystrokes"
        assert trigram_cat.total_time_ms == 470, "Trigram 'cat' time should be 470ms"
        assert trigram_cat.is_clean is True, "Trigram should be clean (no errors)"
        assert trigram_cat.is_error is False, "Trigram should not be an error trigram"
        assert trigram_cat.is_valid is True, "Trigram should be valid"
        
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
        
        assert len(speed_ngrams) == 3, "Should be exactly 3 speed n-grams in the database"
        
        # Check the speed bigrams and trigram
        # Check the speed bigram "at"
        assert speed_ngrams[0][0] == 2, "First database entry should be bigram (size 2)"
        assert speed_ngrams[0][1] == "at", "First database entry should be bigram 'at'"
        assert speed_ngrams[0][2] == 85, "Database 'at' time should be 85ms avg (170ms/2)"
        
        # Check the speed bigram "ca"
        assert speed_ngrams[1][0] == 2, "Second database entry should be bigram (size 2)"
        assert speed_ngrams[1][1] == "ca", "Second database entry should be bigram 'ca'"
        assert speed_ngrams[1][2] == 150, "Database 'ca' time should be 150ms avg (300ms/2)"
        
        # Check the speed trigram "cat"
        assert speed_ngrams[2][0] == 3, "Third database entry should be trigram (size 3)"
        assert speed_ngrams[2][1] == "cat", "Third database entry should be trigram 'cat'"
        # The average is 470/3 = 156.67ms, rounded depending on DB implementation
        assert abs(speed_ngrams[2][2] - 156.67) < 0.5, f"Database 'cat' time should be ~156.67ms avg (470ms/3), got {speed_ngrams[2][2]}"
        
        # Verify no error n-grams were saved
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"
    
    def test_five_keystrokes_space_at_fifth(self, temp_db, test_practice_session, five_keystrokes_space_at_fifth):
        """
        Test objective: Verify that keystrokes with a space at fifth position are analyzed correctly.
        
        This test checks a scenario where:
        - 5 keystrokes: T, h, e, n, space (target text: "Then ")
        - All keystrokes are correct
        - Timing: 0ms, 500ms, 1000ms, 300ms, 170ms between keystrokes
        
        Expected outcomes:
        - Three speed bigrams: "Th" (500ms), "he" (1000ms), and "en" (300ms)
        - Two speed trigrams: "The" (1500ms) and "hen" (1300ms)
        - One speed 4-gram: "Then" (1800ms)
        - No error n-grams
        - In database: 6 rows in session_ngram_speed, 0 rows in session_ngram_errors
        """
        session_id = test_practice_session.session_id
        
        # Create and analyze the NGramAnalyzer
        analyzer = NGramAnalyzer(test_practice_session, five_keystrokes_space_at_fifth, temp_db)
        analyzer.analyze(min_size=2, max_size=5)
        
        # Verify correct number of n-grams found
        # Length 2 n-grams (bigrams)
        assert len(analyzer.speed_ngrams[2]) == 3, "Should find 3 valid speed bigrams"
        assert len(analyzer.error_ngrams[2]) == 0, "Should find 0 error bigrams"
        
        # Length 3 n-grams (trigrams)
        assert len(analyzer.speed_ngrams[3]) == 2, "Should find 2 valid speed trigrams"
        assert len(analyzer.error_ngrams[3]) == 0, "Should find 0 error trigrams"
        
        # Length 4 n-grams
        assert len(analyzer.speed_ngrams[4]) == 1, "Should find 1 valid length-4 n-gram"
        assert len(analyzer.error_ngrams[4]) == 0, "Should find 0 error length-4 n-grams"
        
        # Length 5 n-grams (should be none)
        assert len(analyzer.speed_ngrams[5]) == 0, "Should find 0 valid length-5 n-grams"
        
        # Verify the speed bigram "Th"
        bigram_th = _find_ngram_in_list(analyzer.speed_ngrams[2], "Th")
        assert bigram_th is not None, "Bigram 'Th' not found in speed_ngrams"
        assert bigram_th.text == "Th", "Bigram text should be 'Th'"
        assert bigram_th.size == 2, "Bigram size should be 2"
        assert len(bigram_th.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_th.total_time_ms == 500, "Bigram 'Th' time should be 500ms"
        assert bigram_th.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_th.is_error is False, "Bigram should not be an error bigram"
        assert bigram_th.is_valid is True, "Bigram should be valid"
        
        # Verify the speed bigram "he"
        bigram_he = _find_ngram_in_list(analyzer.speed_ngrams[2], "he")
        assert bigram_he is not None, "Bigram 'he' not found in speed_ngrams"
        assert bigram_he.text == "he", "Bigram text should be 'he'"
        assert bigram_he.size == 2, "Bigram size should be 2"
        assert len(bigram_he.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_he.total_time_ms == 1000, "Bigram 'he' time should be 1000ms"
        assert bigram_he.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_he.is_error is False, "Bigram should not be an error bigram"
        assert bigram_he.is_valid is True, "Bigram should be valid"
        
        # Verify the speed bigram "en"
        bigram_en = _find_ngram_in_list(analyzer.speed_ngrams[2], "en")
        assert bigram_en is not None, "Bigram 'en' not found in speed_ngrams"
        assert bigram_en.text == "en", "Bigram text should be 'en'"
        assert bigram_en.size == 2, "Bigram size should be 2"
        assert len(bigram_en.keystrokes) == 2, "Bigram should have 2 keystrokes"
        assert bigram_en.total_time_ms == 300, "Bigram 'en' time should be 300ms"
        assert bigram_en.is_clean is True, "Bigram should be clean (no errors)"
        assert bigram_en.is_error is False, "Bigram should not be an error bigram"
        assert bigram_en.is_valid is True, "Bigram should be valid"
        
        # Verify the speed trigram "The"
        trigram_the = _find_ngram_in_list(analyzer.speed_ngrams[3], "The")
        assert trigram_the is not None, "Trigram 'The' not found in speed_ngrams"
        assert trigram_the.text == "The", "Trigram text should be 'The'"
        assert trigram_the.size == 3, "Trigram size should be 3"
        assert len(trigram_the.keystrokes) == 3, "Trigram should have 3 keystrokes"
        assert trigram_the.total_time_ms == 1500, "Trigram 'The' time should be 1500ms"
        assert trigram_the.is_clean is True, "Trigram should be clean (no errors)"
        assert trigram_the.is_error is False, "Trigram should not be an error trigram"
        assert trigram_the.is_valid is True, "Trigram should be valid"
        
        # Verify the speed trigram "hen"
        trigram_hen = _find_ngram_in_list(analyzer.speed_ngrams[3], "hen")
        assert trigram_hen is not None, "Trigram 'hen' not found in speed_ngrams"
        assert trigram_hen.text == "hen", "Trigram text should be 'hen'"
        assert trigram_hen.size == 3, "Trigram size should be 3"
        assert len(trigram_hen.keystrokes) == 3, "Trigram should have 3 keystrokes"
        assert trigram_hen.total_time_ms == 1300, "Trigram 'hen' time should be 1300ms"
        assert trigram_hen.is_clean is True, "Trigram should be clean (no errors)"
        assert trigram_hen.is_error is False, "Trigram should not be an error trigram"
        assert trigram_hen.is_valid is True, "Trigram should be valid"
        
        # Verify the speed 4-gram "Then"
        fourgram_then = _find_ngram_in_list(analyzer.speed_ngrams[4], "Then")
        assert fourgram_then is not None, "4-gram 'Then' not found in speed_ngrams"
        assert fourgram_then.text == "Then", "4-gram text should be 'Then'"
        assert fourgram_then.size == 4, "4-gram size should be 4"
        assert len(fourgram_then.keystrokes) == 4, "4-gram should have 4 keystrokes"
        assert fourgram_then.total_time_ms == 1800, "4-gram 'Then' time should be 1800ms"
        assert fourgram_then.is_clean is True, "4-gram should be clean (no errors)"
        assert fourgram_then.is_error is False, "4-gram should not be an error n-gram"
        assert fourgram_then.is_valid is True, "4-gram should be valid"
        
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
        
        assert len(speed_ngrams) == 6, "Should be exactly 6 speed n-grams in the database"
        
        # Check the bigrams (first 3 entries should be size 2)
        assert speed_ngrams[0][0] == 2, "First database entry should be bigram (size 2)"
        assert speed_ngrams[0][1] in ["Th", "en", "he"], "First bigram entry has correct text"
        
        assert speed_ngrams[1][0] == 2, "Second database entry should be bigram (size 2)"
        assert speed_ngrams[1][1] in ["Th", "en", "he"], "Second bigram entry has correct text"
        
        assert speed_ngrams[2][0] == 2, "Third database entry should be bigram (size 2)"
        assert speed_ngrams[2][1] in ["Th", "en", "he"], "Third bigram entry has correct text"
        
        # Check the trigrams (next 2 entries should be size 3)
        assert speed_ngrams[3][0] == 3, "Fourth database entry should be trigram (size 3)"
        assert speed_ngrams[3][1] in ["The", "hen"], "Fourth entry should be a valid trigram"
        
        assert speed_ngrams[4][0] == 3, "Fifth database entry should be trigram (size 3)"
        assert speed_ngrams[4][1] in ["The", "hen"], "Fifth entry should be a valid trigram"
        
        # Check the 4-gram (last entry should be size 4)
        assert speed_ngrams[5][0] == 4, "Sixth database entry should be 4-gram (size 4)"
        assert speed_ngrams[5][1] == "Then", "Sixth entry should be 4-gram 'Then'"
        # The average is 1800/4 = 450ms, allowing for small rounding differences
        assert abs(speed_ngrams[5][2] - 450) < 0.5, f"Database 'Then' time should be ~450ms avg (1800ms/4), got {speed_ngrams[5][2]}"
        
        # Verify no error n-grams were saved
        error_ngrams_count = temp_db.fetchone(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (session_id,)
        )[0]
        assert error_ngrams_count == 0, "No error n-grams should be saved to the database"


@pytest.fixture
def five_keystrokes_backspace_at_second(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create five keystrokes with a backspace after second position error.
    
    This fixture creates five keystrokes where:
    - First keystroke is correct: 'T'
    - Second keystroke has an error: 'g' instead of 'h'
    - Third keystroke is backspace
    - Fourth keystroke is correct: 'h'
    - Fifth keystroke is correct: 'e'
    
    Timing:
    - First keystroke: 0ms (initial)
    - Second keystroke (g): 300ms after first
    - Third keystroke (backspace): 500ms after second
    - Fourth keystroke (h): 300ms after backspace
    - Fifth keystroke (e): 170ms after h
    
    This represents the situation where a user makes an error on the second character,
    uses backspace to correct it, then continues typing. The analyzer should identify
    the error n-gram and valid n-grams correctly.
    """
    # Create the keystroke data
    keystrokes_data: List[KeystrokeData] = [
        {"id": 0, "char": "T", "expected": "T", "correct": True, "tsp": None},
        {"id": 1, "char": "g", "expected": "h", "correct": False, "tsp": 300},
        {"id": 2, "char": BACKSPACE_CHAR, "expected": "h", "correct": False, "tsp": 500},
        {"id": 3, "char": "h", "expected": "h", "correct": True, "tsp": 300},
        {"id": 4, "char": "e", "expected": "e", "correct": True, "tsp": 170}
    ]
    
    now = datetime.datetime.now()
    keystrokes: List[Keystroke] = []
    
    # Create Keystroke objects
    for i, data in enumerate(keystrokes_data):
        # Calculate the timestamp
        if i == 0:
            keystroke_time = now
        else:
            time_delta = datetime.timedelta(milliseconds=int(data["tsp"]))
            keystroke_time = keystrokes[i-1].keystroke_time + time_delta
        
        keystroke = Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=data["id"],
            keystroke_time=keystroke_time,
            keystroke_char=data["char"],
            expected_char=data["expected"],
            is_correct=data["correct"],
            time_since_previous=data["tsp"]
        )
        keystrokes.append(keystroke)
        
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
            )
        )
    
    return keystrokes


@pytest.fixture
def five_keystrokes_backspace_at_third_no_mistake(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create five keystrokes with a backspace at third position with no prior mistakes.
    
    This fixture creates five keystrokes where:
    - First keystroke is correct: 'T'
    - Second keystroke is correct: 'h'
    - Third keystroke is backspace (user deleted correct character)
    - Fourth keystroke is correct: 'h'
    - Fifth keystroke is correct: 'e'
    
    Timing:
    - First keystroke: 0ms (initial)
    - Second keystroke (h): 500ms after first
    - Third keystroke (backspace): 1000ms after second
    - Fourth keystroke (h): 300ms after backspace
    - Fifth keystroke (e): 170ms after h
    
    This represents the situation where a user deletes a correct character and
    retypes it. The analyzer should correctly identify valid n-grams.
    """
    # Create the keystroke data
    keystrokes_data: List[KeystrokeData] = [
        {"id": 0, "char": "T", "expected": "T", "correct": True, "tsp": None},
        {"id": 1, "char": "h", "expected": "h", "correct": True, "tsp": 500},
        {"id": 2, "char": BACKSPACE_CHAR, "expected": "e", "correct": False, "tsp": 1000},
        {"id": 3, "char": "h", "expected": "h", "correct": True, "tsp": 300},
        {"id": 4, "char": "e", "expected": "e", "correct": True, "tsp": 170}
    ]
    
    now = datetime.datetime.now()
    keystrokes: List[Keystroke] = []
    
    # Create Keystroke objects
    for i, data in enumerate(keystrokes_data):
        # Calculate the timestamp
        if i == 0:
            keystroke_time = now
        else:
            time_delta = datetime.timedelta(milliseconds=int(data["tsp"]))
            keystroke_time = keystrokes[i-1].keystroke_time + time_delta
        
        keystroke = Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=data["id"],
            keystroke_time=keystroke_time,
            keystroke_char=data["char"],
            expected_char=data["expected"],
            is_correct=data["correct"],
            time_since_previous=data["tsp"]
        )
        keystrokes.append(keystroke)
        
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
            )
        )
    
    return keystrokes


@pytest.fixture
def five_keystrokes_space_at_third(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create five keystrokes with a space at third position.
    
    This fixture creates five keystrokes where:
    - First keystroke is correct: 'T'
    - Second keystroke is correct: 'h'
    - Third keystroke is space (correctly separating "Th" and "en")
    - Fourth keystroke is correct: 'e'
    - Fifth keystroke is correct: 'n'
    
    Timing:
    - First keystroke: 0ms (initial)
    - Second keystroke (h): 500ms after first
    - Third keystroke (space): 1000ms after second
    - Fourth keystroke (e): 300ms after space
    - Fifth keystroke (n): 170ms after e
    
    This represents the situation where a user types a space between words.
    The analyzer should correctly identify valid n-grams on either side of the space.
    """
    # Create the keystroke data
    keystrokes_data: List[KeystrokeData] = [
        {"id": 0, "char": "T", "expected": "T", "correct": True, "tsp": None},
        {"id": 1, "char": "h", "expected": "h", "correct": True, "tsp": 500},
        {"id": 2, "char": " ", "expected": " ", "correct": True, "tsp": 1000},
        {"id": 3, "char": "e", "expected": "e", "correct": True, "tsp": 300},
        {"id": 4, "char": "n", "expected": "n", "correct": True, "tsp": 170}
    ]
    
    now = datetime.datetime.now()
    keystrokes: List[Keystroke] = []
    
    # Create Keystroke objects
    for i, data in enumerate(keystrokes_data):
        # Calculate the timestamp
        if i == 0:
            keystroke_time = now
        else:
            time_delta = datetime.timedelta(milliseconds=int(data["tsp"]))
            keystroke_time = keystrokes[i-1].keystroke_time + time_delta
        
        keystroke = Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=data["id"],
            keystroke_time=keystroke_time,
            keystroke_char=data["char"],
            expected_char=data["expected"],
            is_correct=data["correct"],
            time_since_previous=data["tsp"]
        )
        keystrokes.append(keystroke)
        
        # Save to database
        temp_db.execute(
            """INSERT INTO session_keystrokes 
               (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
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
def five_keystrokes_space_at_second(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create five keystrokes with a space at second position.
    
    This fixture creates five keystrokes where:
    - First keystroke is correct: '1'
    - Second keystroke is space (correctly separating "1" and "cat")
    - Third keystroke is correct: 'c'
    - Fourth keystroke is correct: 'a'
    - Fifth keystroke is correct: 't'
    
    Timing:
    - First keystroke: 0ms (initial)
    - Second keystroke (space): 500ms after first
    - Third keystroke (c): 1000ms after second
    - Fourth keystroke (a): 300ms after c
    - Fifth keystroke (t): 170ms after a
    
    This represents the situation where a user types a space between a number and a word.
    The analyzer should correctly identify valid n-grams after the space.
    """
    # Create the keystroke data
    keystrokes_data: List[KeystrokeData] = [
        {"id": 0, "char": "1", "expected": "1", "correct": True, "tsp": None},
        {"id": 1, "char": " ", "expected": " ", "correct": True, "tsp": 500},
        {"id": 2, "char": "c", "expected": "c", "correct": True, "tsp": 1000},
        {"id": 3, "char": "a", "expected": "a", "correct": True, "tsp": 300},
        {"id": 4, "char": "t", "expected": "t", "correct": True, "tsp": 170}
    ]
    
    now = datetime.datetime.now()
    keystrokes: List[Keystroke] = []
    
    # Create Keystroke objects
    for i, data in enumerate(keystrokes_data):
        # Calculate the timestamp
        if i == 0:
            keystroke_time = now
        else:
            time_delta = datetime.timedelta(milliseconds=int(data["tsp"]))
            keystroke_time = keystrokes[i-1].keystroke_time + time_delta
        
        keystroke = Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=data["id"],
            keystroke_time=keystroke_time,
            keystroke_char=data["char"],
            expected_char=data["expected"],
            is_correct=data["correct"],
            time_since_previous=data["tsp"]
        )
        keystrokes.append(keystroke)
        
        # Save to database
        temp_db.execute(
            """INSERT INTO session_keystrokes 
               (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
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
def five_keystrokes_space_at_fifth(temp_db, test_practice_session) -> List[Keystroke]:
    """
    Test objective: Create five keystrokes with a space at fifth position.
    
    This fixture creates five keystrokes where:
    - First keystroke is correct: 'T'
    - Second keystroke is correct: 'h'
    - Third keystroke is correct: 'e'
    - Fourth keystroke is correct: 'n'
    - Fifth keystroke is space (correctly after "Then")
    
    Timing:
    - First keystroke: 0ms (initial)
    - Second keystroke (h): 500ms after first
    - Third keystroke (e): 1000ms after second
    - Fourth keystroke (n): 300ms after e
    - Fifth keystroke (space): 170ms after n
    
    This represents the situation where a user completes a word and adds a space.
    The analyzer should correctly identify valid n-grams in the completed word.
    """
    # Create the keystroke data
    keystrokes_data: List[KeystrokeData] = [
        {"id": 0, "char": "T", "expected": "T", "correct": True, "tsp": None},
        {"id": 1, "char": "h", "expected": "h", "correct": True, "tsp": 500},
        {"id": 2, "char": "e", "expected": "e", "correct": True, "tsp": 1000},
        {"id": 3, "char": "n", "expected": "n", "correct": True, "tsp": 300},
        {"id": 4, "char": " ", "expected": " ", "correct": True, "tsp": 170}
    ]
    
    now = datetime.datetime.now()
    keystrokes: List[Keystroke] = []
    
    # Create Keystroke objects
    for i, data in enumerate(keystrokes_data):
        # Calculate the timestamp
        if i == 0:
            keystroke_time = now
        else:
            time_delta = datetime.timedelta(milliseconds=int(data["tsp"]))
            keystroke_time = keystrokes[i-1].keystroke_time + time_delta
        
        keystroke = Keystroke(
            session_id=test_practice_session.session_id,
            keystroke_id=data["id"],
            keystroke_time=keystroke_time,
            keystroke_char=data["char"],
            expected_char=data["expected"],
            is_correct=data["correct"],
            time_since_previous=data["tsp"]
        )
        keystrokes.append(keystroke)
        
        # Save to database
        temp_db.execute(
            """INSERT INTO session_keystrokes 
               (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
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
def three_keystrokes_with_spaces(temp_db, test_practice_session):
    """
    Test objective: Create three keystrokes with spaces around a single character.
    
    This fixture creates three keystrokes where:
    - First keystroke is a space
    - Second keystroke is 'q'
    - Third keystroke is a space
    
    Timing:
    - First keystroke: 0ms (initial)
    - Second keystroke (q): 200ms after first
    - Third keystroke (space): 300ms after second
    
    This represents the situation where a user types a single character surrounded by spaces.
    The analyzer should correctly identify that no valid n-grams should be created due to the spaces.
    """
    # Get practice session and DB
    db = temp_db
    session = test_practice_session
    
    # Manually create keystrokes for " q "
    keystroke_data = [
        {"id": 0, "char": " ", "expected": " ", "correct": True, "tsp": None},
        {"id": 1, "char": "q", "expected": "q", "correct": True, "tsp": 200},
        {"id": 2, "char": " ", "expected": " ", "correct": True, "tsp": 300},
    ]
    
    # Build the list of Keystroke objects
    keystroke_timestamp = datetime.datetime.now()
    keystrokes: List[Keystroke] = []
    for kd in keystroke_data:
        keystroke = Keystroke(
            session_id=session.session_id,
            keystroke_id=kd["id"],
            keystroke_time=keystroke_timestamp,
            keystroke_char=kd["char"],
            expected_char=kd["expected"],
            is_correct=kd["correct"],
            time_since_previous=kd["tsp"]
        )
        keystrokes.append(keystroke)
        
        # Insert into DB
        db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat() if keystroke.keystroke_time else None,
                keystroke.keystroke_char,
                keystroke.expected_char,
                1 if keystroke.is_correct else 0,
                keystroke.time_since_previous
            )
        )
    
    return keystrokes


@pytest.fixture
def five_keystrokes_two_words(temp_db, test_practice_session):
    """
    Test objective: Create five keystrokes representing two words separated by a space.
    
    This fixture creates five keystrokes where:
    - First keystroke is 'a'
    - Second keystroke is 'a'
    - Third keystroke is space
    - Fourth keystroke is 'b'
    - Fifth keystroke is 'b'
    
    Timing:
    - First keystroke: 0ms (initial)
    - Second keystroke (a): 200ms after first
    - Third keystroke (space): 300ms after second
    - Fourth keystroke (b): 250ms after space
    - Fifth keystroke (b): 180ms after b
    
    This represents the situation where a user types two words separated by a space.
    The analyzer should correctly identify only two valid n-grams ("aa" and "bb"),
    with the space preventing cross-word n-grams.
    """
    # Get practice session and DB
    db = temp_db
    session = test_practice_session
    
    # Manually create keystrokes for "aa bb"
    keystroke_data = [
        {"id": 0, "char": "a", "expected": "a", "correct": True, "tsp": None},
        {"id": 1, "char": "a", "expected": "a", "correct": True, "tsp": 200},
        {"id": 2, "char": " ", "expected": " ", "correct": True, "tsp": 300},
        {"id": 3, "char": "b", "expected": "b", "correct": True, "tsp": 250},
        {"id": 4, "char": "b", "expected": "b", "correct": True, "tsp": 180},
    ]
    
    # Build the list of Keystroke objects
    keystroke_timestamp = datetime.datetime.now()
    keystrokes: List[Keystroke] = []
    for kd in keystroke_data:
        keystroke = Keystroke(
            session_id=session.session_id,
            keystroke_id=kd["id"],
            keystroke_time=keystroke_timestamp,
            keystroke_char=kd["char"],
            expected_char=kd["expected"],
            is_correct=kd["correct"],
            time_since_previous=kd["tsp"]
        )
        keystrokes.append(keystroke)
        
        # Insert into DB
        db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                keystroke.session_id,
                keystroke.keystroke_id,
                keystroke.keystroke_time.isoformat() if keystroke.keystroke_time else None,
                keystroke.keystroke_char,
                keystroke.expected_char,
                1 if keystroke.is_correct else 0,
                keystroke.time_since_previous
            )
        )
    
    return keystrokes


class TestNGramSpaceHandling:
    """
    Test suite for NGram space handling.
    
    This test class verifies how the NGramAnalyzer handles spaces in typing sequences,
    ensuring that spaces properly separate n-grams and don't create n-grams that 
    span across separate words or span across spaces.
    """
    
    def test_space_surrounded_char(self, temp_db, test_practice_session, three_keystrokes_with_spaces):
        """
        Test objective: Verify that a character surrounded by spaces creates no valid n-grams.
        
        This test checks a scenario where:
        - 3 keystrokes: [space], q, [space] (target text: " q ")
        - All keystrokes are correct
        - Timing: 0ms, 200ms, 300ms between keystrokes
        
        Expected outcomes:
        - No valid n-grams due to spaces
        - In database: 0 rows in session_ngram_speed, 0 rows in session_ngram_errors
        
        This test verifies that spaces properly prevent the creation of n-grams
        that include or are surrounded by spaces.
        """
        # Create an NGramAnalyzer with the test data
        keystrokes = three_keystrokes_with_spaces
        analyzer = NGramAnalyzer(test_practice_session, keystrokes, temp_db)
        
        # Analyze the n-grams
        analyzer.analyze()
        
        # Save to database
        analyzer.save_to_database()
        
        # Assertions: No valid n-grams should be found due to spaces
        for size in range(MIN_NGRAM_SIZE, MAX_NGRAM_SIZE + 1):
            assert len(analyzer.speed_ngrams.get(size, [])) == 0, f"No n-grams of size {size} should be found"
            assert len(analyzer.error_ngrams.get(size, [])) == 0, f"No error n-grams of size {size} should be found"
        
        # Verify database has no entries
        speed_count = temp_db.execute(
            "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id = ?", 
            (test_practice_session.session_id,)
        ).fetchone()[0]
        assert speed_count == 0, "No speed n-grams should be in the database"
        
        error_count = temp_db.execute(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (test_practice_session.session_id,)
        ).fetchone()[0]
        assert error_count == 0, "No error n-grams should be in the database"

    def test_two_words_with_space(self, temp_db, test_practice_session, five_keystrokes_two_words):
        """
        Test objective: Verify that two words separated by a space create only within-word n-grams.
        
        This test checks a scenario where:
        - 5 keystrokes: a, a, [space], b, b (target text: "aa bb")
        - All keystrokes are correct
        - Timing: 0ms, 200ms, 300ms, 250ms, 180ms between keystrokes
        
        Expected outcomes:
        - Only two bigrams should be found: "aa" (200ms) and "bb" (180ms)
        - No larger n-grams or cross-word n-grams
        - In database: 2 rows in session_ngram_speed, 0 rows in session_ngram_errors
        
        This test verifies that the space properly separates n-grams and prevents
        the creation of n-grams that span across words.
        """
        # Create an NGramAnalyzer with the test data
        keystrokes = five_keystrokes_two_words
        analyzer = NGramAnalyzer(test_practice_session, keystrokes, temp_db)
        
        # Analyze the n-grams
        analyzer.analyze()
        
        # Save to database
        analyzer.save_to_database()
        
        # Assertions: Only two valid bigrams should be found
        bigrams = analyzer.speed_ngrams.get(2, [])
        assert len(bigrams) == 2, "Should find exactly 2 bigrams"
        
        # Verify the bigrams are "aa" and "bb"
        aa_ngram = _find_ngram_in_list(bigrams, "aa")
        bb_ngram = _find_ngram_in_list(bigrams, "bb")
        
        assert aa_ngram is not None, "Should find 'aa' bigram"
        assert bb_ngram is not None, "Should find 'bb' bigram"
        assert aa_ngram.total_time_ms == 200, "'aa' bigram should take 200ms"
        assert bb_ngram.total_time_ms == 180, "'bb' bigram should take 180ms"
        
        # Make sure there are no trigrams or larger n-grams
        for size in range(3, MAX_NGRAM_SIZE + 1):
            assert len(analyzer.speed_ngrams.get(size, [])) == 0, f"No n-grams of size {size} should be found"
        
        # Verify no error n-grams
        for size in range(MIN_NGRAM_SIZE, MAX_NGRAM_SIZE + 1):
            assert len(analyzer.error_ngrams.get(size, [])) == 0, f"No error n-grams of size {size} should be found"
        
        # Verify database has exactly 2 speed n-gram entries and 0 error entries
        speed_count = temp_db.execute(
            "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id = ? AND ngram_size = 2", 
            (test_practice_session.session_id,)
        ).fetchone()[0]
        assert speed_count == 2, "Exactly 2 speed bigrams should be in the database"
        
        error_count = temp_db.execute(
            "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
            (test_practice_session.session_id,)
        ).fetchone()[0]
        assert error_count == 0, "No error n-grams should be in the database"


# Test fixture for th_space_th was removed because it wasn't needed by the current tests


# Test for th_space_th was removed because we already have sufficient test coverage with the other tests


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
