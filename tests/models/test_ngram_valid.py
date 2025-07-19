import sys
from datetime import datetime, timedelta
from typing import List, Tuple

import pytest

from models.ngram_manager import NGramManager
from tests.models.conftest import Keystroke  # Using centralized Keystroke import

# Timestamp helpers for brevity
BASE_TIME = datetime(2023, 1, 1, 12, 0, 0, 0)
T0 = BASE_TIME
T100K_US = BASE_TIME + timedelta(microseconds=100000)
T200K_US = BASE_TIME + timedelta(microseconds=200000)
T300K_US = BASE_TIME + timedelta(microseconds=300000)
T400K_US = BASE_TIME + timedelta(microseconds=400000)
T500K_US = BASE_TIME + timedelta(microseconds=500000)
T600K_US = BASE_TIME + timedelta(microseconds=600000)
T700K_US = BASE_TIME + timedelta(microseconds=700000)
T800K_US = BASE_TIME + timedelta(microseconds=800000)
T900K_US = BASE_TIME + timedelta(microseconds=900000)
T1000K_US = BASE_TIME + timedelta(microseconds=1000000)
T1100K_US = BASE_TIME + timedelta(microseconds=1100000)
T1200K_US = BASE_TIME + timedelta(microseconds=1200000)
T1300K_US = BASE_TIME + timedelta(microseconds=1300000)
T1400K_US = BASE_TIME + timedelta(microseconds=1400000)
T1500K_US = BASE_TIME + timedelta(microseconds=1500000)
T1600K_US = BASE_TIME + timedelta(microseconds=1600000)
T1700K_US = BASE_TIME + timedelta(microseconds=1700000)
T1800K_US = BASE_TIME + timedelta(microseconds=1800000)
T1900K_US = BASE_TIME + timedelta(microseconds=1900000)
T2000K_US = BASE_TIME + timedelta(microseconds=2000000)
T2100K_US = BASE_TIME + timedelta(microseconds=2100000)


# Test cases: (keystrokes, ngram_size, expected_valid_ngram_texts, description)
VALIDITY_TEST_CASES: List[Tuple[List[Keystroke], int, List[str], str]] = [
    # Basic valid n-grams
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
        ],
        2,
        ["ab"],
        "Simple valid bigram",
    ),
    (
        [
            Keystroke(char="c", expected="c", timestamp=T0),
            Keystroke(char="a", expected="a", timestamp=T100K_US),
            Keystroke(char="t", expected="t", timestamp=T200K_US),
        ],
        3,
        ["cat"],
        "Simple valid trigram",
    ),
    # Edge cases for validity
    ([], 2, [], "Empty keystrokes, expect no ngrams"),
    (
        [Keystroke(char="a", expected="a", timestamp=T0)],
        2,
        [],
        "Not enough keystrokes for bigram",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="b", expected="B", timestamp=T100K_US),
        ],
        2,
        ["aB"],
        "Error only at the end, still valid",
    ),
    # Invalid: Error not at the end
    (
        [
            Keystroke(char="x", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
        ],
        2,
        [],
        "Error at the start, invalid",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="x", expected="b", timestamp=T100K_US),
            Keystroke(char="c", expected="c", timestamp=T200K_US),
        ],
        3,
        [],
        "Error in the middle, invalid",
    ),
    # Invalid: Contains backspace
    (
        [
            Keystroke(char="\b", expected="\b", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
        ],
        2,
        [],
        "Backspace at start, invalid",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="\b", expected="\b", timestamp=T100K_US),
        ],
        2,
        [],
        "Backspace at end, invalid",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="\b", expected="\b", timestamp=T100K_US),
            Keystroke(char="c", expected="c", timestamp=T200K_US),
        ],
        3,
        [],
        "Backspace in middle, invalid",
    ),
    # Invalid: Zero total typing time (for n-grams > 1 char)
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T0),
        ],
        2,
        [],
        "Zero duration bigram, invalid",
    ),
    (
        [Keystroke(char="a", expected="a", timestamp=T0)],
        1,
        [],
        "Single char ngram, 0 duration is invalid",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=datetime(2023, 1, 1, 12, 0, 0, 0)),
            Keystroke(char="b", expected="b", timestamp=datetime(2023, 1, 1, 12, 0, 0, 1000)),
            Keystroke(char="c", expected="c", timestamp=datetime(2023, 1, 1, 12, 0, 0, 1000)),
        ],
        3,
        [],
        "Zero duration for last part of trigram, invalid",
    ),
    # Invalid: Contains space
    (
        [
            Keystroke(char=" ", expected=" ", timestamp=datetime(2023, 1, 1, 12, 0, 0, 0)),
            Keystroke(char="b", expected="b", timestamp=datetime(2023, 1, 1, 12, 0, 0, 100000)),
        ],
        2,
        [],
        "Space at start, invalid",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=datetime(2023, 1, 1, 12, 0, 0, 0)),
            Keystroke(char=" ", expected=" ", timestamp=datetime(2023, 1, 1, 12, 0, 0, 100000)),
        ],
        2,
        [],
        "Space at end, invalid",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=datetime(2023, 1, 1, 12, 0, 0, 0)),
            Keystroke(char=" ", expected=" ", timestamp=datetime(2023, 1, 1, 12, 0, 0, 100000)),
            Keystroke(char="c", expected="c", timestamp=datetime(2023, 1, 1, 12, 0, 0, 200000)),
        ],
        3,
        [],
        "Space in middle, invalid",
    ),
    # Combinations
    (
        [
            Keystroke(char="a", expected="X", timestamp=datetime(2023, 1, 1, 12, 0, 0, 0)),
            Keystroke(char=" ", expected=" ", timestamp=datetime(2023, 1, 1, 12, 0, 0, 100000)),
            Keystroke(char="c", expected="c", timestamp=datetime(2023, 1, 1, 12, 0, 0, 200000)),
        ],
        3,
        [],
        "Error at start and space, invalid",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=datetime(2023, 1, 1, 12, 0, 0, 0)),
            Keystroke(char="b", expected="b", timestamp=datetime(2023, 1, 1, 12, 0, 0, 0)),
            Keystroke(char="\b", expected="\b", timestamp=datetime(2023, 1, 1, 12, 0, 0, 100000)),
        ],
        3,
        [],
        "Zero duration and backspace, invalid",
    ),
    # Longer sequences generating multiple ngrams
    (
        [
            Keystroke(char="t", expected="t", timestamp=datetime(2023, 1, 1, 12, 0, 0, 0)),
            Keystroke(char="h", expected="h", timestamp=datetime(2023, 1, 1, 12, 0, 0, 100000)),
            Keystroke(char="e", expected="e", timestamp=datetime(2023, 1, 1, 12, 0, 0, 200000)),
            Keystroke(char="n", expected="N", timestamp=datetime(2023, 1, 1, 12, 0, 0, 300000)),
        ],
        2,
        ["th", "he", "eN"],
        "Seq: 'theN', bigrams, 'en' valid despite end error",
    ),
    (
        [
            Keystroke(char="q", expected="q", timestamp=datetime(2023, 1, 1, 12, 0, 0, 0)),
            Keystroke(char="u", expected="X", timestamp=datetime(2023, 1, 1, 12, 0, 0, 100000)),
            Keystroke(char="i", expected="i", timestamp=datetime(2023, 1, 1, 12, 0, 0, 200000)),
            Keystroke(char="c", expected="c", timestamp=datetime(2023, 1, 1, 12, 0, 0, 300000)),
            Keystroke(char="k", expected="k", timestamp=datetime(2023, 1, 1, 12, 0, 0, 400000)),
        ],
        3,
        ["ick"],
        "Seq: 'qXick', trigrams, 'ick' valid, others not (mid error)",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=datetime(2023, 1, 1, 12, 0, 0, 0)),
            Keystroke(char="\b", expected="\b", timestamp=datetime(2023, 1, 1, 12, 0, 0, 100000)),
            Keystroke(char="c", expected="c", timestamp=datetime(2023, 1, 1, 12, 0, 0, 200000)),
            Keystroke(char="d", expected="d", timestamp=datetime(2023, 1, 1, 12, 0, 0, 300000)),
        ],
        2,
        ["cd"],
        "Sequence: 'a\bcd', bigrams, 'a\b' and '\bc' invalid, 'cd' is valid",
    ),
    (
        [
            Keystroke(char="f", expected="f", timestamp=datetime(2023, 1, 1, 12, 0, 0, 0)),
            Keystroke(char=" ", expected=" ", timestamp=datetime(2023, 1, 1, 12, 0, 0, 100000)),
            Keystroke(char="g", expected="g", timestamp=datetime(2023, 1, 1, 12, 0, 0, 200000)),
            Keystroke(char="h", expected="H", timestamp=datetime(2023, 1, 1, 12, 0, 0, 300000)),
        ],
        2,
        ["gH"],
        "Sequence: 'f ghH', bigrams, 'f ', ' g' invalid, 'gh' is valid with error at end",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
            Keystroke(char="c", expected="c", timestamp=T200K_US),
            Keystroke(char="d", expected="d", timestamp=T300K_US),
            Keystroke(char="e", expected="e", timestamp=T400K_US),
            Keystroke(char="f", expected="f", timestamp=T500K_US),
            Keystroke(char="g", expected="g", timestamp=T600K_US),
            Keystroke(char="h", expected="h", timestamp=T700K_US),
            Keystroke(char="i", expected="i", timestamp=T800K_US),
            Keystroke(char="j", expected="j", timestamp=T900K_US),
            Keystroke(char="k", expected="k", timestamp=T1000K_US),
            Keystroke(char="l", expected="l", timestamp=T1100K_US),
            Keystroke(char="m", expected="m", timestamp=T1200K_US),
            Keystroke(char="n", expected="n", timestamp=T1300K_US),
            Keystroke(char="o", expected="o", timestamp=T1400K_US),
            Keystroke(char="p", expected="p", timestamp=T1500K_US),
            Keystroke(char="q", expected="q", timestamp=T1600K_US),
            Keystroke(char="r", expected="r", timestamp=T1700K_US),
            Keystroke(char="s", expected="s", timestamp=T1800K_US),
            Keystroke(char="t", expected="t", timestamp=T1900K_US),
            Keystroke(char="u", expected="u", timestamp=T2000K_US),
            Keystroke(char="v", expected="v", timestamp=T2100K_US),
        ],
        20,
        ["abcdefghijklmnopqrst", "bcdefghijklmnopqrstu", "cdefghijklmnopqrstuv"],
        "longer than 20 - should be no clean ones (per spec)",
    ),
]


# Using centralized fixtures from conftest.py
# Previous local fixtures for test_user and test_keyboard were removed


@pytest.mark.parametrize(
    "keystrokes, ngram_size, expected_valid_ngram_texts, description", VALIDITY_TEST_CASES
)
def test_ngram_validity(
    keystrokes: List[Keystroke],
    ngram_size: int,
    expected_valid_ngram_texts: List[str],
    description: str,
) -> None:
    """Test objective: Verify n-gram validity based on specified rules."""
    # Add debug printing for test case 12 (Zero duration for last part of trigram)
    debug_mode = "Zero duration for last part of trigram" in description

    if debug_mode:
        print(f"\nDEBUG - Test case: {description}")
        for i, k in enumerate(keystrokes):
            print(
                f"Keystroke {i}: char='{k.char}', expected='{k.expected}', timestamp={k.timestamp}"
            )
        print(f"Expected valid ngrams: {expected_valid_ngram_texts}")

    ngram_manager = NGramManager(db_manager=None)  # Instantiate NGramManager
    generated_ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, ngram_size)

    if debug_mode:
        for ngram in generated_ngrams:
            print(
                f"Generated ngram: text='{ngram.text}', valid={ngram.is_valid}, "
                f"error={ngram.is_error}, clean={ngram.is_clean}"
            )
            print(
                f"  start={ngram.start_time}, end={ngram.end_time}, "
                f"duration={ngram.total_time_ms}ms"
            )

    valid_ngrams_generated = [ngram for ngram in generated_ngrams if ngram.is_valid]
    valid_ngram_texts_generated = [ngram.text for ngram in valid_ngrams_generated]

    assert sorted(valid_ngram_texts_generated) == sorted(expected_valid_ngram_texts), (
        f"Test failed for: {description}. "
        f"Expected valid ngrams: {expected_valid_ngram_texts}, "
        f"Got: {valid_ngram_texts_generated}"
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
