"""
Tests for n-gram related data models.

This module contains tests for the NGram, Keystroke, and Session data models
used in the n-gram analysis functionality.
"""
from __future__ import annotations

import pytest
from datetime import datetime
from models.ngram_analyzer import NGram
from models.keystroke import Keystroke
from models.session import Session

class TestNGram:
    """Test objective: Verify the NGram data model.
    
    This test ensures that the NGram class correctly encapsulates n-gram data
    and provides proper properties for clean/error state determination.
    """
    
    def test_ngram_initialization(self):
        """Test objective: Verify proper initialization of NGram objects."""
        # Test clean n-gram
        clean = NGram("test", 4, 100.0)
        assert clean.ngram == "test"
        assert clean.ngram_size == 4
        assert clean.total_time_ms == 100.0
        assert not clean.has_error_on_last
        assert not clean.has_other_errors
        assert clean.occurrences == 1
        
        # Test n-gram with error on last character
        error_last = NGram("test", 4, 150.0, has_error_on_last=True)
        assert error_last.has_error_on_last
        assert not error_last.has_other_errors
        
        # Test n-gram with other errors
        other_errors = NGram("test", 4, 200.0, has_other_errors=True)
        assert not other_errors.has_error_on_last
        assert other_errors.has_other_errors
    
    def test_ngram_properties(self):
        """Test objective: Verify NGram property calculations."""
        # Test clean n-gram
        clean = NGram("test", 4, 100.0)
        assert clean.is_clean
        assert not clean.is_error
        assert clean.is_valid
        assert clean.chars_per_second == 40.0  # 4 chars / 0.1s = 40 cps
        assert clean.chars_per_millisecond == 0.04  # 4 chars / 100ms = 0.04 c/ms
        
        # Test error n-gram
        error = NGram("test", 4, 100.0, has_error_on_last=True)
        assert not error.is_clean
        assert error.is_error
        assert error.is_valid
        
        # Test invalid n-gram
        invalid = NGram("test", 4, 100.0, has_other_errors=True)
        assert not invalid.is_clean
        assert not invalid.is_error
        assert not invalid.is_valid


class TestKeystroke:
    """Test objective: Verify the Keystroke data model.
    
    This test ensures that the Keystroke class correctly encapsulates
    keystroke data including character, timing, and correctness information.
    """
    
    def test_keystroke_initialization(self):
        """Test objective: Verify proper initialization of Keystroke objects."""
        # Test correct keystroke
        ks = Keystroke(
            keystroke_id=1,
            keystroke_char="a",
            expected_char="a",
            is_correct=True,
            time_since_previous=100.0,
            keystroke_time=1000.0
        )
        
        assert ks.keystroke_id == 1
        assert ks.keystroke_char == "a"
        assert ks.expected_char == "a"
        assert ks.is_correct is True
        assert ks.time_since_previous == 100.0
        assert ks.keystroke_time == 1000.0
        
        # Test error keystroke
        error_ks = Keystroke(
            keystroke_id=2,
            keystroke_char="b",
            expected_char="c",
            is_correct=False,
            time_since_previous=150.0,
            keystroke_time=1150.0
        )
        
        assert error_ks.keystroke_char == "b"
        assert error_ks.expected_char == "c"
        assert error_ks.is_correct is False


class TestSession:
    """Test objective: Verify the Session data model.
    
    This test ensures that the Session class correctly encapsulates
    typing session data including session ID and content.
    """
    
    def test_session_initialization(self):
        """Test objective: Verify proper initialization of Session objects."""
        session_id = "test_session_123"
        content = "Sample typing content"
        
        session = Session(session_id, content)
        
        assert session.session_id == session_id
        assert session.content == content


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__]))
