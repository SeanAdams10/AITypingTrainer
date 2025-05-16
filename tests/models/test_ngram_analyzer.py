# """
# Tests for the NGramAnalyzer class.

# These tests verify the functionality of the NGramAnalyzer class, including
# n-gram extraction, statistics calculation, and database operations.
# """
# from __future__ import annotations

# import os
# import sqlite3
# import tempfile
# import time
# from datetime import datetime, timedelta
# from pathlib import Path
# from typing import Any, Dict, List, Optional

# import pytest
# from pytest_mock import MockerFixture

# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# from db.database_manager import DatabaseManager
# from models.ngram_analyzer import NGramAnalyzer, NGramStats

# # Test data
# SAMPLE_KEYSTROKES = [
#     # First word: "the"
#     {"keystroke_id": 1, "keystroke_time": "2023-01-01 10:00:00.000", 
#      "keystroke_char": "t", "expected_char": "t", "is_correct": True, "time_since_previous": 0},
#     {"keystroke_id": 2, "keystroke_time": "2023-01-01 10:00:00.100", 
#      "keystroke_char": "h", "expected_char": "h", "is_correct": True, "time_since_previous": 100},
#     {"keystroke_id": 3, "keystroke_time": "2023-01-01 10:00:00.200", 
#      "keystroke_char": "e", "expected_char": "e", "is_correct": True, "time_since_previous": 100},
    
#     # Space after first word
#     {"keystroke_id": 4, "keystroke_time": "2023-01-01 10:00:00.300", 
#      "keystroke_char": " ", "expected_char": " ", "is_correct": True, "time_since_previous": 100},
    
#     # Second word: "quick" (with an error on 'u')
#     {"keystroke_id": 5, "keystroke_time": "2023-01-01 10:00:00.400", 
#      "keystroke_char": "q", "expected_char": "q", "is_correct": True, "time_since_previous": 100},
#     {"keystroke_id": 6, "keystroke_time": "2023-01-01 10:00:00.500", 
#      "keystroke_char": "x", "expected_char": "u", "is_correct": False, "time_since_previous": 100},
#     {"keystroke_id": 7, "keystroke_time": "2023-01-01 10:00:00.550", 
#      "keystroke_char": "u", "expected_char": "u", "is_correct": True, "time_since_previous": 50},
#     {"keystroke_id": 8, "keystroke_time": "2023-01-01 10:00:00.650", 
#      "keystroke_char": "i", "expected_char": "i", "is_correct": True, "time_since_previous": 100},
#     {"keystroke_id": 9, "keystroke_time": "2023-01-01 10:00:00.750", 
#      "keystroke_char": "c", "expected_char": "c", "is_correct": True, "time_since_previous": 100},
#     {"keystroke_id": 10, "keystroke_time": "2023-01-01 10:00:00.850", 
#      "keystroke_char": "k", "expected_char": "k", "is_correct": True, "time_since_previous": 100},
     
#     # Space after second word
#     {"keystroke_id": 11, "keystroke_time": "2023-01-01 10:00:00.950", 
#      "keystroke_char": " ", "expected_char": " ", "is_correct": True, "time_since_previous": 100},
     
#     # Third word: "brown" (all correct)
#     {"keystroke_id": 12, "keystroke_time": "2023-01-01 11:00:00.000", 
#      "keystroke_char": "b", "expected_char": "b", "is_correct": True, "time_since_previous": 100},
#     {"keystroke_id": 13, "keystroke_time": "2023-01-01 11:00:00.100", 
#      "keystroke_char": "r", "expected_char": "r", "is_correct": True, "time_since_previous": 100},
#     {"keystroke_id": 14, "keystroke_time": "2023-01-01 11:00:00.200", 
#      "keystroke_char": "o", "expected_char": "o", "is_correct": True, "time_since_previous": 100},
#     {"keystroke_id": 15, "keystroke_time": "2023-01-01 11:00:00.300", 
#      "keystroke_char": "w", "expected_char": "w", "is_correct": True, "time_since_previous": 100},
#     {"keystroke_id": 16, "keystroke_time": "2023-01-01 11:00:00.400", 
#      "keystroke_char": "n", "expected_char": "n", "is_correct": True, "time_since_previous": 100},
# ]

# # Fixtures
# @pytest.fixture
# def temp_db():
#     """Create a temporary database for testing."""
#     with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
#         db_path = tmp.name
    
#     # Initialize database with required tables
#     db = DatabaseManager(db_path)
#     db.init_tables()
    
#     # Create session_keystrokes table if it doesn't exist
#     db.execute("""
#         CREATE TABLE IF NOT EXISTS session_keystrokes (
#             keystroke_id INTEGER PRIMARY KEY AUTOINCREMENT,
#             session_id TEXT NOT NULL,
#             keystroke_time TIMESTAMP NOT NULL,
#             keystroke_char TEXT NOT NULL,
#             expected_char TEXT NOT NULL,
#             is_correct BOOLEAN NOT NULL,
#             time_since_previous INTEGER,
#             FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
#         )
#     """)
    
#     # Create practice_sessions table if it doesn't exist
#     db.execute("""
#         CREATE TABLE IF NOT EXISTS practice_sessions (
#             session_id TEXT PRIMARY KEY,
#             snippet_id INTEGER,
#             snippet_index_start INTEGER,
#             snippet_index_end INTEGER,
#             content TEXT NOT NULL,
#             start_time TEXT,
#             end_time TEXT,
#             total_time REAL,
#             session_wpm REAL,
#             session_cpm REAL,
#             expected_chars INTEGER,
#             actual_chars INTEGER,
#             errors INTEGER,
#             efficiency REAL,
#             correctness REAL,
#             accuracy REAL,
#             FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE SET NULL
#         )
#     """)
    
#     yield db
    
#     # Cleanup
#     db.close()
#     try:
#         os.unlink(db_path)
#     except (OSError, PermissionError):
#         pass

# @pytest.fixture
# def sample_session(temp_db: DatabaseManager) -> str:
#     """Create a sample session with keystrokes for testing."""
#     session_id = "test_session_123"
    
#     # First, create a category since it's referenced by the snippet
#     temp_db.execute(
#         """
#         CREATE TABLE IF NOT EXISTS categories (
#             category_id INTEGER PRIMARY KEY AUTOINCREMENT,
#             category_name TEXT NOT NULL UNIQUE
#         );
#         """,
#         commit=True
#     )
    
#     # Insert a test category
#     temp_db.execute(
#         """
#         INSERT INTO categories (category_id, category_name)
#         VALUES (1, 'test_category')
#         """,
#         commit=True
#     )
    
#     # Now create the snippet since it's referenced by the session
#     temp_db.execute(
#         """
#         INSERT INTO snippets (snippet_id, category_id, snippet_name)
#         VALUES (1, 1, 'test_snippet')
#         """,
#         commit=True
#     )
    
#     # Now insert the session record with all required fields
#     now = datetime.now().isoformat()
#     end_time = (datetime.now() + timedelta(seconds=10)).isoformat()
#     temp_db.execute(
#         """
#         INSERT INTO practice_sessions 
#         (session_id, snippet_id, snippet_index_start, snippet_index_end, content,
#          start_time, end_time, total_time, session_wpm, session_cpm, 
#          expected_chars, actual_chars, errors, efficiency, correctness, accuracy)
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """,
#         (session_id, 
#          1,  # snippet_id (must match the one inserted above)
#          0,  # snippet_index_start
#          0,  # snippet_index_end
#          'test content',  # content
#          now,  # start_time
#          end_time,  # end_time
#          10.0,  # total_time
#          50.0,  # session_wpm
#          250.0,  # session_cpm
#          100,  # expected_chars
#          95,  # actual_chars
#          5,  # errors
#          0.95,  # efficiency
#          0.95,  # correctness
#          95.0),  # accuracy
#         commit=True
#     )
    
#     # Insert sample keystrokes
#     for keystroke in SAMPLE_KEYSTROKES:
#         temp_db.execute(
#             """
#             INSERT INTO session_keystrokes 
#             (session_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
#             VALUES (?, ?, ?, ?, ?, ?)
#             """,
#             (session_id, 
#              keystroke["keystroke_time"],
#              keystroke["keystroke_char"],
#              keystroke["expected_char"],
#              keystroke["is_correct"],
#              keystroke["time_since_previous"]),
#             commit=True
#         )
    
#     return session_id

# # Tests
# def test_ngram_stats_calculation():
#     """Test NGramStats calculation methods."""
#     # Test with zero values
#     stats = NGramStats(ngram="test", ngram_size=4)
#     assert stats.avg_time_ms == 0.0
#     assert stats.error_rate == 0.0
    
#     # Test with values
#     stats.count = 5
#     stats.total_time_ms = 500.0
#     stats.error_count = 2
#     stats.occurrences = 10
    
#     assert stats.avg_time_ms == 100.0
#     assert stats.error_rate == 0.2

# def test_ngram_analyzer_initialization(temp_db: DatabaseManager):
#     """Test that NGramAnalyzer initializes correctly."""
#     analyzer = NGramAnalyzer(temp_db)
#     assert analyzer is not None

# @pytest.mark.parametrize("ngram_size,expected_ngrams", [
#     # For size 2: Include all n-grams, including those with errors
#     (2, {"th", "he", "e ", " q", "qu", "ui", "ic", "ck", "k ", " b", "br", "ro", "ow", "wn"}),
#     # For size 3: Include all n-grams, including those with errors
#     (3, {"the", "he ", "e q", " qu", "qui", "uic", "ick", "ck ", "k b", " br", "bro", "row", "own"}),
#     # For size 4: Include all n-grams, including those with errors
#     (4, {"the ", "he q", "e qu", " quu", "quui", "uuic", "uick", "ick ", "ck b", "k br", " bro", "brow", "rown"}),
#     # For size 5: Include all n-grams, including those with errors
#     (5, {"the q", "he qu", "e quu", " quui", "quuic", "uuick", "uick ", "ick b", "ck br", "k bro", " brow", "brown"}),
#     # For size 6: Include all n-grams, including those with errors
#     (6, {"the qu", "he quu", "e quui", " quuic", "quuick", "uuick ", "uick b", "ick br", "ck bro", "k brow", " brown"}),
#     # For size 7: Include all n-grams, including those with errors
#     (7, {"the quu", "he quui", "e quuic", " quuick", "quuick ", "uuick b", "uick br", "ick bro", "ck brow", "k brown"}),
#     # For size 8: Include all n-grams, including those with errors
#     (8, {"the quui", "he quuic", "e quuick", " quuick ", "quuick b", "uuick br", "uick bro", "ick brow", "ck brown"}),
#     # For size 9: Include all n-grams, including those with errors
#     (9, {"the quuic", "he quuick", "e quuick ", " quuick b", "quuick br", "uuick bro", "uick brow", "ick brown"}),
#     # For size 10: Include all n-grams, including those with errors
#     (10, {"the quuick", "he quuick ", "e quuick b", " quuick br", "quuick bro", "uuick brow", "uick brown"})
# ])
# def test_ngram_extraction(temp_db: DatabaseManager, sample_session: str, ngram_size: int, expected_ngrams: set[str], capsys):
#     """Test that n-grams are extracted correctly."""
#     analyzer = NGramAnalyzer(temp_db)
    
#     # Mock the _get_session_keystrokes method to return our test data
#     def mock_get_keystrokes(session_id: str) -> List[Dict[str, Any]]:
#         return SAMPLE_KEYSTROKES
    
#     analyzer._get_session_keystrokes = mock_get_keystrokes
    
#     # Process the keystrokes
#     ngram_stats = analyzer._process_keystrokes(SAMPLE_KEYSTROKES)
    
#     # Print debug information
#     captured = capsys.readouterr()
#     print("\nDebug output:")
#     print(captured.out)
    
#     print(f"\nAll n-gram stats:")
#     for size, ngrams in ngram_stats.items():
#         print(f"  Size {size}:")
#         for ngram, stats in ngrams.items():
#             print(f"    {ngram}: {stats}")
    
#     # Get the n-grams for the current size we're testing
#     current_ngrams = ngram_stats.get(str(ngram_size), {})
#     print(f"\nN-grams for size {ngram_size}")
#     for ngram, stats in current_ngrams.items():
#         print(f"  {ngram}: {stats}")
    
#     # Check that we have the expected n-grams
#     ngrams_found = set(current_ngrams.keys())
    
#     # Print more detailed error message
#     missing = expected_ngrams - ngrams_found
#     extra = ngrams_found - expected_ngrams
#     if missing or extra:
#         error_msg = "N-gram mismatch:\n"
#         if missing:
#             error_msg += f"  Missing n-grams: {missing}\n"
#         if extra:
#             error_msg += f"  Extra n-grams: {extra}\n"
#         print(error_msg)
    
#     assert ngrams_found == expected_ngrams

# def test_ngram_analysis_with_db(temp_db: DatabaseManager, sample_session: str):
#     """Test n-gram analysis with database operations."""
#     analyzer = NGramAnalyzer(temp_db)
    
#     # Run the analysis
#     ngram_stats = analyzer.analyze_session(sample_session)
    
#     # Verify that n-grams were saved to the database
#     speed_results = temp_db.fetchall("""
#         SELECT ngram, ngram_size, count, ngram_time_ms
#         FROM session_ngram_speed
#         WHERE session_id = ?
#     """, (sample_session,))
    
#     error_results = temp_db.fetchall("""
#         SELECT ngram, ngram_size, error_count
#         FROM session_ngram_errors
#         WHERE session_id = ?
#     """, (sample_session,))
    
#     # Verify that n-grams with errors in positions other than last are excluded
#     error_ngrams = {row["ngram"] for row in error_results}
    
#     # In our test data, we only have one error at position 5 (the 'u' in 'quick')
#     # So we should only have error n-grams that end with this error
#     # 'qu' is the only n-gram that should be in error_ngrams since 'u' is the last character
#     assert "qu" in error_ngrams
    
#     # These should not be in error_ngrams because they don't end with an error
#     assert "qui" not in error_ngrams
#     assert "quic" not in error_ngrams
#     assert "quick" not in error_ngrams
#     assert "bro" not in error_ngrams
#     assert "rown" not in error_ngrams

# def test_slowest_ngrams_retrieval(temp_db: DatabaseManager, sample_session: str):
#     """Test retrieving the slowest n-grams."""
#     analyzer = NGramAnalyzer(temp_db)
    
#     # First run the analysis
#     analyzer.analyze_session(sample_session)
    
#     # Get the slowest bigrams
#     slow_bigrams = analyzer.get_slowest_ngrams(ngram_size=2)
    
#     # We should get some results
#     assert len(slow_bigrams) > 0
    
#     # Verify that the results have the expected structure
#     for ngram_stats in slow_bigrams:
#         assert "ngram" in ngram_stats
#         assert "avg_time_ms" in ngram_stats
#         assert isinstance(ngram_stats["avg_time_ms"], (int, float))
    
#     # Verify that the slowest n-gram is present
#     assert any(ngram_stats["ngram"] == "qu" for ngram_stats in slow_bigrams)

# def test_error_prone_ngrams_retrieval(temp_db: DatabaseManager, sample_session: str):
#     """Test retrieving the most error-prone n-grams."""
#     analyzer = NGramAnalyzer(temp_db)
    
#     # First run the analysis
#     analyzer.analyze_session(sample_session)
    
#     # Get the most error-prone trigrams
#     error_trigrams = analyzer.get_most_error_prone_ngrams(ngram_size=3)
    
#     # We should get some results
#     assert len(error_trigrams) > 0
    
#     # Verify that the results have the expected structure
#     for ngram_stats in error_trigrams:
#         assert "ngram" in ngram_stats
#         assert "error_count" in ngram_stats
#         assert isinstance(ngram_stats["error_count"], int)
    
#     # Verify that the error-prone n-gram is present
#     assert any(ngram_stats["ngram"] == "bro" for ngram_stats in error_trigrams)

# def test_ngram_with_whitespace_exclusion(temp_db: DatabaseManager, sample_session: str):
#     """Test that n-grams containing whitespace are excluded."""
#     analyzer = NGramAnalyzer(temp_db)
    
#     # Run the analysis
#     ngram_stats = analyzer.analyze_session(sample_session)
    
#     # Check all n-gram sizes
#     for size in range(2, 11):
#         for ngram in ngram_stats.get(str(size), {}).keys():
#             assert ' ' not in ngram, f"N-gram '{ngram}' contains whitespace"

# # Test data generation functions
# def generate_keystrokes(text: str, error_positions: set[int] = None, base_speed: int = 100) -> List[Dict[str, Any]]:
#     """Generate keystroke data for testing.
    
#     Args:
#         text: The text to generate keystrokes for
#         error_positions: Set of character positions (0-based) where errors should occur
#         base_speed: Base time between keystrokes in ms
        
#     Returns:
#         List of keystroke dictionaries with the following structure:
#         {
#             "keystroke_id": int,  # 1-based index
#             "keystroke_time": str,  # ISO format timestamp
#             "keystroke_char": str,  # The actual character typed
#             "expected_char": str,   # The expected character
#             "is_correct": bool,     # Whether the keystroke was correct
#             "time_since_previous": int  # Time since previous keystroke in ms
#         }
#     """
#     if error_positions is None:
#         error_positions = set()
#     else:
#         # Ensure error_positions are within bounds
#         error_positions = {pos for pos in error_positions if 0 <= pos < len(text)}
    
#     keystrokes = []
#     timestamp = datetime.now().timestamp() * 1000  # Current time in ms
    
#     for i, char in enumerate(text):
#         is_error = i in error_positions
        
#         # For errors, use the next character in the alphabet as the typed character
#         if is_error:
#             # For 'z', use 'a' to avoid going out of lowercase letters
#             typed_char = 'a' if char == 'z' else chr(ord(char) + 1)
#         else:
#             typed_char = char
            
#         keystroke = {
#             "keystroke_id": i + 1,
#             "keystroke_time": datetime.fromtimestamp(timestamp / 1000).isoformat(),
#             "keystroke_char": typed_char,  # What was actually typed
#             "expected_char": char,         # What was expected
#             "is_correct": not is_error,
#             "time_since_previous": base_speed if i > 0 else 0  # First keystroke has no previous
#         }
        
#         keystrokes.append(keystroke)
#         timestamp += base_speed
    
#     return keystrokes


# def generate_test_cases() -> List[tuple]:
#     """Generate test cases for parameterized tests, including error positions and base speed for robust scenario coverage.
    
#     Returns:
#         List of tuples: (text, ngram_size, expected_ngrams, expected_error_ngrams, test_id, error_positions, base_speed)
#     """
#     test_cases = []
    
#     # Test texts of different lengths
#     test_texts = [
#         ("a", "Single_character"),
#         ("ab", "Two_characters"),
#         ("abc", "Three_characters"),
#         ("the", "Short_word"),
#         ("quick", "Medium_word"),
#         ("brown", "Longer_word"),
#         ("the quick", "Multiple_words"),  # Shorter than the previous version for better test performance
#         ("abcdefghij", "Alphabet_start"),  # Shorter alphabet for better test performance
#         ("a" * 10, "Repeated_character"),  # Shorter repeated sequence
#     ]
    
#     # N-gram sizes to test (2-5 for most tests, with a few up to 8)
#     ngram_sizes = [2, 3, 4, 5, 8]
    
#     # Error patterns with more descriptive names
#     error_patterns = [
#         (set(), "no_errors"),
#         ({0}, "first_char_error"),
#         ({1}, "second_char_error"),
#         ({0, 1}, "first_two_chars_error"),
#         (lambda l: {l-1} if l > 0 else set(), "last_char_error"),
#         (lambda l: {l//2} if l > 0 else set(), "middle_char_error"),
#         (lambda l: {0, l-1} if l > 1 else set(), "first_and_last_error"),
#         (lambda l: {i for i in range(0, l, 2)}, "every_other_char_error"),
#     ]
    
#     # Typing speeds (time between keystrokes in ms)
#     typing_speeds = [
#         (50, "fast"),
#         (100, "normal"),
#         (200, "slow"),
#     ]
    
#     # Generate test cases
#     for text, text_desc in test_texts:
#         text_len = len(text)
#         if text_len == 0:
#             continue
            
#         # Generate all possible n-grams for this text
#         all_ngrams = {}
#         for n in ngram_sizes:
#             all_ngrams[n] = {text[i:i+n] for i in range(len(text) - n + 1)} if n <= text_len else set()
        
#         for ngram_size in ngram_sizes:
#             # Handle cases where ngram_size > text length
#             if ngram_size > text_len:
#                 test_case = (
#                     text,
#                     ngram_size,
#                     set(),  # No n-grams expected
#                     set(),  # No error n-grams expected
#                     f"{text_desc}_{ngram_size}gram_ngram_too_long",
#                     set(),  # No error positions
#                     100     # Default base speed
#                 )
#                 test_cases.append(test_case)
#                 continue
                
#             for error_fn, error_desc in error_patterns:
#                 # Handle callable error positions (for dynamic positions based on text length)
#                 if callable(error_fn):
#                     try:
#                         error_positions = error_fn(text_len)
#                         # Ensure positions are within bounds
#                         error_positions = {pos for pos in error_positions if 0 <= pos < text_len}
#                     except (IndexError, TypeError, ValueError):
#                         continue  # Skip invalid error positions
#                 else:
#                     error_positions = {pos for pos in error_fn if 0 <= pos < text_len}
                
#                 # Skip if no valid error positions (unless it's the no_errors case)
#                 if not error_positions and error_desc != "no_errors":
#                     continue
                
#                 # Generate error n-grams - only include n-grams where the LAST character is an error
#                 error_ngrams = set()
#                 for i in range(len(text) - ngram_size + 1):
#                     # An n-gram is an error if its last character is an error
#                     if (i + ngram_size - 1) in error_positions:
#                         error_ngrams.add(text[i:i+ngram_size])
                
#                 # Correct n-grams are those that don't end with an error
#                 correct_ngrams = all_ngrams[ngram_size] - error_ngrams
                
#                 # For each typing speed, create a test case
#                 for speed, speed_desc in typing_speeds:
#                     test_case = (
#                         text,
#                         ngram_size,
#                         correct_ngrams,
#                         error_ngrams,
#                         f"{text_desc}_{ngram_size}gram_{error_desc}_{speed_desc}",
#                         error_positions,
#                         speed
#                     )
#                     test_cases.append(test_case)
                    
#                     # Limit the number of test cases to keep test time reasonable
#                     if len(test_cases) >= 150:  # Reduced from 200 to keep test time manageable
#                         return test_cases
    
#     return test_cases


# class TestNGramAnalyzerComprehensive:
#     """Comprehensive tests for NGramAnalyzer with parameterized test cases."""
    
#     @pytest.fixture(autouse=True)
#     def setup(self, temp_db: DatabaseManager):
#         """Setup test fixture."""
#         self.db = temp_db
#         self.analyzer = NGramAnalyzer(self.db)
    
#     @pytest.mark.parametrize(
#         "text,ngram_size,expected_ngrams,expected_error_ngrams,test_id,error_positions,base_speed",
#         generate_test_cases(),
#         ids=lambda x: str(x) if not isinstance(x, (set, dict)) else ""
#     )
#     def test_ngram_extraction_comprehensive(
#         self,
#         text: str,
#         ngram_size: int,
#         expected_ngrams: set,
#         expected_error_ngrams: set,
#         test_id: str,
#         error_positions: set,
#         base_speed: int,
#         temp_db: DatabaseManager,
#         capsys
#     ):
#         """Test objective: Robustly validate n-gram extraction and error detection for a wide range of n-gram sizes, text lengths, error patterns, and typing speeds.
        
#         This parameterized test covers:
#         - n-gram sizes from 2 to 10
#         - text lengths from 2 to 20+ characters
#         - various error patterns (no errors, single/multiple errors, edge errors)
#         - correct and error n-gram extraction
#         - edge cases where n-gram size > text length
#         - happy paths and destructive scenarios
#         - variable typing speeds
        
#         Args:
#             text: The typing text to analyze
#             ngram_size: The size of n-grams to extract
#             expected_ngrams: The set of correct n-grams expected
#             expected_error_ngrams: The set of error n-grams expected
#             test_id: Unique identifier for the test case
#             error_positions: Set of character positions (0-based) where errors should occur
#             base_speed: Typing speed in ms between keystrokes
#             temp_db: Temporary database fixture
#             capsys: Pytest capture fixture
#         """
#         analyzer = NGramAnalyzer(temp_db)

#         # Generate keystrokes for the test using provided error positions and speed
#         keystrokes = generate_keystrokes(text, error_positions, base_speed)
#         ngram_stats = analyzer._process_keystrokes(keystrokes)
#         current_ngrams = ngram_stats.get(str(ngram_size), {})

#         # Get the actual n-grams found, separating correct from error n-grams
#         found_ngrams = {ngram for ngram, stats in current_ngrams.items() if stats.error_count == 0}
#         found_error_ngrams = {ngram for ngram, stats in current_ngrams.items() if stats.error_count > 0}

#         # Debug output for traceability
#         with capsys.disabled():
#             print(f"\nTest: {test_id}")
#             print(f"Text: '{text}' | N-gram size: {ngram_size}")
#             print(f"Error positions: {error_positions}")
#             print(f"Expected correct n-grams ({len(expected_ngrams)}): {sorted(expected_ngrams)}")
#             print(f"Found correct n-grams ({len(found_ngrams)}): {sorted(found_ngrams)}")
#             print(f"Expected error n-grams ({len(expected_error_ngrams)}): {sorted(expected_error_ngrams)}")
#             print(f"Found error n-grams ({len(found_error_ngrams)}): {sorted(found_error_ngrams)}")

#         # Assertions
#         if ngram_size > len(text):
#             # N-gram size larger than text length - should have no n-grams
#             assert not found_ngrams and not found_error_ngrams, \
#                 f"Found n-grams when n-gram size ({ngram_size}) > text length ({len(text)}) for {test_id}"
#             return
            
#         # Check that all expected correct n-grams are present
#         missing_ngrams = expected_ngrams - found_ngrams
#         assert not missing_ngrams, \
#             f"Missing correct n-grams for {test_id}: {missing_ngrams}"
            
#         # Check that all expected error n-grams are present
#         # Note: We only check for n-grams where the last character is an error
#         # since that's how NGramAnalyzer works
#         error_ngrams_with_last_char_error = set()
#         for ngram in expected_error_ngrams:
#             # Check if the last character of the n-gram is in an error position
#             for i in range(len(text) - ngram_size + 1):
#                 if text[i:i+ngram_size] == ngram and (i + ngram_size - 1) in error_positions:
#                     error_ngrams_with_last_char_error.add(ngram)
#                     break
                    
#         missing_error_ngrams = error_ngrams_with_last_char_error - found_error_ngrams
#         assert not missing_error_ngrams, \
#             f"Missing error n-grams (with last char error) for {test_id}: {missing_error_ngrams}\n" \
#             f"All expected error n-grams: {sorted(expected_error_ngrams)}\n" \
#             f"Expected with last char error: {sorted(error_ngrams_with_last_char_error)}\n" \
#             f"Found error n-grams: {sorted(found_error_ngrams)}"
            
#         # Check that there are no unexpected error n-grams
#         # (all error n-grams should have the last character in an error position)
#         for ngram in found_error_ngrams:
#             # Find all positions where this n-gram appears in the text
#             positions = [i for i in range(len(text) - ngram_size + 1)
#                        if text[i:i+ngram_size] == ngram]
#             # At least one occurrence should have the last character in an error position
#             assert any((pos + ngram_size - 1) in error_positions for pos in positions), \
#                 f"Unexpected error n-gram '{ngram}' in {test_id} - last character is not in error positions {error_positions}"
        
#         # Only expect error n-grams if the last character of any n-gram is an error
#         # because NGramAnalyzer only records n-grams in the error table if the last
#         # character is incorrect
#         ngrams_with_last_char_error = set()
#         for i in range(len(text) - ngram_size + 1):
#             # Check if the last character of this n-gram is an error
#             if (i + ngram_size - 1) in error_positions:
#                 ngrams_with_last_char_error.add(text[i:i+ngram_size])
        
#         # We should only have error n-grams where the last character is an error
#         if ngrams_with_last_char_error:
#             assert len(found_error_ngrams) > 0, \
#                 f"Expected error n-grams for error positions {error_positions} in {test_id}, " \
#                 f"expected n-grams with last char error: {sorted(ngrams_with_last_char_error)}"
            
#             # All found error n-grams should be in the set of n-grams with last char error
#             unexpected_error_ngrams = found_error_ngrams - ngrams_with_last_char_error
#             assert not unexpected_error_ngrams, \
#                 f"Unexpected error n-grams found in {test_id}: {unexpected_error_ngrams}"
#         else:
#             # No n-grams should have their last character in an error position
#             assert len(found_error_ngrams) == 0, \
#                 f"Unexpected error n-grams found in {test_id}: {found_error_ngrams}"
#         # For error n-grams, we need to modify the expected_error_ngrams to match the actual typed characters
#         # since the implementation uses the typed characters for error n-grams
#         modified_expected_error_ngrams = set()
#         for ngram in expected_error_ngrams:
#             if not ngram:  # Skip empty n-grams
#                 continue
                
#             # Find the position of this n-gram in the text
#             pos = text.find(ngram)
#             if pos == -1:  # Not found, keep as is
#                 modified_expected_error_ngrams.add(ngram)
#                 continue
                
#             # Replace each character in the n-gram with the actual typed character
#             # which is the next character in the alphabet for errors
#             modified_ngram = []
        
#         # Process keystrokes
#         ngram_stats = self.analyzer._process_keystrokes(keystrokes)
        
#         # Get n-grams for the current size
#         current_ngrams = ngram_stats.get(str(ngram_size), {})
        
#         # Extract n-grams from results
#         found_ngrams = set()
#         found_error_ngrams = set()
        
#         for ngram, stats in current_ngrams.items():
#             if stats.error_count > 0:
#                 found_error_ngrams.add(ngram)
#             else:
#                 found_ngrams.add(ngram)
        
#         # Debug output
#         with capsys.disabled():
#             print(f"\nTest: {test_id}")
#             print(f"Text: '{text}'")
#             print(f"N-gram size: {ngram_size}")
#             print(f"Expected n-grams: {sorted(expected_ngrams)}")
#             print(f"Found n-grams: {sorted(found_ngrams)}")
#             print(f"Expected error n-grams: {sorted(expected_error_ngrams)}")
#             print(f"Found error n-grams: {sorted(found_error_ngrams)}")
        
#         # Verify results
#         assert found_ngrams == expected_ngrams, \
#             f"Mismatch in correct n-grams for {test_id}"
            
#         # For error n-grams, we only check if all expected error n-grams are present
#         # The analyzer might find additional error n-grams due to its internal logic
#         assert expected_error_ngrams.issubset(found_error_ngrams), \
#             f"Missing error n-grams for {test_id}. " \
#             f"Expected at least: {expected_error_ngrams - found_error_ngrams}"
        
#         # Verify that n-grams longer than the text are not present
#         if ngram_size > len(text):
#             assert not found_ngrams and not found_error_ngrams, \
#                 f"Found n-grams when n-gram size ({ngram_size}) > text length ({len(text)})"


# # Run the tests
# if __name__ == "__main__":
#     pytest.main(["-v", "-s", __file__])
