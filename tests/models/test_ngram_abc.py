"""
Tests for the NGramAnalyzer class with ABC sequence.

These tests verify the n-gram analysis for the specific ABC sequence.
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
from datetime import datetime
from typing import List, Tuple

import pytest

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from db.database_manager import DatabaseManager
from models.ngram_analyzer import NGramAnalyzer

# Enable debug logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Use a temporary file that will be automatically cleaned up
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database with required tables
        db = DatabaseManager(db_path)
        db.init_tables()
        yield db
    finally:
        # Cleanup
        if 'db' in locals():
            db.close()
        try:
            os.unlink(db_path)
        except (OSError, PermissionError) as e:
            logger.warning("Could not remove temporary database file: %s", e)

def insert_test_session(db: DatabaseManager, session_id: str, content: str, keystrokes: List[Tuple]) -> None:
    """Helper function to insert a test session with keystrokes."""
    now = datetime.now().isoformat()
    
    # Create a test session
    db.execute(
        """
        INSERT INTO practice_sessions 
        (session_id, content, start_time, end_time, total_time, session_wpm, session_cpm, 
         expected_chars, actual_chars, errors, efficiency, correctness, accuracy)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, content, now, now, 0, 0, 0, len(content), len(content), 0, 1.0, 1.0, 100.0),
        commit=True
    )
    
    # Insert test keystrokes
    for idx, (char, expected, is_correct, time_since_prev) in enumerate(keystrokes, 1):
        db.execute(
            """
            INSERT INTO session_keystrokes 
            (session_id, keystroke_id, keystroke_time, keystroke_char, 
             expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, idx, now, char, expected, int(is_correct), time_since_prev),
            commit=True
        )

class TestNGramAnalyzerABC:
    """Test suite for NGramAnalyzer class with ABC sequence."""
    
    def test_abc_sequence_ngram_analysis(self, temp_db: DatabaseManager):
        """Test n-gram analysis for sequence 'a', 'b', 'c' with specific timings.
        
        This test verifies that:
        - Keystrokes 'a', 'b', 'c' with timings 0.0, 1.2, 0.9 seconds
        - Correctly generates n-grams: 'ab' (1.2s), 'bc' (0.9s), 'abc' (2.1s)
        - No n-gram errors are recorded
        """
        # Setup test data
        session_id = "test_abc_session"
        
        # Insert test session with keystrokes
        # time_since_previous is the time since the previous keystroke
        keystrokes = [
            ('a', 'a', True, 0.0),    # First keystroke, no time since previous
            ('b', 'b', True, 1.2),    # 1.2s after first keystroke
            ('c', 'c', True, 0.9)     # 0.9s after second keystroke (2.1s total)
        ]
        insert_test_session(temp_db, session_id, 'abc', keystrokes)
        
        # Initialize and run n-gram analysis
        analyzer = NGramAnalyzer(temp_db)
        ngram_stats = analyzer.analyze_session(session_id)
        
        # Print debug info
        logger.debug("N-gram stats: %s", ngram_stats)
        
        # Verify the results
        assert ngram_stats is not None, "analyze_session should return a dictionary"
        
        # Check for expected n-grams (bigrams and trigrams)
        assert '2' in ngram_stats, \
            f"Expected bigrams in results, got: {list(ngram_stats.keys())}"
        assert '3' in ngram_stats, \
            f"Expected trigrams in results, got: {list(ngram_stats.keys())}"
        
        # Get n-gram statistics
        bigrams = ngram_stats['2']
        trigrams = ngram_stats['3']
        
        logger.debug("Bigrams found: %s", list(bigrams.keys()))
        logger.debug("Trigrams found: %s", list(trigrams.keys()))
        
        # Check for 'ab' bigram
        ab_bigram = bigrams['ab']
        assert 'ab' in bigrams, \
            f"Expected 'ab' bigram in results, found: {list(bigrams.keys())}"
        assert ab_bigram.total_time_ms == pytest.approx(1.2, abs=0.01), \
            f"Incorrect timing for 'ab' bigram: expected ~1.2, got {ab_bigram.total_time_ms}"
        assert ab_bigram.error_count == 0, \
            f"Expected no errors for 'ab' bigram, got {ab_bigram.error_count}"
        
        # Check for 'bc' bigram
        bc_bigram = bigrams['bc']
        assert 'bc' in bigrams, \
            f"Expected 'bc' bigram in results, found: {list(bigrams.keys())}"
        assert bc_bigram.total_time_ms == pytest.approx(0.9, abs=0.01), \
            f"Incorrect timing for 'bc' bigram: expected ~0.9, got {bc_bigram.total_time_ms}"
        assert bc_bigram.error_count == 0, \
            f"Expected no errors for 'bc' bigram, got {bc_bigram.error_count}"
        
        # Check for 'abc' trigram
        abc_trigram = trigrams['abc']
        assert 'abc' in trigrams, \
            f"Expected 'abc' trigram in results, found: {list(trigrams.keys())}"
        assert abc_trigram.total_time_ms == pytest.approx(2.1, abs=0.01), \
            f"Incorrect timing for 'abc' trigram: expected ~2.1, got {abc_trigram.total_time_ms}"
        assert abc_trigram.error_count == 0, \
            f"Expected no errors for 'abc' trigram, got {abc_trigram.error_count}"
        
        # Verify no error n-grams were recorded in the database
        error_results = temp_db.execute(
            """
            SELECT ngram, ngram_size 
            FROM session_ngram_errors 
            WHERE session_id = ?
            """,
            (session_id,)
        ).fetchall()
        
        assert len(error_results) == 0, f"Expected no error n-grams, but found {len(error_results)}"

    def test_th_sequence_ngram_analysis(self, temp_db: DatabaseManager):
        """Test n-gram analysis for sequence 'T', 'h' with specific timing of 1 second.
        
        This test verifies that:
        - Keystrokes 'T', 'h' with timing of 1.0 second
        - Correctly generates a bigram: 'Th' (1.0s)
        - No n-gram errors are recorded
        """
        # Setup test data
        session_id = "test_th_session"
        
        # Insert test session with keystrokes
        # time_since_previous is the time since the previous keystroke
        keystrokes = [
            ('T', 'T', True, 0.0),    # First keystroke, no time since previous
            ('h', 'h', True, 1.0)     # 1.0s after first keystroke
        ]
        insert_test_session(temp_db, session_id, 'Th', keystrokes)
        
        # Initialize and run n-gram analysis
        analyzer = NGramAnalyzer(temp_db)
        ngram_stats = analyzer.analyze_session(session_id)
        
        # Print debug info
        logger.debug("N-gram stats for Th sequence: %s", ngram_stats)
        
        # Verify the results
        assert ngram_stats is not None, "analyze_session should return a dictionary"
        
        # Check for expected n-grams (bigrams)
        assert '2' in ngram_stats, \
            f"Expected bigrams in results, got: {list(ngram_stats.keys())}"
        
        # Get n-gram statistics
        bigrams = ngram_stats['2']
        
        logger.debug("Bigrams found: %s", list(bigrams.keys()))
        
        # Check for 'Th' bigram
        assert 'Th' in bigrams, \
            f"Expected 'Th' bigram in results, found: {list(bigrams.keys())}"
        
        th_bigram = bigrams['Th']
        assert th_bigram.total_time_ms == pytest.approx(1.0, abs=0.01), \
            f"Incorrect timing for 'Th' bigram: expected ~1.0, got {th_bigram.total_time_ms}"
        assert th_bigram.error_count == 0, \
            f"Expected no errors for 'Th' bigram, got {th_bigram.error_count}"
        
        # Verify ngram was recorded in the session_ngram_speed table
        ngram_results = temp_db.execute(
            """
            SELECT ngram, ngram_time_ms, ngram_size
            FROM session_ngram_speed
            WHERE session_id = ? AND ngram = 'Th'
            """,
            (session_id,)
        ).fetchall()
        
        assert len(ngram_results) == 1, f"Expected 1 'Th' ngram entry, found {len(ngram_results)}"
        ngram, ngram_time_ms, ngram_size = ngram_results[0]
        assert ngram == 'Th', f"Expected ngram 'Th', got '{ngram}'"
        # Despite column name having 'ms', the actual value is stored in seconds
        assert ngram_time_ms == pytest.approx(1.0, abs=0.01), f"Expected time ~1.0s, got {ngram_time_ms}s"
        assert ngram_size == 2, f"Expected ngram_size 2, got {ngram_size}"
        
        # Verify no error n-grams were recorded
        error_results = temp_db.execute(
            """
            SELECT ngram, ngram_size 
            FROM session_ngram_errors 
            WHERE session_id = ?
            """,
            (session_id,)
        ).fetchall()
        
        assert len(error_results) == 0, f"Expected no error n-grams, but found {len(error_results)}"

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
