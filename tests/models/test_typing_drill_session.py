"""
Test creation and persistence of a PracticeSession with content field.
"""

import pytest
import datetime
from db.database_manager import DatabaseManager
from models.practice_session import PracticeSession, PracticeSessionManager


@pytest.fixture
def db_manager(tmp_path):
    db_path = tmp_path / "test_typing.db"
    dbm = DatabaseManager(str(db_path))
    dbm.init_tables()
    yield dbm
    dbm.close()


@pytest.fixture
def session_manager(db_manager):
    # Insert a test snippet to satisfy the foreign key constraint
    db_manager.execute("""
        INSERT INTO categories (category_id, name, description) 
        VALUES (1, 'Test Category', 'Test Description')
    """, commit=True)
    
    db_manager.execute("""
        INSERT INTO snippets (snippet_id, category_id, title, description, difficulty)
        VALUES (1, 1, 'Test Snippet', 'Test Description', 'easy')
    """, commit=True)
    
    db_manager.execute("""
        INSERT INTO snippet_parts (snippet_id, part_order, content)
        VALUES (1, 1, 'The quick brown fox jumps over the lazy dog')
    """, commit=True)
    
    return PracticeSessionManager(db_manager)


def test_create_practice_session_with_content(session_manager):
    session = PracticeSession(
        session_id=None,
        snippet_id=1,
        snippet_index_start=0,
        snippet_index_end=10,
        content="The quick brown fox",
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now(),
        total_time=30,
        session_wpm=60.0,
        session_cpm=300.0,
        expected_chars=19,
        actual_chars=19,
        errors=0,
        accuracy=1.0,
    )
    session_id = session_manager.create_session(session)
    assert session_id is not None
    # Retrieve and check content
    sessions = session_manager.list_sessions_for_snippet(1)
    assert len(sessions) == 1
    assert sessions[0].content == "The quick brown fox"
    assert sessions[0].snippet_id == 1
    assert sessions[0].snippet_index_start == 0
    assert sessions[0].snippet_index_end == 10
    assert sessions[0].expected_chars == 19
    assert sessions[0].actual_chars == 19
    assert sessions[0].errors == 0
    assert sessions[0].accuracy == 1.0
