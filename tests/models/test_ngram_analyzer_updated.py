"""
Tests for the NGramAnalyzer class.

These tests verify the functionality of the NGramAnalyzer class, including
n-gram extraction, statistics calculation, and database operations.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import pytest
from pytest_mock import MockerFixture

# Add the project root to the Python path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from db.database_manager import DatabaseManager
from models.ngram_analyzer import NGramAnalyzer, NGram
from models.session import Session
from models.keystroke import Keystroke

# Test data
SAMPLE_KEYSTROKES = [
    # First word: "the"
    {"keystroke_id": 1, "keystroke_time": "2023-01-01 10:00:00.000", 
     "keystroke_char": "t", "expected_char": "t", "is_correct": True, "time_since_previous": 0},
    {"keystroke_id": 2, "keystroke_time": "2023-01-01 10:00:00.100", 
     "keystroke_char": "h", "expected_char": "h", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 3, "keystroke_time": "2023-01-01 10:00:00.200", 
     "keystroke_char": "e", "expected_char": "e", "is_correct": True, "time_since_previous": 100},
    
    # Space after first word
    {"keystroke_id": 4, "keystroke_time": "2023-01-01 10:00:00.300", 
     "keystroke_char": " ", "expected_char": " ", "is_correct": True, "time_since_previous": 100},
    
    # Second word: "quick" (with an error on 'u')
    {"keystroke_id": 5, "keystroke_time": "2023-01-01 10:00:00.400", 
     "keystroke_char": "q", "expected_char": "q", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 6, "keystroke_time": "2023-01-01 10:00:00.500", 
     "keystroke_char": "x", "expected_char": "u", "is_correct": False, "time_since_previous": 100},
    {"keystroke_id": 7, "keystroke_time": "2023-01-01 10:00:00.550", 
     "keystroke_char": "u", "expected_char": "u", "is_correct": True, "time_since_previous": 50},
    {"keystroke_id": 8, "keystroke_time": "2023-01-01 10:00:00.650", 
     "keystroke_char": "i", "expected_char": "i", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 9, "keystroke_time": "2023-01-01 10:00:00.750", 
     "keystroke_char": "c", "expected_char": "c", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 10, "keystroke_time": "2023-01-01 10:00:00.850", 
     "keystroke_char": "k", "expected_char": "k", "is_correct": True, "time_since_previous": 100},
     
    # Space after second word
    {"keystroke_id": 11, "keystroke_time": "2023-01-01 10:00:00.950", 
     "keystroke_char": " ", "expected_char": " ", "is_correct": True, "time_since_previous": 100},
     
    # Third word: "brown" (all correct)
    {"keystroke_id": 12, "keystroke_time": "2023-01-01 11:00:00.000", 
     "keystroke_char": "b", "expected_char": "b", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 13, "keystroke_time": "2023-01-01 11:00:00.100", 
     "keystroke_char": "r", "expected_char": "r", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 14, "keystroke_time": "2023-01-01 11:00:00.200", 
     "keystroke_char": "o", "expected_char": "o", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 15, "keystroke_time": "2023-01-01 11:00:00.300", 
     "keystroke_char": "w", "expected_char": "w", "is_correct": True, "time_since_previous": 100},
    {"keystroke_id": 16, "keystroke_time": "2023-01-01 11:00:00.400", 
     "keystroke_char": "n", "expected_char": "n", "is_correct": True, "time_since_previous": 100},
]

# Fixtures
@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    # Initialize database with required tables
    db = DatabaseManager(db_path)
    db.init_tables()
    
    # Create session_keystrokes table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS session_keystrokes (
            keystroke_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            keystroke_time TIMESTAMP NOT NULL,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            time_since_previous INTEGER,
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
        )
    """, commit=True)
    
    # Create practice_sessions table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS practice_sessions (
            session_id TEXT PRIMARY KEY,
            snippet_id INTEGER,
            snippet_index_start INTEGER,
            snippet_index_end INTEGER,
            content TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            total_time REAL,
            session_wpm REAL,
            session_cpm REAL,
            expected_chars INTEGER,
            actual_chars INTEGER,
            errors INTEGER,
            efficiency REAL,
            correctness REAL,
            accuracy REAL,
            FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE SET NULL
        )
    """, commit=True)
    
    # Create snippets table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS snippets (
            snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            snippet_name TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL
        )
    """, commit=True)
    
    # Create categories table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE
        )
    """, commit=True)
    
    # Create n-gram tables
    db.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_speed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            ngram_size INTEGER NOT NULL,
            ngram TEXT NOT NULL,
            ngram_time_ms REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE,
            UNIQUE(session_id, ngram)
        )
    """, commit=True)
    
    db.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            ngram_size INTEGER NOT NULL,
            ngram TEXT NOT NULL,
            error_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE,
            UNIQUE(session_id, ngram)
        )
    """, commit=True)
    
    yield db
    
    # Cleanup
    db.close()
    try:
        os.unlink(db_path)
    except (OSError, PermissionError):
        pass

@pytest.fixture
def sample_session(temp_db: DatabaseManager) -> str:
    """Create a sample session with keystrokes for testing."""
    session_id = "test_session_123"
    
    # Insert a test category
    temp_db.execute(
        """
        INSERT INTO categories (category_id, category_name)
        VALUES (1, 'test_category')
        """,
        commit=True
    )
    
    # Insert a test snippet
    temp_db.execute(
        """
        INSERT INTO snippets (snippet_id, category_id, snippet_name)
        VALUES (1, 1, 'test_snippet')
        """,
        commit=True
    )
    
    # Insert the session record with all required fields
    now = datetime.now().isoformat()
    end_time = (datetime.now() + timedelta(seconds=10)).isoformat()
    temp_db.execute(
        """
        INSERT INTO practice_sessions 
        (session_id, snippet_id, snippet_index_start, snippet_index_end, content,
         start_time, end_time, total_time, session_wpm, session_cpm, 
         expected_chars, actual_chars, errors, efficiency, correctness, accuracy)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, 
         1,  # snippet_id (must match the one inserted above)
         0,  # snippet_index_start
         0,  # snippet_index_end
         'test content',  # content
         now,  # start_time
         end_time,  # end_time
         10.0,  # total_time
         50.0,  # session_wpm
         250.0,  # session_cpm
         100,  # expected_chars
         95,  # actual_chars
         5,  # errors
         0.95,  # efficiency
         0.95,  # correctness
         95.0),  # accuracy
        commit=True
    )
    
    # Insert sample keystrokes
    for keystroke in SAMPLE_KEYSTROKES:
        temp_db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, 
             keystroke["keystroke_time"],
             keystroke["keystroke_char"],
             keystroke["expected_char"],
             1 if keystroke["is_correct"] else 0,
             keystroke["time_since_previous"]),
            commit=True
        )
        
    # Create the n-gram tables if they don't exist
    temp_db.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_speed (
            session_id TEXT,
            ngram_size INTEGER,
            ngram TEXT,
            ngram_time_ms REAL,
            PRIMARY KEY (session_id, ngram_size, ngram),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
        )
    """, commit=True)
    
    temp_db.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_errors (
            session_id TEXT,
            ngram_size INTEGER,
            ngram TEXT,
            PRIMARY KEY (session_id, ngram_size, ngram),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
        )
    """, commit=True)
    
    return session_id

# Test NGramStats
class TestNGram:
    """Test objective: Verify that the NGram class correctly encapsulates n-gram data and provides proper properties.
    
    This test ensures that the NGram class initializes correctly and its properties accurately
    reflect the state of the n-gram regarding errors and cleanliness.
    """
    
    def test_ngram_initialization(self):
        """Test objective: Verify proper initialization of NGram objects with various parameters."""
        # Create a clean n-gram
        clean_ngram = NGram("test", 4, 100.0)
        assert clean_ngram.ngram == "test"
        assert clean_ngram.ngram_size == 4
        assert clean_ngram.total_time_ms == 100.0
        assert not clean_ngram.has_error_on_last
        assert not clean_ngram.has_other_errors
        assert clean_ngram.occurrences == 1
        
        # Create an n-gram with error on last character
        error_ngram = NGram("test", 4, 150.0, has_error_on_last=True)
        assert error_ngram.ngram == "test"
        assert error_ngram.total_time_ms == 150.0
        assert error_ngram.has_error_on_last
        assert not error_ngram.has_other_errors
        
        # Create an n-gram with other errors
        invalid_ngram = NGram("test", 4, 200.0, has_other_errors=True)
        assert invalid_ngram.ngram == "test"
        assert invalid_ngram.total_time_ms == 200.0
        assert not invalid_ngram.has_error_on_last
        assert invalid_ngram.has_other_errors
    
    def test_ngram_properties(self):
        """Test objective: Verify that NGram properties correctly identify clean and error states."""
        clean_ngram = NGram("test", 4, 100.0)
        error_ngram = NGram("test", 4, 150.0, has_error_on_last=True)
        invalid_ngram = NGram("test", 4, 200.0, has_other_errors=True)
        both_errors_ngram = NGram("test", 4, 250.0, has_error_on_last=True, has_other_errors=True)
        
        # Test is_clean property
        assert clean_ngram.is_clean
        assert not error_ngram.is_clean
        assert not invalid_ngram.is_clean
        assert not both_errors_ngram.is_clean
        
        # Test is_error property
        assert not clean_ngram.is_error
        assert error_ngram.is_error
        assert not invalid_ngram.is_error  # Only error on last position counts as error n-gram
        assert error_ngram.is_error


class TestSession:
    """Test objective: Verify that the Session class correctly represents typing sessions.
    
    This test ensures that the Session class properly encapsulates session ID and content.
    """
    
    def test_session_initialization(self):
        """Test objective: Verify proper initialization of Session objects."""
        session_id = "test_session_123"
        content = "Sample typing content"
        session = Session(session_id, content)
        
        assert session.session_id == session_id
        assert session.content == content


class TestKeystroke:
    """Test objective: Verify that the Keystroke class correctly represents typing keystrokes.
    
    This test ensures that the Keystroke class properly encapsulates keystroke data including
    character, correctness, and timing information.
    """
    
    def test_keystroke_initialization(self):
        """Test objective: Verify proper initialization of Keystroke objects."""
        keystroke = Keystroke(
            keystroke_id=1,
            keystroke_char="a",
            expected_char="a",
            is_correct=True,
            time_since_previous=100.0,
            keystroke_time=1000.0
        )
        
        assert keystroke.keystroke_id == 1
        assert keystroke.keystroke_char == "a"
        assert keystroke.expected_char == "a"
        assert keystroke.is_correct == True
        assert keystroke.time_since_previous == 100.0
        assert keystroke.keystroke_time == 1000.0
        
        # Test with error
        error_keystroke = Keystroke(
            keystroke_id=2,
            keystroke_char="b",
            expected_char="c",
            is_correct=False,
            time_since_previous=150.0,
            keystroke_time=1150.0
        )
        
        assert error_keystroke.keystroke_id == 2
        assert error_keystroke.keystroke_char == "b"
        assert error_keystroke.expected_char == "c"
        assert error_keystroke.is_correct == False
        assert error_keystroke.time_since_previous == 150.0
        assert error_keystroke.keystroke_time == 1150.0

# Test NGramAnalyzer
class TestNGramAnalyzer:
    """Test objective: Verify that the NGramAnalyzer class correctly analyzes typing sessions.
    
    This test class validates that the NGramAnalyzer correctly processes typing sessions,
    identifies n-grams, calculates timing and error statistics, and saves results to the database.
    It uses pytest fixtures for setup and teardown of test resources.
    """
    
    def test_load_from_database(self, temp_db: DatabaseManager, sample_session: str):
        """Test objective: Verify that the NGramAnalyzer correctly loads session and keystroke data from the database."""
        # Make sure we have valid data in our test DB
        session_data = temp_db.fetchone(
            "SELECT content FROM practice_sessions WHERE session_id = ?", (sample_session,)
        )
        assert session_data is not None, f"No session data found for {sample_session}"
        
        # Make sure we have keystroke data
        keystroke_data = temp_db.fetchall(
            "SELECT keystroke_id, keystroke_char, expected_char, is_correct, time_since_previous, keystroke_time FROM session_keystrokes WHERE session_id = ?", 
            (sample_session,)
        )
        assert len(keystroke_data) > 0, f"No keystroke data found for {sample_session}"
        
        # Now initialize analyzer and load data
        analyzer = NGramAnalyzer(temp_db)
        success = analyzer.load_from_database(sample_session)
        assert success, "Failed to load session data from database"
        
        # Verify session data was loaded
        assert analyzer.session is not None, "Session was not loaded properly"
        assert isinstance(analyzer.session, Session), "Session object is not of the correct type"
        assert analyzer.session.session_id == sample_session, "Session ID doesn't match"
        assert len(analyzer.session.content) > 0, "Session content is empty"
        
        # Verify keystroke data was loaded
        assert analyzer.keystrokes is not None, "Keystrokes were not loaded properly"
        assert isinstance(analyzer.keystrokes, list), "Keystrokes is not a list"
        assert len(analyzer.keystrokes) > 0, "No keystrokes were loaded"
        assert all(isinstance(k, Keystroke) for k in analyzer.keystrokes), "Not all keystrokes are Keystroke objects"
    
    def test_analyze_method(self, temp_db: DatabaseManager, sample_session: str):
        """Test objective: Verify that the analyze method correctly processes keystrokes and generates NGram objects."""
        analyzer = NGramAnalyzer(temp_db)
        
        # Load the session data first
        success = analyzer.load_from_database(sample_session)
        assert success, "Failed to load session data from database"
        
        # Analyze the session with small n-gram sizes to ensure we get results
        result = analyzer.analyze(min_size=2, max_size=3)
        assert result, "Analyze method failed"
        
        # Verify results are stored in the analyzer
        assert len(analyzer.ngrams) > 0
        assert 2 in analyzer.ngrams, "No 2-grams found"
        
        # Check for specific n-grams that should be present based on our test data
        # 'test content' should have at least some 2-grams
        assert len(analyzer.ngrams[2]) > 0, "No 2-grams were found in the analyzer's ngrams dictionary"
    
    def test_save_to_database(self, temp_db: DatabaseManager, sample_session: str):
        """Test objective: Verify that NGramAnalyzer correctly saves analysis results to the database."""
        analyzer = NGramAnalyzer(temp_db)
        
        # Insert some test data directly for reliable testing
        # Load session data first
        success = analyzer.load_from_database(sample_session)
        assert success, "Failed to load session data"
        
        # Manually create some simple n-grams for testing
        analyzer.ngrams = {
            2: {
                "te": NGram("te", 2, 100.0),
                "es": NGram("es", 2, 150.0),
                "st": NGram("st", 2, 120.0),
                "t ": NGram("t ", 2, 0.0)  # This one should be filtered out due to whitespace
            },
            3: {
                "tes": NGram("tes", 3, 200.0),
                "est": NGram("est", 3, 220.0),
                "st ": NGram("st ", 3, 0.0)  # This one should be filtered out due to whitespace
            }
        }
        
        # Add some error n-grams
        analyzer.ngrams[2]["te"].has_error_on_last = True
        analyzer.ngrams[3]["tes"].has_error_on_last = True
        
        # Save to database
        success = analyzer.save_to_database()
        assert success, "Failed to save n-grams to database"
        
        # Verify data was saved to speed table (only clean n-grams)
        speed_results = temp_db.fetchall(
            "SELECT ngram_size, ngram, ngram_time_ms FROM session_ngram_speed WHERE session_id = ? ORDER BY ngram_size, ngram",
            (sample_session,)
        )
        
        # Should have at least the 'es' and 'st' n-grams in the speed table
        assert len(speed_results) > 0, "No speed n-grams were saved to the database"
        
        # Verify some n-grams were saved to error table
        error_results = temp_db.fetchall(
            "SELECT ngram_size, ngram FROM session_ngram_errors WHERE session_id = ? ORDER BY ngram_size, ngram",
            (sample_session,)
        )
        assert len(error_results) > 0, "No error n-grams were saved to the database"
        
        # Verify specific n-grams are in the right tables
        speed_ngrams = [row["ngram"] for row in speed_results]
        assert "es" in speed_ngrams, "Expected 'es' in speed n-grams"
        assert "st" in speed_ngrams, "Expected 'st' in speed n-grams"
        
        error_ngrams = [row["ngram"] for row in error_results]
        assert "te" in error_ngrams, "Expected 'te' in error n-grams"
    
    def test_analyze_session_ngrams(self, temp_db: DatabaseManager, sample_session: str):
        """Test objective: Verify that the analyze_session_ngrams method correctly processes a complete session."""
        # First, verify we have a valid session with content and keystrokes
        session_data = temp_db.fetchone(
            "SELECT content FROM practice_sessions WHERE session_id = ?", (sample_session,)
        )
        assert session_data is not None, f"No session data found for {sample_session}"
        
        keystroke_data = temp_db.fetchall(
            "SELECT keystroke_id FROM session_keystrokes WHERE session_id = ?", 
            (sample_session,)
        )
        assert len(keystroke_data) > 0, f"No keystroke data found for {sample_session}"
        
        # Create the analyzer
        analyzer = NGramAnalyzer(temp_db)
        
        # Update the content to something we can easily test for n-grams
        # This helps ensure we have a predictable content string with adequate data for n-gram analysis
        temp_db.execute(
            "UPDATE practice_sessions SET content = ? WHERE session_id = ?",
            ("testcontent", sample_session)
        )
        
        # Make sure we have some simple keystrokes that will work for n-gram analysis
        # First delete any existing keystrokes to have a clean slate
        temp_db.execute("DELETE FROM session_keystrokes WHERE session_id = ?", (sample_session,))
        
        # Add simple test keystrokes with proper timestamp values
        # Use increasing float values for keystroke_time starting from 1000.0
        for i, char in enumerate("testcontent"):
            base_time = 1000.0 + (i * 100.0)  # Start at 1000ms and increase by 100ms for each keystroke
            temp_db.execute(
                "INSERT INTO session_keystrokes (keystroke_id, session_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (i+1, sample_session, base_time, char, char, 1, 100.0)
            )
        
        # First check what data we have in the session and keystrokes
        session_content = temp_db.fetchone(
            "SELECT content FROM practice_sessions WHERE session_id = ?", (sample_session,)
        )["content"]
        print(f"\nSession content: '{session_content}'")
        
        keystrokes = temp_db.fetchall(
            "SELECT keystroke_id, keystroke_char, expected_char, is_correct, time_since_previous FROM session_keystrokes WHERE session_id = ? ORDER BY keystroke_id", 
            (sample_session,)
        )
        print(f"Number of keystrokes: {len(keystrokes)}")
        for i, ks in enumerate(keystrokes[:10]):  # Just print first 10 to avoid excessive output
            print(f"  Keystroke {i+1}: '{ks['keystroke_char']}', expected: '{ks['expected_char']}', correct: {bool(ks['is_correct'])}")
        
        # Make sure the relevant tables exist
        temp_db.execute("""
            CREATE TABLE IF NOT EXISTS session_ngram_speed (
                session_id TEXT,
                ngram_size INTEGER,
                ngram TEXT,
                ngram_time_ms REAL,
                PRIMARY KEY (session_id, ngram_size, ngram),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            )
        """, commit=True)
        
        temp_db.execute("""
            CREATE TABLE IF NOT EXISTS session_ngram_errors (
                session_id TEXT,
                ngram_size INTEGER,
                ngram TEXT,
                PRIMARY KEY (session_id, ngram_size, ngram),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            )
        """, commit=True)
        
        # Now analyze the session with specific n-gram sizes
        success = analyzer.analyze_session_ngrams(sample_session, min_size=2, max_size=3)
        if not success:
            # Try to understand why it failed
            print("\nAnalyzing why analyze_session_ngrams failed:")
            
            # Check if load_from_database works
            load_success = analyzer.load_from_database(sample_session)
            print(f"  load_from_database success: {load_success}")
            if load_success:
                print(f"  Session data: {analyzer.session.content if analyzer.session else 'None'}")
                print(f"  Keystroke count: {len(analyzer.keystrokes) if analyzer.keystrokes else 'None'}")
                
                # Try analyzing manually
                analyze_success = analyzer.analyze(min_size=2, max_size=3)
                print(f"  analyze success: {analyze_success}")
                if analyze_success:
                    print(f"  Number of n-grams generated: {sum(len(ngrams) for ngrams in analyzer.ngrams.values())}")
                    
                    # Try saving manually
                    save_success = analyzer.save_to_database()
                    print(f"  save_to_database success: {save_success}")
        
        assert success, "Failed to analyze session using analyze_session_ngrams"
        
        # Verify data exists in the database after analysis
        speed_results = temp_db.fetchall(
            "SELECT ngram_size, ngram FROM session_ngram_speed WHERE session_id = ? ORDER BY ngram_size, ngram",
            (sample_session,)
        )
        assert len(speed_results) > 0, "No n-grams were saved to the speed table"
        
        # Check for specific 2-grams that should be present in our test content
        found_ngrams = set(row["ngram"] for row in speed_results if row["ngram_size"] == 2)
        expected_ngrams = {"te", "es", "st", "tc", "co", "on", "nt", "te", "en", "nt"}
        
        # Check that at least some of our expected n-grams are present
        assert len(found_ngrams.intersection(expected_ngrams)) > 0, f"Expected some of {expected_ngrams} but found {found_ngrams}"
    
    def test_get_slowest_ngrams(self, temp_db: DatabaseManager, sample_session: str):
        """Test objective: Verify that the get_slowest_ngrams method returns correctly formatted results."""
        analyzer = NGramAnalyzer(temp_db)
        
        # Insert test data directly
        temp_db.execute(
            "INSERT OR REPLACE INTO session_ngram_speed (session_id, ngram_size, ngram, ngram_time_ms) VALUES (?, ?, ?, ?)",
            (sample_session, 2, "th", 100.0)
        )
        temp_db.execute(
            "INSERT OR REPLACE INTO session_ngram_speed (session_id, ngram_size, ngram, ngram_time_ms) VALUES (?, ?, ?, ?)",
            (sample_session, 2, "he", 120.0)
        )
        temp_db.execute(
            "INSERT OR REPLACE INTO session_ngram_speed (session_id, ngram_size, ngram, ngram_time_ms) VALUES (?, ?, ?, ?)",
            (sample_session, 2, "eq", 150.0)
        )
        
        # Get the slowest bigrams
        slow_bigrams = analyzer.get_slowest_ngrams(2, limit=5)
        
        assert isinstance(slow_bigrams, list)
        assert len(slow_bigrams) > 0, "No slow bigrams were returned"
        
        # Check the structure of the results
        for ngram_stats in slow_bigrams:
            assert "ngram" in ngram_stats, "Missing 'ngram' key in result"
            assert "avg_time_ms" in ngram_stats, "Missing 'avg_time_ms' key in result"
            assert isinstance(ngram_stats["ngram"], str)
            assert isinstance(ngram_stats["avg_time_ms"], (int, float))
        
        # Verify the slowest n-gram is first
        assert slow_bigrams[0]["ngram"] == "eq", f"Expected 'eq' as the slowest n-gram, got {slow_bigrams[0]['ngram']}"
        assert slow_bigrams[0]["avg_time_ms"] == 150.0, f"Expected 150.0 ms, got {slow_bigrams[0]['avg_time_ms']}"
    
    def test_get_most_error_prone_ngrams(self, temp_db: DatabaseManager, sample_session: str):
        """Test objective: Verify that the get_most_error_prone_ngrams method returns correctly formatted results."""
        analyzer = NGramAnalyzer(temp_db)
        
        # Insert test data directly
        temp_db.execute(
            "INSERT OR REPLACE INTO session_ngram_errors (session_id, ngram_size, ngram) VALUES (?, ?, ?)",
            (sample_session, 2, "qu")
        )
        temp_db.execute(
            "INSERT OR REPLACE INTO session_ngram_errors (session_id, ngram_size, ngram) VALUES (?, ?, ?)",
            (sample_session, 2, "qu")
        )
        temp_db.execute(
            "INSERT OR REPLACE INTO session_ngram_errors (session_id, ngram_size, ngram) VALUES (?, ?, ?)",
            (sample_session, 2, "fo")
        )
        
        # Get the most error-prone bigrams
        error_bigrams = analyzer.get_most_error_prone_ngrams(2, limit=5)
        
        assert isinstance(error_bigrams, list)
        assert len(error_bigrams) > 0, "No error-prone bigrams were returned"
        
        # Check the structure of the results
        for ngram_stats in error_bigrams:
            assert "ngram" in ngram_stats, "Missing 'ngram' key in result"
            assert "error_count" in ngram_stats, "Missing 'error_count' key in result"
            assert isinstance(ngram_stats["ngram"], str)
            assert isinstance(ngram_stats["error_count"], int)

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))
