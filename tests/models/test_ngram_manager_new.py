import uuid
from datetime import datetime, timedelta, timezone
import sqlite3
import pytest

from models.ngram_manager_new import NGramManagerNew
from models.ngram_new import Keystroke, SpeedMode, MAX_NGRAM_SIZE


def ts(ms: int) -> datetime:
    return datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc) + timedelta(milliseconds=ms)


def make_k(text: str, start_ms: int = 0, step_ms: int = 100):
    # Build keystrokes for expected text with perfect typing
    ks = []
    t = start_ms
    for i, ch in enumerate(text):
        ks.append(Keystroke(timestamp=ts(t), text_index=i, expected_char=ch, actual_char=ch, correctness=True))
        t += step_ms
    return ks


class TestAnalyzeBasic:
    def test_clean_windows_and_gross_up(self):
        mgr = NGramManagerNew()
        expected = "Then"  # no separators
        # T(0), h(1000), e(2000), n(3000)
        ks = [
            Keystroke(timestamp=ts(0), text_index=0, expected_char="T", actual_char="T", correctness=True),
            Keystroke(timestamp=ts(1000), text_index=1, expected_char="h", actual_char="h", correctness=True),
            Keystroke(timestamp=ts(1500), text_index=2, expected_char="e", actual_char="e", correctness=True),
            Keystroke(timestamp=ts(2000), text_index=3, expected_char="n", actual_char="n", correctness=True),
        ]
        speed, errors = mgr.analyze(session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks)
        # Expect multiple clean n-grams
        assert errors == []
        # Find Then size 4 with gross-up: (2000/(4-1))*4 = 2666.666...
        # First 4-gram starts at sequence start, so gross-up applies
        first4 = next(s for s in speed if s.size == 4 and s.text == "Then")
        assert first4.duration_ms == pytest.approx(2666.6666666667, rel=1e-3)

    def test_ignored_zero_duration(self):
        mgr = NGramManagerNew()
        expected = "ab"
        ks = [
            Keystroke(timestamp=ts(1000), text_index=0, expected_char="a", actual_char="a", correctness=True),
            Keystroke(timestamp=ts(1000), text_index=1, expected_char="b", actual_char="b", correctness=True),
        ]
        speed, errors = mgr.analyze(session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks)
        assert speed == [] and errors == []

    def test_separators_split_runs(self):
        mgr = NGramManagerNew()
        expected = "hi there"  # space splits
        ks = make_k(expected)
        speed, errors = mgr.analyze(session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks)
        # There should be no n-grams that include the space; only from runs "hi" and "there"
        assert all(" " not in ng.text for ng in speed)
        assert errors == []


class TestErrorClassification:
    def test_error_last_only(self):
        mgr = NGramManagerNew()
        expected = "th"
        ks = [
            Keystroke(timestamp=ts(0), text_index=0, expected_char="t", actual_char="t", correctness=True),
            Keystroke(timestamp=ts(1000), text_index=1, expected_char="h", actual_char="g", correctness=False),
        ]
        speed, errors = mgr.analyze(session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks)
        assert len(speed) == 0
        assert len(errors) == 1
        err = errors[0]
        assert err.size == 2
        assert err.expected_text == "th"
        assert err.actual_text == "tg"
        assert err.duration_ms > 0

    def test_error_not_last_is_ignored(self):
        mgr = NGramManagerNew()
        expected = "th"
        ks = [
            Keystroke(timestamp=ts(0), text_index=0, expected_char="t", actual_char="x", correctness=False),
            Keystroke(timestamp=ts(1000), text_index=1, expected_char="h", actual_char="h", correctness=True),
        ]
        speed, errors = mgr.analyze(session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks)
        assert speed == [] and errors == []
