"""
Test module for NGramAnalyzer class.

This module contains tests for the NGramAnalyzer class which is responsible for
analyzing typing sessions and generating n-gram statistics.
"""
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Now import the modules
from db.database_manager import DatabaseManager
from models.ngram_analyzer import NGramAnalyzer, MIN_NGRAM_SIZE, MAX_NGRAM_SIZE
from models.ngram_stats import NGramStats

# Test the NGramAnalyzer class

def test_abc_sequence_ngram_analysis(temp_db: DatabaseManager, caplog) -> None:
    """Test n-gram analysis for a simple 'a', 'b', 'c' sequence.
    
    This test verifies that:
    1. Keystrokes are correctly inserted into the database
    2. NGramAnalyzer processes the keystrokes correctly
    3. The correct n-grams are generated with proper timing
    4. No errors are recorded for correct keystrokes
    """
    # Enable debug logging for this test
    caplog.set_level('DEBUG')
    
    # Setup test data
    session_id = "test_abc_session"
    now = datetime.now().isoformat()
    
    print(f"\n{'*' * 80}")
    print("Starting test_abc_sequence_ngram_analysis")
    print(f"Session ID: {session_id}")
    print(f"Current time: {now}")
    print('*' * 80)

    # Create a test session
    temp_db.execute(
        """
        INSERT OR REPLACE INTO practice_sessions
        (session_id, content, start_time, end_time, total_time, session_wpm, session_cpm,
         expected_chars, actual_chars, errors, efficiency, correctness, accuracy)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, 'abc', now, now, 3.3, 0, 0, 3, 3, 0, 1.0, 1.0, 100.0),
        commit=True
    )
    print("Inserted practice session record")

    # Insert test keystrokes with explicit keystroke_id and proper timing
    test_keystrokes = [
        (session_id, 1, now, 'a', 'a', 1, 0.0),    # First keystroke, no time since previous
        (session_id, 2, now, 'b', 'b', 1, 1.2),    # 1.2s after first keystroke
        (session_id, 3, now, 'c', 'c', 1, 0.9)     # 0.9s after second keystroke (2.1s total)
    ]
    
    for idx, keystroke in enumerate(test_keystrokes, 1):
        temp_db.execute(
            """
            INSERT INTO session_keystrokes
            (session_id, keystroke_id, keystroke_time, keystroke_char, 
             expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            keystroke,
            commit=True
        )
        print(f"Inserted keystroke {idx}: {keystroke}")
    
    # Verify keystrokes were inserted correctly
    keystrokes = temp_db.fetchall(
        "SELECT * FROM session_keystrokes WHERE session_id = ? ORDER BY keystroke_id",
        (session_id,)
    )
    print(f"Retrieved {len(keystrokes)} keystrokes from database")
    for ks in keystrokes:
        print(f"Keystroke in DB: {dict(ks)}")

    # Initialize NGramAnalyzer with debug logging
    analyzer = NGramAnalyzer(temp_db)
    
    # Analyze the session
    print("\nAnalyzing session...")
    ngram_stats = analyzer.analyze_session(session_id)
    
    # Print debug logs
    print("\n=== Debug Logs ===")
    for record in caplog.records:
        print(f"{record.levelname}: {record.message}")
    print("=================\n")
    
    # Verify the results
    assert ngram_stats is not None, "analyze_session should return a dictionary"
    print(f"N-gram stats keys: {list(ngram_stats.keys())}")
    
    # Check for expected n-grams (bigrams and trigrams)
    assert '2' in ngram_stats, f"Expected bigrams in results, got: {list(ngram_stats.keys())}"
    assert '3' in ngram_stats, f"Expected trigrams in results, got: {list(ngram_stats.keys())}"
    
    # Verify specific n-grams
    bigrams = ngram_stats['2']
    trigrams = ngram_stats['3']
    
    print("\nBigrams found:", list(bigrams.keys()))
    print("Trigrams found:", list(trigrams.keys()))
    
    # Check for 'ab' bigram
    assert 'ab' in bigrams, f"Expected 'ab' bigram in results, found: {list(bigrams.keys())}"
    assert bigrams['ab'].total_time_ms == pytest.approx(1.2, abs=0.01), \
        f"Incorrect timing for 'ab' bigram: expected ~1.2, got {bigrams['ab'].total_time_ms}"
    assert bigrams['ab'].error_count == 0, f"Expected no errors for 'ab' bigram, got {bigrams['ab'].error_count}"
    
    # Check for 'bc' bigram
    assert 'bc' in bigrams, f"Expected 'bc' bigram in results, found: {list(bigrams.keys())}"
    assert bigrams['bc'].total_time_ms == pytest.approx(0.9, abs=0.01), \
        f"Incorrect timing for 'bc' bigram: expected ~0.9, got {bigrams['bc'].total_time_ms}"
    assert bigrams['bc'].error_count == 0, f"Expected no errors for 'bc' bigram, got {bigrams['bc'].error_count}"
    
    # Check for 'abc' trigram
    assert 'abc' in trigrams, f"Expected 'abc' trigram in results, found: {list(trigrams.keys())}"
    assert trigrams['abc'].total_time_ms == pytest.approx(2.1, abs=0.01), \
        f"Incorrect timing for 'abc' trigram: expected ~2.1, got {trigrams['abc'].total_time_ms}"
    assert trigrams['abc'].error_count == 0, f"Expected no errors for 'abc' trigram, got {trigrams['abc'].error_count}"
    
    print("\nAll assertions passed!")

# Fixture for database setup
@pytest.fixture
def temp_db():
    """Create a temporary in-memory database for testing."""
    from db.database_manager import DatabaseManager
    
    # Create an in-memory database
    db = DatabaseManager(":memory:")
    
    # Create necessary tables
    db.execute("""
        CREATE TABLE IF NOT EXISTS practice_sessions (
            session_id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            total_time REAL NOT NULL,
            session_wpm REAL NOT NULL,
            session_cpm REAL NOT NULL,
            expected_chars INTEGER NOT NULL,
            actual_chars INTEGER NOT NULL,
            errors INTEGER NOT NULL,
            efficiency REAL NOT NULL,
            correctness REAL NOT NULL,
            accuracy REAL NOT NULL
        )
    """, commit=True)
    
    db.execute("""
        CREATE TABLE IF NOT EXISTS session_keystrokes (
            session_id TEXT,
            keystroke_id INTEGER,
            keystroke_time DATETIME NOT NULL,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            time_since_previous REAL,
            PRIMARY KEY (session_id, keystroke_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
        )
    """, commit=True)
    
    db.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_speed (
            session_id TEXT,
            ngram TEXT NOT NULL,
            ngram_size INTEGER NOT NULL,
            ngram_time_ms REAL NOT NULL,
            PRIMARY KEY (session_id, ngram, ngram_size),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
        )
    """, commit=True)
    
    db.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_errors (
            session_id TEXT,
            ngram TEXT NOT NULL,
            ngram_size INTEGER NOT NULL,
            PRIMARY KEY (session_id, ngram, ngram_size),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
        )
    """, commit=True)
    
    yield db
    
    # Cleanup
    db.close()
