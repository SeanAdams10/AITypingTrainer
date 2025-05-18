"""
Test cases for NGramAnalyzer class.

This module contains tests for the NGramAnalyzer class, which is responsible for
analyzing n-grams in typing sessions to identify patterns, errors, and performance
metrics.
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytest

from models.keystroke import Keystroke
from models.ngram_analyzer_new import NGramAnalyzer, NGram
from db.database_manager import DatabaseManager

# Sample keystroke data for testing
SAMPLE_KEYSTROKES = [
    {"keystroke_id": 1, "keystroke_time": "2023-01-01T10:00:00.000", "keystroke_char": "t", "expected_char": "t", "is_correct": True, "time_since_previous": 0, "wpm": 60.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 2, "keystroke_time": "2023-01-01T10:00:00.100", "keystroke_char": "h", "expected_char": "h", "is_correct": True, "time_since_previous": 100, "wpm": 60.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 3, "keystroke_time": "2023-01-01T10:00:00.200", "keystroke_char": "e", "expected_char": "e", "is_correct": True, "time_since_previous": 100, "wpm": 60.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 4, "keystroke_time": "2023-01-01T10:00:00.300", "keystroke_char": " ", "expected_char": " ", "is_correct": True, "time_since_previous": 100, "wpm": 60.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 5, "keystroke_time": "2023-01-01T10:00:00.400", "keystroke_char": "q", "expected_char": "q", "is_correct": True, "time_since_previous": 100, "wpm": 55.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 6, "keystroke_time": "2023-01-01T10:00:00.500", "keystroke_char": "x", "expected_char": "u", "is_correct": False, "time_since_previous": 100, "wpm": 50.0, "accuracy": 0.0},
    {"keystroke_id": 7, "keystroke_time": "2023-01-01T10:00:00.600", "keystroke_char": "i", "expected_char": "i", "is_correct": True, "time_since_previous": 100, "wpm": 60.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 8, "keystroke_time": "2023-01-01T10:00:00.700", "keystroke_char": "c", "expected_char": "c", "is_correct": True, "time_since_previous": 100, "wpm": 60.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 9, "keystroke_time": "2023-01-01T10:00:00.800", "keystroke_char": "k", "expected_char": "k", "is_correct": True, "time_since_previous": 100, "wpm": 60.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 10, "keystroke_time": "2023-01-01T10:00:00.900", "keystroke_char": " ", "expected_char": " ", "is_correct": True, "time_since_previous": 100, "wpm": 60.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 11, "keystroke_time": "2023-01-01T10:00:01.000", "keystroke_char": "b", "expected_char": "b", "is_correct": True, "time_since_previous": 100, "wpm": 58.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 12, "keystroke_time": "2023-01-01T10:00:01.100", "keystroke_char": "r", "expected_char": "r", "is_correct": True, "time_since_previous": 100, "wpm": 58.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 13, "keystroke_time": "2023-01-01T10:00:01.200", "keystroke_char": "o", "expected_char": "o", "is_correct": True, "time_since_previous": 100, "wpm": 58.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 14, "keystroke_time": "2023-01-01T10:00:01.300", "keystroke_char": "w", "expected_char": "w", "is_correct": True, "time_since_previous": 100, "wpm": 58.0, "accuracy": 100.0, "error_type": None},
    {"keystroke_id": 15, "keystroke_time": "2023-01-01T10:00:01.400", "keystroke_char": "n", "expected_char": "n", "is_correct": True, "time_since_previous": 100, "wpm": 58.0, "accuracy": 100.0, "error_type": None},
]

# Fixtures
@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    # Initialize database with schema
    db = DatabaseManager(db_path)
    
    # Create the typing_sessions table first since it's referenced by session_keystrokes
    db.execute("""
        CREATE TABLE IF NOT EXISTS typing_sessions (
            session_id TEXT PRIMARY KEY,
            start_time TEXT NOT NULL,
            end_time TEXT,
            total_time_seconds REAL,
            total_keystrokes INTEGER,
            correct_keystrokes INTEGER,
            accuracy REAL,
            wpm REAL
        )
    """)
    
    # Create the session_keystrokes table with foreign key reference
    db.execute("""
        CREATE TABLE IF NOT EXISTS session_keystrokes (
            keystroke_id INTEGER PRIMARY KEY,
            session_id TEXT NOT NULL,
            keystroke_time TEXT NOT NULL,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,

            time_since_previous INTEGER NOT NULL,
            wpm REAL,
            accuracy REAL,
            FOREIGN KEY (session_id) REFERENCES typing_sessions(session_id)
        )
    """)
    
    yield db
    
    # Cleanup
    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass

@pytest.fixture
def sample_keystrokes(temp_db):
    """Insert sample keystrokes into the test database."""
    session_id = "test_session_123"
    
    # Insert a session record first
    temp_db.execute("""
        INSERT INTO typing_sessions (
            session_id, 
            start_time,
            end_time,
            total_time_seconds,
            total_keystrokes,
            correct_keystrokes,
            accuracy,
            wpm
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        "2023-01-01T10:00:00.000",  # start_time
        "2023-01-01T10:05:00.000",  # end_time
        300.0,  # total_time_seconds
        len(SAMPLE_KEYSTROKES),  # total_keystrokes
        len([k for k in SAMPLE_KEYSTROKES if k['is_correct']]),  # correct_keystrokes
        95.0,  # accuracy
        50.0  # wpm
    ))
    
    # Insert keystrokes
    for ks in SAMPLE_KEYSTROKES:
        temp_db.execute("""
            INSERT INTO session_keystrokes (
                keystroke_id, session_id, keystroke_time, keystroke_char, 
                expected_char, is_correct, time_since_previous, 
                wpm, accuracy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ks['keystroke_id'],
            session_id,
            ks['keystroke_time'],
            ks['keystroke_char'],
            ks['expected_char'],
            ks['is_correct'],

            ks['time_since_previous'],
            ks['wpm'],
            ks['accuracy']
        ))
    
    return session_id, temp_db

@pytest.fixture
def ngram_analyzer(sample_keystrokes):
    """Create an NGramAnalyzer instance with test data."""
    session_id, db = sample_keystrokes
    return NGramAnalyzer(session_id=session_id, db=db)

def create_test_keystrokes(text: str, is_error: bool = False, 
                         wpm: float = 60.0, accuracy: float = 100.0) -> List[Dict[str, Any]]:
    """Helper function to create test keystrokes."""
    keystrokes = []
    timestamp = datetime.now().timestamp()
    
    for i, char in enumerate(text):
        keystrokes.append({
            "keystroke_id": i + 1,
            "keystroke_time": datetime.fromtimestamp(timestamp + i).isoformat(),
            "keystroke_char": char,
            "expected_char": char if not is_error else 'x',  # Simulate error if needed
            "is_correct": not is_error,

            "time_since_previous": 100,  # 100ms between keystrokes
            "wpm": wpm,
            "accuracy": accuracy
        })
    
    return keystrokes

# Tests

def test_ngram_analyzer_initialization(ngram_analyzer: NGramAnalyzer):
    """Test NGramAnalyzer initialization and basic properties."""
    assert ngram_analyzer is not None
    assert ngram_analyzer.session_id == "test_session_123"
    assert len(ngram_analyzer.keystrokes) > 0
    assert ngram_analyzer.ngrams == {}

def test_count_speed_ngrams(ngram_analyzer: NGramAnalyzer):
    """Test counting speed n-grams."""
    # Analyze with n-gram sizes 2 and 3
    ngram_analyzer.analyze(min_size=2, max_size=3)
    
    # Test counting bigrams with different speed ranges
    bigrams = ngram_analyzer.count_speed_ngrams(2, min_speed=40, max_speed=70)
    assert len(bigrams) > 0, "Expected to find some bigrams in the 40-70 WPM range"
    
    # Verify the structure of the returned data
    for bigram in bigrams:
        assert "ngram" in bigram
        assert "count" in bigram
        assert "avg_speed" in bigram
        assert 40 <= bigram["avg_speed"] <= 70
    
    # Test with a very restrictive speed range (should find few or none)
    fast_bigrams = ngram_analyzer.count_speed_ngrams(2, min_speed=100, max_speed=200)
    assert len(fast_bigrams) == 0, "Did not expect to find bigrams in the 100-200 WPM range"

def test_count_error_ngrams(ngram_analyzer: NGramAnalyzer):
    """Test counting error n-grams."""
    # Analyze with n-gram sizes 2 and 3
    ngram_analyzer.analyze(min_size=2, max_size=3)
    
    # Get all error bigrams
    error_bigrams = ngram_analyzer.count_error_ngrams(2)
    
    # We should find at least one error bigram (the one with 'x' in it)
    assert len(error_bigrams) > 0, "Expected to find at least one error bigram"
    
    # Verify the structure of the returned data
    for error_ngram in error_bigrams:
        assert "ngram" in error_ngram
        assert "count" in error_ngram
        assert "error_count" in error_ngram
        assert isinstance(error_ngram["error_count"], int)
    
    # Test filtering by error type
    error_ngrams = ngram_analyzer.count_error_ngrams(2)
    assert len(error_ngrams) > 0  # Should find at least one error n-gram

def test_get_ngrams(ngram_analyzer: NGramAnalyzer):
    """Test retrieving n-grams as NGram objects."""
    # Analyze with n-gram sizes 2 and 3
    ngram_analyzer.analyze(min_size=2, max_size=3)
    
    # Get all bigrams as NGram objects
    bigrams = ngram_analyzer.get_ngrams(2)
    
    # We should find several bigrams
    assert len(bigrams) > 0, "Expected to find several bigrams"
    
    # Verify the structure of the returned NGram objects
    for ngram in bigrams:
        assert isinstance(ngram, NGram)
        assert hasattr(ngram, "ngram")
        assert hasattr(ngram, "ngram_size")
        assert hasattr(ngram, "total_time_ms")
        assert hasattr(ngram, "has_error_on_last")
        assert hasattr(ngram, "has_other_errors")
        assert hasattr(ngram, "occurrences")
        assert hasattr(ngram, "is_clean")
        assert hasattr(ngram, "is_error")
        assert hasattr(ngram, "is_valid")
        assert hasattr(ngram, "chars_per_second")
        assert hasattr(ngram, "chars_per_millisecond")

def test_ngram_analysis_with_different_sizes(ngram_analyzer: NGramAnalyzer):
    """Test n-gram analysis with different n-gram sizes."""
    # Test with different n-gram sizes
    for size in [2, 3, 4]:
        ngram_analyzer.analyze(min_size=size, max_size=size)
        
        # Get n-grams of the current size
        ngrams = ngram_analyzer.get_ngrams(size)
        
        # We should find some n-grams
        assert len(ngrams) > 0, f"Expected to find some {size}-grams"
        
        # All n-grams should have the correct length
        for ngram in ngrams:
            assert len(ngram.text) == size, f"Expected n-gram length {size}, got {len(ngram.text)}"

def test_empty_keystrokes():
    """Test behavior with empty keystroke list."""
    # Create a new analyzer with no keystrokes
    empty_db = DatabaseManager(":memory:")
    empty_db.init_tables()
    analyzer = NGramAnalyzer(session_id="empty_session", db=empty_db)
    
    # Analyze with empty keystrokes
    analyzer.analyze()
    
    # Should return empty lists
    assert analyzer.count_speed_ngrams(2) == []
    assert analyzer.count_error_ngrams(2) == []
    assert analyzer.get_ngrams(2) == []

def test_keystroke_accuracy_calculation(ngram_analyzer: NGramAnalyzer):
    """Test accuracy calculation for keystrokes."""
    # Add some keystrokes with known accuracy values
    keystrokes = create_test_keystrokes(
        "test", 
        is_error=False, 
        wpm=60.0, 
        accuracy=95.0  # 95% accuracy
    )
    
    # Add some error keystrokes
    error_keystrokes = create_test_keystrokes(
        "x", 
        is_error=True, 

        wpm=30.0, 
        accuracy=0.0
    )
    
    # Replace the analyzer's keystrokes with our test data
    ngram_analyzer.keystrokes = [Keystroke(**ks) for ks in keystrokes + error_keystrokes]
    
    # Analyze the keystrokes
    ngram_analyzer.analyze(min_size=2, max_size=2)
    
    # Check the accuracy of the n-grams
    ngrams = ngram_analyzer.get_ngrams(2)
    assert len(ngrams) > 0, "Expected to find some n-grams"
    
    # The n-gram containing the error should have lower accuracy
    for ngram in ngrams:
        if any(not ks.is_correct for ks in ngram.keystrokes):
            assert ngram.accuracy < 100.0, "Expected n-gram with error to have accuracy < 100%"
        else:
            assert ngram.accuracy == 95.0, "Expected clean n-gram to have 95% accuracy"

def test_ngram_keystroke_sequence(ngram_analyzer: NGramAnalyzer):
    """Test that n-grams are built from consecutive keystrokes."""
    # Create a sequence of keystrokes with a known pattern
    keystrokes = create_test_keystrokes("abcdefghijklmnopqrstuvwxyz")
    ngram_analyzer.keystrokes = [Keystroke(**ks) for ks in keystrokes]
    
    # Analyze with n-gram size 3
    ngram_analyzer.analyze(min_size=3, max_size=3)
    
    # Get all 3-grams
    trigrams = ngram_analyzer.get_ngrams(3)
    
    # We should have (26 - 3 + 1) = 24 trigrams
    assert len(trigrams) == 24, f"Expected 24 trigrams, got {len(trigrams)}"
    
    # Verify the sequence is correct
    for i, ngram in enumerate(trigrams):
        expected_text = "abc"[i:i+3] if i < 3 else chr(97+i) + chr(98+i) + chr(99+i)  # 'a' is 97 in ASCII
        assert ngram.text == expected_text, f"Expected {expected_text}, got {ngram.text}"

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
