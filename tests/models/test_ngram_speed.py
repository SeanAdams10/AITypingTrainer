import logging
import sys
from typing import List, Tuple

import pytest

# Import only needed modules
from models.ngram_manager import MAX_NGRAM_SIZE, MIN_NGRAM_SIZE

# Import only the centralized fixtures we actually use
# test_session_setup fixture is used as a parameter in the test function

logger = logging.getLogger(__name__)

# --- Using centralized fixtures from conftest.py ---
# All fixtures (db_manager, test_session_setup, etc.) now imported from conftest.py


# --- N-gram Speed Calculation Logic ---


def generate_ngrams_with_speed(
    keystrokes: List[Tuple[str, int]], n: int
) -> List[Tuple[str, float]]:
    """Generates n-grams of size n from keystrokes and calculates their speed.
    Keystrokes are (char, timestamp_ms).
    Speed is (timestamp_last - timestamp_first) / (n - 1) in ms.
    Only n-grams of size MIN_NGRAM_SIZE to MAX_NGRAM_SIZE (inclusive) are processed.
    # Returns an empty list if n is outside this range,
    # n > len(keystrokes), or n < 2 (for speed calc).
    """
    if not (MIN_NGRAM_SIZE <= n <= MAX_NGRAM_SIZE):
        return []
    if n > len(keystrokes) or n < 2:  # n < 2 would lead to division by zero or undefined for speed
        return []

    ngrams_with_speed: List[Tuple[str, float]] = []
    for i in range(len(keystrokes) - n + 1):
        ngram_chars = keystrokes[i : i + n]
        ngram_text = "".join(char for char, ts in ngram_chars)

        time_first_char = ngram_chars[0][1]
        time_last_char = ngram_chars[n - 1][1]

        duration = float(time_last_char - time_first_char)
        speed = duration / (n - 1)

        ngrams_with_speed.append((ngram_text, speed))
    return ngrams_with_speed


# --- Test Cases ---

KEYSTROKE_SPEED_TEST_CASES: List[
    Tuple[List[Tuple[str, int]], int, List[Tuple[str, float]], str]
] = [
    # Basic cases from prompt
    (
        [("a", 0), ("b", 1000), ("c", 1500)],
        2,
        [("ab", 1000.0), ("bc", 500.0)],
        "Basic bigram speed calculation",
    ),
    (
        [("a", 0), ("b", 1000), ("c", 1500)],
        3,
        [("abc", 750.0)],
        "Basic trigram speed calculation",
    ),
    # Consistent 10ms intervals
    (
        [("t", 0), ("e", 10), ("s", 20), ("t", 30)],
        2,
        [("te", 10.0), ("es", 10.0), ("st", 10.0)],
        "Consistent intervals - bigrams",
    ),
    (
        [("t", 0), ("e", 10), ("s", 20), ("t", 30)],
        3,
        [("tes", 10.0), ("est", 10.0)],
        "Consistent intervals - trigrams",
    ),
    (
        [("t", 0), ("e", 10), ("s", 20), ("t", 30)],
        4,
        [("test", 10.0)],
        "Consistent intervals - 4-gram",
    ),
    # Edge cases: empty lists, too short
    ([], 2, [], "Empty keystrokes list"),
    ([("a", 0)], 2, [], "Single keystroke - insufficient for bigram"),
    ([("a", 0), ("b", 10)], 3, [], "Two keystrokes - insufficient for trigram"),
    # Edge cases: n out of bounds
    (
        [("a", 0), ("b", 10)],
        1,
        [],
        "N-gram size below minimum",
    ),
    (
        [("a", 0)] * 21,
        21,
        [],
        "N-gram size above maximum",
    ),
    # Varied timings
    (
        [("q", 0), ("w", 150), ("e", 200), ("r", 400)],
        2,
        [("qw", 150.0), ("we", 50.0), ("er", 200.0)],
        "Varied timing intervals - bigrams",
    ),
    (
        [("q", 0), ("w", 150), ("e", 200), ("r", 400)],
        3,
        [("qwe", 100.0), ("wer", 125.0)],
        "Varied timing intervals - trigrams",
    ),
    # Zero duration (simultaneous keystrokes for the purpose of speed calc)
    (
        [("x", 0), ("y", 0), ("z", 100)],
        2,
        [("xy", 0.0), ("yz", 100.0)],
        "Zero duration - simultaneous keystrokes bigrams",
    ),
    (
        [("x", 0), ("y", 0), ("z", 100)],
        3,
        [("xyz", 50.0)],
        "Zero duration - simultaneous keystrokes trigram",
    ),
    # Max n-gram size
    (
        [
            (char_val, i * 10)
            for i, char_val in enumerate("abcdefghijklmnopqrstuv"[:MAX_NGRAM_SIZE])
        ],
        MAX_NGRAM_SIZE,
        [("abcdefghijklmnopqrst", 10.0)],
        "Max n-gram size - single result",
    ),
    (
        [(char_val, i * 10) for i, char_val in enumerate("abcdefghijklmnopqrstuv")],
        MAX_NGRAM_SIZE,
        [
            ("abcdefghijklmnopqrst", 10.0),
            ("bcdefghijklmnopqrstu", 10.0),
            ("cdefghijklmnopqrstuv", 10.0),
        ],
        "Max n-gram size - multiple results",
    ),
    # Additional test cases
    (
        [("s", 0), ("l", 50), ("o", 250), ("w", 300)],
        2,
        [("sl", 50.0), ("lo", 200.0), ("ow", 50.0)],
        "Mixed intervals - bigrams",
    ),
    (
        [("s", 0), ("l", 50), ("o", 250), ("w", 300)],
        3,
        [("slo", 125.0), ("low", 125.0)],
        "Mixed intervals - trigrams",
    ),
    (
        [("f", 0), ("a", 10), ("s", 20), ("t", 30), ("e", 40), ("r", 50)],
        6,
        [("faster", 10.0)],
        "Six-character word - 6-gram",
    ),
    (
        [("o", 0), ("n", 10), ("e", 20)],
        2,
        [("on", 10.0), ("ne", 10.0)],
        "Short word - bigrams",
    ),
    (
        [("o", 0), ("n", 10), ("e", 20)],
        3,
        [("one", 10.0)],
        "Short word - trigram",
    ),
]


@pytest.mark.parametrize(
    "keystrokes, n, expected_ngrams_with_speed, description",
    KEYSTROKE_SPEED_TEST_CASES,
    ids=[
        test_case[3] for test_case in KEYSTROKE_SPEED_TEST_CASES
    ],  # Extract descriptions as test IDs
)
def test_ngram_speed_calculation(
    keystrokes: List[Tuple[str, int]],
    n: int,
    expected_ngrams_with_speed: List[Tuple[str, float]],
    description: str,
    test_session_setup: Tuple[int, int, int],
) -> None:
    """
    Test objective: Verify n-gram speed calculation for various keystroke sequences and n-sizes.
    This test uses the test_session_setup fixture as requested, though the fixture's
    outputs are not directly used by generate_ngrams_with_speed itself.
    """
    # session_id, snippet_id, category_id = test_session_setup # Unused in this specific test

    actual_ngrams_with_speed = generate_ngrams_with_speed(keystrokes, n)

    # For float comparisons, it's often better to use pytest.approx
    # However, for this specific calculation, direct comparison should be fine if inputs are simple.
    # If issues arise, convert expected speeds to
    # pytest.approx(speed, rel=1e-5)

    assert len(actual_ngrams_with_speed) == len(expected_ngrams_with_speed), (
        f"For keystrokes={keystrokes}, n={n}: Expected "
        f"{len(expected_ngrams_with_speed)} ngrams, "
        f"got {len(actual_ngrams_with_speed)}"
    )

    for actual, expected in zip(actual_ngrams_with_speed, expected_ngrams_with_speed, strict=True):
        assert actual[0] == expected[0], (
            f"For keystrokes={keystrokes}, n={n}: Ngram text mismatch. "
            f"Expected '{expected[0]}', got '{actual[0]}'"
        )
        assert actual[1] == pytest.approx(expected[1]), (
            f"For keystrokes={keystrokes}, n={n}, ngram='{actual[0]}': "
            f"Speed mismatch. Expected {expected[1]}, got {actual[1]}"
        )


# --- Standalone Execution ---

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
