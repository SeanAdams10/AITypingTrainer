import pytest
import sqlite3
from unittest.mock import MagicMock

from models.practice_session import PracticeSessionManager

@pytest.fixture
def in_memory_db():
    conn = sqlite3.connect(":memory:")
    # Create minimal schema for practice_sessions and keystrokes
    conn.execute("""
        CREATE TABLE practice_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            actual_chars INTEGER,
            accuracy REAL
        )
    """)
    conn.execute("""
        CREATE TABLE session_keystrokes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            keystroke TEXT,
            FOREIGN KEY(session_id) REFERENCES practice_sessions(session_id)
        )
    """)
    yield conn
    conn.close()

@pytest.fixture
def mock_typing_drill(in_memory_db):
    # Mock the TypingDrillScreen with the minimal interface
    drill = MagicMock(spec=TypingDrillScreen)
    drill.session_manager = PracticeSessionManager(in_memory_db)
    drill.db_manager = drill.session_manager.db_manager
    return drill

def insert_typing_session(drill, content, keystrokes, accuracy):
    # Simulate saving a session
    stats = {
        'total_time': 10,
        'wpm': 20,
        'cpm': 100,
        'expected_chars': len(content),
        'actual_chars': len(keystrokes),
        'errors': len([k for k in keystrokes if k != content]),
        'accuracy': accuracy
    }
    drill.content = content
    drill.keystrokes = keystrokes
    drill.error_records = []
    session_id = drill.save_session(stats, drill.session_manager)
    return session_id

# All TypingDrillScreen UI tests have been moved to tests/desktop_ui/test_typing_drill.py

    # Test 1: Only one row per session
    session_id = insert_typing_session(mock_typing_drill, "hello", list("hello"), 100.0)
    rows = in_memory_db.execute("SELECT COUNT(*) FROM practice_sessions").fetchone()[0]
    assert rows == 1


    # Test 2: Content column matches template
    content = "sample text"
    session_id = insert_typing_session(mock_typing_drill, content, list(content), 100.0)
    db_content = in_memory_db.execute("SELECT content FROM practice_sessions WHERE session_id=?", (session_id,)).fetchone()[0]
    assert db_content == content


    # Test 3: actual_chars counts all keystrokes
    content = "ab"
    keystrokes = ["x", "\b", "a", "b"]  # wrong, backspace, correct a, b
    session_id = insert_typing_session(mock_typing_drill, content, keystrokes, 50.0)
    actual_chars = in_memory_db.execute("SELECT actual_chars FROM practice_sessions WHERE session_id=?", (session_id,)).fetchone()[0]
    assert actual_chars == 4


    # Test 4: accuracy calculation
    content = "ab"
    # Scenario 1: a, wrong, backspace, b => 50%
    keystrokes1 = ["a", "x", "\b", "b"]
    session_id1 = insert_typing_session(mock_typing_drill, content, keystrokes1, 50.0)
    accuracy1 = in_memory_db.execute("SELECT accuracy FROM practice_sessions WHERE session_id=?", (session_id1,)).fetchone()[0]
    assert accuracy1 == 50.0
    # Scenario 2: a, backspace, a, b => 75%
    keystrokes2 = ["a", "\b", "a", "b"]
    session_id2 = insert_typing_session(mock_typing_drill, content, keystrokes2, 75.0)
    accuracy2 = in_memory_db.execute("SELECT accuracy FROM practice_sessions WHERE session_id=?", (session_id2,)).fetchone()[0]
    assert accuracy2 == 75.0
