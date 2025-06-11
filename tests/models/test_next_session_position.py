"""
Tests for determining the next session position based on previous sessions.
"""

import datetime
import os
import sys
import uuid

import pytest

# Add project root to path for test imports
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.database_manager import DatabaseManager
from models.session import Session
from models.session_manager import SessionManager


@pytest.fixture
def temp_db():
    """Create a temporary in-memory database for testing."""
    db_manager = DatabaseManager(":memory:")
    db_manager.init_tables()

    # Use UUIDs for category and snippet IDs
    category_id = str(uuid.uuid4())
    snippet_id = str(uuid.uuid4())

    # Create a sample category
    db_manager.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)", (category_id, "Test Category")
    )

    # Create a sample snippet
    db_manager.execute(
        "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
        (snippet_id, category_id, "Test Snippet"),
    )

    db_manager.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (snippet_id, 1, "This is a test snippet that is exactly fifty characters long."),
    )

    # Create session manager
    session_manager = SessionManager(db_manager)

    return {
        "db_manager": db_manager,
        "session_manager": session_manager,
        "snippet_id": snippet_id,
        "snippet_content": "This is a test snippet that is exactly fifty characters long.",
    }


def test_get_next_position_no_previous_session(temp_db):
    """Test that next position is 0 when there are no previous sessions."""
    session_manager = temp_db["session_manager"]

    # Get next position when there are no previous sessions
    next_position = session_manager.get_next_position(temp_db["snippet_id"])

    # Should start from the beginning when there are no previous sessions
    assert next_position == 0


def test_get_next_position_continue_from_previous(temp_db):
    """Test that next position continues from where the last session ended."""
    session_manager = temp_db["session_manager"]
    snippet_id = temp_db["snippet_id"]

    # Create a session with start=0, end=10
    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=snippet_id,
        snippet_index_start=0,
        snippet_index_end=10,
        content=temp_db["snippet_content"][0:10],
        start_time=datetime.datetime.now() - datetime.timedelta(minutes=10),
        end_time=datetime.datetime.now() - datetime.timedelta(minutes=9),
        actual_chars=10,
        errors=0,
    )
    session_manager.save_session(session)

    # Get next position
    next_position = session_manager.get_next_position(snippet_id)

    # Should continue from where the last session ended
    assert next_position == 10


def test_get_next_position_wrap_around(temp_db):
    """Test that next position wraps to 0 when the last session ended at the end of the snippet."""
    session_manager = temp_db["session_manager"]
    snippet_id = temp_db["snippet_id"]
    snippet_length = len(temp_db["snippet_content"])

    # Create a session with start=40, end=50 (end of snippet)
    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=snippet_id,
        snippet_index_start=40,
        snippet_index_end=snippet_length,
        content=temp_db["snippet_content"][40:snippet_length],
        start_time=datetime.datetime.now() - datetime.timedelta(minutes=10),
        end_time=datetime.datetime.now() - datetime.timedelta(minutes=9),
        actual_chars=10,
        errors=0,
    )
    session_manager.save_session(session)

    # Get next position
    next_position = session_manager.get_next_position(snippet_id)

    # Should wrap around to the beginning when the last session reached the end
    assert next_position == 0


def test_get_next_position_beyond_length(temp_db):
    """Test that next position wraps to 0 if last position was beyond snippet length."""
    session_manager = temp_db["session_manager"]
    snippet_id = temp_db["snippet_id"]
    snippet_length = len(temp_db["snippet_content"])

    # Create a session with end position beyond actual snippet length (simulating content change)
    session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=snippet_id,
        snippet_index_start=30,
        snippet_index_end=100,  # Intentionally beyond actual length
        content=temp_db["snippet_content"][30:],
        start_time=datetime.datetime.now() - datetime.timedelta(minutes=10),
        end_time=datetime.datetime.now() - datetime.timedelta(minutes=9),
        actual_chars=20,
        errors=0,
    )
    session_manager.save_session(session)

    # Get next position
    next_position = session_manager.get_next_position(snippet_id)

    # Should wrap around to beginning if the last end position is beyond content length
    assert next_position == 0


def test_get_next_position_multiple_sessions(temp_db):
    """Test that next position is based on the most recent session only."""
    session_manager = temp_db["session_manager"]
    snippet_id = temp_db["snippet_id"]

    # Create an older session
    older_session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=snippet_id,
        snippet_index_start=0,
        snippet_index_end=10,
        content=temp_db["snippet_content"][0:10],
        start_time=datetime.datetime.now() - datetime.timedelta(minutes=20),
        end_time=datetime.datetime.now() - datetime.timedelta(minutes=19),
        actual_chars=10,
        errors=0,
    )
    session_manager.save_session(older_session)

    # Create a newer session
    newer_session = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=snippet_id,
        snippet_index_start=20,
        snippet_index_end=30,
        content=temp_db["snippet_content"][20:30],
        start_time=datetime.datetime.now() - datetime.timedelta(minutes=10),
        end_time=datetime.datetime.now() - datetime.timedelta(minutes=9),
        actual_chars=10,
        errors=0,
    )
    session_manager.save_session(newer_session)

    # Get next position
    next_position = session_manager.get_next_position(snippet_id)

    # Should be based on the most recent session
    assert next_position == 30
