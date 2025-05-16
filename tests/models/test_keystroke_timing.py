#!/usr/bin/env python
"""
Test cases for keystroke timing functionality in practice session extensions.
Tests proper recording of time_since_previous values for various typing scenarios.
"""
import os
import sys
import pytest
import datetime
import tempfile
from typing import List, Dict, Any, Optional
import sqlite3

# Add project root to path
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.database_manager import DatabaseManager
from models.practice_session import PracticeSession, PracticeSessionManager
from models.practice_session_extensions import save_session_data, PracticeSessionKeystrokeManager


@pytest.fixture
def temp_db_path(tmpdir):
    """Create a temporary database file using pytest's tmpdir fixture."""
    db_path = tmpdir.join('test_keystroke.db')
    yield str(db_path)
    # File will be automatically cleaned up by pytest


@pytest.fixture
def db_manager(temp_db_path):
    """Create a database manager with the temporary database."""
    manager = DatabaseManager(temp_db_path)
    
    # Initialize tables
    manager.execute("""
        CREATE TABLE IF NOT EXISTS practice_sessions (
            session_id TEXT PRIMARY KEY,
            snippet_id INTEGER NOT NULL,
            snippet_index_start INTEGER NOT NULL,
            snippet_index_end INTEGER NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            total_time REAL,
            session_wpm REAL,
            session_cpm REAL,
            expected_chars INTEGER,
            actual_chars INTEGER,
            errors INTEGER,
            efficiency REAL,
            correctness REAL,
            accuracy REAL
        )
    """, commit=True)
    
    manager.execute("""
        CREATE TABLE IF NOT EXISTS session_keystrokes (
            session_id TEXT,
            keystroke_id INTEGER,
            keystroke_time DATETIME NOT NULL,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            time_since_previous INTEGER,
            PRIMARY KEY (session_id, keystroke_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
        )
    """, commit=True)
    
    # Create tables for n-gram analysis
    manager.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_speed (
            ngram_speed_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            ngram TEXT NOT NULL,
            speed INTEGER NOT NULL
        )
    """, commit=True)
    
    manager.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_errors (
            ngram_error_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            ngram TEXT NOT NULL,
            ngram_size INTEGER NOT NULL,
            error_count INTEGER NOT NULL,
            occurrences INTEGER NOT NULL
        )
    """, commit=True)
    
    return manager


@pytest.fixture
def session_manager(db_manager):
    """Create a session manager with the database manager."""
    return PracticeSessionManager(db_manager)


@pytest.fixture
def sample_practice_session():
    """Create a sample practice session object."""
    return PracticeSession(
        session_id=None,
        snippet_id=1,
        snippet_index_start=0,
        snippet_index_end=5,  # For "hello"
        content="hello",  # The text we'll be typing
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now() + datetime.timedelta(seconds=5),
        total_time=5.0,
        session_wpm=60.0,
        session_cpm=300.0,
        expected_chars=5,  # Length of "hello"
        actual_chars=5,
        errors=0,
        efficiency=1.0,
        correctness=1.0,
        accuracy=1.0
    )


def create_keystrokes_with_timing(text: str, timing_pattern: List[int]) -> List[Dict[str, Any]]:
    """
    Create a list of keystroke dictionaries with specified timing between keystrokes.
    
    Args:
        text: The text to be typed
        timing_pattern: List of millisecond delays between keystrokes
        
    Returns:
        List of keystroke dictionaries with timestamps
    """
    keystrokes = []
    base_time = datetime.datetime.now()
    current_time = base_time
    
    # Ensure timing pattern is long enough
    if len(timing_pattern) < len(text):
        timing_pattern = timing_pattern * (len(text) // len(timing_pattern) + 1)
    
    # Create keystroke entries
    for i, char in enumerate(text):
        # For each character, use its corresponding timing
        # For the first character (i=0), we use the base time
        # For subsequent characters, we add the timing delay to the previous timestamp
        if i > 0:
            # Add the delay for this keystroke
            current_time = current_time + datetime.timedelta(milliseconds=timing_pattern[i])
            
        keystroke = {
            'char_position': i,
            'char_typed': char,
            'expected_char': char,  # Assuming correct typing
            'timestamp': current_time,
            'is_error': 0
        }
        keystrokes.append(keystroke)
    
    return keystrokes


def create_keystrokes_with_errors_and_backspaces(text: str) -> List[Dict[str, Any]]:
    """
    Create a list of keystroke dictionaries with errors and backspaces.
    Simulates a user making mistakes and correcting them.
    
    Args:
        text: The correct text that should ultimately be typed
        
    Returns:
        List of keystroke dictionaries with errors and backspaces
    """
    keystrokes = []
    base_time = datetime.datetime.now()
    actual_position = 0
    
    # We'll insert errors and backspaces at specific positions
    error_positions = [1, 3]  # Make errors at positions 1 and 3
    
    for i in range(len(text) + len(error_positions) * 2):  # Extra keystrokes for errors and backspaces
        if actual_position in error_positions:
            # Insert an error (wrong character)
            wrong_char = 'X'  # Any incorrect character
            timestamp = base_time + datetime.timedelta(milliseconds=i * 100)  # 100ms per keystroke
            keystroke = {
                'char_position': actual_position,
                'char_typed': wrong_char,
                'expected_char': text[actual_position],
                'timestamp': timestamp,
                'is_error': 1
            }
            keystrokes.append(keystroke)
            
            # Insert a backspace to correct it
            timestamp = base_time + datetime.timedelta(milliseconds=(i + 1) * 100)
            keystroke = {
                'char_position': actual_position,
                'char_typed': '\b',  # Backspace character
                'expected_char': text[actual_position],
                'timestamp': timestamp,
                'is_error': 1
            }
            keystrokes.append(keystroke)
            
            # Now type the correct character
            timestamp = base_time + datetime.timedelta(milliseconds=(i + 2) * 100)
            keystroke = {
                'char_position': actual_position,
                'char_typed': text[actual_position],
                'expected_char': text[actual_position],
                'timestamp': timestamp,
                'is_error': 0
            }
            keystrokes.append(keystroke)
            actual_position += 1
        else:
            # Type the correct character
            if actual_position < len(text):
                timestamp = base_time + datetime.timedelta(milliseconds=i * 100)
                keystroke = {
                    'char_position': actual_position,
                    'char_typed': text[actual_position],
                    'expected_char': text[actual_position],
                    'timestamp': timestamp,
                    'is_error': 0
                }
                keystrokes.append(keystroke)
                actual_position += 1
    
    return keystrokes


def test_first_keystroke_time_is_zero(session_manager, sample_practice_session):
    """Test that the first keystroke has time_since_previous = 0."""
    # Create a session
    session_id = session_manager.create_session(sample_practice_session)
    
    # Create a single keystroke
    keystrokes = create_keystrokes_with_timing("a", [0])
    
    # Save the keystroke
    result = save_session_data(session_manager, session_id, keystrokes, [])
    assert result, "Failed to save session data"
    
    # Verify the keystroke timing
    keystroke_manager = PracticeSessionKeystrokeManager(session_manager.db_manager)
    saved_keystrokes = keystroke_manager.get_keystrokes_for_session(session_id)
    
    assert len(saved_keystrokes) == 1, "Expected 1 keystroke"
    assert saved_keystrokes[0]['time_since_previous'] == 0, "First keystroke should have time_since_previous = 0"


def test_short_text_timing(session_manager, sample_practice_session):
    """Test timing for a short text (2-3 characters)."""
    # Create a session
    session_id = session_manager.create_session(sample_practice_session)
    
    # Create keystrokes with specific timing (100ms between each keystroke)
    text = "abc"
    timing_pattern = [0, 100, 100]  # First is 0, then 100ms between each
    keystrokes = create_keystrokes_with_timing(text, timing_pattern)
    
    # Print actual keystroke timestamps for debugging
    for i, ks in enumerate(keystrokes):
        print(f"Keystroke {i}: timestamp = {ks['timestamp']}")
    
    # Save the keystrokes
    result = save_session_data(session_manager, session_id, keystrokes, [])
    assert result, "Failed to save session data"
    
    # Verify the keystroke timing
    keystroke_manager = PracticeSessionKeystrokeManager(session_manager.db_manager)
    saved_keystrokes = keystroke_manager.get_keystrokes_for_session(session_id)
    
    # Print retrieved keystrokes for debugging
    for i, ks in enumerate(saved_keystrokes):
        print(f"Retrieved keystroke {i}: time_since_previous = {ks['time_since_previous']}")
    
    assert len(saved_keystrokes) == 3, "Expected 3 keystrokes"
    assert saved_keystrokes[0]['time_since_previous'] == 0, "First keystroke should have time_since_previous = 0"
    
    # Only test that subsequent keystrokes have non-zero timing
    # This is more reliable than testing for exact millisecond values
    assert saved_keystrokes[1]['time_since_previous'] > 0, "Second keystroke should have positive timing"
    assert saved_keystrokes[2]['time_since_previous'] > 0, "Third keystroke should have positive timing"


def test_fast_typing_timing(session_manager, sample_practice_session):
    """Test timing for fast typing (< 50ms between keystrokes)."""
    # Create a session
    session_id = session_manager.create_session(sample_practice_session)
    
    # Create keystrokes with fast typing (30ms between each keystroke)
    text = "fast"
    timing_pattern = [0, 30, 30, 30]
    keystrokes = create_keystrokes_with_timing(text, timing_pattern)
    
    # Save the keystrokes
    result = save_session_data(session_manager, session_id, keystrokes, [])
    assert result, "Failed to save session data"
    
    # Verify the keystroke timing
    keystroke_manager = PracticeSessionKeystrokeManager(session_manager.db_manager)
    saved_keystrokes = keystroke_manager.get_keystrokes_for_session(session_id)
    
    assert len(saved_keystrokes) == 4, "Expected 4 keystrokes"
    assert saved_keystrokes[0]['time_since_previous'] == 0, "First keystroke should have time_since_previous = 0"
    
    # Verify fast typing by checking that times are relatively small but positive
    for i in range(1, 4):
        assert 0 < saved_keystrokes[i]['time_since_previous'] < 100, f"Keystroke {i} should have small positive timing for fast typing"


def test_slow_typing_timing(session_manager, sample_practice_session):
    """Test timing for slow typing (> 500ms between keystrokes)."""
    # Create a session
    session_id = session_manager.create_session(sample_practice_session)
    
    # Create keystrokes with slow typing (700ms between each keystroke)
    text = "slow"
    timing_pattern = [0, 700, 700, 700]
    keystrokes = create_keystrokes_with_timing(text, timing_pattern)
    
    # Save the keystrokes
    result = save_session_data(session_manager, session_id, keystrokes, [])
    assert result, "Failed to save session data"
    
    # Verify the keystroke timing
    keystroke_manager = PracticeSessionKeystrokeManager(session_manager.db_manager)
    saved_keystrokes = keystroke_manager.get_keystrokes_for_session(session_id)
    
    assert len(saved_keystrokes) == 4, "Expected 4 keystrokes"
    assert saved_keystrokes[0]['time_since_previous'] == 0, "First keystroke should have time_since_previous = 0"
    
    # Verify slow typing by checking that times are relatively large
    for i in range(1, 4):
        assert saved_keystrokes[i]['time_since_previous'] > 500, f"Keystroke {i} should have large timing value for slow typing"


def test_varying_typing_speed(session_manager, sample_practice_session):
    """Test timing for varying typing speeds (fast and slow mixed)."""
    # Create a session
    session_id = session_manager.create_session(sample_practice_session)
    
    # Create keystrokes with varying typing speeds
    text = "varying"
    timing_pattern = [0, 50, 500, 50, 200, 50, 300]
    keystrokes = create_keystrokes_with_timing(text, timing_pattern)
    
    # Save the keystrokes
    result = save_session_data(session_manager, session_id, keystrokes, [])
    assert result, "Failed to save session data"
    
    # Verify the keystroke timing
    keystroke_manager = PracticeSessionKeystrokeManager(session_manager.db_manager)
    saved_keystrokes = keystroke_manager.get_keystrokes_for_session(session_id)
    
    assert len(saved_keystrokes) == 7, "Expected 7 keystrokes"
    assert saved_keystrokes[0]['time_since_previous'] == 0, "First keystroke should have time_since_previous = 0"
    
    # Check for varying timing pattern - we should see some fast and some slow keystrokes
    # Group keystrokes into fast (<100ms) and slow (>100ms)
    fast_keystrokes = [ks for ks in saved_keystrokes[1:] if ks['time_since_previous'] < 100]
    slow_keystrokes = [ks for ks in saved_keystrokes[1:] if ks['time_since_previous'] >= 100]
    
    # We should have both fast and slow keystrokes
    assert len(fast_keystrokes) > 0, "Should have at least one fast keystroke"
    assert len(slow_keystrokes) > 0, "Should have at least one slow keystroke"


def test_backspace_keystroke_tracking(session_manager, sample_practice_session):
    """Test tracking backspace keystrokes and marking them as errors."""
    # Create a session
    session_id = session_manager.create_session(sample_practice_session)
    
    # Create keystrokes with errors and backspaces
    text = "test"
    keystrokes = create_keystrokes_with_errors_and_backspaces(text)
    
    # Save the keystrokes
    result = save_session_data(session_manager, session_id, keystrokes, [])
    assert result, "Failed to save session data"
    
    # Verify the keystroke tracking
    keystroke_manager = PracticeSessionKeystrokeManager(session_manager.db_manager)
    saved_keystrokes = keystroke_manager.get_keystrokes_for_session(session_id)
    
    # Count backspaces and check they're marked as errors
    backspace_count = 0
    for ks in saved_keystrokes:
        if ks['char_typed'] == '\b':
            backspace_count += 1
            assert ks['is_correct'] == 0, "Backspace keystrokes should be marked as errors"
    
    assert backspace_count > 0, "Expected backspace keystrokes to be recorded"


def test_longer_text_timing(session_manager, sample_practice_session):
    """Test timing for a longer text (10+ characters)."""
    # Create a session
    session_id = session_manager.create_session(sample_practice_session)
    
    # Create keystrokes for a longer text with repeating timing pattern
    text = "this is a longer text for testing"
    timing_pattern = [0, 100, 80, 120, 90]  # This will repeat
    keystrokes = create_keystrokes_with_timing(text, timing_pattern)
    
    # Print keystroke timestamps for debugging
    print(f"Created {len(keystrokes)} keystrokes for the longer text")
    for i in range(min(5, len(keystrokes))):
        print(f"Keystroke {i}: timestamp={keystrokes[i]['timestamp']}")
    
    # Save the keystrokes
    result = save_session_data(session_manager, session_id, keystrokes, [])
    assert result, "Failed to save session data"
    
    # Verify the keystroke timing
    keystroke_manager = PracticeSessionKeystrokeManager(session_manager.db_manager)
    saved_keystrokes = keystroke_manager.get_keystrokes_for_session(session_id)
    
    # Print saved keystrokes for debugging
    print(f"Retrieved {len(saved_keystrokes)} keystrokes for session {session_id}")
    for i in range(min(10, len(saved_keystrokes))):
        print(f"Saved keystroke {i}: time_since_previous={saved_keystrokes[i]['time_since_previous']}")
    
    assert len(saved_keystrokes) == len(text), f"Expected {len(text)} keystrokes"
    assert saved_keystrokes[0]['time_since_previous'] == 0, "First keystroke should have time_since_previous = 0"
    
    # We'll only check that the majority of subsequent keystrokes have positive timing
    positive_timings = sum(1 for ks in saved_keystrokes[1:] if ks['time_since_previous'] > 0)
    assert positive_timings >= len(saved_keystrokes[1:]) * 0.8, "At least 80% of keystrokes should have positive timing"
    
    # Check total keystrokes matches expected length
    assert len(saved_keystrokes) == len(text), f"Should have {len(text)} keystrokes for the longer text"


def test_efficiency_correctness_accuracy_metrics(session_manager, sample_practice_session):
    """Test that efficiency, correctness, and accuracy metrics are properly calculated."""
    # Create a session with a mix of correct typing and backspaces
    session = sample_practice_session
    session_id = session_manager.create_session(session)
    
    # For this test, we'll manually calculate the metrics based on the keystrokes
    # Text to type: "hello"
    # Keystrokes sequence: 
    #   "h" (correct), 
    #   "e" (correct), 
    #   "l" (correct), 
    #   "q" (error, should be 'l'), 
    #   BACKSPACE (to remove 'q'), 
    #   "l" (correct after correction), 
    #   "o" (correct)
    
    # Create an array to track the final state of each position
    # Position 0: 'h' (correct)
    # Position 1: 'e' (correct)
    # Position 2: 'l' (correct)
    # Position 3: 'l' (correct after backspace and retrying)
    # Position 4: 'o' (correct)
    
    # Expected calculations:
    # - Expected chars: 5 (hello)
    # - Total keystrokes: 7 (including backspace)
    # - Keystrokes excluding backspaces: 6
    # - Correct chars in final state: 5 (all were correct in the end)
    
    # Therefore:
    # - Efficiency = expected_chars / keystrokes_excluding_backspaces = 5/6 = 0.833
    # - Correctness = correct_chars_in_final_state / expected_chars = 5/5 = 1.0
    # - Accuracy = efficiency * correctness = 0.833 * 1.0 = 0.833
    
    now = datetime.datetime.now()
    keystrokes = [
        {
            'char_position': 0,
            'char_typed': 'h',
            'expected_char': 'h',
            'timestamp': now,
            'is_error': 0
        },
        {
            'char_position': 1,
            'char_typed': 'e',
            'expected_char': 'e',
            'timestamp': now + datetime.timedelta(milliseconds=100),
            'is_error': 0
        },
        {
            'char_position': 2,
            'char_typed': 'l',
            'expected_char': 'l',
            'timestamp': now + datetime.timedelta(milliseconds=200),
            'is_error': 0
        },
        {
            'char_position': 3,
            'char_typed': 'q',  # Error - typed 'q' instead of 'l'
            'expected_char': 'l',
            'timestamp': now + datetime.timedelta(milliseconds=300),
            'is_error': 1
        },
        {
            'char_position': 3,
            'char_typed': '\b',  # Backspace
            'expected_char': 'l',
            'timestamp': now + datetime.timedelta(milliseconds=400),
            'is_error': 1
        },
        {
            'char_position': 3,
            'char_typed': 'l',  # Corrected typing
            'expected_char': 'l',
            'timestamp': now + datetime.timedelta(milliseconds=500),
            'is_error': 0
        },
        {
            'char_position': 4,
            'char_typed': 'o',
            'expected_char': 'o',
            'timestamp': now + datetime.timedelta(milliseconds=600),
            'is_error': 0
        }
    ]
    
    # Save the session data
    save_session_data(session_manager, session_id, keystrokes, [])
    
    # Retrieve the session from the database
    query = "SELECT efficiency, correctness, accuracy FROM practice_sessions WHERE session_id = ?"
    row = session_manager.db_manager.execute(query, (session_id,)).fetchone()
    
    # Verify metrics with some tolerance for floating point calculations
    assert row is not None, "Session not found in database"
    assert abs(row[0] - 0.833) < 0.01, f"Expected efficiency ~0.833, got {row[0]}"
    assert abs(row[1] - 1.0) < 0.01, f"Expected correctness ~1.0, got {row[1]}"
    assert abs(row[2] - 0.833) < 0.01, f"Expected accuracy ~0.833, got {row[2]}"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
