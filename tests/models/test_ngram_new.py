"""
Tests for the new N-Gram data models.

This module tests the SpeedNGram, ErrorNGram, and Keystroke models
according to the updated specification in ngram.md.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from models.ngram_new import (
    SpeedNGram, ErrorNGram, Keystroke, SpeedMode, NGramClassifier,
    MIN_NGRAM_SIZE, MAX_NGRAM_SIZE, SEQUENCE_SEPARATORS,
    validate_ngram_size, has_sequence_separators, is_valid_ngram_text
)


class TestSpeedNGram:
    """Test cases for SpeedNGram model."""

    def test_speed_ngram_creation_valid(self):
        """Test creating a valid SpeedNGram."""
        session_id = uuid4()
        ngram_id = uuid4()
        created_at = datetime.utcnow()
        
        ngram = SpeedNGram(
            id=ngram_id,
            session_id=session_id,
            size=3,
            text="the",
            duration_ms=150.0,
            ms_per_keystroke=50.0,
            speed_mode=SpeedMode.RAW,
            created_at=created_at
        )
        
        assert ngram.id == ngram_id
        assert ngram.session_id == session_id
        assert ngram.size == 3
        assert ngram.text == "the"
        assert ngram.duration_ms == 150.0
        assert ngram.ms_per_keystroke == 50.0
        assert ngram.speed_mode == SpeedMode.RAW
        assert ngram.created_at == created_at

    def test_speed_ngram_auto_calculate_ms_per_keystroke(self):
        """Test automatic calculation of ms_per_keystroke."""
        ngram = SpeedNGram(
            id=uuid4(),
            session_id=uuid4(),
            size=4,
            text="test",
            duration_ms=200.0,
            ms_per_keystroke=0,  # Should be auto-calculated
            speed_mode=SpeedMode.NET
        )
        
        assert ngram.ms_per_keystroke == 50.0  # 200.0 / 4

    def test_speed_ngram_size_validation(self):
        """Test n-gram size validation."""
        # Valid sizes
        for size in [MIN_NGRAM_SIZE, 5, 10, MAX_NGRAM_SIZE]:
            ngram = SpeedNGram(
                id=uuid4(),
                session_id=uuid4(),
                size=size,
                text="a" * size,
                duration_ms=100.0,
                ms_per_keystroke=20.0,
                speed_mode=SpeedMode.RAW
            )
            assert ngram.size == size

        # Invalid sizes
        for invalid_size in [0, 1, MAX_NGRAM_SIZE + 1, 100]:
            with pytest.raises(ValidationError):
                SpeedNGram(
                    id=uuid4(),
                    session_id=uuid4(),
                    size=invalid_size,
                    text="test",
                    duration_ms=100.0,
                    ms_per_keystroke=20.0,
                    speed_mode=SpeedMode.RAW
                )

    def test_speed_ngram_sequence_separator_validation(self):
        """Test that sequence separators are rejected."""
        for separator in SEQUENCE_SEPARATORS:
            with pytest.raises(ValidationError, match="sequence separator"):
                SpeedNGram(
                    id=uuid4(),
                    session_id=uuid4(),
                    size=3,
                    text=f"te{separator}st",
                    duration_ms=100.0,
                    ms_per_keystroke=33.33,
                    speed_mode=SpeedMode.RAW
                )

    def test_speed_ngram_positive_duration_required(self):
        """Test that duration must be positive."""
        with pytest.raises(ValidationError):
            SpeedNGram(
                id=uuid4(),
                session_id=uuid4(),
                size=3,
                text="the",
                duration_ms=0.0,  # Invalid
                ms_per_keystroke=0.0,
                speed_mode=SpeedMode.RAW
            )

        with pytest.raises(ValidationError):
            SpeedNGram(
                id=uuid4(),
                session_id=uuid4(),
                size=3,
                text="the",
                duration_ms=-50.0,  # Invalid
                ms_per_keystroke=0.0,
                speed_mode=SpeedMode.RAW
            )

    def test_speed_ngram_to_dict(self):
        """Test conversion to dictionary."""
        ngram = SpeedNGram(
            id=uuid4(),
            session_id=uuid4(),
            size=3,
            text="the",
            duration_ms=150.0,
            ms_per_keystroke=50.0,
            speed_mode=SpeedMode.RAW
        )
        
        d = ngram.to_dict()
        assert isinstance(d, dict)
        assert d["text"] == "the"
        assert d["size"] == 3
        assert d["duration_ms"] == 150.0
        assert d["speed_mode"] == SpeedMode.RAW

    def test_speed_ngram_from_dict_roundtrip(self):
        """Test dictionary roundtrip conversion."""
        original = SpeedNGram(
            id=uuid4(),
            session_id=uuid4(),
            size=2,
            text="hi",
            duration_ms=80.0,
            ms_per_keystroke=40.0,
            speed_mode=SpeedMode.NET
        )
        
        d = original.to_dict()
        restored = SpeedNGram.from_dict(d)
        
        assert restored.id == original.id
        assert restored.text == original.text
        assert restored.size == original.size
        assert restored.duration_ms == original.duration_ms
        assert restored.speed_mode == original.speed_mode


class TestErrorNGram:
    """Test cases for ErrorNGram model."""

    def test_error_ngram_creation_valid(self):
        """Test creating a valid ErrorNGram."""
        session_id = uuid4()
        ngram_id = uuid4()
        created_at = datetime.utcnow()
        
        ngram = ErrorNGram(
            id=ngram_id,
            session_id=session_id,
            size=3,
            expected_text="the",
            actual_text="thg",  # Error in last position
            duration_ms=200.0,
            created_at=created_at
        )
        
        assert ngram.id == ngram_id
        assert ngram.session_id == session_id
        assert ngram.size == 3
        assert ngram.expected_text == "the"
        assert ngram.actual_text == "thg"
        assert ngram.duration_ms == 200.0
        assert ngram.created_at == created_at

    def test_error_ngram_validates_error_pattern(self):
        """Test that error pattern validation works correctly."""
        # Valid: error only in last position
        ngram = ErrorNGram(
            id=uuid4(),
            session_id=uuid4(),
            size=3,
            expected_text="cat",
            actual_text="cax",  # Only last char different
            duration_ms=150.0
        )
        assert ngram.actual_text == "cax"

        # Invalid: error in first position
        with pytest.raises(ValidationError, match="errors only in the last position"):
            ErrorNGram(
                id=uuid4(),
                session_id=uuid4(),
                size=3,
                expected_text="cat",
                actual_text="bat",  # First char different
                duration_ms=150.0
            )

        # Invalid: error in middle position
        with pytest.raises(ValidationError, match="errors only in the last position"):
            ErrorNGram(
                id=uuid4(),
                session_id=uuid4(),
                size=3,
                expected_text="cat",
                actual_text="cbt",  # Middle char different
                duration_ms=150.0
            )

        # Invalid: no error (all chars same)
        with pytest.raises(ValidationError, match="error in the last position"):
            ErrorNGram(
                id=uuid4(),
                session_id=uuid4(),
                size=3,
                expected_text="cat",
                actual_text="cat",  # No difference
                duration_ms=150.0
            )

    def test_error_ngram_sequence_separator_validation(self):
        """Test that sequence separators are rejected."""
        for separator in SEQUENCE_SEPARATORS:
            with pytest.raises(ValidationError, match="sequence separator"):
                ErrorNGram(
                    id=uuid4(),
                    session_id=uuid4(),
                    size=3,
                    expected_text=f"te{separator}",
                    actual_text=f"te{separator}",
                    duration_ms=100.0
                )

    def test_error_ngram_to_dict(self):
        """Test conversion to dictionary."""
        ngram = ErrorNGram(
            id=uuid4(),
            session_id=uuid4(),
            size=2,
            expected_text="hi",
            actual_text="hx",
            duration_ms=120.0
        )
        
        d = ngram.to_dict()
        assert isinstance(d, dict)
        assert d["expected_text"] == "hi"
        assert d["actual_text"] == "hx"
        assert d["size"] == 2
        assert d["duration_ms"] == 120.0


class TestKeystroke:
    """Test cases for Keystroke model."""

    def test_keystroke_creation_valid(self):
        """Test creating a valid Keystroke."""
        session_id = uuid4()
        timestamp = datetime.utcnow()
        
        keystroke = Keystroke(
            id=uuid4(),
            session_id=session_id,
            timestamp=timestamp,
            text_index=5,
            expected_char="t",
            actual_char="t",
            is_correct=True
        )
        
        assert keystroke.session_id == session_id
        assert keystroke.timestamp == timestamp
        assert keystroke.text_index == 5
        assert keystroke.expected_char == "t"
        assert keystroke.actual_char == "t"
        assert keystroke.is_correct is True
        assert keystroke.is_error is False

    def test_keystroke_correctness_validation(self):
        """Test that is_correct is validated against character comparison."""
        # Correct keystroke
        keystroke = Keystroke(
            session_id=uuid4(),
            timestamp=datetime.utcnow(),
            text_index=0,
            expected_char="a",
            actual_char="a",
            is_correct=False  # This should be overridden to True
        )
        assert keystroke.is_correct is True
        assert keystroke.is_error is False

        # Incorrect keystroke
        keystroke = Keystroke(
            session_id=uuid4(),
            timestamp=datetime.utcnow(),
            text_index=0,
            expected_char="a",
            actual_char="b",
            is_correct=True  # This should be overridden to False
        )
        assert keystroke.is_correct is False
        assert keystroke.is_error is True

    def test_keystroke_to_dict(self):
        """Test conversion to dictionary."""
        keystroke = Keystroke(
            session_id=uuid4(),
            timestamp=datetime.utcnow(),
            text_index=3,
            expected_char="e",
            actual_char="e",
            is_correct=True
        )
        
        d = keystroke.to_dict()
        assert isinstance(d, dict)
        assert d["text_index"] == 3
        assert d["expected_char"] == "e"
        assert d["actual_char"] == "e"
        assert d["is_correct"] is True


class TestEnumsAndConstants:
    """Test cases for enums and constants."""

    def test_speed_mode_enum(self):
        """Test SpeedMode enum values."""
        assert SpeedMode.RAW.value == "raw"
        assert SpeedMode.NET.value == "net"
        assert len(SpeedMode) == 2

    def test_ngram_classifier_enum(self):
        """Test NGramClassifier enum values."""
        assert NGramClassifier.CLEAN.value == "CLEAN"
        assert NGramClassifier.ERROR.value == "ERROR"
        assert NGramClassifier.IGNORED.value == "IGNORED"
        assert len(NGramClassifier) == 3

    def test_constants(self):
        """Test constant values."""
        assert MIN_NGRAM_SIZE == 2
        assert MAX_NGRAM_SIZE == 20
        assert ' ' in SEQUENCE_SEPARATORS
        assert '\n' in SEQUENCE_SEPARATORS
        assert '\t' in SEQUENCE_SEPARATORS
        assert '\0' in SEQUENCE_SEPARATORS


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_validate_ngram_size(self):
        """Test n-gram size validation function."""
        # Valid sizes
        assert validate_ngram_size(MIN_NGRAM_SIZE) is True
        assert validate_ngram_size(5) is True
        assert validate_ngram_size(MAX_NGRAM_SIZE) is True
        
        # Invalid sizes
        assert validate_ngram_size(0) is False
        assert validate_ngram_size(1) is False
        assert validate_ngram_size(MAX_NGRAM_SIZE + 1) is False
        assert validate_ngram_size(-1) is False

    def test_has_sequence_separators(self):
        """Test sequence separator detection."""
        # Text with separators
        assert has_sequence_separators("hello world") is True  # space
        assert has_sequence_separators("line1\nline2") is True  # newline
        assert has_sequence_separators("col1\tcol2") is True    # tab
        assert has_sequence_separators("null\0char") is True    # null
        
        # Text without separators
        assert has_sequence_separators("hello") is False
        assert has_sequence_separators("test123") is False
        assert has_sequence_separators("") is False

    def test_is_valid_ngram_text(self):
        """Test complete n-gram text validation."""
        # Valid n-gram text
        assert is_valid_ngram_text("th") is True
        assert is_valid_ngram_text("the") is True
        assert is_valid_ngram_text("a" * MAX_NGRAM_SIZE) is True
        
        # Invalid: too short
        assert is_valid_ngram_text("") is False
        assert is_valid_ngram_text("a") is False
        
        # Invalid: too long
        assert is_valid_ngram_text("a" * (MAX_NGRAM_SIZE + 1)) is False
        
        # Invalid: contains separators
        assert is_valid_ngram_text("a b") is False
        assert is_valid_ngram_text("a\n") is False
        assert is_valid_ngram_text("a\t") is False


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_unicode_characters(self):
        """Test handling of Unicode characters."""
        # Unicode should be valid in n-gram text
        ngram = SpeedNGram(
            id=uuid4(),
            session_id=uuid4(),
            size=3,
            text="café",
            duration_ms=150.0,
            ms_per_keystroke=50.0,
            speed_mode=SpeedMode.RAW
        )
        assert ngram.text == "café"

        # Unicode in keystrokes
        keystroke = Keystroke(
            session_id=uuid4(),
            timestamp=datetime.utcnow(),
            text_index=0,
            expected_char="é",
            actual_char="é",
            is_correct=True
        )
        assert keystroke.expected_char == "é"

    def test_empty_and_none_values(self):
        """Test handling of empty and None values."""
        # Empty text should fail validation
        with pytest.raises(ValidationError):
            SpeedNGram(
                id=uuid4(),
                session_id=uuid4(),
                size=2,
                text="",  # Empty
                duration_ms=100.0,
                ms_per_keystroke=50.0,
                speed_mode=SpeedMode.RAW
            )

        # None values should fail validation
        with pytest.raises(ValidationError):
            Keystroke(
                session_id=uuid4(),
                timestamp=None,  # None
                text_index=0,
                expected_char="a",
                actual_char="a",
                is_correct=True
            )

    def test_boundary_values(self):
        """Test boundary values for sizes and durations."""
        # Minimum valid n-gram
        ngram = SpeedNGram(
            id=uuid4(),
            session_id=uuid4(),
            size=MIN_NGRAM_SIZE,
            text="ab",
            duration_ms=0.1,  # Very small but positive
            ms_per_keystroke=0.05,
            speed_mode=SpeedMode.RAW
        )
        assert ngram.size == MIN_NGRAM_SIZE

        # Maximum valid n-gram
        max_text = "a" * MAX_NGRAM_SIZE
        ngram = SpeedNGram(
            id=uuid4(),
            session_id=uuid4(),
            size=MAX_NGRAM_SIZE,
            text=max_text,
            duration_ms=1000.0,
            ms_per_keystroke=50.0,
            speed_mode=SpeedMode.NET
        )
        assert ngram.size == MAX_NGRAM_SIZE
        assert len(ngram.text) == MAX_NGRAM_SIZE


if __name__ == "__main__":
    pytest.main(["-v", __file__])
