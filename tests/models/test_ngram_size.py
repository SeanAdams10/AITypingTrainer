import uuid
from datetime import datetime, timedelta

import pytest

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke
from models.keystroke_manager import KeystrokeManager
from models.ngram_manager import NGramManager
from models.session import Session
from models.snippet import Snippet

# Fixtures from conftest.py will be automatically available


# Session fixture is now available from conftest.py as 'test_session'


def expected_ngram_count_with_filtering(text: str, n: int) -> int:
    """Calculate expected n-gram count accounting for space filtering.
    
    NGramManager filters out n-grams containing spaces, backspaces, newlines, or tabs.
    This function calculates the actual expected count after filtering.
    """
    if len(text) < n:
        return 0
    
    count = 0
    for i in range(len(text) - n + 1):
        ngram_text = text[i:i + n]
        # Skip n-grams containing filtered characters (same logic as NGramManager)
        if any(c in [' ', '\b', '\n', '\t'] for c in ngram_text):
            continue
        count += 1
    return count


def test_ngram_size_counts(db_with_tables: DatabaseManager, test_session: Session, test_snippet: Snippet) -> None:
    # Simulate keystrokes for the snippet
    km = KeystrokeManager(db_with_tables)
    now = datetime.now()
    for i, c in enumerate(test_session.content):
        k = Keystroke(
            keystroke_id=str(uuid.uuid4()),
            session_id=test_session.session_id,
            keystroke_time=now + timedelta(milliseconds=10 * i),
            keystroke_char=c,
            expected_char=c,
            is_error=False,
            time_since_previous=10 if i > 0 else 0,
        )
        km.add_keystroke(k)
    km.save_keystrokes()

    # Explicitly trigger n-gram analysis and saving
    ngram_manager = NGramManager(db_with_tables)
    keystrokes = km.keystroke_list
    for n in range(2, 11):
        ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, n)
        for ngram in ngrams:
            ngram_manager.save_ngram(ngram, test_session.session_id)

    # Check n-gram counts for sizes 2-10
    for n in range(2, 11):
        query = "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id=? AND ngram_size=?"
        result = db_with_tables.fetchone(query, (test_session.session_id, n))
        count = list(result.values())[0] if result else 0
        expected = expected_ngram_count_with_filtering(test_session.content, n)
        assert count == expected, (
            f"N-gram size {n}: expected {expected}, got {count}"
        )


@pytest.mark.parametrize(
    "test_string",
    [
        "",
        "a",
        "ab",
        "abc",
        "abcd",
        "abcde",
        "abcdef",
        "abcdefghij",
        "abcdefghijk",
        "abcdefghijklmnop",
    ],
)
def test_ngram_size_counts_various_lengths(db_with_tables: DatabaseManager, test_string: str) -> None:
    # Create category
    cat_id = str(uuid.uuid4())
    db_with_tables.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)", (cat_id, "TestCat")
    )
    # Create snippet
    snip_id = str(uuid.uuid4())
    db_with_tables.execute(
        "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
        (snip_id, cat_id, "TestSnippet"),
    )
    # Insert content into snippet_parts as a single part
    db_with_tables.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (snip_id, 0, test_string),
    )
    # Create session
    sess_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    keyboard_id = str(uuid.uuid4())
    db_with_tables.execute(
        "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
        (user_id, "Test", "User", f"testuser_{user_id[:8]}@example.com"),
    )
    db_with_tables.execute(
        "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
        (keyboard_id, user_id, "Test Keyboard"),
    )
    now = datetime.now()
    db_with_tables.execute(
        "INSERT INTO practice_sessions (session_id, snippet_id, user_id, keyboard_id, snippet_index_start, snippet_index_end, content, start_time, end_time, actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sess_id,
            snip_id,
            user_id,
            keyboard_id,
            0,
            len(test_string),
            test_string,
            now.isoformat(),
            (now + timedelta(seconds=1)).isoformat(),
            len(test_string),
            0,
            10.0,
        ),
    )
    # Generate keystrokes
    km = KeystrokeManager(db_with_tables)
    for i, char in enumerate(test_string):
        k = Keystroke(
            keystroke_id=str(uuid.uuid4()),
            session_id=sess_id,
            keystroke_char=char,  # for DB compatibility
            expected_char=char,  # for DB compatibility
            is_error=False,
            keystroke_time=now + timedelta(milliseconds=10 * i),
            time_since_previous=10 if i > 0 else 0,
        )
        km.add_keystroke(k)
    km.save_keystrokes()
    # Trigger n-gram analysis if not automatic
    ngram_manager = NGramManager(db_with_tables)
    for n in range(2, 11):
        keystrokes = km.keystroke_list
        ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, n)
        for ngram in ngrams:
            ngram_manager.save_ngram(ngram, sess_id)
    # Check n-gram counts for sizes 2-10
    for n in range(2, 11):
        query = "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id=? AND ngram_size=?"
        row = db_with_tables.fetchone(query, (sess_id, n))
        count = list(row.values())[0] if row else 0
        expected = expected_ngram_count_with_filtering(test_string, n)
        assert count == expected, (
            f"N-gram size {n}: expected {expected}, got {count} "
            f"for string '{test_string}'"
        )
