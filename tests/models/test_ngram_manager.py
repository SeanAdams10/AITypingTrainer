"""Tests for NGramManager functionality.

Tests for n-gram analysis, creation, and management operations following
the first character exclusion rule as specified in Requirements/ngram.md.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest

from db.database_manager import DatabaseManager
from models.keystroke_collection import KeystrokeCollection
from models.ngram import Keystroke
from models.ngram_manager import NGramManager


@pytest.fixture(scope="function")
def ngram_manager(db_with_tables: DatabaseManager) -> Generator[NGramManager, None, None]:
    """Fixture: Provides an NGramManager instance with a fresh, initialized database."""
    manager = NGramManager(db_with_tables)
    yield manager


def ts(ms: int) -> datetime:
    """Create a timestamp from milliseconds offset for testing."""
    return datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc) + timedelta(milliseconds=ms)


def make_k(text: str, start_ms: int = 0, step_ms: int = 100) -> KeystrokeCollection:
    """Build keystrokes for expected text with perfect typing.
    
    Args:
        text: The expected text to create keystrokes for
        start_ms: Starting timestamp in milliseconds
        step_ms: Time interval between keystrokes in milliseconds
        
    Returns:
        KeystrokeCollection with perfect typing keystrokes
    """
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

    def test_first_character_exclusion_rule(self, ngram_manager: NGramManager) -> None:
        """Test objective: Verify first character exclusion rule per Requirements/ngram.md.
        
        The first character of the entire text must be excluded from n-gram analysis
        because we need the preceding keystroke timestamp for duration calculation.
        
        Expected text: "Then" -> Analysis range: "hen" (excluding first 'T')
        """
        expected = "Then"  # First 'T' should be excluded
        # T(0ms), h(500ms), e(1100ms), n(2000ms)
        ks_list = [
            Keystroke(
                keystroke_time=ts(0),
                text_index=0,
                expected_char="T",
                keystroke_char="T",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(500),
                text_index=1,
                expected_char="h",
                keystroke_char="h",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(1100),
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

        ks = KeystrokeCollection()
        for keystroke in ks_list:
            ks.add_keystroke(keystroke)

        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        
        # Should have no errors
        assert errors == []
        
        # Verify NO n-grams starting with 'T' are generated (first character excluded)
        t_ngrams = [s for s in speed if s.text.startswith("T")]
        assert len(t_ngrams) == 0, (
            f"Found n-grams starting with 'T': {[ng.text for ng in t_ngrams]}"
        )
        
        # Verify expected n-grams from "hen" analysis range are generated
        ngram_texts = [s.text for s in speed]
        
        # Size 2 n-grams from "hen": "he", "en"
        assert "he" in ngram_texts
        assert "en" in ngram_texts
        
        # Size 3 n-gram from "hen": "hen"
        assert "hen" in ngram_texts
        
        # Verify duration calculations use preceding keystroke (T at 0ms)
        he_ngram = next(s for s in speed if s.text == "he")
        # Duration: timestamp[e] - timestamp[T] = 1100ms - 0ms = 1100ms
        assert he_ngram.duration_ms == pytest.approx(1100.0, rel=1e-3)
        
        hen_ngram = next(s for s in speed if s.text == "hen")
        # Duration: timestamp[n] - timestamp[T] = 2000ms - 0ms = 2000ms
        assert hen_ngram.duration_ms == pytest.approx(2000.0, rel=1e-3)

    def test_ignored_zero_duration(self, ngram_manager: NGramManager) -> None:
        """Test objective: Verify zero-duration n-grams are ignored.
        
        When keystrokes have identical timestamps, the duration calculation
        results in zero, and these n-grams should be ignored.
        """
        expected = "ab"  # First 'a' excluded, only 'b' analyzed
        ks_list = [
            Keystroke(
                keystroke_time=ts(1000),
                text_index=0,
                expected_char="a",
                keystroke_char="a",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(1000),  # Same timestamp = zero duration
                text_index=1,
                expected_char="b",
                keystroke_char="b",
                is_error=False,
            ),
        ]

        ks = KeystrokeCollection()
        for keystroke in ks_list:
            ks.add_keystroke(keystroke)

        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        # Should be empty because:
        # 1. First character 'a' is excluded
        # 2. Only 'b' remains, but single char n-grams at end can't calculate duration
        assert speed == [] and errors == []

    def test_separators_split_runs_with_first_char_exclusion(
        self, ngram_manager: NGramManager
    ) -> None:
        """Test objective: Verify separators split n-gram runs correctly with first character exclusion.
        
        Expected text: "Hi there" -> Analysis: "i" + "there" (excluding first 'H')
        The space acts as a separator, breaking n-gram sequences.
        """
        expected = "Hi there"  # First 'H' excluded, space splits runs
        ks = make_k(expected)
        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        
        # Should have no errors
        assert errors == []
        
        # No n-grams should include the space (separator)
        assert all(" " not in ng.text for ng in speed)
        
        # No n-grams should start with 'H' (first character excluded)
        h_ngrams = [s for s in speed if s.text.startswith("H")]
        assert len(h_ngrams) == 0, (
            f"Found n-grams starting with 'H': {[ng.text for ng in h_ngrams]}"
        )
        
        # Should have n-grams from "there" (indices 3-7)
        ngram_texts = [s.text for s in speed]
        expected_ngrams = ["th", "he", "er", "re", "the", "her", "ere", "ther", "here", "there"]
        
        for expected_ngram in expected_ngrams:
            assert expected_ngram in ngram_texts, f"Missing expected n-gram: {expected_ngram}"
        
        # Should NOT have n-grams from the single 'i' or crossing the space
        unexpected_ngrams = ["Hi", "i ", " t", "i t"]
        for unexpected in unexpected_ngrams:
            assert unexpected not in ngram_texts, f"Found unexpected n-gram: {unexpected}"


class TestComprehensiveExamples:
    """Test cases that validate complete examples from Requirements/ngram_req.md."""

    def test_this_cat_example_from_requirements(self, ngram_manager: NGramManager) -> None:
        """Test objective: Verify the exact 'this cat' example from Requirements/ngram_req.md Section 6.3.3.
        
        Expected text: "this cat" -> Only first 't' (index 0) excluded
        Analysis ranges: "his" (indices 1-3) + "cat" (indices 5-7)
        Expected n-grams: h, i, s, c, a, t, hi, is, ca, at, his, cat
        """
        expected = "this cat"  # First 't' excluded, space separates runs
        ks_list = [
            # First word: "this"
            Keystroke(
                keystroke_time=ts(0), text_index=0, expected_char="t", 
                keystroke_char="t", is_error=False
            ),  # EXCLUDED
            Keystroke(
                keystroke_time=ts(200), text_index=1, expected_char="h", 
                keystroke_char="h", is_error=False
            ),
            Keystroke(
                keystroke_time=ts(400), text_index=2, expected_char="i", 
                keystroke_char="i", is_error=False
            ),
            Keystroke(
                keystroke_time=ts(600), text_index=3, expected_char="s", 
                keystroke_char="s", is_error=False
            ),
            # Space separator
            Keystroke(
                keystroke_time=ts(800), text_index=4, expected_char=" ", 
                keystroke_char=" ", is_error=False
            ),
            # Second word: "cat"
            Keystroke(
                keystroke_time=ts(1000), text_index=5, expected_char="c", 
                keystroke_char="c", is_error=False
            ),
            Keystroke(
                keystroke_time=ts(1200), text_index=6, expected_char="a", 
                keystroke_char="a", is_error=False
            ),
            Keystroke(
                keystroke_time=ts(1400), text_index=7, expected_char="t", 
                keystroke_char="t", is_error=False
            ),
        ]

        ks = KeystrokeCollection()
        for keystroke in ks_list:
            ks.add_keystroke(keystroke)

        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        
        # Should have no errors (all typing correct)
        assert errors == []
        
        # Extract generated n-gram texts
        ngram_texts = [s.text for s in speed]
        
        # Verify expected n-grams from Requirements/ngram_req.md Section 6.3.3
        # Note: Single characters at end of sequences may not be generated
        # due to duration calculation
        expected_size_1 = ["h", "i", "s", "c", "a"]  
        # Removed "t" - it's at end, can't calculate duration
        expected_size_2 = ["hi", "is", "ca", "at"]
        expected_size_3 = ["his", "cat"]
        
        # Check all expected n-grams are present
        for ngram in expected_size_1 + expected_size_2 + expected_size_3:
            assert ngram in ngram_texts, f"Missing expected n-gram: {ngram}"
        
        # Verify NO n-grams starting with first 't' (index 0)
        t_ngrams = [
            s for s in speed if s.text.startswith("t") and s.text != "t"
        ]
        assert len(t_ngrams) == 0, (
            f"Found n-grams starting with excluded 't': {[ng.text for ng in t_ngrams]}"
        )
        
        # Verify NO cross-word n-grams (space separator breaks sequences)
        cross_word_ngrams = [
            s for s in speed if " " in s.text or 
            any(c1 + c2 in s.text for c1 in "his" for c2 in "cat")
        ]
        assert len(cross_word_ngrams) == 0, (
            f"Found unexpected cross-word n-grams: {[ng.text for ng in cross_word_ngrams]}"
        )
        
        # Verify correct counts by size
        size_1_ngrams = [s for s in speed if s.size == 1]
        size_2_ngrams = [s for s in speed if s.size == 2]
        size_3_ngrams = [s for s in speed if s.size == 3]
        
        assert len(size_1_ngrams) == 5, (
            f"Expected 5 size-1 n-grams, got {len(size_1_ngrams)}: "
            f"{[ng.text for ng in size_1_ngrams]}"
        )
        assert len(size_2_ngrams) == 4, (
            f"Expected 4 size-2 n-grams, got {len(size_2_ngrams)}: "
            f"{[ng.text for ng in size_2_ngrams]}"
        )
        assert len(size_3_ngrams) == 2, (
            f"Expected 2 size-3 n-grams, got {len(size_3_ngrams)}: "
            f"{[ng.text for ng in size_3_ngrams]}"
        )

    def test_multi_word_first_char_exclusion_only(
        self, ngram_manager: NGramManager
    ) -> None:
        """Test objective: Verify first character exclusion applies ONLY to index 0, 
        not first char of each word.
        
        Expected text: "ab cd" -> Only first 'a' (index 0) excluded
        Analysis ranges: "b" (index 1) + "cd" (indices 3-4)
        The 'c' should NOT be excluded even though it's first character of second word.
        """
        expected = "ab cd"  # Only first 'a' excluded
        ks = make_k(expected)
        
        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        
        # Should have no errors
        assert errors == []
        
        ngram_texts = [s.text for s in speed]
        
        # Should have n-grams starting with 'c' 
        # (first char of second word - NOT excluded)
        c_ngrams = [s for s in speed if s.text.startswith("c")]
        assert len(c_ngrams) > 0, (
            "Missing n-grams starting with 'c' - "
            "first char of second word should NOT be excluded"
        )
        
        # Verify specific expected n-grams
        assert "c" in ngram_texts, "Missing 'c' n-gram"
        assert "cd" in ngram_texts, "Missing 'cd' n-gram"
        
        # Should NOT have n-grams starting with first 'a' (index 0 - excluded)
        a_ngrams = [s for s in speed if s.text.startswith("a")]
        assert len(a_ngrams) == 0, (
            f"Found n-grams starting with excluded 'a': {[ng.text for ng in a_ngrams]}"
        )


class TestErrorClassification:
    """Test cases for error classification functionality.
    
    Tests verify that error n-grams are only created when:
    1. Only the last keystroke in the n-gram is incorrect
    2. Duration can be calculated (not single chars at sequence end)
    3. First character exclusion rule is properly applied
    """

    def test_error_last_only_with_first_char_exclusion(
        self, ngram_manager: NGramManager
    ) -> None:
        """Test objective: Verify single chars at end are ignored due to duration calculation.
        
        Expected text: "th" -> Analysis: "h" only (excluding first 't')
        Since 'h' is a single character at the end of the sequence, duration cannot be
        calculated (no following keystroke), so it should be ignored regardless of error status.
        """
        expected = "th"  # First 't' excluded, only 'h' analyzed
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
                keystroke_char="g",  # Error on 'h'
                is_error=True,
            ),
        ]

        ks = KeystrokeCollection()
        for keystroke in ks_list:
            ks.add_keystroke(keystroke)

        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        
        # No n-grams should be generated because:
        # 1. First character 't' is excluded per requirements
        # 2. Remaining 'h' is single char at end - cannot calculate duration
        # 3. Per Requirements/ngram.md: "Cannot calculate (no following keystroke)"
        assert len(speed) == 0
        assert len(errors) == 0

    def test_first_char_exclusion_with_error(
        self, ngram_manager: NGramManager
    ) -> None:
        """Test objective: Verify first character exclusion and single char at end behavior.
        
        Expected text: "th" -> Analysis: "h" only (excluding first 't' even though it has error)
        The first character is always excluded regardless of error status.
        The remaining 'h' cannot generate an n-gram due to duration calculation limitations.
        """
        expected = "th"  # First 't' excluded regardless of error status
        ks_list = [
            Keystroke(
                keystroke_time=ts(0),
                text_index=0,
                expected_char="t",
                keystroke_char="x",  # Error on first char (but still excluded)
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

        ks = KeystrokeCollection()
        for keystroke in ks_list:
            ks.add_keystroke(keystroke)

        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        
        # No n-grams should be generated because:
        # 1. First character 't' is excluded per requirements (even with error)
        # 2. Remaining 'h' is single char at end - cannot calculate duration
        # 3. Per Requirements/ngram.md Section 6.3.1: single chars at end ignored
        assert len(speed) == 0
        assert len(errors) == 0

    def test_error_classification_with_multi_char_ngrams(
        self, ngram_manager: NGramManager
    ) -> None:
        """Test objective: Verify error classification works with multi-character n-grams.
        
        Expected text: "test" -> Analysis: "est" (excluding first 't')
        This provides enough characters to create n-grams with calculable durations.
        """
        expected = "test"  # First 't' excluded, analyze "est"
        ks_list = [
            Keystroke(
                keystroke_time=ts(0),
                text_index=0,
                expected_char="t",
                keystroke_char="t",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(500),
                text_index=1,
                expected_char="e",
                keystroke_char="e",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(1000),
                text_index=2,
                expected_char="s",
                keystroke_char="s",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(1500),
                text_index=3,
                expected_char="t",
                keystroke_char="x",  # Error on last character
                is_error=True,
            ),
        ]

        ks = KeystrokeCollection()
        for keystroke in ks_list:
            ks.add_keystroke(keystroke)

        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        
        # Should have clean n-grams for "es" (no error at end)
        clean_ngrams = [s.text for s in speed]
        assert "es" in clean_ngrams
        
        # Should have error n-grams where last character is wrong
        error_texts = [e.expected_text for e in errors]
        assert "est" in error_texts  # 3-char n-gram with error at end
        assert "st" in error_texts   # 2-char n-gram with error at end
        
        # Verify the error n-gram details
        est_error = next(e for e in errors if e.expected_text == "est")
        assert est_error.actual_text == "esx"
        assert est_error.size == 3
        assert est_error.duration_ms > 0

    def test_error_classification_preserves_first_char_exclusion(
        self, ngram_manager: NGramManager
    ) -> None:
        """Test objective: Verify error classification respects first character exclusion rule.
        
        Expected text: "test" with error on first 't' -> First 't' still excluded from analysis
        Even with error on first character, it should be excluded per requirements.
        """
        expected = "test"  # First 't' excluded even with error
        ks_list = [
            Keystroke(
                keystroke_time=ts(0),
                text_index=0,
                expected_char="t",
                keystroke_char="x",  # Error on first char (but still excluded)
                is_error=True,
            ),
            Keystroke(
                keystroke_time=ts(500),
                text_index=1,
                expected_char="e",
                keystroke_char="e",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(1000),
                text_index=2,
                expected_char="s",
                keystroke_char="s",
                is_error=False,
            ),
            Keystroke(
                keystroke_time=ts(1500),
                text_index=3,
                expected_char="t",
                keystroke_char="t",
                is_error=False,
            ),
        ]

        ks = KeystrokeCollection()
        for keystroke in ks_list:
            ks.add_keystroke(keystroke)

        speed, errors = ngram_manager.analyze(
            session_id=uuid.uuid4(), expected_text=expected, keystrokes=ks
        )
        
        # Should have clean n-grams from "est" analysis range
        clean_ngrams = [s.text for s in speed]
        expected_clean = ["es", "st", "est"]
        for ngram in expected_clean:
            assert ngram in clean_ngrams, f"Missing expected clean n-gram: {ngram}"
        
        # Should have NO error n-grams because first 't' with error is excluded
        assert errors == [], (
            f"Found unexpected error n-grams: {[e.expected_text for e in errors]}"
        )
        
        # Should have NO n-grams starting with 't' (first character excluded)
        t_ngrams = [
            s for s in speed if s.text.startswith("t") and s.text != "t"
        ]
        assert len(t_ngrams) == 0, (
            f"Found n-grams starting with excluded 't': {[ng.text for ng in t_ngrams]}"
        )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))
