"""
Minimal test that reproduces the session persistence functionality test.
This isolates the core functionality being tested from the PyQt test environment.
"""
import os
import sys
import pytest
import sqlite3
import datetime
from typing import Dict, List, Any, NamedTuple, Tuple, Optional
from unittest.mock import MagicMock

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models.practice_session import PracticeSession, PracticeSessionManager

# Test fixtures and helpers
class KeystrokeScenario(NamedTuple):
    """Represents a test scenario for typing drill keystrokes."""
    name: str
    content: str
    keystrokes: List[Dict[str, Any]]
    expected_accuracy: float
    expected_efficiency: float = 100.0
    expected_correctness: float = 100.0
    expected_errors: int = 0
    expected_actual_chars: int = 0
    expected_backspace_count: int = 0

def create_keystroke(position: int, character: str, timestamp: float = 1.0, is_error: int = 0) -> Dict[str, Any]:
    """Helper to create a keystroke record."""
    return {
        'position': position,
        'character': character,
        'timestamp': timestamp,
        'is_error': is_error
    }

SCENARIOS = [
    KeystrokeScenario(
        name="perfect_typing",
        content="hello",
        keystrokes=[
            create_keystroke(0, 'h', 1.0, 0),
            create_keystroke(1, 'e', 1.2, 0),
            create_keystroke(2, 'l', 1.4, 0),
            create_keystroke(3, 'l', 1.6, 0),
            create_keystroke(4, 'o', 1.8, 0),
        ],
        expected_accuracy=100.0,
        expected_errors=0,
        expected_actual_chars=5
    )
]

@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    
    # Create practice_sessions table
    conn.execute("""
        CREATE TABLE practice_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            snippet_id INTEGER,
            snippet_index_start INTEGER,
            snippet_index_end INTEGER,
            content TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            total_time REAL,
            session_wpm REAL,
            session_cpm REAL,
            expected_chars INTEGER,
            actual_chars INTEGER,
            errors INTEGER,
            accuracy REAL
        )
    """)
    
    # Create session_keystrokes table
    conn.execute("""
        CREATE TABLE session_keystrokes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            timestamp REAL,
            position INTEGER,
            character TEXT,
            is_error INTEGER,
            FOREIGN KEY(session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
        )
    """)
    
    # Create session_errors table
    conn.execute("""
        CREATE TABLE session_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            timestamp REAL,
            position INTEGER,
            expected_char TEXT,
            actual_char TEXT,
            FOREIGN KEY(session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
        )
    """)
    
    yield conn
    conn.close()

class TestPracticeSessionManager:
    """Tests for PracticeSessionManager isolated from UI components."""
    
    def test_create_session(self, in_memory_db):
        """Test creation of a practice session."""
        # Create a mock database manager
        db_manager = MagicMock()
        db_manager.conn = in_memory_db
        
        def mock_execute(query, params=(), commit=False):
            cursor = in_memory_db.cursor()
            cursor.execute(query, params)
            if commit:
                in_memory_db.commit()
            return cursor
        
        db_manager.execute = mock_execute
        
        # Create the session manager
        session_manager = PracticeSessionManager(db_manager)
        
        # Get test scenario
        scenario = SCENARIOS[0]
        
        # Create practice session
        session = PracticeSession(
            snippet_id=1,
            snippet_index_start=0,
            snippet_index_end=len(scenario.content),
            content=scenario.content,
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now(),
            total_time=5.0,
            session_wpm=60.0,
            session_cpm=300.0,
            expected_chars=len(scenario.content),
            actual_chars=scenario.expected_actual_chars,
            errors=scenario.expected_errors,
            accuracy=scenario.expected_accuracy
        )
        
        # Save session to database
        session_id = session_manager.create_session(session)
        
        # Verify session was saved
        assert session_id is not None
        
        # Query the database to check session data
        cursor = in_memory_db.cursor()
        session_row = cursor.execute(
            "SELECT content, expected_chars, actual_chars, errors, accuracy FROM practice_sessions WHERE session_id=?", 
            (session_id,)
        ).fetchone()
        
        assert session_row is not None
        assert session_row[0] == scenario.content  # content matches
        assert session_row[1] == len(scenario.content)  # expected_chars
        assert session_row[2] == scenario.expected_actual_chars  # actual_chars
        assert session_row[3] == scenario.expected_errors  # errors
        assert session_row[4] == scenario.expected_accuracy  # accuracy
        
        print("Test passed successfully!")

# Run the test if executed directly
if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-xvs", __file__]))
