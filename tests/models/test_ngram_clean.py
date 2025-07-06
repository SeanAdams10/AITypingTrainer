"""Test suite for n-gram clean status using real NGramManager logic.

Verifies the is_clean flag behavior according to defined rules:
- No errors
- No backspaces
- No spaces
- No newlines
- Total time > 0.0ms (for n-grams > 1 char)
- Only n-grams of size 2-10 are processed (size 0, 1, or >10 are ignored)
"""

import sys
import uuid
from datetime import datetime, timedelta
from typing import List, Tuple

import pytest

from AITypingTrainer.models.ngram_manager import Keystroke, NGramManager
from db.database_manager import DatabaseManager

# Timestamp helpers for brevity
BASE_TIME = datetime(2023, 1, 1, 12, 0, 0, 0)
T0 = BASE_TIME
T10K_US = BASE_TIME + timedelta(microseconds=10000)
T100K_US = BASE_TIME + timedelta(microseconds=100000)
T200K_US = BASE_TIME + timedelta(microseconds=200000)
T300K_US = BASE_TIME + timedelta(microseconds=300000)
T400K_US = BASE_TIME + timedelta(microseconds=400000)
T500K_US = BASE_TIME + timedelta(microseconds=500000)
T600K_US = BASE_TIME + timedelta(microseconds=600000)
T700K_US = BASE_TIME + timedelta(microseconds=700000)

# Test cases: (keystrokes, ngram_size, expected_clean_ngram_texts, description)
# Rule: is_clean is True if:
#   - no errors in any keystroke of the ngram
#   - no backspace characters ('\b') in the ngram
#   - no space characters (' ') in the ngram
#   - no newline characters ('\n') in the ngram
#   - total_time_ms > 0.0 (for n-grams > 1 char)
#   - ngram size is 2-10 (size 0, 1, or >10 are ignored per specification)
CLEAN_STATUS_TEST_CASES: List[Tuple[List[Keystroke], int, List[str], str]] = [
    # Basic clean n-grams
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
        ],
        2,
        ["ab"],
        "Clean bigram",
    ),
    (
        [
            Keystroke(char="c", expected="c", timestamp=T0),
            Keystroke(char="a", expected="a", timestamp=T100K_US),
            Keystroke(char="t", expected="t", timestamp=T200K_US),
        ],
        3,
        ["cat"],
        "Cln trigram",
    ),
    # Size 1 n-grams are not allowed per specification (ignored)
    ([Keystroke(char="z", expected="z", timestamp=T0)], 1, [], "1char ignored per spec"),
    # Not clean: Contains error
    (
        [
            Keystroke(char="x", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
        ],
        2,
        [],
        "Err st, !cln",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="x", expected="b", timestamp=T100K_US),
        ],
        2,
        [],
        "Err end, !cln",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="X", expected="b", timestamp=T100K_US),
            Keystroke(char="c", expected="c", timestamp=T200K_US),
        ],
        3,
        [],
        "Err mid, !cln",
    ),
    (
        [
            Keystroke(char=" ", expected=" ", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
        ],
        2,
        [],
        "Spc st, !cln",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char=" ", expected=" ", timestamp=T100K_US),
        ],
        2,
        [],
        "Spc end, !cln",
    ),
    # Not clean: Contains newline
    (
        [
            Keystroke(char="\n", expected="\n", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
        ],
        2,
        [],
        "Newline st, !cln",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="\n", expected="\n", timestamp=T100K_US),
        ],
        2,
        [],
        "Newline end, !cln",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="\n", expected="\n", timestamp=T100K_US),
            Keystroke(char="c", expected="c", timestamp=T200K_US),
        ],
        3,
        [],
        "Newline mid, !cln",
    ),
    # Not clean: Contains tab
    (
        [
            Keystroke(char="\t", expected="\t", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
        ],
        2,
        [],
        "Tab st, !cln",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="\t", expected="\t", timestamp=T100K_US),
        ],
        2,
        [],
        "Tab end, !cln",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="\t", expected="\t", timestamp=T100K_US),
            Keystroke(char="c", expected="c", timestamp=T200K_US),
        ],
        3,
        [],
        "Tab mid, !cln",
    ),
    # Not clean: Zero total typing time (for n-grams > 1 char)
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T0),
        ],
        2,
        [],
        "0dur bi, !cln",
    ),
    # Edge cases
    ([], 2, [], "No keys, !cln"),
    ([Keystroke(char="a", expected="a", timestamp=T0)], 2, [], "<2 keys bi"),
    # Combinations of non-clean criteria
    (
        [
            Keystroke(char="x", expected="a", timestamp=T0),
            Keystroke(char=" ", expected=" ", timestamp=T100K_US),
        ],
        2,
        [],
        "Err & space, !clean",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="\b", expected="\b", timestamp=T0),
        ],
        2,
        [],
        "Bksp & 0dur, !clean",
    ),
    # Longer sequences
    (
        [
            Keystroke(char="t", expected="t", timestamp=T0),
            Keystroke(char="h", expected="h", timestamp=T100K_US),
            Keystroke(char="e", expected="e", timestamp=T200K_US),
            Keystroke(char=" ", expected=" ", timestamp=T300K_US),  # space
            Keystroke(char="E", expected="e", timestamp=T400K_US),  # error
            Keystroke(char="n", expected="n", timestamp=T500K_US),
        ],
        3,
        ["the"],
        "Seq 'the En'. Cln:the. Not:he,eE,En",
    ),
    (
        [
            Keystroke(char="c", expected="c", timestamp=T0),
            Keystroke(char="l", expected="l", timestamp=T100K_US),
            Keystroke(char="e", expected="e", timestamp=T200K_US),
            Keystroke(char="a", expected="a", timestamp=T300K_US),
            Keystroke(char="n", expected="n", timestamp=T400K_US),
        ],
        5,
        ["clean"],
        "Long clean 'clean'",
    ),
    (
        [
            Keystroke(char="n", expected="n", timestamp=T0),
            Keystroke(char="o", expected="o", timestamp=T100K_US),
            Keystroke(char="T", expected="t", timestamp=T200K_US),  # error
            Keystroke(char="c", expected="c", timestamp=T300K_US),
            Keystroke(char="l", expected="l", timestamp=T400K_US),
            Keystroke(char="e", expected="e", timestamp=T500K_US),
            Keystroke(char="a", expected="a", timestamp=T600K_US),
            Keystroke(char="n", expected="n", timestamp=T700K_US),
        ],
        4,
        ["clea", "lean"],
        "Seq 'noTcln'. Cln:clea,ln. !noTc,oTcl,Tcle",
    ),
    # Size 1 n-grams are not allowed per specification (ignored)
    ([Keystroke(char="a", expected="a", timestamp=T10K_US)], 1, [], "1char ignored per spec"),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T0),
            Keystroke(char="c", expected="c", timestamp=T0),
        ],
        3,
        [],
        "3gram all 0t, !clean",
    ),
    (
        [
            Keystroke(char="f", expected="f", timestamp=T0),
            Keystroke(char="a", expected="a", timestamp=T100K_US),
            Keystroke(char="s", expected="s", timestamp=T200K_US),
            Keystroke(char="t", expected="t", timestamp=T300K_US),
        ],
        4,
        ["fast"],
        "Clean 4g 'fast'",
    ),
    (
        [
            Keystroke(char="s", expected="s", timestamp=T0),
            Keystroke(char="l", expected="l", timestamp=T100K_US),
            Keystroke(char="o", expected="o", timestamp=T200K_US),
            Keystroke(char="W", expected="w", timestamp=T300K_US),  # Error
        ],
        4,
        [],
        "4-gram 'sloW' w/err, not clean",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
            Keystroke(char=" ", expected=" ", timestamp=T200K_US),  # Space
            Keystroke(char="d", expected="d", timestamp=T300K_US),
        ],
        4,
        [],
        "4-gram 'ab d' w/space, not clean",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),  # ab is clean
            Keystroke(char="c", expected="c", timestamp=T100K_US),
            # bc is not clean (0 duration)
            Keystroke(char="d", expected="d", timestamp=T200K_US),  # cd is clean
        ],
        2,
        ["ab", "cd"],
        "Seq a0b1c1d2. N=2. Clean:ab,cd. Not:bc",
    ),
    (
        [
            Keystroke(char="a", expected="a", timestamp=T0),
            Keystroke(char="b", expected="b", timestamp=T100K_US),
            Keystroke(char="C", expected="c", timestamp=T200K_US),  # Error
            Keystroke(char="d", expected="d", timestamp=T300K_US),
            Keystroke(char="e", expected="e", timestamp=T400K_US),
        ],
        3,
        [],
        "Seq abCde. N=3. Err C. Ngrams:abC,bCd,Cde. None clean.",
    ),
]


@pytest.fixture(scope="module")
def test_user(request: pytest.FixtureRequest) -> str:
    db = getattr(request, "db", None)
    if db is None:
        db = DatabaseManager(":memory:")
        db.init_tables()
    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (user_id, username, email) VALUES (?, ?, ?)",
        (user_id, "testuser", f"testuser_{user_id[:8]}@example.com"),
    )
    return user_id


@pytest.fixture(scope="module")
def test_keyboard(request: pytest.FixtureRequest, test_user: str) -> str:
    db = getattr(request, "db", None)
    if db is None:
        db = DatabaseManager(":memory:")
        db.init_tables()
    keyboard_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO keyboards (keyboard_id, keyboard_name) VALUES (?, ?)",
        (keyboard_id, "Test Keyboard"),
    )
    return keyboard_id


@pytest.mark.parametrize(
    "keystrokes, ngram_size, expected_clean_ngram_texts, description", CLEAN_STATUS_TEST_CASES
)
def test_ngram_clean_status(
    keystrokes: List[Keystroke],
    ngram_size: int,
    expected_clean_ngram_texts: List[str],
    description: str,
) -> None:
    """Test objective: Verify n-gram is_clean flag based on specified rules."""
    ngram_manager = NGramManager(db_manager=None)
    # Instantiate real NGramManager
    generated_ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, ngram_size)

    clean_ngram_texts_generated = [ngram.text for ngram in generated_ngrams if ngram.is_clean]

    sorted_generated = sorted(clean_ngram_texts_generated)
    sorted_expected = sorted(expected_clean_ngram_texts)
    assert sorted_generated == sorted_expected, (
        f"FAIL: {description}. EXP_CLEAN: {sorted_expected}, GOT_CLEAN: {sorted_generated}"
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
