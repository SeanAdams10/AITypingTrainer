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
from typing import Dict, List, Tuple, Any

import pytest

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from db.database_manager import DatabaseManager
from models.ngram_analyzer import NGramAnalyzer, NGramStats

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
            logger.warning(f"Could not remove temporary database file: {e}")

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
        logger.debug(f"N-gram stats: {ngram_stats}")
        
        # Verify the results
        assert ngram_stats is not None, "analyze_session should return a dictionary"
        
        # Check for expected n-grams (bigrams and trigrams)
        assert '2' in ngram_stats, f"Expected bigrams in results, got: {list(ngram_stats.keys())}"
        assert '3' in ngram_stats, f"Expected trigrams in results, got: {list(ngram_stats.keys())}"
        
        # Get n-gram statistics
        bigrams = ngram_stats['2']
        trigrams = ngram_stats['3']
        
        logger.debug(f"Bigrams found: {list(bigrams.keys())}")
        logger.debug(f"Trigrams found: {list(trigrams.keys())}")
        
        # Check for 'ab' bigram
        assert 'ab' in bigrams, f"Expected 'ab' bigram in results, found: {list(bigrams.keys())}"
        assert bigrams['ab'].count == 1, f"Expected count of 1 for 'ab' bigram, got {bigrams['ab'].count}"
        assert bigrams['ab'].total_time_ms == pytest.approx(1.2, abs=0.01), \
            f"Incorrect timing for 'ab' bigram: expected ~1.2, got {bigrams['ab'].total_time_ms}"
        assert bigrams['ab'].error_count == 0, f"Expected no errors for 'ab' bigram, got {bigrams['ab'].error_count}"
        
        # Check for 'bc' bigram
        assert 'bc' in bigrams, f"Expected 'bc' bigram in results, found: {list(bigrams.keys())}"
        assert bigrams['bc'].count == 1, f"Expected count of 1 for 'bc' bigram, got {bigrams['bc'].count}"
        assert bigrams['bc'].total_time_ms == pytest.approx(0.9, abs=0.01), \
            f"Incorrect timing for 'bc' bigram: expected ~0.9, got {bigrams['bc'].total_time_ms}"
        assert bigrams['bc'].error_count == 0, f"Expected no errors for 'bc' bigram, got {bigrams['bc'].error_count}"
        
        # Check for 'abc' trigram
        assert 'abc' in trigrams, f"Expected 'abc' trigram in results, found: {list(trigrams.keys())}"
        assert trigrams['abc'].count == 1, f"Expected count of 1 for 'abc' trigram, got {trigrams['abc'].count}"
        assert trigrams['abc'].total_time_ms == pytest.approx(2.1, abs=0.01), \
            f"Incorrect timing for 'abc' trigram: expected ~2.1, got {trigrams['abc'].total_time_ms}"
        assert trigrams['abc'].error_count == 0, f"Expected no errors for 'abc' trigram, got {trigrams['abc'].error_count}"
        
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

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
