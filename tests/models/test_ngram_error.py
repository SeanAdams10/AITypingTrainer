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

# Test cases: (keystrokes, ngram_size, expected_ngram_texts_with_error_true, description)
# We expect a list of texts for ngrams where is_error should be True.
# Rule: is_error is True if an error exists ONLY in the last position of the ngram's keystrokes.
ERROR_STATUS_TEST_CASES: List[Tuple[List[Keystroke], int, List[str], str]] = [
    # Basic cases for is_error = True (error ONLY at the end)
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="x", expected="b", timestamp=T100K_US),
        ],
        2,
        ["ab"],
        "Bigram, error only at end",
    ),
    (
        [
            Keystroke(char="c", expected="c", timestamp=T0),
            Keystroke(char="a", expected="a", timestamp=T100K_US),
            Keystroke(char="X", expected="t", timestamp=T200K_US),
        ],
        3,
        ["cat"],
        "Trigram, error only at end",
    ),
    # Basic cases for is_error = False (no errors at all)
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
        ],
        2,
        [],
        "Bigram, no errors",
    ),
    (
        [
            Keystroke(char="c", expected="c", timestamp=T0),
            Keystroke(char="a", expected="a", timestamp=T100K_US),
            Keystroke(char="t", expected="t", timestamp=T200K_US),
        ],
        3,
        [],
        "Trigram, no errors",
    ),
    # Basic cases for is_error = False (errors present, but NOT only at the end)
    (
        [
            Keystroke(char="x", expected="a", timestamp=T0),  # Error at start
            Keystroke(char="b", expected="b", timestamp=T100K_US),
        ],
        2,
        [],
        "Bigram, error at start",
    ),
    (
        [
            Keystroke(char="x", expected="a", timestamp=T0),  # Error at start
            Keystroke(char="Y", expected="b", timestamp=T100K_US),  # Error at end
        ],
        2,
        [],
        "Bigram, errors at start and end",
    ),
    (
        [
            Keystroke(char="c", expected="c", timestamp=T0),
            Keystroke(char="X", expected="a", timestamp=T100K_US),  # Error in middle
            Keystroke(char="t", expected="t", timestamp=T200K_US),
        ],
        3,
        [],
        "Trigram, error in middle",
    ),
    (
        [
            Keystroke(char="C", expected="c", timestamp=T0),  # All errors
            Keystroke(char="A", expected="a", timestamp=T100K_US),
            Keystroke(char="T", expected="t", timestamp=T200K_US),
        ],
        3,
        [],
        "Trigram, all errors",
    ),
    (
        [
            Keystroke(char="c", expected="c", timestamp=T0),
            Keystroke(char="X", expected="a", timestamp=T100K_US),  # Error in middle
            Keystroke(char="Y", expected="t", timestamp=T200K_US),  # Error at end
        ],
        3,
        [],
        "Trigram, errors in middle and end",
    ),
    # Edge cases
    ([], 2, [], "Empty keystrokes"),
    (
        [Keystroke(char="q", expected="Q", timestamp=T0)],
        2,
        [],
        "Not enough keystrokes for bigram",
    ),
    # Size 1 n-grams are not allowed per specification (ignored)
    (
        [Keystroke(char="X", expected="a", timestamp=T0)],
        1,
        [],
        "n=1, ignored per spec (was error)",
    ),
    (
        [Keystroke(char="q", expected="Q", timestamp=T0)],
        1,
        [],
        "n=1, ignored per spec (was clean)",
    ),
    # Longer sequences generating multiple ngrams
    (
        [
            Keystroke(char="t", expected="t", timestamp=T0),
            Keystroke(char="h", expected="h", timestamp=T100K_US),
            Keystroke(char="e", expected="e", timestamp=T200K_US),
            Keystroke(char="N", expected="n", timestamp=T300K_US),  # error at end of 'eN'
        ],
        2,
        ["en"],
        "Seq:'theN'. is_err:th(F),he(F),eN(T)",
    ),
    # Longer sequences generating multiple ngrams
    (
        [
            Keystroke(char="t", expected="t", timestamp=T0),
            Keystroke(char="h", expected="h", timestamp=T100K_US),
            Keystroke(char="e", expected="e", timestamp=T200K_US),
            Keystroke(char="N", expected="n", timestamp=T300K_US),  # error at end of 'eN'
        ],
        3,
        ["hen"],
        "Seq:'theN'. is_err:th(F),he(F),eN(T)",
    ),
    # Longer sequences generating multiple ngrams
    (
        [
            Keystroke(char="t", expected="t", timestamp=T0),
            Keystroke(char="h", expected="h", timestamp=T100K_US),
            Keystroke(char="e", expected="e", timestamp=T200K_US),
            Keystroke(char="N", expected="n", timestamp=T300K_US),  # error at end of 'eN'
        ],
        4,
        ["then"],
        "Seq:'theN'. is_err:th(F),he(F),eN(T)",
    ),
    (
        [
            Keystroke(char="q", expected="Q", timestamp=T0),  # error at start of 'Qui'
            Keystroke(char="u", expected="u", timestamp=T100K_US),
            Keystroke(char="i", expected="i", timestamp=T200K_US),
            Keystroke(char="c", expected="c", timestamp=T300K_US),
            Keystroke(char="K", expected="k", timestamp=T400K_US),  # error at end of 'icK'
        ],
        3,
        ["ick"],
        "Seq:'QuicK'. is_err:Qui(F),uic(F),icK(T)",
    ),
    (
        [
            Keystroke(char="e", expected="E", timestamp=T0),
            Keystroke(char="r", expected="R", timestamp=T100K_US),
            Keystroke(char="r", expected="R", timestamp=T200K_US),
            Keystroke(char="s", expected="S", timestamp=T300K_US),
        ],
        2,
        [],
        "Seq 'ERRS', all errors. is_error: ER(F), RR(F), RS(F)",
    ),
    (
        [
            Keystroke(char="o", expected="o", timestamp=T0),
            Keystroke(char="n", expected="n", timestamp=T100K_US),
            Keystroke(
                char="L", expected="l", timestamp=T200K_US
            ),  # error in middle of 'onLy' and 'nLyE'
            Keystroke(char="y", expected="y", timestamp=T300K_US),
            Keystroke(char="E", expected="e", timestamp=T400K_US),  # error at end of 'nLyE'
        ],
        4,
        [],
        "Seq: 'onLyE'. is_error: onLy(F), nLyE(F) - has errors in two positions",
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
            Keystroke(char="T", expected="t", timestamp=T1900K_US),
            Keystroke(char="u", expected="u", timestamp=T2000K_US),
            Keystroke(char="v", expected="v", timestamp=T2100K_US),
        ],
        20,
        ["abcdefghijklmnopqrst"],
        "20 should still register errors",
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
            Keystroke(char="T", expected="t", timestamp=T1900K_US),
            Keystroke(char="u", expected="u", timestamp=T2000K_US),
            Keystroke(char="v", expected="v", timestamp=T2100K_US),
        ],
        20,
        ["abcdefghijklmnopqrst"],
        "20 should still register errors",
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
            Keystroke(char="T", expected="t", timestamp=T1900K_US),
            Keystroke(char="u", expected="u", timestamp=T2000K_US),
            Keystroke(char="v", expected="v", timestamp=T2100K_US),
        ],
        21,
        [],
        "longer than 20 - should be no clean ones (per spec)",
    ),
]


# Using centralized fixtures from conftest.py
# Previous local fixtures for test_user and test_keyboard were removed


@pytest.mark.parametrize(
    "keystrokes, ngram_size, expected_ngram_texts_with_error_true, description",
    ERROR_STATUS_TEST_CASES,
)
def test_ngram_error_status(
    keystrokes: List[Keystroke],
    ngram_size: int,
    expected_ngram_texts_with_error_true: List[str],
    description: str,
) -> None:
    """Test objective: Verify n-gram is_error flag based on specified rules."""
    # Print debug header for each test case
    print(f"\n============= DEBUG: {description} ==============")
    print(f"NGram size: {ngram_size}")
    print("Keystrokes:")
    for i, k in enumerate(keystrokes):
        is_err = k.char != k.expected
        print(f"  [{i}] char='{k.char}', expected='{k.expected}', is_error={is_err}")
    print(f"Expected error n-grams: {expected_ngram_texts_with_error_true}")

    # Generate ngrams and analyze
    ngram_manager = NGramManager(db_manager=None)  # Instantiate real NGramManager
    generated_ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, ngram_size)

    # Debug output for each generated ngram
    print("\nGenerated NGrams:")
    for i, ngram in enumerate(generated_ngrams):
        # Analyze error positions in this ngram
        keystroke_seq = keystrokes[i : i + ngram_size]
        error_positions = []
        for j, k in enumerate(keystroke_seq):
            if k.char != k.expected:
                error_positions.append(j)

        error_positions_str = "none" if not error_positions else str(error_positions)
        print(f"  NGram '{ngram.text}': is_error={ngram.is_error}, ")
        print(f"    Error positions: {error_positions_str}")
        print(f"    Last pos only?: {error_positions == [ngram_size - 1]}")

    # Get result for assertion
    error_true_ngram_texts_generated = [ngram.text for ngram in generated_ngrams if ngram.is_error]
    print("\nResults - NGrams with is_error=True:")
    print(f"  Expected: {sorted(expected_ngram_texts_with_error_true)}")
    print(f"  Actual:   {sorted(error_true_ngram_texts_generated)}")

    # Assertion with detailed error message
    assert sorted(error_true_ngram_texts_generated) == sorted(
        expected_ngram_texts_with_error_true
    ), (
        f"FAIL: {description}. "
        f"EXP_ERR: {expected_ngram_texts_with_error_true}, "
        f"GOT_ERR: {error_true_ngram_texts_generated}"
    )
    print("Test PASSED")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
