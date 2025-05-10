"""
Tests for PracticeSessionManager and PracticeSession.
Uses pytest and a temporary SQLite database.
"""
import os
import tempfile
import pytest
import datetime
from models.practice_session import PracticeSession, PracticeSessionManager
from models.database_manager import DatabaseManager

@pytest.fixture
def temp_db() -> DatabaseManager:
    """
    Pytest fixture for a temporary SQLite database with minimal schema for practice_sessions and snippet_parts.
    Ensures DB is closed before file removal to avoid PermissionError on Windows.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DatabaseManager(path)
    db.init_tables()
    yield db
    db.close()
    os.remove(path)

@pytest.fixture
def session_manager(temp_db):
    return PracticeSessionManager(temp_db)

@pytest.fixture
def sample_snippet(temp_db):
    # Insert a snippet with 2 parts
    temp_db.execute("INSERT INTO snippet_parts (snippet_id, content) VALUES (?, ?)", (1, 'abc'), commit=True)
    temp_db.execute("INSERT INTO snippet_parts (snippet_id, content) VALUES (?, ?)", (1, 'defg'), commit=True)
    return 1

def test_create_and_get_last_session(session_manager, sample_snippet):
    session = PracticeSession(
        session_id=None,
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=7,
        start_time=datetime.datetime(2025, 5, 10, 12, 0, 0),
        end_time=datetime.datetime(2025, 5, 10, 12, 1, 0),
        total_time=60,
        session_wpm=40.0,
        session_cpm=200.0,
        expected_chars=7,
        actual_chars=7,
        errors=0,
        accuracy=1.0
    )
    sid = session_manager.create_session(session)
    assert sid > 0
    last = session_manager.get_last_session_for_snippet(sample_snippet)
    assert last is not None
    assert last.snippet_index_start == 0
    assert last.snippet_index_end == 7
    assert last.session_wpm == 40.0
    assert last.session_cpm == 200.0

def test_get_session_info(session_manager, sample_snippet):
    # No session yet
    info = session_manager.get_session_info(sample_snippet)
    assert info["last_start_index"] == 0
    assert info["last_end_index"] == 0
    assert info["snippet_length"] == 7
    # Add a session
    session = PracticeSession(
        session_id=None,
        snippet_id=sample_snippet,
        snippet_index_start=2,
        snippet_index_end=7,
        start_time=datetime.datetime(2025, 5, 10, 12, 2, 0),
        end_time=datetime.datetime(2025, 5, 10, 12, 3, 0),
        total_time=60,
        session_wpm=42.0,
        session_cpm=210.0,
        expected_chars=5,
        actual_chars=5,
        errors=1,
        accuracy=0.8
    )
    session_manager.create_session(session)
    info2 = session_manager.get_session_info(sample_snippet)
    assert info2["last_start_index"] == 2
    assert info2["last_end_index"] == 7
    assert info2["snippet_length"] == 7

def test_list_sessions_for_snippet(session_manager, sample_snippet):
    # Add two sessions
    session1 = PracticeSession(
        session_id=None,
        snippet_id=sample_snippet,
        snippet_index_start=0,
        snippet_index_end=3,
        start_time=datetime.datetime(2025, 5, 10, 12, 0, 0),
        end_time=datetime.datetime(2025, 5, 10, 12, 1, 0),
        total_time=60,
        session_wpm=30.0,
        session_cpm=150.0,
        expected_chars=3,
        actual_chars=3,
        errors=0,
        accuracy=1.0
    )
    session2 = PracticeSession(
        session_id=None,
        snippet_id=sample_snippet,
        snippet_index_start=3,
        snippet_index_end=7,
        start_time=datetime.datetime(2025, 5, 10, 12, 1, 0),
        end_time=datetime.datetime(2025, 5, 10, 12, 2, 0),
        total_time=60,
        session_wpm=50.0,
        session_cpm=250.0,
        expected_chars=4,
        actual_chars=4,
        errors=0,
        accuracy=1.0
    )
    session_manager.create_session(session1)
    session_manager.create_session(session2)
    sessions = session_manager.list_sessions_for_snippet(sample_snippet)
    assert len(sessions) == 2
    assert sessions[0].snippet_index_start == 3
    assert sessions[1].snippet_index_start == 0
