import os
import tempfile
import uuid
from datetime import datetime, timedelta

import pytest

from db.database_manager import DatabaseManager
from models.category import Category
from models.keystroke import Keystroke
from models.keystroke_manager import KeystrokeManager
from models.ngram_manager import NGramManager
from models.session import Session
from models.snippet import Snippet


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DatabaseManager(path)
    db.init_tables()
    yield db
    db.close()
    import gc

    gc.collect()
    try:
        os.remove(path)
    except PermissionError:
        pass  # Ignore if file is still locked


@pytest.fixture
def category(temp_db):
    cat = Category(category_id=str(uuid.uuid4()), category_name="TestCat")
    temp_db.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
        (cat.category_id, cat.category_name),
    )
    return cat


@pytest.fixture
def snippet(temp_db, category):
    snip = Snippet(
        snippet_id=str(uuid.uuid4()),
        category_id=category.category_id,
        snippet_name="TestSnippet",
        content="abcdefghij",
    )
    temp_db.execute(
        "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
        (snip.snippet_id, snip.category_id, snip.snippet_name),
    )
    # Insert content into snippet_parts as a single part (part_number=0)
    temp_db.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (snip.snippet_id, 0, snip.content),
    )
    return snip


@pytest.fixture
def session(temp_db, snippet):
    sess = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=snippet.snippet_id,
        snippet_index_start=0,
        snippet_index_end=len(snippet.content),
        content=snippet.content,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        actual_chars=len(snippet.content),
        errors=0,
    )
    temp_db.execute(
        "INSERT INTO practice_sessions (session_id, snippet_id, snippet_index_start, snippet_index_end, content, start_time, end_time, actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sess.session_id,
            sess.snippet_id,
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


def expected_ngram_count(text_len, n):
    return max(0, text_len - n + 1)


def test_ngram_size_counts(temp_db, session, snippet):
    # Simulate keystrokes for the snippet
    km = KeystrokeManager(temp_db)
    now = datetime.now()
    for i, c in enumerate(snippet.content):
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
    ngram_manager = NGramManager(temp_db)
    keystrokes = km.keystroke_list
    for n in range(2, 11):
        ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, n)
        for ngram in ngrams:
            ngram_manager.save_ngram(ngram, session.session_id)

    # Check n-gram counts for sizes 2-10
    for n in range(2, 11):
        query = "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id=? AND ngram_size=?"
        count = temp_db.fetchone(query, (session.session_id, n))[0]
        assert count == expected_ngram_count(len(snippet.content), n), (
            f"N-gram size {n}: expected {expected_ngram_count(len(snippet.content), n)}, got {count}"
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
def test_ngram_size_counts_various_lengths(temp_db, test_string):
    # Create category
    cat_id = str(uuid.uuid4())
    temp_db.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)", (cat_id, "TestCat")
    )
    # Create snippet
    snip_id = str(uuid.uuid4())
    temp_db.execute(
        "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
        (snip_id, cat_id, "TestSnippet"),
    )
    # Insert content into snippet_parts as a single part
    temp_db.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (snip_id, 0, test_string),
    )
    # Create session
    sess_id = str(uuid.uuid4())
    now = datetime.now()
    temp_db.execute(
        "INSERT INTO practice_sessions (session_id, snippet_id, snippet_index_start, snippet_index_end, content, start_time, end_time, actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sess_id,
            snip_id,
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
    km = KeystrokeManager(temp_db)
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
    ngram_manager = NGramManager(temp_db)
    for n in range(2, 11):
        keystrokes = km.keystroke_list
        ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, n)
        for ngram in ngrams:
            ngram_manager.save_ngram(ngram, sess_id)
    # Check n-gram counts for sizes 2-10
    for n in range(2, 11):
        query = "SELECT COUNT(*) FROM session_ngram_speed WHERE session_id=? AND ngram_size=?"
        row = temp_db.fetchone(query, (sess_id, n))
        count = row[0] if row else 0
        expected = expected_ngram_count(len(test_string), n)
        assert count == expected, (
            f"N-gram size {n}: expected {expected}, got {count} for string '{test_string}'"
        )
