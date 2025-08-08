"""
Tests for the new N-Gram Manager implementation.

This module tests the NGramManager class according to the updated
specification in ngram.md, including speed modes, classification logic,
timing calculations, and batch operations.
"""

import math
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# Add parent directory to path to allow importing from models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from models.ngram_new_manager import NGramManager
from models.ngram_new import (
    SpeedNGram, ErrorNGram, Keystroke, SpeedMode, NGramClassifier,
    MIN_NGRAM_SIZE, MAX_NGRAM_SIZE, SEQUENCE_SEPARATORS
)


class MockDB:
    """Mock database for testing."""

    def __init__(self, results=None, supports_batch=True):
        self.results = results or []
        self.last_query = None
        self.last_params = None
        self.execute_calls = []
        self.executemany_calls = []
        self._supports_batch = supports_batch

    def execute(self, query, params=()):
        self.last_query = query
        self.last_params = params
        self.execute_calls.append((query, params))
        return MagicMock()

    def executemany(self, query, data):
        self.executemany_calls.append((query, data))
        return MagicMock()

    def fetchall(self, query, params=()):
        self.last_query = query
        self.last_params = params
        return self.results

    def supports_batch_operations(self):
        return self._supports_batch


@pytest.fixture
def mock_db():
    """Create a mock database with test data."""
    return MockDB()


@pytest.fixture
def mock_db_no_batch():
    """Create a mock database without batch support."""
    return MockDB(supports_batch=False)


@pytest.fixture
def ngram_manager(mock_db):
    """Create an NGramManager instance with a mock database."""
    return NGramManager(mock_db)


@pytest.fixture
def sample_keystrokes():
    """Create sample keystroke data for testing."""
    session_id = uuid4()
    base_time = datetime.utcnow()
    
    return [
        Keystroke(
            id=uuid4(),
            session_id=session_id,
            timestamp=base_time,
            text_index=0,
            expected_char="t",
            actual_char="t",
            is_correct=True
        ),
        Keystroke(
            id=uuid4(),
            session_id=session_id,
            timestamp=base_time + timedelta(milliseconds=50),
            text_index=1,
            expected_char="h",
            actual_char="h",
            is_correct=True
        ),
        Keystroke(
            id=uuid4(),
            session_id=session_id,
            timestamp=base_time + timedelta(milliseconds=100),
            text_index=2,
            expected_char="e",
            actual_char="e",
            is_correct=True
        )
    ]


@pytest.fixture
def error_keystrokes():
    """Create sample keystroke data with errors for testing."""
    session_id = uuid4()
    base_time = datetime.utcnow()
    
    return [
        Keystroke(
            id=uuid4(),
            session_id=session_id,
            timestamp=base_time,
            text_index=0,
            expected_char="t",
            actual_char="t",
            is_correct=True
        ),
        Keystroke(
            id=uuid4(),
            session_id=session_id,
            timestamp=base_time + timedelta(milliseconds=50),
            text_index=1,
            expected_char="h",
            actual_char="h",
            is_correct=True
        ),
        Keystroke(
            id=uuid4(),
            session_id=session_id,
            timestamp=base_time + timedelta(milliseconds=100),
            text_index=2,
            expected_char="e",
            actual_char="x",  # Error in last position
            is_correct=False
        )
    ]


class TestNGramManagerBasics:
    """Test basic NGramManager functionality."""

    def test_initialization(self, mock_db):
        """Test NGramManager initialization."""
        manager = NGramManager(mock_db)
        assert manager.db == mock_db

    def test_initialization_no_db(self):
        """Test NGramManager initialization without database."""
        manager = NGramManager(None)
        assert manager.db is None

    def test_delete_all_ngrams_success(self, ngram_manager, mock_db):
        """Test successful deletion of all n-gram data."""
        result = ngram_manager.delete_all_ngrams()
        
        assert result is True
        assert len(mock_db.execute_calls) == 2
        
        # Check that both tables were cleared
        queries = [call[0] for call in mock_db.execute_calls]
        assert "DELETE FROM session_ngram_speed" in queries
        assert "DELETE FROM session_ngram_errors" in queries

    def test_delete_all_ngrams_no_db(self):
        """Test deletion with no database connection."""
        manager = NGramManager(None)
        result = manager.delete_all_ngrams()
        assert result is False


class TestInputValidation:
    """Test input validation methods."""

    def test_validate_input_valid(self, ngram_manager):
        """Test valid input validation."""
        result = ngram_manager._validate_input("test-session-id", "raw")
        assert result is True

        result = ngram_manager._validate_input("test-session-id", "net")
        assert result is True

    def test_validate_input_invalid_session_id(self, ngram_manager):
        """Test invalid session ID validation."""
        assert ngram_manager._validate_input(None, "raw") is False
        assert ngram_manager._validate_input("", "raw") is False
        assert ngram_manager._validate_input("   ", "raw") is False

    def test_validate_input_invalid_speed_mode(self, ngram_manager):
        """Test invalid speed mode validation."""
        assert ngram_manager._validate_input("test-id", "invalid") is False
        assert ngram_manager._validate_input("test-id", "RAW") is False  # Case sensitive
        assert ngram_manager._validate_input("test-id", "") is False

    def test_validate_input_no_db(self):
        """Test validation with no database connection."""
        manager = NGramManager(None)
        result = manager._validate_input("test-id", "raw")
        assert result is False


class TestNGramExtraction:
    """Test n-gram extraction functionality."""

    def test_extract_ngrams_basic(self, ngram_manager, sample_keystrokes):
        """Test basic n-gram extraction."""
        expected_text = "the"
        ngrams = ngram_manager.extract_ngrams(sample_keystrokes, expected_text, 2)
        
        expected_ngrams = ["th", "he"]
        assert ngrams == expected_ngrams

    def test_extract_ngrams_size_3(self, ngram_manager, sample_keystrokes):
        """Test 3-gram extraction."""
        expected_text = "the"
        ngrams = ngram_manager.extract_ngrams(sample_keystrokes, expected_text, 3)
        
        expected_ngrams = ["the"]
        assert ngrams == expected_ngrams

    def test_extract_ngrams_with_separators(self, ngram_manager, sample_keystrokes):
        """Test n-gram extraction with sequence separators."""
        expected_text = "hi there"
        ngrams = ngram_manager.extract_ngrams(sample_keystrokes, expected_text, 2)
        
        # Should extract "hi" (stops at space), then "th", "he", "er", "re"
        expected_ngrams = ["hi", "th", "he", "er", "re"]
        assert ngrams == expected_ngrams

    def test_extract_ngrams_invalid_size(self, ngram_manager, sample_keystrokes):
        """Test extraction with invalid n-gram size."""
        expected_text = "test"
        
        # Too small
        ngrams = ngram_manager.extract_ngrams(sample_keystrokes, expected_text, 1)
        assert ngrams == []
        
        # Too large
        ngrams = ngram_manager.extract_ngrams(sample_keystrokes, expected_text, MAX_NGRAM_SIZE + 1)
        assert ngrams == []

    def test_extract_ngrams_text_too_short(self, ngram_manager, sample_keystrokes):
        """Test extraction when text is shorter than n-gram size."""
        expected_text = "a"
        ngrams = ngram_manager.extract_ngrams(sample_keystrokes, expected_text, 2)
        assert ngrams == []

    def test_extract_ngrams_empty_text(self, ngram_manager, sample_keystrokes):
        """Test extraction with empty text."""
        ngrams = ngram_manager.extract_ngrams(sample_keystrokes, "", 2)
        assert ngrams == []


class TestNGramClassification:
    """Test n-gram classification logic."""

    def test_classify_clean_ngram(self, ngram_manager, sample_keystrokes):
        """Test classification of clean n-grams."""
        classification = ngram_manager.classify_ngram("th", sample_keystrokes, 0)
        assert classification == NGramClassifier.CLEAN

    def test_classify_error_ngram(self, ngram_manager, error_keystrokes):
        """Test classification of error n-grams."""
        classification = ngram_manager.classify_ngram("th", error_keystrokes, 1)
        assert classification == NGramClassifier.ERROR

    def test_classify_ignored_ngram_with_separators(self, ngram_manager, sample_keystrokes):
        """Test classification of n-grams with sequence separators."""
        classification = ngram_manager.classify_ngram("t h", sample_keystrokes, 0)
        assert classification == NGramClassifier.IGNORED

    def test_classify_ignored_ngram_invalid_size(self, ngram_manager, sample_keystrokes):
        """Test classification with invalid n-gram size."""
        classification = ngram_manager.classify_ngram("t", sample_keystrokes, 0)  # Size 1
        assert classification == NGramClassifier.IGNORED

    def test_classify_ignored_ngram_missing_keystrokes(self, ngram_manager):
        """Test classification when keystrokes are missing."""
        empty_keystrokes = []
        classification = ngram_manager.classify_ngram("th", empty_keystrokes, 0)
        assert classification == NGramClassifier.IGNORED


class TestTimingCalculation:
    """Test timing calculation with gross-up logic."""

    def test_calculate_timing_basic(self, ngram_manager, sample_keystrokes):
        """Test basic timing calculation."""
        # Keystrokes are 50ms apart, so "th" raw duration is 50ms
        # With gross-up formula: (50ms / (2-1)) * 2 = 100ms
        duration = ngram_manager.calculate_timing(sample_keystrokes, 0, 2)
        assert duration == 100.0

    def test_calculate_timing_gross_up_at_start(self, ngram_manager):
        """Test gross-up logic when n-gram is at sequence start."""
        session_id = uuid4()
        base_time = datetime.utcnow()
        
        keystrokes = [
            Keystroke(
                session_id=session_id,
                timestamp=base_time,
                text_index=0,
                expected_char="a",
                actual_char="a",
                is_correct=True
            ),
            Keystroke(
                session_id=session_id,
                timestamp=base_time + timedelta(milliseconds=100),
                text_index=1,
                expected_char="b",
                actual_char="b",
                is_correct=True
            )
        ]
        
        # At start (start_index=0), should use gross-up: (100 / (2-1)) * 2 = 200ms
        duration = ngram_manager.calculate_timing(keystrokes, 0, 2)
        assert duration == 200.0

    def test_calculate_timing_with_preceding_character(self, ngram_manager):
        """Test timing calculation with preceding character (no gross-up)."""
        session_id = uuid4()
        base_time = datetime.utcnow()
        
        keystrokes = [
            Keystroke(
                session_id=session_id,
                timestamp=base_time,
                text_index=0,
                expected_char="a",
                actual_char="a",
                is_correct=True
            ),
            Keystroke(
                session_id=session_id,
                timestamp=base_time + timedelta(milliseconds=50),
                text_index=1,
                expected_char="b",
                actual_char="b",
                is_correct=True
            ),
            Keystroke(
                session_id=session_id,
                timestamp=base_time + timedelta(milliseconds=150),
                text_index=2,
                expected_char="c",
                actual_char="c",
                is_correct=True
            )
        ]
        
        # For "bc" starting at index 1, should use actual time from index 0 to 2: 150ms
        duration = ngram_manager.calculate_timing(keystrokes, 1, 2)
        assert duration == 150.0

    def test_calculate_timing_negative_duration(self, ngram_manager):
        """Test handling of negative duration (out-of-order timestamps)."""
        session_id = uuid4()
        base_time = datetime.utcnow()
        
        keystrokes = [
            Keystroke(
                session_id=session_id,
                timestamp=base_time + timedelta(milliseconds=100),  # Later timestamp
                text_index=0,
                expected_char="a",
                actual_char="a",
                is_correct=True
            ),
            Keystroke(
                session_id=session_id,
                timestamp=base_time,  # Earlier timestamp
                text_index=1,
                expected_char="b",
                actual_char="b",
                is_correct=True
            )
        ]
        
        duration = ngram_manager.calculate_timing(keystrokes, 0, 2)
        assert duration == 0.0  # Should return 0 for invalid timing

    def test_calculate_timing_single_character(self, ngram_manager):
        """Test timing calculation for single character."""
        session_id = uuid4()
        base_time = datetime.utcnow()
        
        keystrokes = [
            Keystroke(
                session_id=session_id,
                timestamp=base_time,
                text_index=0,
                expected_char="a",
                actual_char="a",
                is_correct=True
            )
        ]
        
        duration = ngram_manager.calculate_timing(keystrokes, 0, 1)
        assert duration == 0.0  # Single character has no duration


class TestSpeedModeProcessing:
    """Test speed mode processing (raw vs net)."""

    def test_apply_speed_mode_raw(self, ngram_manager):
        """Test raw speed mode (no filtering)."""
        session_id = uuid4()
        base_time = datetime.utcnow()
        
        keystrokes = [
            Keystroke(session_id=session_id, timestamp=base_time, text_index=0, 
                     expected_char="a", actual_char="a", is_correct=True),
            Keystroke(session_id=session_id, timestamp=base_time + timedelta(milliseconds=50), 
                     text_index=1, expected_char="b", actual_char="x", is_correct=False),
            Keystroke(session_id=session_id, timestamp=base_time + timedelta(milliseconds=100), 
                     text_index=1, expected_char="b", actual_char="b", is_correct=True),  # Correction
        ]
        
        filtered = ngram_manager._apply_speed_mode(keystrokes, SpeedMode.RAW.value)
        assert len(filtered) == 3  # All keystrokes preserved

    def test_apply_speed_mode_net(self, ngram_manager):
        """Test net speed mode (filters corrections)."""
        session_id = uuid4()
        base_time = datetime.utcnow()
        
        keystrokes = [
            Keystroke(session_id=session_id, timestamp=base_time, text_index=0, 
                     expected_char="a", actual_char="a", is_correct=True),
            Keystroke(session_id=session_id, timestamp=base_time + timedelta(milliseconds=50), 
                     text_index=1, expected_char="b", actual_char="x", is_correct=False),
            Keystroke(session_id=session_id, timestamp=base_time + timedelta(milliseconds=100), 
                     text_index=1, expected_char="b", actual_char="b", is_correct=True),  # Correction
            Keystroke(session_id=session_id, timestamp=base_time + timedelta(milliseconds=150), 
                     text_index=2, expected_char="c", actual_char="c", is_correct=True),
        ]
        
        filtered = ngram_manager._apply_speed_mode(keystrokes, SpeedMode.NET.value)
        assert len(filtered) == 3  # Should keep only last occurrence of each text_index
        
        # Check that the correction (text_index=1) kept the final keystroke
        text_index_1_keystroke = next(k for k in filtered if k.text_index == 1)
        assert text_index_1_keystroke.actual_char == "b"  # Corrected version
        assert text_index_1_keystroke.is_correct is True

    def test_clone_keystrokes(self, ngram_manager, sample_keystrokes):
        """Test keystroke cloning for separate processing."""
        cloned = ngram_manager._clone_keystrokes(sample_keystrokes)
        
        assert len(cloned) == len(sample_keystrokes)
        assert cloned is not sample_keystrokes  # Different objects
        
        # Modify clone and ensure original is unchanged
        cloned[0].actual_char = "modified"
        assert sample_keystrokes[0].actual_char != "modified"


class TestBatchOperations:
    """Test batch database operations."""

    def test_save_ngrams_batch_with_support(self, mock_db):
        """Test batch saving when database supports batch operations."""
        manager = NGramManager(mock_db)
        
        speed_ngrams = [
            SpeedNGram(
                id=uuid4(),
                session_id=uuid4(),
                size=2,
                text="th",
                duration_ms=100.0,
                ms_per_keystroke=50.0,
                speed_mode=SpeedMode.RAW
            )
        ]
        
        error_ngrams = [
            ErrorNGram(
                id=uuid4(),
                session_id=uuid4(),
                size=2,
                expected_text="he",
                actual_text="hx",
                duration_ms=120.0
            )
        ]
        
        result = manager._save_ngrams_batch(speed_ngrams, error_ngrams)
        assert result is True
        
        # Should use executemany for batch operations
        assert len(mock_db.executemany_calls) == 2

    def test_save_ngrams_batch_without_support(self, mock_db_no_batch):
        """Test batch saving when database doesn't support batch operations."""
        manager = NGramManager(mock_db_no_batch)
        
        speed_ngrams = [
            SpeedNGram(
                id=uuid4(),
                session_id=uuid4(),
                size=2,
                text="th",
                duration_ms=100.0,
                ms_per_keystroke=50.0,
                speed_mode=SpeedMode.RAW
            )
        ]
        
        error_ngrams = []
        
        result = manager._save_ngrams_batch(speed_ngrams, error_ngrams)
        assert result is True
        
        # Should use individual execute calls
        assert len(mock_db_no_batch.execute_calls) == 1
        assert len(mock_db_no_batch.executemany_calls) == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_analyze_session_empty_keystrokes(self, ngram_manager):
        """Test analysis with empty keystrokes."""
        with patch.object(ngram_manager, '_get_session') as mock_get_session:
            mock_get_session.return_value = {
                'keystrokes': [],
                'expected_text': 'test'
            }
            
            result = ngram_manager.analyze_session("test-session", "raw")
            assert result is True  # Should succeed but do nothing

    def test_analyze_session_empty_expected_text(self, ngram_manager):
        """Test analysis with empty expected text."""
        with patch.object(ngram_manager, '_get_session') as mock_get_session:
            mock_get_session.return_value = {
                'keystrokes': [{'char': 'a'}],
                'expected_text': ''
            }
            
            result = ngram_manager.analyze_session("test-session", "raw")
            assert result is True  # Should succeed but do nothing

    def test_analyze_session_nonexistent_session(self, ngram_manager):
        """Test analysis with nonexistent session."""
        with patch.object(ngram_manager, '_get_session') as mock_get_session:
            mock_get_session.return_value = None
            
            result = ngram_manager.analyze_session("nonexistent", "raw")
            assert result is False

    def test_convert_to_keystroke_objects_various_formats(self, ngram_manager):
        """Test conversion of various keystroke formats."""
        session_id = str(uuid4())
        
        # Test with dictionary format
        dict_keystroke = {
            'timestamp': datetime.utcnow(),
            'text_index': 0,
            'expected_char': 'a',
            'actual_char': 'a',
            'is_correct': True
        }
        
        # Test with object format (mock)
        class MockKeystroke:
            def __init__(self):
                self.timestamp = datetime.utcnow()
                self.text_index = 1
                self.expected = 'b'
                self.char = 'b'
                self.is_correct = True
        
        keystrokes_data = [dict_keystroke, MockKeystroke()]
        
        converted = ngram_manager._convert_to_keystroke_objects(keystrokes_data, session_id)
        
        assert len(converted) == 2
        assert all(isinstance(k, Keystroke) for k in converted)
        assert converted[0].expected_char == 'a'
        assert converted[1].expected_char == 'b'

    def test_unicode_handling(self, ngram_manager):
        """Test handling of Unicode characters in n-grams."""
        session_id = uuid4()
        base_time = datetime.utcnow()
        
        unicode_keystrokes = [
            Keystroke(
                session_id=session_id,
                timestamp=base_time,
                text_index=0,
                expected_char="é",
                actual_char="é",
                is_correct=True
            ),
            Keystroke(
                session_id=session_id,
                timestamp=base_time + timedelta(milliseconds=50),
                text_index=1,
                expected_char="ñ",
                actual_char="ñ",
                is_correct=True
            )
        ]
        
        ngrams = ngram_manager.extract_ngrams(unicode_keystrokes, "éñ", 2)
        assert ngrams == ["éñ"]
        
        classification = ngram_manager.classify_ngram("éñ", unicode_keystrokes, 0)
        assert classification == NGramClassifier.CLEAN


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_analysis_workflow_clean_ngrams(self, mock_db):
        """Test complete analysis workflow with clean n-grams."""
        manager = NGramManager(mock_db)
        
        # Mock session data
        session_id = str(uuid4())
        session_data = {
            'keystrokes': [
                {
                    'timestamp': datetime.utcnow(),
                    'text_index': 0,
                    'expected_char': 't',
                    'actual_char': 't',
                    'is_correct': True
                },
                {
                    'timestamp': datetime.utcnow() + timedelta(milliseconds=50),
                    'text_index': 1,
                    'expected_char': 'h',
                    'actual_char': 'h',
                    'is_correct': True
                },
                {
                    'timestamp': datetime.utcnow() + timedelta(milliseconds=100),
                    'text_index': 2,
                    'expected_char': 'e',
                    'actual_char': 'e',
                    'is_correct': True
                }
            ],
            'expected_text': 'the'
        }
        
        with patch.object(manager, '_get_session') as mock_get_session:
            mock_get_session.return_value = session_data
            
            result = manager.analyze_session(session_id, "raw")
            assert result is True
            
            # Should have saved speed n-grams (th, he, the)
            assert len(mock_db.executemany_calls) >= 1

    def test_performance_with_large_text(self, ngram_manager):
        """Test performance with large expected text."""
        large_text = "a" * 1000  # 1000 character text
        session_id = uuid4()
        
        # Create corresponding keystrokes
        keystrokes = []
        base_time = datetime.utcnow()
        for i, char in enumerate(large_text):
            keystrokes.append(Keystroke(
                session_id=session_id,
                timestamp=base_time + timedelta(milliseconds=i * 10),
                text_index=i,
                expected_char=char,
                actual_char=char,
                is_correct=True
            ))
        
        # Test extraction for various n-gram sizes
        for size in [2, 5, 10]:
            ngrams = ngram_manager.extract_ngrams(keystrokes, large_text, size)
            expected_count = len(large_text) - size + 1
            assert len(ngrams) == expected_count


if __name__ == "__main__":
    pytest.main(["-v", __file__])
