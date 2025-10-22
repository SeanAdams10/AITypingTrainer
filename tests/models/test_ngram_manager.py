"""Tests for NGramManager functionality.

Tests for n-gram analysis, creation, and management operations.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from db.database_manager import DatabaseManager
from models.ngram import Keystroke
from models.ngram_manager import NGramManager


@pytest.fixture
def ngram_manager(db_with_tables: DatabaseManager) -> NGramManager:
    """Fixture: Provides an NGramManager instance with test database."""
    return NGramManager(db_with_tables)


def ts(ms: int) -> datetime:
    return datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc) + timedelta(milliseconds=ms)


def make_k(text: str, start_ms: int = 0, step_ms: int = 100):
    # Build keystrokes for expected text with perfect typing
    from models.keystroke_collection import KeystrokeCollection

    collection = KeystrokeCollection()
    t = start_ms
    for i, ch in enumerate(text):
        keystroke = Keystroke(
            keystroke_time=ts(t),
            text_index=i,
            expected_char=ch,
            keystroke_char=ch,
            is_error=False,
        )
        collection.add_keystroke(keystroke)
        t += step_ms
    return collection


class TestAnalyzeBasic:
    """Test cases for basic analysis functionality."""

    def test_clean_windows_and_gross_up(self, ngram_manager: NGramManager) -> None:
        """Test objective: Verify clean windows and gross-up calculation for n-grams."""
        expected = "Then"  # no separators
        # T(0), h(1000), e(2000), n(3000)
        ks_list = [
            Keystroke(
                keystroke_time=ts(0),
                text_index=0,
                expected_char="T",
                keystroke_char="T",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(1000),
                text_index=1,
                expected_char="h",
                keystroke_char="h",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(1500),
                text_index=2,
                expected_char="e",
                keystroke_char="e",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(2000),
                text_index=3,
                expected_char="n",
                keystroke_char="n",
                is_error=False,
            ),
        ]

        # Create KeystrokeCollection and add keystrokes
        from models.keystroke_collection import KeystrokeCollection

        ks = KeystrokeCollection()
        for keystroke in ks_list:
            ks.add_keystroke(keystroke)

        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        # Expect multiple clean n-grams
        assert errors == []
        # Find Then size 4 with gross-up: (2000/(4-1))*4 = 2666.666...
        # First 4-gram starts at sequence start, so gross-up applies
        first4 = next(s for s in speed if s.size == 4 and s.text == "Then")
        assert first4.duration_ms == pytest.approx(2666.6666666667, rel=1e-3)

    def test_ignored_zero_duration(self, ngram_manager: NGramManager) -> None:
        """Test objective: Verify zero-duration n-grams are ignored."""
        expected = "ab"
        ks_list = [
            Keystroke(
                keystroke_time=ts(1000),
                text_index=0,
                expected_char="a",
                keystroke_char="a",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(1000),
                text_index=1,
                expected_char="b",
                keystroke_char="b",
                is_error=False,
            ),
        ]

        from models.keystroke_collection import KeystrokeCollection

        ks = KeystrokeCollection()
        for keystroke in ks_list:
            ks.add_keystroke(keystroke)

        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        assert speed == [] and errors == []

    def test_separators_split_runs(self, ngram_manager: NGramManager) -> None:
        """Test objective: Verify separators split n-gram runs correctly."""
        expected = "hi there"  # space splits
        ks = make_k(expected)
        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        # There should be no n-grams that include the space; only from runs "hi" and "there"
        assert all(" " not in ng.text for ng in speed)
        assert errors == []


class TestErrorClassification:
    """Test cases for error classification functionality."""

    def test_error_last_only(self, ngram_manager: NGramManager) -> None:
        """Test objective: Verify only errors at the end of n-grams are recorded."""
        expected = "th"
        ks_list = [
            Keystroke(
                keystroke_time=ts(0),
                text_index=0,
                expected_char="t",
                keystroke_char="t",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(1000),
                text_index=1,
                expected_char="h",
                keystroke_char="g",
                is_error=True,
            ),
        ]

        from models.keystroke_collection import KeystrokeCollection

        ks = KeystrokeCollection()
        for keystroke in ks_list:
            ks.add_keystroke(keystroke)

        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        assert len(speed) == 0
        assert len(errors) == 1
        err = errors[0]
        assert err.size == 2
        assert err.expected_text == "th"
        assert err.actual_text == "tg"
        assert err.duration_ms > 0

    def test_error_not_last_is_ignored(self, ngram_manager: NGramManager) -> None:
        """Test objective: Verify errors not at the end of n-grams are ignored."""
        expected = "th"
        ks_list = [
            Keystroke(
                keystroke_time=ts(0),
                text_index=0,
                expected_char="t",
                keystroke_char="x",
                is_error=True,
            ),
            Keystroke(
                keystroke_time=ts(1000),
                text_index=1,
                expected_char="h",
                keystroke_char="h",
                is_error=False,
            ),
        ]

        from models.keystroke_collection import KeystrokeCollection

        ks = KeystrokeCollection()
        for keystroke in ks_list:
            ks.add_keystroke(keystroke)

        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        assert speed == [] and errors == []


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))
