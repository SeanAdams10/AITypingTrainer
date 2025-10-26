# ruff: noqa: D102, D103
"""Tests for n-gram model functionality.

Tests for n-gram data structures, analysis, and core operations.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pytest import approx

from models.ngram import (
    MAX_NGRAM_SIZE,
    ErrorNGram,
    Keystroke,
    SpeedMode,
    SpeedNGram,
    has_sequence_separators,
    is_valid_ngram_text,
)


def ts(ms: int) -> datetime:
    return datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc) + timedelta(milliseconds=ms)


class TestKeystroke:
    """Test cases for Keystroke functionality."""

    def test_keystroke_basic(self) -> None:
        k = Keystroke(
            keystroke_time=ts(0),
            text_index=0,
            expected_char="a",
            keystroke_char="a",
            is_error=False,
        )
        assert k.expected_char == "a"
        assert k.keystroke_char == "a"

    def test_keystroke_nfc_single_char(self) -> None:
        # composed e + ́
        k = Keystroke(
            keystroke_time=ts(0),
            text_index=0,
            expected_char="e\u0301",
            keystroke_char="é",
            is_error=False,
        )
        assert k.expected_char == "é"
        assert k.keystroke_char == "é"


class TestNGramTextRules:
    """Test cases for N-gram text validation rules."""

    def test_has_sequence_separators(self) -> None:
        assert has_sequence_separators("a b") is True
        assert has_sequence_separators("ab") is False

    def test_is_valid_ngram_text(self) -> None:
        assert is_valid_ngram_text(text="ab") is True
        assert is_valid_ngram_text(text="a") is True
        assert is_valid_ngram_text(text="a b") is False  # separator


class TestSpeedNGram:
    """Test cases for SpeedNGram functionality."""

    def test_speed_ngram_computes_ms_per_keystroke(self) -> None:
        ng = SpeedNGram(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            size=2,
            text="ab",
            duration_ms=100.0,
            ms_per_keystroke=None,
            speed_mode=SpeedMode.RAW,
        )
        assert ng.ms_per_keystroke == approx(50.0)

    def test_speed_ngram_rejects_separators(self) -> None:
        with pytest.raises(ValueError):
            SpeedNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=2,
                text="a b",
                duration_ms=100.0,
                speed_mode=SpeedMode.RAW,
            )

    def test_speed_ngram_invalid_size(self) -> None:
        with pytest.raises(ValueError):
            SpeedNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=0,
                text="",
                duration_ms=100.0,
                speed_mode=SpeedMode.RAW,
            )

    def test_speed_ngram_size_one_allowed(self) -> None:
        ng = SpeedNGram(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            size=1,
            text="a",
            duration_ms=80.0,
            ms_per_keystroke=None,
            speed_mode=SpeedMode.RAW,
        )
        assert ng.ms_per_keystroke == approx(80.0)

    def test_speed_ngram_at_max_size(self) -> None:
        text = "a" * MAX_NGRAM_SIZE
        ng = SpeedNGram(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            size=MAX_NGRAM_SIZE,
            text=text,
            duration_ms=MAX_NGRAM_SIZE * 10.0,
            ms_per_keystroke=None,
            speed_mode=SpeedMode.RAW,
        )
        assert ng.text == text
        assert ng.ms_per_keystroke == approx(10.0)

    def test_speed_ngram_rejects_over_max(self) -> None:
        text = "a" * (MAX_NGRAM_SIZE + 1)
        with pytest.raises(ValueError):
            SpeedNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=MAX_NGRAM_SIZE + 1,
                text=text,
                duration_ms=100.0,
                speed_mode=SpeedMode.RAW,
            )


class TestErrorNGram:
    """Test cases for ErrorNGram functionality."""

    def test_error_ngram_pattern_last_char_only(self) -> None:
        # differs only on last char
        ErrorNGram(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            size=2,
            expected_text="ab",
            actual_text="ax",
            duration_ms=120.0,
        )

    def test_error_ngram_size_one_allowed(self) -> None:
        ng = ErrorNGram(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            size=1,
            expected_text="é",
            actual_text="e",
            duration_ms=95.0,
        )
        assert ng.expected_text == "é"
        assert ng.actual_text == "e"

    def test_error_ngram_pattern_invalid_first_char(self) -> None:
        with pytest.raises(ValueError):
            ErrorNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=2,
                expected_text="ab",
                actual_text="xb",
                duration_ms=120.0,
            )

    def test_error_ngram_rejects_separators_in_expected_text(self) -> None:
        """Test that sequence separators are banned from expected_text."""
        with pytest.raises(ValueError, match="n-gram text contains a sequence separator"):
            ErrorNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=2,
                expected_text="a b",  # Space separator should be rejected
                actual_text="ab",
                duration_ms=100.0,
            )

    def test_error_ngram_allows_separators_in_actual_text(self) -> None:
        """Test that sequence separators are allowed in actual_text."""
        # This should succeed - user typed a space when they shouldn't have
        ngram = ErrorNGram(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            size=2,
            expected_text="ab",
            actual_text="a ",  # Space in actual_text should be allowed
            duration_ms=100.0,
        )
        assert ngram.expected_text == "ab"
        assert ngram.actual_text == "a "

    def test_error_ngram_various_separators_in_actual_text(self) -> None:
        """Test that various sequence separators are allowed in actual_text."""
        separators = [" ", "\t", "\n", "\r", "\0"]
        
        for separator in separators:
            # Should succeed for each separator type in actual_text
            ngram = ErrorNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=2,
                expected_text="ab",
                actual_text=f"a{separator}",
                duration_ms=100.0,
            )
            assert ngram.expected_text == "ab"
            assert ngram.actual_text == f"a{separator}"

    def test_error_ngram_rejects_all_separators_in_expected_text(self) -> None:
        """Test that all sequence separators are banned from expected_text."""
        separators = [" ", "\t", "\n", "\r", "\0"]
        
        for separator in separators:
            with pytest.raises(ValueError, match="n-gram text contains a sequence separator"):
                ErrorNGram(
                    id=uuid.uuid4(),
                    session_id=uuid.uuid4(),
                    size=2,
                    expected_text=f"a{separator}",  # Separator in expected should fail
                    actual_text="ab",
                    duration_ms=100.0,
                )

    def test_error_ngram_at_max_size(self) -> None:
        exp = "a" * (MAX_NGRAM_SIZE - 1) + "b"
        act = "a" * (MAX_NGRAM_SIZE - 1) + "x"
        e = ErrorNGram(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            size=MAX_NGRAM_SIZE,
            expected_text=exp,
            actual_text=act,
            duration_ms=MAX_NGRAM_SIZE * 10.0,
        )
        assert e.size == MAX_NGRAM_SIZE

    def test_error_ngram_rejects_over_max(self) -> None:
        exp = "a" * MAX_NGRAM_SIZE + "b"
        act = "a" * MAX_NGRAM_SIZE + "x"
        with pytest.raises(ValueError):
            ErrorNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=MAX_NGRAM_SIZE + 1,
                expected_text=exp,
                actual_text=act,
                duration_ms=100.0,
            )
