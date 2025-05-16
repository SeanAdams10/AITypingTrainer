# """
# Refactored tests for the NGramAnalyzer class.

# These tests verify the functionality of the NGramAnalyzer class, including
# n-gram extraction, statistics calculation, and database operations.
# """
# from __future__ import annotations

# import os
# import sys
# import tempfile
# from datetime import datetime
# from typing import Any, Dict, List, Set

# import pytest
# from pytest_mock import MockerFixture

# # Add the project root to the Python path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# from db.database_manager import DatabaseManager
# from models.ngram_analyzer import NGramAnalyzer, NGramStats

# # Sample test data
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
    
#     # Initialize database without calling init_tables
#     db = DatabaseManager(db_path)
    
#     # Create practice_sessions table first (referenced by foreign keys)
#     db.execute("""
#         CREATE TABLE IF NOT EXISTS practice_sessions (
#             session_id TEXT PRIMARY KEY,
#             snippet_id INTEGER,
#             start_time TIMESTAMP,
#             end_time TIMESTAMP,
#             wpm REAL,
#             accuracy REAL,
#             error_count INTEGER,
#             total_keystrokes INTEGER
#         )
#     """)
    
#     # Create session_keystrokes table with foreign key reference
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
    
#     # practice_sessions table was already created at the beginning of the fixture
    
#     # Create n-gram tables if they don't exist
#     db.execute("""
#         CREATE TABLE IF NOT EXISTS session_ngram_speed (
#             session_id TEXT NOT NULL,
#             ngram_size INTEGER NOT NULL,
#             ngram TEXT NOT NULL,
#             ngram_time_ms REAL NOT NULL,
#             PRIMARY KEY (session_id, ngram_size, ngram),
#             FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
#         )
#     """)
    
#     db.execute("""
#         CREATE TABLE IF NOT EXISTS session_ngram_errors (
#             session_id TEXT NOT NULL,
#             ngram_size INTEGER NOT NULL,
#             ngram TEXT NOT NULL,
#             error_count INTEGER NOT NULL DEFAULT 1,
#             PRIMARY KEY (session_id, ngram_size, ngram),
#             FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
#         )
#     """)
    
#     yield db
    
#     # Clean up
#     db.close()
#     try:
#         os.unlink(db_path)
#     except OSError:
#         pass

# @pytest.fixture
# def sample_session(temp_db: DatabaseManager) -> str:
#     """Create a sample session with keystrokes for testing."""
#     # Create a test session
#     session_id = "test_session_123"
#     temp_db.execute(
#         """
#         INSERT INTO practice_sessions 
#         (session_id, snippet_id, start_time, end_time, wpm, accuracy, error_count, total_keystrokes)
#         VALUES (?, 1, ?, ?, 50.0, 95.0, 1, 16)
#         """,
#         (session_id, "2023-01-01 10:00:00", "2023-01-01 10:05:00")
#     )
    
#     # Add keystrokes with proper typing for n-gram analysis
#     # The sample text is "the quick brown" with an error on 'u' in 'quick'
#     keystroke_data = [
#         # First word: "the"
#         (session_id, "2023-01-01 10:00:00.000", "t", "t", 1, 0),
#         (session_id, "2023-01-01 10:00:00.100", "h", "h", 1, 100),
#         (session_id, "2023-01-01 10:00:00.200", "e", "e", 1, 100),
#         # Space after first word
#         (session_id, "2023-01-01 10:00:00.300", " ", " ", 1, 100),
#         # Second word: "quick" with an error on 'u'
#         (session_id, "2023-01-01 10:00:00.400", "q", "q", 1, 100),
#         (session_id, "2023-01-01 10:00:00.500", "x", "u", 0, 100),  # Error: typed 'x' instead of 'u'
#         (session_id, "2023-01-01 10:00:00.550", "u", "u", 1, 50),   # Corrected 'u'
#         (session_id, "2023-01-01 10:00:00.650", "i", "i", 1, 100),
#         (session_id, "2023-01-01 10:00:00.750", "c", "c", 1, 100),
#         (session_id, "2023-01-01 10:00:00.850", "k", "k", 1, 100),
#         # Space after second word
#         (session_id, "2023-01-01 10:00:00.950", " ", " ", 1, 100),
#         # Third word: "brown" (all correct)
#         (session_id, "2023-01-01 11:00:00.000", "b", "b", 1, 100),
#         (session_id, "2023-01-01 11:00:00.100", "r", "r", 1, 100),
#         (session_id, "2023-01-01 11:00:00.200", "o", "o", 1, 100),
#         (session_id, "2023-01-01 11:00:00.300", "w", "w", 1, 100),
#         (session_id, "2023-01-01 11:00:00.400", "n", "n", 1, 100),
#     ]
    
#     # Insert keystrokes one by one
#     for keystroke in keystroke_data:
#         temp_db.execute(
#             """
#             INSERT INTO session_keystrokes 
#             (session_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
#             VALUES (?, ?, ?, ?, ?, ?)
#             """,
#             keystroke
#         )
    
#     return session_id

# # Test NGramStats class
# def test_ngram_stats_calculation():
#     """Test NGramStats calculation methods."""
#     # Test with count and total_time_ms
#     stats = NGramStats("test", 4, count=5, total_time_ms=1000.0)
#     assert stats.avg_time_ms == 200.0
#     assert not stats.is_error
    
#     # Test with error_count
#     error_stats = NGramStats("test", 4, error_count=1)
#     assert error_stats.is_error

# # Test NGramAnalyzer initialization
# def test_ngram_analyzer_initialization(temp_db: DatabaseManager):
#     """Test that NGramAnalyzer initializes correctly."""
#     analyzer = NGramAnalyzer(temp_db)
#     assert analyzer is not None

# # Test n-gram extraction with different n-gram sizes
# def test_ngram_extraction_size_2(temp_db: DatabaseManager, sample_session: str):
#     """Test extraction of 2-grams from sample session."""
#     # First, verify the test data is in the database
#     keystrokes = temp_db.fetchall(
#         "SELECT keystroke_char, expected_char, is_correct FROM session_keystrokes WHERE session_id = ? ORDER BY keystroke_time",
#         (sample_session,)
#     )
#     print("\nKeystrokes in database:")
#     for i, ks in enumerate(keystrokes):
#         print(f"  {i+1}. Char: '{ks['keystroke_char']}', Expected: '{ks['expected_char']}', Correct: {bool(ks['is_correct'])}")
    
#     analyzer = NGramAnalyzer(temp_db)
#     ngram_stats = analyzer.analyze_session(sample_session)
    
#     print("\nN-gram stats:", ngram_stats)
    
#     # Check that we have stats for ngram_size=2
#     assert 2 in ngram_stats, f"No 2-grams found in {ngram_stats.keys()}"
    
#     # Check specific 2-grams that should be present
#     expected_2grams = {"th", "he", "qu", "ui", "ic", "ck", "br", "ro", "ow", "wn"}
#     print("\nExpected 2-grams:", expected_2grams)
    
#     # Get the actual 2-grams that were found
#     found_2grams = set(ngram_stats.get(2, {}).keys())
#     print("Found 2-grams:", found_2grams)
    
#     # Check which expected 2-grams are missing
#     missing = expected_2grams - found_2grams
#     if missing:
#         print("\nMissing 2-grams:", missing)
    
#     # Check which unexpected 2-grams were found
#     unexpected = found_2grams - expected_2grams
#     if unexpected:
#         print("Unexpected 2-grams:", unexpected)
    
#     # Verify all expected 2-grams are present
#     for ngram in expected_2grams:
#         assert ngram in ngram_stats[2], f"2-gram '{ngram}' not found in {list(ngram_stats[2].keys())}"
#         assert ngram_stats[2][ngram].count >= 1, f"2-gram '{ngram}' has count {ngram_stats[2][ngram].count} (expected >=1)"

# def test_ngram_extraction_size_3(temp_db: DatabaseManager, sample_session: str):
#     """Test extraction of 3-grams from sample session."""
#     analyzer = NGramAnalyzer(temp_db)
#     ngram_stats = analyzer.analyze_session(sample_session)
    
#     # Check that we have stats for ngram_size=3
#     assert 3 in ngram_stats
    
#     # Check specific 3-grams that should be present
#     expected_3grams = {"the", "qui", "uic", "ick", "bro", "row", "own"}
#     for ngram in expected_3grams:
#         assert ngram in ngram_stats[3]
#         assert ngram_stats[3][ngram].count >= 1

# def test_ngram_extraction_size_4(temp_db: DatabaseManager, sample_session: str):
#     """Test extraction of 4-grams from sample session."""
#     analyzer = NGramAnalyzer(temp_db)
#     ngram_stats = analyzer.analyze_session(sample_session)
    
#     # Check that we have stats for ngram_size=4
#     assert 4 in ngram_stats
    
#     # Check specific 4-grams that should be present
#     expected_4grams = {"quic", "uick", "brow", "rown"}
#     for ngram in expected_4grams:
#         assert ngram in ngram_stats[4]
#         assert ngram_stats[4][ngram].count >= 1

# # Test error handling in n-gram extraction
# def test_ngram_with_error_at_end(temp_db: DatabaseManager, sample_session: str):
#     """Test that n-grams with error at the end are recorded in error table."""
#     analyzer = NGramAnalyzer(temp_db)
#     analyzer.analyze_session(sample_session)
    
#     # Check that the error n-gram is recorded in the error table
#     error_ngrams = temp_db.fetch_all(
#         "SELECT ngram, error_count FROM session_ngram_errors WHERE session_id = ? AND ngram_size = 2",
#         (sample_session,)
#     )
    
#     # The 'xu' bigram should be recorded as an error (from 'x' typed instead of 'u' in 'quick')
#     assert any(ngram[0] == 'xu' and ngram[1] >= 1 for ngram in error_ngrams)

# # Test whitespace exclusion
# def test_ngram_with_whitespace_exclusion(temp_db: DatabaseManager, sample_session: str):
#     """Test that n-grams containing whitespace are excluded."""
#     analyzer = NGramAnalyzer(temp_db)
#     ngram_stats = analyzer.analyze_session(sample_session)
    
#     # Check that no n-grams contain whitespace
#     for ngram_size, ngrams in ngram_stats.items():
#         for ngram in ngrams:
#             assert ' ' not in ngram, f"N-gram '{ngram}' contains whitespace"

# # Test database operations
# def test_ngram_analysis_with_db(temp_db: DatabaseManager, sample_session: str):
#     """Test n-gram analysis with database operations."""
#     analyzer = NGramAnalyzer(temp_db)
#     ngram_stats = analyzer.analyze_session(sample_session)
    
#     # Check that n-gram stats were saved to the database
#     for ngram_size, ngrams in ngram_stats.items():
#         for ngram, stats in ngrams.items():
#             if stats.is_error:
#                 # Check error n-grams in session_ngram_errors
#                 result = temp_db.fetch_one(
#                     "SELECT error_count FROM session_ngram_errors "
#                     "WHERE session_id = ? AND ngram_size = ? AND ngram = ?",
#                     (sample_session, ngram_size, ngram)
#                 )
#                 assert result is not None
#                 assert result[0] == stats.error_count
#             else:
#                 # Check speed n-grams in session_ngram_speed
#                 result = temp_db.fetch_one(
#                     "SELECT ngram_time_ms FROM session_ngram_speed "
#                     "WHERE session_id = ? AND ngram_size = ? AND ngram = ?",
#                     (sample_session, ngram_size, ngram)
#                 )
#                 assert result is not None
#                 assert abs(result[0] - stats.avg_time_ms) < 0.001

# # Test retrieving slowest n-grams
# def test_slowest_ngrams_retrieval(temp_db: DatabaseManager, sample_session: str):
#     """Test retrieving the slowest n-grams."""
#     analyzer = NGramAnalyzer(temp_db)
#     analyzer.analyze_session(sample_session)
    
#     # Get the slowest 2-grams
#     slowest = analyzer.get_slowest_ngrams(sample_session, ngram_size=2, limit=5)
    
#     # Should return a list of tuples (ngram, avg_time_ms)
#     assert isinstance(slowest, list)
#     assert all(isinstance(item, tuple) and len(item) == 2 for item in slowest)
    
#     # The list should be sorted by average time in descending order
#     assert all(slowest[i][1] >= slowest[i+1][1] for i in range(len(slowest)-1))

# # Test retrieving most error-prone n-grams
# def test_error_prone_ngrams_retrieval(temp_db: DatabaseManager, sample_session: str):
#     """Test retrieving the most error-prone n-grams."""
#     analyzer = NGramAnalyzer(temp_db)
#     analyzer.analyze_session(sample_session)
    
#     # Get the most error-prone 2-grams
#     error_prone = analyzer.get_most_error_prone_ngrams(sample_session, ngram_size=2, limit=5)
    
#     # Should return a list of tuples (ngram, error_count)
#     assert isinstance(error_prone, list)
#     assert all(isinstance(item, tuple) and len(item) == 2 for item in error_prone)
    
#     # The list should be sorted by error count in descending order
#     assert all(error_prone[i][1] >= error_prone[i+1][1] for i in range(len(error_prone)-1))

# # Test with empty session
# def test_empty_session(temp_db: DatabaseManager):
#     """Test analysis with an empty session (no keystrokes)."""
#     # Create an empty session
#     session_id = "empty_session_123"
#     temp_db.execute(
#         """
#         INSERT INTO practice_sessions 
#         (session_id, snippet_id, start_time, end_time, wpm, accuracy, error_count, total_keystrokes)
#         VALUES (?, 1, ?, ?, 0.0, 0.0, 0, 0)
#         """,
#         (session_id, "2023-01-01 12:00:00", "2023-01-01 12:01:00")
#     )
    
#     analyzer = NGramAnalyzer(temp_db)
#     ngram_stats = analyzer.analyze_session(session_id)
    
#     # Should return an empty dictionary for empty session
#     assert ngram_stats == {}

# # Test with single character session
# def test_single_character_session(temp_db: DatabaseManager):
#     """Test analysis with a session containing only one character."""
#     session_id = "single_char_session_123"
#     temp_db.execute(
#         """
#         INSERT INTO practice_sessions 
#         (session_id, snippet_id, start_time, end_time, wpm, accuracy, error_count, total_keystrokes)
#         VALUES (?, 1, ?, ?, 60.0, 100.0, 0, 1)
#         """,
#         (session_id, "2023-01-01 12:00:00", "2023-01-01 12:01:00")
#     )
    
#     # Add a single keystroke
#     temp_db.execute(
#         """
#         INSERT INTO session_keystrokes 
#         (session_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
#         VALUES (?, ?, ?, ?, ?, ?)
#         """,
#         (session_id, "2023-01-01 12:00:00.500", "a", "a", True, 0)
#     )
    
#     analyzer = NGramAnalyzer(temp_db)
#     ngram_stats = analyzer.analyze_session(session_id)
    
#     # Should return an empty dictionary since n-grams require at least 2 characters
#     assert ngram_stats == {}

# # Test with very short session (2 characters)
# def test_two_character_session(temp_db: DatabaseManager):
#     """Test analysis with a session containing exactly two characters."""
#     session_id = "two_char_session_123"
#     temp_db.execute(
#         """
#         INSERT INTO practice_sessions 
#         (session_id, snippet_id, start_time, end_time, wpm, accuracy, error_count, total_keystrokes)
#         VALUES (?, 1, ?, ?, 60.0, 100.0, 0, 2)
#         """,
#         (session_id, "2023-01-01 12:00:00", "2023-01-01 12:01:00")
#     )
    
#     # Add two keystrokes
#     temp_db.execute(
#         """
#         INSERT INTO session_keystrokes 
#         (session_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
#         VALUES (?, ?, ?, ?, ?, ?)
#         """,
#         (session_id, "2023-01-01 12:00:00.500", "a", "a", True, 0)
#     )
#     temp_db.execute(
#         """
#         INSERT INTO session_keystrokes 
#         (session_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
#         VALUES (?, ?, ?, ?, ?, ?)
#         """,
#         (session_id, "2023-01-01 12:00:00.600", "b", "b", True, 100)
#     )
    
#     analyzer = NGramAnalyzer(temp_db)
#     ngram_stats = analyzer.analyze_session(session_id)
    
#     # Should return stats for n-gram size 2 only
#     assert set(ngram_stats.keys()) == {2}
#     assert "ab" in ngram_stats[2]
#     assert ngram_stats[2]["ab"].count == 1
#     assert abs(ngram_stats[2]["ab"].avg_time_ms - 100.0) < 0.001

# # Run the tests
# if __name__ == "__main__":
#     pytest.main(["-v", "-s", __file__])
