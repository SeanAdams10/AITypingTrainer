import os
import tempfile
from datetime import datetime, timedelta

import pytest

from db.database_manager import DatabaseManager
from models.category import Category
from models.keystroke import Keystroke
from models.ngram_manager import NGramManager
from models.session import Session
from models.snippet import Snippet


@pytest.fixture
def temp_db():
    # Create a temporary file-based SQLite DB
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    db = DatabaseManager(db_path)
    db.init_tables()
    yield db
    os.remove(db_path)


@pytest.fixture
def setup_category_snippet(temp_db):
    db = temp_db
    # Insert a category
    category = Category(category_name="TestCat")
    db.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
        (category.category_id, category.category_name),
    )
    # Insert a snippet
    snippet = Snippet(
        snippet_name="TestSnippet", content="TheQuick", category_id=category.category_id
    )
    db.execute(
        "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
        (snippet.snippet_id, snippet.category_id, snippet.snippet_name),
    )
    return db, category, snippet


def test_ngram_misc_error_and_speed(setup_category_snippet):
    db, category, snippet = setup_category_snippet
    ngram_manager = NGramManager(db)
    session = Session(
        snippet_id=snippet.snippet_id,
        snippet_index_start=0,
        snippet_index_end=8,
        content="TheQuick",
        start_time=datetime(2025, 6, 12, 15, 3, 53, 484594),
        end_time=datetime(2025, 6, 12, 15, 3, 56, 604964),
        actual_chars=8,
        errors=5,
    )
    db.execute(
        "INSERT INTO practice_sessions (session_id, snippet_id, snippet_index_start, snippet_index_end, content, start_time, end_time, actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session.session_id,
            session.snippet_id,
            session.snippet_index_start,
            session.snippet_index_end,
            session.content,
            session.start_time.isoformat(),
            session.end_time.isoformat(),
            session.actual_chars,
            session.errors,
            session.ms_per_keystroke,
        ),
    )
    # Keystrokes as per the image
    base = datetime(2025, 6, 12, 15, 3, 53, 484594)
    keystrokes = [
        Keystroke(
            session_id=session.session_id,
            keystroke_id=None,
            keystroke_time=base,
            keystroke_char="T",
            expected_char="T",
            is_error=False,
            time_since_previous=0,
        ),
        Keystroke(
            session_id=session.session_id,
            keystroke_id=None,
            keystroke_time=base + timedelta(milliseconds=64),
            keystroke_char="h",
            expected_char="h",
            is_error=False,
            time_since_previous=64,
        ),
        Keystroke(
            session_id=session.session_id,
            keystroke_id=None,
            keystroke_time=base + timedelta(milliseconds=1056),
            keystroke_char="x",
            expected_char="e",
            is_error=True,
            time_since_previous=992,
        ),
        Keystroke(
            session_id=session.session_id,
            keystroke_id=None,
            keystroke_time=base + timedelta(milliseconds=1912),
            keystroke_char="Q",
            expected_char="Q",
            is_error=False,
            time_since_previous=856,
        ),
        Keystroke(
            session_id=session.session_id,
            keystroke_id=None,
            keystroke_time=base + timedelta(milliseconds=2623),
            keystroke_char="i",
            expected_char="u",
            is_error=True,
            time_since_previous=711,
        ),
        Keystroke(
            session_id=session.session_id,
            keystroke_id=None,
            keystroke_time=base + timedelta(milliseconds=2832),
            keystroke_char="u",
            expected_char="i",
            is_error=True,
            time_since_previous=209,
        ),
        Keystroke(
            session_id=session.session_id,
            keystroke_id=None,
            keystroke_time=base + timedelta(milliseconds=2853),
            keystroke_char="j",
            expected_char="c",
            is_error=True,
            time_since_previous=21,
        ),
        Keystroke(
            session_id=session.session_id,
            keystroke_id=None,
            keystroke_time=base + timedelta(milliseconds=2989),
            keystroke_char="c",
            expected_char="k",
            is_error=True,
            time_since_previous=136,
        ),
        Keystroke(
            session_id=session.session_id,
            keystroke_id=None,
            keystroke_time=base + timedelta(milliseconds=3100),
            keystroke_char="k",
            expected_char="k",
            is_error=False,
            time_since_previous=111,
        ),
    ]
    # Generate and save ngrams for n=2
    ngrams2 = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, 2)
    for ng in ngrams2:
        ngram_manager.save_ngram(ng, session.session_id)
    # Generate and save ngrams for n=3
    ngrams3 = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, 3)
    for ng in ngrams3:
        ngram_manager.save_ngram(ng, session.session_id)
    # Query ngram_speed
    speed_rows = db.fetchall(
        "SELECT ngram_text FROM session_ngram_speed WHERE session_id = ?", (session.session_id,)
    )
    speed_ngrams = {row[0] if isinstance(row, tuple) else row["ngram_text"] for row in speed_rows}
    # Query ngram_errors
    error_rows = db.fetchall(
        "SELECT ngram_text FROM session_ngram_errors WHERE session_id = ?", (session.session_id,)
    )
    error_ngrams = {row[0] if isinstance(row, tuple) else row["ngram_text"] for row in error_rows}
    # Assert only 'Th' in speed, and 'he', 'The' in error
    assert speed_ngrams == {"Th"}, f"Expected only 'Th' in ngram_speed, got {speed_ngrams}"
    assert error_ngrams == {"he", "The"}, (
        f"Expected 'he' and 'The' in ngram_errors, got {error_ngrams}"
    )
