import uuid
from datetime import datetime, timedelta, timezone

import pytest

from models.ngram_new import (
    ErrorNGram,
    Keystroke,
    MIN_NGRAM_SIZE,
    MAX_NGRAM_SIZE,
    SpeedMode,
    SpeedNGram,
    has_sequence_separators,
    is_valid_ngram_text,
    nfc,
)


def ts(ms: int) -> datetime:
    return datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc) + timedelta(milliseconds=ms)


class TestKeystroke:
    def test_keystroke_basic(self):
        k = Keystroke(timestamp=ts(0), text_index=0, expected_char="a", actual_char="a", correctness=True)
        assert k.expected_char == "a"
        assert k.actual_char == "a"

    def test_keystroke_nfc_single_char(self):
        # composed e + ́
        k = Keystroke(timestamp=ts(0), text_index=0, expected_char="e\u0301", actual_char="é", correctness=True)
        assert k.expected_char == "é"
        assert k.actual_char == "é"


class TestNGramTextRules:
    def test_has_sequence_separators(self):
        assert has_sequence_separators("a b") is True
        assert has_sequence_separators("ab") is False

    def test_is_valid_ngram_text(self):
        assert is_valid_ngram_text("ab") is True
        assert is_valid_ngram_text("a") is False  # too short
        assert is_valid_ngram_text("a b") is False  # separator


class TestSpeedNGram:
    def test_speed_ngram_computes_ms_per_keystroke(self):
        ng = SpeedNGram(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            size=2,
            text="ab",
            duration_ms=100.0,
            ms_per_keystroke=None,
            speed_mode=SpeedMode.RAW,
        )
        assert ng.ms_per_keystroke == pytest.approx(50.0)

    def test_speed_ngram_rejects_separators(self):
        with pytest.raises(Exception):
            SpeedNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=2,
                text="a b",
                duration_ms=100.0,
                speed_mode=SpeedMode.RAW,
            )

    def test_speed_ngram_invalid_size(self):
        with pytest.raises(Exception):
            SpeedNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=1,
                text="a",
                duration_ms=100.0,
                speed_mode=SpeedMode.RAW,
            )

    def test_speed_ngram_at_max_size(self):
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
        assert ng.ms_per_keystroke == pytest.approx(10.0)

    def test_speed_ngram_rejects_over_max(self):
        text = "a" * (MAX_NGRAM_SIZE + 1)
        with pytest.raises(Exception):
            SpeedNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=MAX_NGRAM_SIZE + 1,
                text=text,
                duration_ms=100.0,
                speed_mode=SpeedMode.RAW,
            )


class TestErrorNGram:
    def test_error_ngram_pattern_last_char_only(self):
        # differs only on last char
        ErrorNGram(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            size=2,
            expected_text="ab",
            actual_text="ax",
            duration_ms=120.0,
        )

    def test_error_ngram_pattern_invalid_first_char(self):
        with pytest.raises(Exception):
            ErrorNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=2,
                expected_text="ab",
                actual_text="xb",
                duration_ms=120.0,
            )

    def test_error_ngram_rejects_separators(self):
        with pytest.raises(Exception):
            ErrorNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=2,
                expected_text="a b",
                actual_text="azb",
                duration_ms=100.0,
            )

    def test_error_ngram_at_max_size(self):
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

    def test_error_ngram_rejects_over_max(self):
        exp = "a" * MAX_NGRAM_SIZE + "b"
        act = "a" * MAX_NGRAM_SIZE + "x"
        with pytest.raises(Exception):
            ErrorNGram(
                id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                size=MAX_NGRAM_SIZE + 1,
                expected_text=exp,
                actual_text=act,
                duration_ms=100.0,
            )
