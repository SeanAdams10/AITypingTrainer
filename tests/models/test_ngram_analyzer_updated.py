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
from models.ngram_analyzer import NGramAnalyzer, NGramStats

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
    
    return session_id

# Test NGramStats
class TestNGramStats:
    """Test the NGramStats data class."""
    
    def test_ngram_stats_initialization(self):
        """Test NGramStats initialization."""
        stats = NGramStats("test", 4, 100.0, 0)
        assert stats.ngram == "test"
        assert stats.ngram_size == 4
        assert stats.total_time_ms == 100.0
        assert stats.error_count == 0
        assert not stats.is_error
    
    def test_is_error_property(self):
        """Test the is_error property."""
        stats1 = NGramStats("test", 4, 100.0, 0)
        stats2 = NGramStats("test", 4, 100.0, 1)
        
        assert not stats1.is_error
        assert stats2.is_error

# Test NGramAnalyzer
class TestNGramAnalyzer:
    """Test the NGramAnalyzer class."""
    
    def test_analyze_session(self, temp_db: DatabaseManager, sample_session: str):
        """Test analyzing a session with keystrokes."""
        analyzer = NGramAnalyzer(temp_db)
        
        # Analyze the session
        result = analyzer.analyze_session(sample_session)
        
        # Check that we got results for different n-gram sizes
        assert isinstance(result, dict)
        assert len(result) > 0
        
        # Check that we have data for n-gram size 2
        assert "2" in result
        assert len(result["2"]) > 0
        
        # Check that we have some n-grams with errors
        has_errors = any(stats.is_error for stats in result["2"].values())
        assert has_errors, "Expected to find some n-grams with errors"
    
    def test_get_slowest_ngrams(self, temp_db: DatabaseManager, sample_session: str):
        """Test retrieving the slowest n-grams."""
        analyzer = NGramAnalyzer(temp_db)
        
        # First analyze the session to populate the data
        analyzer.analyze_session(sample_session)
        
        # Get the slowest bigrams
        slow_bigrams = analyzer.get_slowest_ngrams(2, limit=5)
        
        assert isinstance(slow_bigrams, list)
        assert len(slow_bigrams) > 0
        
        # Check the structure of the results
        for ngram_stats in slow_bigrams:
            assert "ngram" in ngram_stats
            assert "avg_time_ms" in ngram_stats
            assert isinstance(ngram_stats["ngram"], str)
            assert isinstance(ngram_stats["avg_time_ms"], (int, float))
    
    def test_get_most_error_prone_ngrams(self, temp_db: DatabaseManager, sample_session: str):
        """Test retrieving the most error-prone n-grams."""
        analyzer = NGramAnalyzer(temp_db)
        
        # First analyze the session to populate the data
        analyzer.analyze_session(sample_session)
        
        # Get the most error-prone bigrams
        error_bigrams = analyzer.get_most_error_prone_ngrams(2, limit=5)
        
        assert isinstance(error_bigrams, list)
        
        # We might not have errors in our test data, but the function should still work
        if error_bigrams:
            for ngram_stats in error_bigrams:
                assert "ngram" in ngram_stats
                assert "error_count" in ngram_stats
                assert isinstance(ngram_stats["ngram"], str)
                assert isinstance(ngram_stats["error_count"], int)

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))
