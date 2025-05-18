"""
Tests for the NGramAnalyzer class.

These tests verify the functionality of the NGramAnalyzer class, including
n-gram extraction, statistics calculation, and database operations.
"""
from __future__ import annotations

import os
import tempfile
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import sqlite3
from pytest_mock import MockerFixture

# Add project root to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke
from models.ngram_analyzer import NGramAnalyzer, NGram
from models.ngram_stats import NGramStats

# Sample keystroke data for testing
SAMPLE_KEYSTROKES = [
    {"keystroke_id": 1, "keystroke_time": 1672570800.000, "keystroke_char": "t", "expected_char": "t", "is_correct": True, "time_since_previous": 0},
    {"keystroke_id": 2, "keystroke_time": 1672570800.100, "keystroke_char": "h", "expected_char": "h", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 3, "keystroke_time": 1672570800.200, "keystroke_char": "e", "expected_char": "e", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 4, "keystroke_time": 1672570800.300, "keystroke_char": " ", "expected_char": " ", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 5, "keystroke_time": 1672570800.400, "keystroke_char": "q", "expected_char": "q", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 6, "keystroke_time": 1672570800.500, "keystroke_char": "x", "expected_char": "u", "is_correct": False, "time_since_previous": 100},
    {"keystroke_id": 7, "keystroke_time": 1672570800.600, "keystroke_char": "i", "expected_char": "i", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 8, "keystroke_time": 1672570800.700, "keystroke_char": "c", "expected_char": "c", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 9, "keystroke_time": 1672570800.800, "keystroke_char": "k", "expected_char": "k", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 10, "keystroke_time": 1672570800.900, "keystroke_char": " ", "expected_char": " ", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 11, "keystroke_time": 1672570801.000, "keystroke_char": "b", "expected_char": "b", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 12, "keystroke_time": 1672570801.100, "keystroke_char": "r", "expected_char": "r", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 13, "keystroke_time": 1672570801.200, "keystroke_char": "o", "expected_char": "o", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 14, "keystroke_time": 1672570801.300, "keystroke_char": "w", "expected_char": "w", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 15, "keystroke_time": 1672570801.400, "keystroke_char": "n", "expected_char": "n", "is_correct": True, "time_since_previous": 100},
]

# Fixtures

@pytest.fixture
def temp_db() -> DatabaseManager:
    """Create a temporary database for testing.
    
    Test objective: Provide a temporary, isolated database for testing
    that matches the schema expected by the application.
    
    Yields:
        DatabaseManager: A database manager connected to an in-memory SQLite database
    """
    # Create an in-memory database for testing
    db = DatabaseManager(":memory:")
    
    # Initialize database with all required tables - this creates the official schema
    db.init_tables()
    
    # Create any indexes needed for test performance
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_keystrokes_session_test ON session_keystrokes(session_id)
    """)
    
    yield db
    
    # Cleanup - in-memory database will be discarded automatically
    db.close()


@pytest.fixture
def sample_session(temp_db: DatabaseManager) -> str:
    """Create a sample session with keystrokes for testing.
    
    Test objective: Provide a sample practice session with realistic keystrokes
    that can be used for testing n-gram analysis functionality.
    
    Args:
        temp_db: Database manager fixture
        
    Returns:
        str: The session ID of the created session
    """
    session_id = "test_session_123"
    content = "the quick brown"
    start_time = "2023-01-01T10:00:00.000"
    end_time = "2023-01-01T10:00:01.400"
    total_time = 1.4
    total_keystrokes = 15
    correct_keystrokes = 14  # One error in 'quick' (x instead of u)
    accuracy = (correct_keystrokes / total_keystrokes) * 100
    
    # First, ensure we have a category and snippet
    temp_db.execute("""
        INSERT OR IGNORE INTO categories (category_id, category_name)
        VALUES (1, 'test_category')
    """, commit=True)
    
    temp_db.execute("""
        INSERT OR IGNORE INTO snippets (snippet_id, category_id, snippet_name)
        VALUES (1, 1, 'test_snippet')
    """, commit=True)
    
    # Insert session with all required fields according to the schema defined in init_tables
    temp_db.execute(
        """
        INSERT INTO practice_sessions (
            session_id, snippet_id, content, start_time, end_time, 
            total_time, session_wpm, session_cpm, expected_chars, 
            actual_chars, errors, efficiency, correctness, accuracy,
            snippet_index_start, snippet_index_end
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id, 1, content, start_time, end_time,
            total_time, 60.0, 300.0,  # total_time, session_wpm, session_cpm
            total_keystrokes, total_keystrokes,  # expected_chars, actual_chars
            1, 0.95, 0.95, accuracy,  # errors, efficiency, correctness, accuracy
            0, len(content)  # snippet_index_start, snippet_index_end
        ),
        commit=True
    )
    
    # Insert keystrokes
    for i, ks in enumerate(SAMPLE_KEYSTROKES):
        temp_db.execute(
            """
            INSERT INTO session_keystrokes (
                session_id, keystroke_id, keystroke_time, keystroke_char,
                expected_char, is_correct, time_since_previous
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id, i+1, ks["keystroke_time"],
                ks["keystroke_char"], ks["expected_char"],
                ks["is_correct"], ks["time_since_previous"]
            ),
            commit=True
        )
    
    return session_id


@pytest.fixture
def ngram_analyzer_fixture(temp_db: DatabaseManager, sample_session: str) -> NGramAnalyzer:
    """Create an NGramAnalyzer instance with test data.
    
    Test objective: Provide a preconfigured NGramAnalyzer instance with
    test session data loaded for testing analysis methods.
    
    Args:
        temp_db: Database manager fixture
        sample_session: Sample session ID fixture
        
    Returns:
        NGramAnalyzer: Configured NGramAnalyzer instance
    """
    # Load the practice session from the database
    session_row = temp_db.fetch_one(
        "SELECT * FROM practice_sessions WHERE session_id = ?",
        (sample_session,)
    )
    
    if not session_row:
        pytest.fail(f"Could not find practice session with ID: {sample_session}")
    
    # Create PracticeSession object
    from models.practice_session import PracticeSession
    practice_session = PracticeSession(
        session_id=session_row["session_id"],
        snippet_id=session_row["snippet_id"],
        start_time=datetime.fromisoformat(session_row["start_time"]) if isinstance(session_row["start_time"], str) else session_row["start_time"],
        end_time=datetime.fromisoformat(session_row["end_time"]) if isinstance(session_row["end_time"], str) else session_row["end_time"],
        wpm=session_row["wpm"],
        accuracy=session_row["accuracy"],
        error_count=session_row["error_count"],
        total_keystrokes=session_row["total_keystrokes"]
    )
    
    # Load keystrokes from the database
    keystroke_rows = temp_db.fetch_all(
        """SELECT * FROM session_keystrokes 
        WHERE session_id = ? 
        ORDER BY keystroke_time""",
        (sample_session,)
    )
    
    # Convert to Keystroke objects
    keystrokes = []
    for row in keystroke_rows:
        keystroke = Keystroke(
            keystroke_id=row["keystroke_id"],
            session_id=row["session_id"],
            keystroke_time=datetime.fromisoformat(row["keystroke_time"]) if isinstance(row["keystroke_time"], str) else row["keystroke_time"],
            keystroke_char=row["keystroke_char"],
            expected_char=row["expected_char"],
            is_correct=bool(row["is_correct"]),
            error_type=row.get("error_type"),  # Handle potential missing column
            time_since_previous=row["time_since_previous"]
        )
        keystrokes.append(keystroke)
    
    # Initialize analyzer with the correct constructor parameters
    analyzer = NGramAnalyzer(practice_session, keystrokes, temp_db)
    
    # Analyze the keystrokes
    analyzer.analyze()
    
    return analyzer


# Helper functions

def create_test_keystrokes(text: str, is_error: bool = False) -> List[Dict[str, Any]]:
    """Helper function to create test keystrokes.
    
    Args:
        text: The text to create keystrokes for
        is_error: If True, all keystrokes will be marked as errors
        
    Returns:
        List of keystroke dictionaries
    """
    keystrokes = []
    timestamp = datetime.now().timestamp() * 1000  # Current time in ms
    
    for i, char in enumerate(text):
        keystroke = {
            "keystroke_id": i + 1,
            "keystroke_time": datetime.fromtimestamp(timestamp / 1000).isoformat(),
            "keystroke_char": char,
            "expected_char": char if not is_error else chr(ord(char) + 1),  # Next character for errors
            "is_correct": not is_error,
            "time_since_previous": 0 if i == 0 else 100  # 100ms between keystrokes
        }
        keystrokes.append(keystroke)
        timestamp += 100  # Add 100ms for next keystroke
    
    return keystrokes

# Test Classes

class TestNGramAnalyzer:
    """Test the NGramAnalyzer class."""
    
    def test_load_from_database(self, temp_db: DatabaseManager, sample_session: str):
        """Test loading session data from the database.
        
        Test objective: Verify that NGramAnalyzer can load session and keystroke data
        from the database correctly using the static _load_keystrokes_for_session method.
        """
        # Load session from database
        from models.practice_session import PracticeSessionManager
        session_manager = PracticeSessionManager(temp_db)
        practice_session = session_manager.get_session_by_id(sample_session)
        
        assert practice_session is not None, "Failed to load practice session from database"
        assert practice_session.session_id == sample_session, "Session ID doesn't match"
        
        # Load keystrokes using the static method
        keystrokes = NGramAnalyzer._load_keystrokes_for_session(sample_session, temp_db)
        
        # Verify keystroke data was loaded
        assert keystrokes is not None, "Keystrokes were not loaded properly"
        assert isinstance(keystrokes, list), "Keystrokes is not a list"
        assert len(keystrokes) > 0, "No keystrokes were loaded"
        assert all(isinstance(k, Keystroke) for k in keystrokes), \
               "Not all keystrokes are Keystroke objects"
               
        # Verify we can create a NGramAnalyzer with this data
        analyzer = NGramAnalyzer(practice_session, keystrokes, temp_db)
        assert analyzer is not None, "Failed to create NGramAnalyzer with loaded data"
    
    def test_analyze_method(self, ngram_analyzer_fixture: NGramAnalyzer):
        """Test objective: Verify the analyze method processes keystrokes correctly."""
        analyzer = ngram_analyzer_fixture
        
        # Analyze with n-gram sizes 2 and 3
        analyzer.analyze(min_size=2, max_size=3)
        
        # Verify that n-grams were generated
        assert hasattr(analyzer, "speed_ngrams"), "No speed_ngrams attribute found"
        assert hasattr(analyzer, "error_ngrams"), "No error_ngrams attribute found"
        
        # Check that n-grams were generated for sizes 2 and 3
        assert 2 in analyzer.speed_ngrams.keys(), "No clean bigrams generated"
        assert 3 in analyzer.speed_ngrams.keys(), "No clean trigrams generated"
        
        # Check that some n-grams were extracted (either clean or error)
        # Note: There might not be any error n-grams if the test data has no errors
        assert (len(analyzer.speed_ngrams[2]) > 0 or len(analyzer.error_ngrams.get(2, {})) > 0), \
               "No bigrams extracted"
        assert (len(analyzer.speed_ngrams[3]) > 0 or len(analyzer.error_ngrams.get(3, {})) > 0), \
               "No trigrams extracted"
        
        # Check n-gram contents for clean n-grams
        for size, size_ngrams in analyzer.speed_ngrams.items():
            for text, ngram in size_ngrams.items():
                # Every n-gram should be an instance of NGram
                assert isinstance(ngram, NGram), f"Item {ngram} is not an NGram object"
                
                # Make sure properties make sense
                assert isinstance(text, str), "N-gram text is not a string"
                assert len(text) == size, f"N-gram '{text}' length doesn't match size {size}"
                assert ngram.total_time_ms >= 0, "Negative total time"
                
                # Clean n-grams shouldn't have errors
                assert ngram.is_clean, "Item in speed_ngrams should be a clean n-gram"
                assert not ngram.error_on_last, "Clean n-gram shouldn't have error on last character"
                assert not ngram.other_errors, "Clean n-gram shouldn't have other errors"
        
        # Save to database
        success = analyzer.save_to_database()
        assert success, "Failed to save n-grams to database"
        
    def test_save_to_database(self, temp_db: DatabaseManager, sample_session: str):
        """Test objective: Verify that analysis results are saved to the database."""
        # Initialize and analyze
        analyzer = NGramAnalyzer(sample_session, temp_db)
        analyzer.analyze(min_size=2, max_size=3)
        
        # Add some error n-grams
        if 2 in analyzer.error_ngrams:
            analyzer.error_ngrams[2]["qu"].has_error_on_last = True
        if 3 in analyzer.error_ngrams:
            analyzer.error_ngrams[3]["qui"].has_error_on_last = True
        
        # Save to database
        success = analyzer.save_to_database()
        assert success, "Failed to save n-grams to database"
        
        # Verify data was saved to speed table (only clean n-grams)
        speed_results = temp_db.fetchall(
            "SELECT ngram_size, ngram, ngram_time_ms FROM session_ngram_speed WHERE session_id = ? ORDER BY ngram_size, ngram",
            (sample_session,)
        )
        
        # Should have at least some clean n-grams
        assert len(speed_results) > 0, "No clean n-grams were saved to the database"
        
        # Verify data was saved to errors table
        error_results = temp_db.fetchall(
            "SELECT ngram_size, ngram, error_count FROM session_ngram_errors WHERE session_id = ? ORDER BY ngram_size, ngram",
            (sample_session,)
        )
        
        # Should have our error n-grams
        assert len(error_results) >= 2, "Expected at least 2 error n-grams"
        
        # Check that our specific error n-grams are there
        error_ngrams = {(r["ngram_size"], r["ngram"]) for r in error_results}
        assert (2, "qu") in error_ngrams, "Missing 'qu' error bigram"
        assert (3, "qui") in error_ngrams, "Missing 'qui' error trigram"
    
    def test_analyze_session_ngrams(self, temp_db: DatabaseManager, sample_session: str):
        """Test objective: Verify the analyze_session_ngrams method."""
        analyzer = NGramAnalyzer(sample_session, temp_db)
        
        # Analyze the session
        result = analyzer.analyze_session_ngrams(sample_session, min_size=2, max_size=3)
        
        # Should return a dictionary with n-gram stats
        assert isinstance(result, dict), "analyze_session_ngrams should return a dictionary"
        assert 2 in result, "Missing bigram stats"
        assert 3 in result, "Missing trigram stats"
        
        # Should have some n-grams
        assert len(result[2]) > 0, "No bigrams were analyzed"
        assert len(result[3]) > 0, "No trigrams were analyzed"
        
        # Check that the data was saved to the database
        speed_count = temp_db.fetchone(
            "SELECT COUNT(*) as count FROM session_ngram_speed WHERE session_id = ?",
            (sample_session,)
        )["count"]
        
        error_count = temp_db.fetchone(
            "SELECT COUNT(*) as count FROM session_ngram_errors WHERE session_id = ?",
            (sample_session,)
        )["count"]
        
        assert speed_count > 0, "No n-gram speed data was saved"
        assert error_count > 0, "No n-gram error data was saved"
    
    def test_get_slowest_ngrams(self, ngram_analyzer_fixture: NGramAnalyzer):
        """Test objective: Verify retrieval of slowest n-grams."""
        analyzer = ngram_analyzer_fixture
        
        # First analyze the data
        analyzer.analyze(min_size=2, max_size=3)
        
        # Get the slowest n-grams
        slowest = analyzer.get_slowest_ngrams(ngram_size=2, limit=5)
        
        # Should return a list of dictionaries
        assert isinstance(slowest, list), "Expected a list of n-grams"
        
        # Should have some results (may be fewer than limit)
        assert len(slowest) > 0, "No slow n-grams found"
        
        # Each item should have the expected keys
        for item in slowest:
            assert "ngram" in item, "Missing 'ngram' key"
            assert "avg_speed" in item, "Missing 'avg_speed' key"
            assert "total_occurrences" in item, "Missing 'total_occurrences' key"
    
    def test_get_most_error_prone_ngrams(self, ngram_analyzer_fixture: NGramAnalyzer):
        """Test objective: Verify retrieval of most error-prone n-grams."""
        analyzer = ngram_analyzer_fixture
        
        # First analyze the data
        analyzer.analyze(min_size=2, max_size=3)
        
        # Add some errors for testing
        if "qu" in analyzer.ngrams[2]:
            analyzer.ngrams[2]["qu"].has_error_on_last = True
        if "ui" in analyzer.ngrams[2]:
            analyzer.ngrams[2]["ui"].has_error_on_last = True
        
        # Save to update the database
        analyzer.save_to_database()
        
        # Get the most error-prone n-grams
        error_prone = analyzer.get_most_error_prone_ngrams(ngram_size=2, limit=5)
        
        # Should return a list of dictionaries
        assert isinstance(error_prone, list), "Expected a list of n-grams"
        
        # Should have some results (may be fewer than limit)
        assert len(error_prone) > 0, "No error-prone n-grams found"
        
        # Each item should have the expected keys
        for item in error_prone:
            assert "ngram" in item, "Missing 'ngram' key"
            assert "error_count" in item, "Missing 'error_count' key"
            assert "total_occurrences" in item, "Missing 'total_occurrences' key"


# Test running
if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))

def test_database_schema(temp_db: DatabaseManager, sample_session: str):
    """Test that the database schema is correct."""
    # Get the database path from the DatabaseManager
    db_path = temp_db.db_path
    
    # Connect directly to the SQLite database
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get the schema for the session_keystrokes table
        cursor.execute("PRAGMA table_info(session_keystrokes);")
        schema = cursor.fetchall()
        
        print("\nSession_keystrokes table schema:")
        for column in schema:
            print(f"Column: {column[1]}, Type: {column[2]}, Not Null: {column[3]}, Default: {column[4]}, PK: {column[5]}")
        
        # Get all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("\nTables in database:")
        for table in tables:
            print(f"- {table[0]}")
        
        # Get the data from session_keystrokes
        cursor.execute("SELECT * FROM session_keystrokes WHERE session_id = ?", (sample_session,))
        keystrokes = cursor.fetchall()
        
        print(f"\nKeystrokes in session {sample_session} (first 5):")
        for i, row in enumerate(keystrokes[:5]):  # Print first 5 keystrokes
            print(f"Keystroke {i+1}: {row}")
        
        # Get column names from schema
        column_names = [col[1] for col in schema]
        print(f"\nColumn names: {column_names}")
        
        # Verify the schema has the expected columns
        expected_columns = {'session_id', 'keystroke_id', 'keystroke_time', 'keystroke_char', 
                          'expected_char', 'is_correct', 'time_since_previous'}
        actual_columns = set(column_names)
        
        print(f"\nExpected columns: {expected_columns}")
        print(f"Actual columns: {actual_columns}")
        
        # Check for missing columns
        missing_columns = expected_columns - actual_columns
        assert not missing_columns, f"Missing columns in session_keystrokes: {missing_columns}"
        
        # Check for extra columns (wpm and accuracy should be removed)
        extra_columns = actual_columns - expected_columns
        print(f"Extra columns: {extra_columns}")
        
        assert 'wpm' not in actual_columns, "wpm column still exists in session_keystrokes"
        assert 'accuracy' not in actual_columns, "accuracy column still exists in session_keystrokes"
        
    finally:
        conn.close()

# Tests
def test_count_error_ngrams(ngram_analyzer: NGramAnalyzer):
    """Test counting error n-grams.
    
    Test objective: Verify that the count_error_ngrams method correctly identifies
    and counts n-grams with errors.
    """
    # Analyze keystrokes to generate n-grams
    assert ngram_analyzer.analyze(min_size=2, max_size=3), "Failed to analyze n-grams"
    
    # Count error n-grams for bigrams
    error_ngrams = ngram_analyzer.count_error_ngrams(2)
    
    # We should have at least one error n-gram based on our test data
    assert len(error_ngrams) > 0, "Expected at least one error n-gram"
    
    # Verify the structure of the returned data
    for error_ngram in error_ngrams:
        assert "ngram" in error_ngram, "Missing 'ngram' key in error n-gram data"
        assert "error_count" in error_ngram, "Missing 'error_count' key in error n-gram data"
        assert isinstance(error_ngram["ngram"], str), "N-gram should be a string"
        assert isinstance(error_ngram["error_count"], int), "Error count should be an integer"
        assert error_ngram["error_count"] > 0, "Error count should be greater than 0"

def test_get_ngrams(ngram_analyzer: NGramAnalyzer):
    """Test retrieving n-grams as NGram objects.
    
    Test objective: Verify that the get_ngrams method returns NGram objects with the
    correct structure and properties.
    """
    # Analyze with n-gram sizes 2 and 3
    ngram_analyzer.analyze(min_size=2, max_size=3)
    
    # Get all bigrams as NGram objects
    bigrams = ngram_analyzer.get_ngrams(2)
    
    # We should find several bigrams
    assert len(bigrams) > 0, "Expected to find several bigrams"
    
    # Verify the structure of the returned NGram objects
    for ngram in bigrams:
        assert isinstance(ngram, NGram), f"Expected NGram object, got {type(ngram)}"
        assert hasattr(ngram, "ngram"), "NGram missing 'ngram' attribute"
        assert hasattr(ngram, "ngram_size"), "NGram missing 'ngram_size' attribute"
        assert hasattr(ngram, "total_time_ms"), "NGram missing 'total_time_ms' attribute"
        assert hasattr(ngram, "has_error_on_last"), "NGram missing 'has_error_on_last' attribute"
        assert hasattr(ngram, "has_other_errors"), "NGram missing 'has_other_errors' attribute"
        
        # Verify the values
        assert isinstance(ngram.ngram, str), "NGram.ngram should be a string"
        assert isinstance(ngram.ngram_size, int), "NGram.ngram_size should be an integer"
        assert ngram.ngram_size == 2, "NGram size should be 2"

def test_ngram_analysis_with_different_sizes(ngram_analyzer: NGramAnalyzer):
    """Test n-gram analysis with different n-gram sizes.
    
    Test objective: Verify that the analyzer can process different n-gram sizes
    and that it correctly generates n-grams for each size.
    """
    # Test with different n-gram sizes
    for size in [2, 3]:
        # Reset for each size to ensure clean analysis
        assert ngram_analyzer.analyze(min_size=size, max_size=size), \
            f"Failed to analyze n-grams of size {size}"
        
        # Verify n-grams were created for this size
        assert size in ngram_analyzer.ngrams, f"No n-grams dictionary for size {size}"
        assert len(ngram_analyzer.ngrams[size]) > 0, f"No {size}-grams were generated"
        
        # Check a few properties of the generated n-grams
        for ngram_text, ngram_stats in ngram_analyzer.ngrams[size].items():
            assert len(ngram_text) == size, \
                f"N-gram '{ngram_text}' has incorrect size {len(ngram_text)}, should be {size}"
            assert isinstance(ngram_stats, NGram), \
                f"Expected NGram object, got {type(ngram_stats)}"
            assert ngram_stats.ngram_size == size, \
                f"NGram size mismatch: {ngram_stats.ngram_size} != {size}"
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
