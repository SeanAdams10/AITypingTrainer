import uuid
from datetime import datetime, timedelta

import pytest

from db.database_manager import DatabaseManager
from models.category import Category
from models.keystroke import Keystroke
from models.keyboard import Keyboard
from models.keystroke_manager import KeystrokeManager
from models.ngram_manager import NGramManager
from models.session import Session
from models.snippet import Snippet
from models.user import User

# Import centralized fixtures
from tests.models.conftest import (
    db_manager as conftest_db_manager,
    test_session_setup
)


@pytest.fixture
def session(test_category: Category, test_snippet: Snippet, test_user: User, 
           test_keyboard: Keyboard, conftest_db_manager: DatabaseManager) -> Session:
    # Get the session data using our centralized fixtures
    session_id, snippet_id, _ = test_session_setup(test_category, test_snippet, test_user)
    
    # Get snippet content to create a proper Session object
    result = conftest_db_manager.execute(
        "SELECT content FROM snippet_parts WHERE snippet_id = ? AND part_number = 0", 
        (snippet_id,)
    ).fetchone()
    
    snippet_content = result[0] if result else "test content"
    
    # Use test_user and test_keyboard directly
    user_id = test_user.user_id
    keyboard_id = test_keyboard.keyboard_id
    
    sess = Session(
        session_id=session_id,
        snippet_id=snippet_id,
        user_id=user_id,
        keyboard_id=keyboard_id,
        snippet_index_start=0,
        snippet_index_end=len(snippet_content),
        content=snippet_content,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        actual_chars=len(snippet_content),
        errors=0,
    )
    conftest_db_manager.execute(
        "INSERT INTO practice_sessions (session_id, snippet_id, user_id, keyboard_id, snippet_index_start, snippet_index_end, content, start_time, end_time, actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sess.session_id,
            sess.snippet_id,
            sess.user_id,
            sess.keyboard_id,
            sess.snippet_index_start,
            sess.snippet_index_end,
            sess.content,
            sess.start_time.isoformat(),
            sess.end_time.isoformat(),
            sess.actual_chars,
            sess.errors,
            10.0,
        ),
    )
    return sess


def expected_ngram_count(text_len: int, n: int) -> int:
    return max(0, text_len - n + 1)


def test_ngram_size_counts(conftest_db_manager: DatabaseManager, session: Session, test_snippet: Snippet) -> None:
    # Simulate keystrokes for the snippet
    km = KeystrokeManager(conftest_db_manager)
    now = datetime.now()
    for i, c in enumerate(session.content):
        k = Keystroke(
            keystroke_id=str(uuid.uuid4()),
            session_id=session.session_id,
            keystroke_time=now + timedelta(milliseconds=10 * i),
            keystroke_char=c,
            expected_char=c,
            is_error=False,
            time_since_previous=10 if i > 0 else 0,
        )
        km.add_keystroke(k)
    km.save_keystrokes()

    # Explicitly trigger n-gram analysis and saving
    ngram_manager = NGramManager(conftest_db_manager)
    keystrokes = km.keystroke_list
    for n in range(2, 11):
        ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, n)
        for ngram in ngrams:
            ngram_manager.save_ngram(ngram, session.session_id)

    # Check n-gram counts for sizes 2-10
    for n in range(2, 11):
        query = "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id=? AND ngram_size=?"
        result = conftest_db_manager.fetchone(query, (session.session_id, n))
        count = result[0] if result else 0
        assert count == expected_ngram_count(len(session.content), n), (
            f"N-gram size {n}: expected {expected_ngram_count(len(session.content), n)}, got {count}"
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
def test_ngram_size_counts_various_lengths(conftest_db_manager: DatabaseManager, test_string: str) -> None:
    # Create category
    cat_id = str(uuid.uuid4())
    conftest_db_manager.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)", (cat_id, "TestCat")
    )
    # Create snippet
    snip_id = str(uuid.uuid4())
    conftest_db_manager.execute(
        "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
        (snip_id, cat_id, "TestSnippet"),
    )
    # Insert content into snippet_parts as a single part
    conftest_db_manager.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (snip_id, 0, test_string),
    )
    # Create session
    sess_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    keyboard_id = str(uuid.uuid4())
    conftest_db_manager.execute(
        "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
        (user_id, "Test", "User", f"testuser_{user_id[:8]}@example.com"),
    )
    conftest_db_manager.execute(
        "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
        (keyboard_id, user_id, "Test Keyboard"),
    )
    now = datetime.now()
    conftest_db_manager.execute(
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
    km = KeystrokeManager(conftest_db_manager)
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
    ngram_manager = NGramManager(conftest_db_manager)
    for n in range(2, 11):
        keystrokes = km.keystroke_list
        ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, n)
        for ngram in ngrams:
            ngram_manager.save_ngram(ngram, sess_id)
    # Check n-gram counts for sizes 2-10
    for n in range(2, 11):
        query = "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id=? AND ngram_size=?"
        row = conftest_db_manager.fetchone(query, (sess_id, n))
        count = row[0] if row else 0
        expected = expected_ngram_count(len(test_string), n)
        assert count == expected, (
            f"N-gram size {n}: expected {expected}, got {count} for string '{test_string}'"
        )
