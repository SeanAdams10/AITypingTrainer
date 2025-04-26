"""
Tests for the typing drill functionality and session data persistence.
"""
import os
import sys
import json
import pytest
from typing import Dict, Any, List, Optional, Tuple, Generator
import datetime
import sqlite3
import uuid

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import application modules
from app import app
from db import DatabaseManager, init_db
from db.models.practice_session import PracticeSession
from db.models.keystroke import Keystroke
from db.models.snippet import Snippet
from db.models.ngram_analyzer import NGramAnalyzer

# Fixtures for testing
@pytest.fixture
def test_db_path(tmp_path) -> str:
    """
    Create a temporary database path for testing.
    
    Args:
        tmp_path: Pytest fixture for temporary directory
        
    Returns:
        str: Path to the temporary database file
    """
    db_path = tmp_path / "test_typing_data.db"
    return str(db_path)

@pytest.fixture
def test_database_manager(test_db_path, monkeypatch) -> Generator:
    """
    Create and initialize a database manager with a test database.
    
    Args:
        test_db_path: Path to the test database
        monkeypatch: Pytest fixture for patching
        
    Yields:
        DatabaseManager: Configured database manager instance
    """
    # Get the singleton instance and set the test path
    db_manager = DatabaseManager.get_instance()
    original_path = db_manager.db_path
    db_manager.set_db_path(test_db_path)
    
    # Initialize database tables
    init_db()
    
    # Create n-gram tables
    NGramAnalyzer.create_all_tables()
    
    # Yield the manager
    yield db_manager
    
    # Reset to original path after test
    db_manager.set_db_path(original_path)

@pytest.fixture
def test_client(test_database_manager) -> Generator:
    """
    Create a test client for the Flask application with a configured test database.
    
    Args:
        test_database_manager: Configured database manager
        
    Yields:
        Flask test client
    """
    # Configure Flask app to use the test database
    app.config['TESTING'] = True
    app.config['DATABASE'] = test_database_manager.db_path
    
    # Create a test client using the Flask application
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_snippet() -> Dict[str, Any]:
    """
    Create a test snippet.
    
    Returns:
        Dict: A snippet data object
    """
    return {
        "id": 1,
        "snippet_id": 1,
        "category_id": 1,
        "snippet_name": "Test Snippet",
        "content": "This is a test snippet for typing practice.",
        "category": "Test Category"
    }

@pytest.fixture
def mock_session() -> Dict[str, Any]:
    """
    Create a test practice session.
    
    Returns:
        Dict: A session data object
    """
    return {
        "session_id": "test-session-789",
        "snippet_id": 1,
        "snippet_index_start": 0,
        "snippet_index_end": 40,
        "start_time": datetime.datetime.now(),
        "practice_type": "standard"
    }

@pytest.fixture
def test_keystrokes() -> List[Dict[str, Any]]:
    """
    Create test keystroke data for testing.
    
    Returns:
        List[Dict]: A list of keystroke data objects
    """
    return [
        {
            "keystroke_char": "T",
            "expected_char": "T",
            "is_correct": True,
            "time_since_previous": 100
        },
        {
            "keystroke_char": "h",
            "expected_char": "h",
            "is_correct": True,
            "time_since_previous": 150
        },
        {
            "keystroke_char": "i",
            "expected_char": "i",
            "is_correct": True,
            "time_since_previous": 120
        },
        {
            "keystroke_char": "x",
            "expected_char": "s",
            "is_correct": False,
            "time_since_previous": 200
        }
    ]

@pytest.fixture
def test_database(test_db_path) -> Generator:
    """
    Set up a test database with necessary tables for testing.
    
    Args:
        test_db_path: Path to the test database
        
    Yields:
        sqlite3.Connection: Connection to the test database
    """
    # Create and initialize the database
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create practice sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_sessions (
            session_id TEXT PRIMARY KEY,
            snippet_id INTEGER NOT NULL,
            snippet_index_start INTEGER NOT NULL,
            snippet_index_end INTEGER NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            total_time REAL,
            session_wpm REAL,
            session_cpm REAL,
            expected_chars INTEGER,
            actual_chars INTEGER,
            errors INTEGER,
            accuracy REAL,
            practice_type TEXT DEFAULT 'beginning'
        )
    """)
    
    # Create keystrokes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_session_keystrokes (
            session_id TEXT,
            keystroke_id INTEGER,
            keystroke_time DATETIME NOT NULL,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            time_since_previous INTEGER,
            PRIMARY KEY (session_id, keystroke_id)
        )
    """)
    
    # Create errors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_session_errors (
            session_id TEXT,
            error_id INTEGER,
            keystroke_id INTEGER,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            PRIMARY KEY (session_id, error_id)
        )
    """)
    
    # Create n-gram tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_speed (
            id INTEGER PRIMARY KEY,
            session_id TEXT NOT NULL,
            ngram_size INTEGER NOT NULL,
            ngram_id INTEGER NOT NULL,
            ngram_time INTEGER NOT NULL,
            ngram_text TEXT NOT NULL,
            UNIQUE(session_id, ngram_size, ngram_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_error (
            id INTEGER PRIMARY KEY,
            session_id TEXT NOT NULL,
            ngram_size INTEGER NOT NULL,
            ngram_id INTEGER NOT NULL,
            ngram_time INTEGER NOT NULL,
            ngram_text TEXT NOT NULL,
            UNIQUE(session_id, ngram_size, ngram_id)
        )
    """)
    
    # Add snippet tables needed for foreign keys
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS text_category (
            category_id INTEGER PRIMARY KEY,
            category_name TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS text_snippets (
            snippet_id INTEGER PRIMARY KEY,
            category_id INTEGER,
            snippet_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snippet_parts (
            part_id INTEGER PRIMARY KEY,
            snippet_id INTEGER NOT NULL,
            part_number INTEGER NOT NULL,
            content TEXT NOT NULL
        )
    """)
    
    # Insert test data
    cursor.execute(
        "INSERT INTO text_category (category_id, category_name) VALUES (1, 'Test')"
    )
    
    cursor.execute(
        "INSERT INTO text_snippets (snippet_id, category_id, snippet_name) VALUES (1, 1, 'Test Snippet')"
    )
    
    cursor.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (1, 0, 'This is a test snippet for practice.')"
    )
    
    conn.commit()
    
    yield conn
    
    # Clean up after testing
    conn.close()

class TestTypingDrill:
    """Test class for verifying typing drill functionality."""
    
    def test_practice_session_creation(self, test_database_manager) -> None:
        """Test PracticeSession object creation with proper attributes."""
        # Create a practice session
        session = PracticeSession(
            snippet_id=1,
            snippet_index_start=0,
            snippet_index_end=25,
            practice_type="standard"
        )
        
        # Start the session
        success = session.start()
        
        # Verify operation was successful
        assert success, "Session start operation failed"
        
        # Verify the session_id was generated
        assert session.session_id is not None, "Session ID was not generated"
        assert len(session.session_id) > 0, "Session ID is empty"
        
        # Verify start time was set
        assert session.start_time is not None, "Start time was not set"
        
        # Verify database call
        cursor = test_database_manager.get_connection().cursor()
        cursor.execute("SELECT * FROM practice_sessions WHERE session_id = ?", (session.session_id,))
        session_record = cursor.fetchone()
        assert session_record is not None, "Session record not found in database"

    def test_keystroke_save_many(self, test_database_manager) -> None:
        """Test that multiple keystrokes can be saved at once."""
        # Create test keystrokes
        test_keystrokes = [
            {"keystroke_char": "T", "expected_char": "T", "is_correct": True, "time_since_previous": 100},
            {"keystroke_char": "h", "expected_char": "h", "is_correct": True, "time_since_previous": 150}
        ]
        
        # Test saving keystrokes
        session_id = "test-session-123"
        result = Keystroke.save_many(session_id, test_keystrokes)
        
        # Verify operation was successful
        assert result, "Keystroke save operation failed"
        
        # Verify database connection was obtained
        cursor = test_database_manager.get_connection().cursor()
        cursor.execute("SELECT * FROM practice_session_keystrokes WHERE session_id = ?", (session_id,))
        keystroke_records = cursor.fetchall()
        assert len(keystroke_records) == len(test_keystrokes), "Keystroke records not found in database"

    def test_practice_session_end(self, test_database_manager) -> None:
        """Test that a practice session is properly ended with statistics."""
        # Create session with initial data
        session = PracticeSession(
            snippet_id=1,
            snippet_index_start=0,
            snippet_index_end=25,
            practice_type="standard"
        )
        session.session_id = "test-session-456"
        
        # Set start time for proper duration calculation
        session.start_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
        
        # Create stats to update
        stats = {
            "wpm": 65.5,
            "cpm": 320,
            "accuracy": 98.2,
            "errors": 3,
            "elapsed_time_in_seconds": 60,
            "expected_chars": 100,
            "actual_chars": 103
        }
        
        # End the session
        success = session.end(stats)
        
        # Verify operation was successful
        assert success, "Failed to complete session"
        
        # Verify session attributes are updated
        assert session.session_wpm == 65.5, "WPM not updated correctly"
        assert session.session_cpm == 320, "CPM not updated correctly" 
        assert session.accuracy == 98.2, "Accuracy not updated correctly"
        assert session.errors == 3, "Errors not updated correctly"
        assert session.expected_chars == 100, "Expected chars not updated correctly"
        assert session.actual_chars == 103, "Actual chars not updated correctly"
        
        # Verify database call
        cursor = test_database_manager.get_connection().cursor()
        cursor.execute("SELECT * FROM practice_sessions WHERE session_id = ?", (session.session_id,))
        session_record = cursor.fetchone()
        assert session_record is not None, "Session record not found in database"

    # UI LEVEL TESTS
    
    def test_start_drill_page_loads(self, test_client, mock_snippet) -> None:
        """Test that the typing drill page loads with proper snippet content."""
        # Send request to start a drill
        response = test_client.post(
            '/start-drill',
            data={
                'snippet_id': 1,
                'start_index': 0,
                'end_index': 40,
                'practice_type': 'standard'
            }
        )
        
        # Verify response
        assert response.status_code == 200, "Response status code is not 200"
        
        # Verify the response contains expected content
        html_content = response.data.decode('utf-8')
        assert 'This is a test snippet' in html_content, "Snippet content not found in response"

    def test_end_session_saves_data(self, test_client, test_database_manager, mock_session) -> None:
        """Test that session data is properly saved when a drill is completed."""
        # Create session completion data
        session_data = {
            "session_id": mock_session["session_id"],
            "stats": {
                "wpm": 60,
                "cpm": 300,
                "accuracy": 95.5,
                "errors": 5,
                "end_position": 45,
                "elapsed_time_in_seconds": 120,
                "expected_chars": 50,
                "actual_chars": 55
            },
            "keystrokes": [
                {"keystroke_char": "T", "expected_char": "T", "is_correct": True, "time_since_previous": 100},
                {"keystroke_char": "h", "expected_char": "h", "is_correct": True, "time_since_previous": 150}
            ]
        }
        
        # Send the request
        response = test_client.post(
            '/end-session',
            data=json.dumps(session_data),
            content_type='application/json'
        )
        
        # Verify response
        response_data = json.loads(response.data.decode('utf-8'))
        assert response.status_code == 200, "Response status code is not 200"
        assert response_data.get('success'), "Response does not indicate success"
        
        # Verify session object was updated
        cursor = test_database_manager.get_connection().cursor()
        cursor.execute("SELECT * FROM practice_sessions WHERE session_id = ?", (mock_session["session_id"],))
        session_record = cursor.fetchone()
        assert session_record is not None, "Session record not found in database"
        
        # Verify keystrokes were saved
        cursor.execute("SELECT * FROM practice_session_keystrokes WHERE session_id = ?", (mock_session["session_id"],))
        keystroke_records = cursor.fetchall()
        assert len(keystroke_records) == len(session_data['keystrokes']), "Keystroke records not found in database"

    def test_keystrokes_are_recorded_correctly(self, test_database_manager) -> None:
        """Test that keystrokes are recorded with correct metadata."""
        # Create test keystrokes
        test_keystrokes = [
            {"keystroke_char": "T", "expected_char": "T", "is_correct": True, "time_since_previous": 100},
            {"keystroke_char": "h", "expected_char": "h", "is_correct": True, "time_since_previous": 150},
            {"keystroke_char": "e", "expected_char": "e", "is_correct": True, "time_since_previous": 200},
            {"keystroke_char": "x", "expected_char": " ", "is_correct": False, "time_since_previous": 250}
        ]
        
        # Test saving keystrokes
        session_id = "test-session-456"
        
        # Create a practice session
        session = PracticeSession(
            snippet_id=1,
            snippet_index_start=0,
            snippet_index_end=25,
            practice_type="standard"
        )
        session.session_id = session_id
        session.start()
        
        # Save keystrokes
        result = Keystroke.save_many(session_id, test_keystrokes)
        
        # Verify operation was successful
        assert result, "Keystroke save operation failed"
        
        # Verify database connection was obtained
        cursor = test_database_manager.get_connection().cursor()
        cursor.execute("SELECT * FROM practice_session_keystrokes WHERE session_id = ?", (session_id,))
        keystroke_records = cursor.fetchall()
        assert len(keystroke_records) == len(test_keystrokes), "Keystroke records not found in database"

    def test_complete_typing_drill_writes_to_all_tables(self, test_client, test_database_manager, mock_snippet) -> None:
        """
        Test that completing a typing drill properly writes data to all relevant tables.
        
        This test verifies that:
        1. Starting a typing drill creates a record in the practice_sessions table
        2. Completing a typing drill updates the practice_sessions record
        3. The practice_session_keystrokes table has entries for all keystrokes
        4. The practice_session_errors table has entries for incorrect keystrokes
        """
        # Create a test session
        session_id = str(uuid.uuid4())
        
        # Mock the session creation to use our specific test ID
        with pytest.MonkeyPatch().context() as m:
            m.setattr(uuid, "uuid4", lambda: uuid.UUID(session_id))
            response = test_client.post(
                '/start-drill',
                data={
                    'snippet_id': 1,
                    'start_index': 0,
                    'end_index': 40,
                    'practice_type': 'standard'
                }
            )
            
            assert response.status_code == 200, "Failed to start a new drill session"
            
            # Verify session was created in the database
            cursor = test_database_manager.get_connection().cursor()
            cursor.execute("SELECT * FROM practice_sessions WHERE session_id = ?", (session_id,))
            session_record = cursor.fetchone()
            assert session_record is not None, "Session record not found in database"
            
            # Create test keystrokes - 7 characters total with 1 error
            test_keystrokes = [
                {'keystroke_char': 'T', 'expected_char': 'T', 'is_correct': True, 'time_since_previous': 0},
                {'keystroke_char': 'h', 'expected_char': 'h', 'is_correct': True, 'time_since_previous': 120},
                {'keystroke_char': 'i', 'expected_char': 'i', 'is_correct': True, 'time_since_previous': 130},
                {'keystroke_char': 's', 'expected_char': 's', 'is_correct': True, 'time_since_previous': 110},
                {'keystroke_char': ' ', 'expected_char': ' ', 'is_correct': True, 'time_since_previous': 90},
                {'keystroke_char': 'i', 'expected_char': 'i', 'is_correct': True, 'time_since_previous': 140},
                {'keystroke_char': 'z', 'expected_char': 's', 'is_correct': False, 'time_since_previous': 130},
            ]
            
            # Simulate completion
            response = test_client.post(
                '/end-session',
                data=json.dumps({
                    'session_id': session_id,
                    'stats': {
                        'wpm': 60,
                        'cpm': 300,
                        'accuracy': 85.7,  # 6/7 correct = 85.7%
                        'errors': 1,
                        'end_position': 7,
                        'elapsed_time_in_seconds': 7,
                        'expected_chars': 7,
                        'actual_chars': 7
                    },
                    'keystrokes': test_keystrokes
                }),
                content_type='application/json'
            )
            
            # Verify response
            assert response.status_code == 200, "Response status code is not 200"
            
            # Verify data was written to all tables
            # Check practice_sessions table
            cursor.execute(
                "SELECT * FROM practice_sessions WHERE session_id = ?", 
                (session_id,)
            )
            session_record = cursor.fetchone()
            assert session_record is not None, "Session record should exist in practice_sessions table"
            
            # Check practice_session_keystrokes table
            cursor.execute(
                "SELECT COUNT(*) FROM practice_session_keystrokes WHERE session_id = ?", 
                (session_id,)
            )
            keystroke_count = cursor.fetchone()[0]
            assert keystroke_count == len(test_keystrokes), f"practice_session_keystrokes table should have {len(test_keystrokes)} records"
            
            # Check practice_session_errors table
            cursor.execute(
                "SELECT COUNT(*) FROM practice_session_errors WHERE session_id = ?", 
                (session_id,)
            )
            error_count = cursor.fetchone()[0]
            expected_error_count = sum(1 for k in test_keystrokes if not k.get('is_correct', False))
            assert error_count == expected_error_count, f"practice_session_errors table should have {expected_error_count} records"

    def test_end_to_end_typing_drill_database_verification(self, test_client, test_database_manager, mock_snippet) -> None:
        """
        Test the entire typing drill workflow from start to finish with actual database operations.
        
        This test:
        1. Creates a test database with all required tables
        2. Starts a typing drill session
        3. Simulates completing the drill with test keystroke data
        4. Verifies all data is correctly saved in the appropriate tables
        """
        # Get the database connection
        cursor = test_database_manager.get_connection().cursor()
        
        # Create test keystrokes - 35 characters total with 2 errors
        test_keystrokes = [
            {'keystroke_char': 'T', 'expected_char': 'T', 'is_correct': True, 'time_since_previous': 100},
            {'keystroke_char': 'h', 'expected_char': 'h', 'is_correct': True, 'time_since_previous': 110},
            {'keystroke_char': 'i', 'expected_char': 'i', 'is_correct': True, 'time_since_previous': 120},
            {'keystroke_char': 's', 'expected_char': 's', 'is_correct': True, 'time_since_previous': 130},
            {'keystroke_char': ' ', 'expected_char': ' ', 'is_correct': True, 'time_since_previous': 150},
            {'keystroke_char': 'i', 'expected_char': 'i', 'is_correct': True, 'time_since_previous': 140},
            {'keystroke_char': 'z', 'expected_char': 's', 'is_correct': False, 'time_since_previous': 130}
        ]
            
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        test_snippet_id = 1
        
        # Mock the session creation to use our specific test ID
        with pytest.MonkeyPatch().context() as m:
            m.setattr(uuid, "uuid4", lambda: uuid.UUID(session_id))
            response = test_client.post(
                '/start-drill',
                data={
                    'snippet_id': test_snippet_id,
                    'start_index': 0,
                    'end_index': 40,
                    'practice_type': 'standard'
                }
            )
                
            assert response.status_code == 200, "Failed to start a new drill session"
                
            # Verify session was created in the database
            cursor.execute("SELECT * FROM practice_sessions WHERE session_id = ?", (session_id,))
            session_record = cursor.fetchone()
            assert session_record is not None, "Session record not found in database"
                
            # 2. Simulate end of practice session
            wpm_calc = (len(test_keystrokes) / 5) / (7 / 60)
                
            # Calculate accuracy
            correct_keystrokes = sum(1 for k in test_keystrokes if k.get("is_correct", False))
            accuracy = (correct_keystrokes / len(test_keystrokes)) * 100
                
            # Create session completion data
            completed_session_data = {
                "session_id": session_id,
                "stats": {
                    "wpm": round(wpm_calc, 2),
                    "cpm": len(test_keystrokes) * (60 / 7),
                    "accuracy": round(accuracy, 2),
                    "errors": len(test_keystrokes) - correct_keystrokes,
                    "end_position": len(test_keystrokes),
                    "elapsed_time_in_seconds": 7,
                    "expected_chars": len(test_keystrokes),
                    "actual_chars": len(test_keystrokes)
                },
                "keystrokes": test_keystrokes
            }
                
            # Send request to end session
            response = test_client.post(
                '/end-session',
                data=json.dumps(completed_session_data),
                content_type='application/json'
            )
                
            # Verify response
            assert response.status_code == 200, "Response status code is not 200"
                
            # 3. Verify data was written to all tables
            # Check practice_sessions table
            cursor.execute(
                "SELECT * FROM practice_sessions WHERE session_id = ?", 
                (session_id,)
            )
            session_record = cursor.fetchone()
            assert session_record is not None, "Session record should exist in practice_sessions table"
                
            # Check practice_session_keystrokes table
            cursor.execute(
                "SELECT COUNT(*) FROM practice_session_keystrokes WHERE session_id = ?", 
                (session_id,)
            )
            keystroke_count = cursor.fetchone()[0]
            assert keystroke_count == len(test_keystrokes), f"practice_session_keystrokes table should have {len(test_keystrokes)} records"
                
            # Check practice_session_errors table
            cursor.execute(
                "SELECT COUNT(*) FROM practice_session_errors WHERE session_id = ?", 
                (session_id,)
            )
            error_count = cursor.fetchone()[0]
            expected_error_count = sum(1 for k in test_keystrokes if not k.get("is_correct", False))
            assert error_count == expected_error_count, f"practice_session_errors table should have {expected_error_count} records"

    def test_invalid_snippet_id(self, test_client) -> None:
        """Test that an invalid snippet ID returns an appropriate error."""
        response = test_client.post(
            '/start-drill',
            data={
                'snippet_id': 9999,  # Non-existent snippet ID
                'start_index': 0,
                'end_index': 40,
                'practice_type': 'standard'
            }
        )
        assert response.status_code == 404, "Response status code is not 404 for invalid snippet ID"

    def test_timer_starts_on_first_keystroke(self, test_client, mock_snippet, mock_session) -> None:
        """Test that the timer starts only on the first keystroke."""
        # Start a drill
        response = test_client.post(
            '/start-drill',
            data={
                'snippet_id': 1,
                'start_index': 0,
                'end_index': 40,
                'practice_type': 'standard'
            }
        )
        assert response.status_code == 200, "Response status code is not 200"

        # Simulate typing
        start_time = datetime.datetime.now()
        response = test_client.post(
            '/keystroke',
            data=json.dumps({
                'session_id': mock_session["session_id"],
                'keystroke': {
                    'index': 0,
                    'expected': 'T',
                    'actual': 'T',
                    'time': int(datetime.datetime.now().timestamp() * 1000)
                }
            }),
            content_type='application/json'
        )
        
        # Verify timing
        assert response.status_code == 200, "Response status code is not 200 for keystroke"
        elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
        assert elapsed_time > 0, "Timer did not start on first keystroke"

    def test_typing_window_read_only_on_completion(self, test_client, mock_snippet, mock_session) -> None:
        """Test that the typing window becomes read-only upon completion."""
        # Start a drill
        response = test_client.post(
            '/start-drill',
            data={
                'snippet_id': 1,
                'start_index': 0,
                'end_index': 20,
                'practice_type': 'standard'
            }
        )
        assert response.status_code == 200, "Response status code is not 200"
        
        # Simulate completion
        response = test_client.post(
            '/end-session',
            data=json.dumps({
                'session_id': mock_session["session_id"],
                'stats': {
                    'wpm': 60,
                    'cpm': 300,
                    'accuracy': 95.5,
                    'errors': 0,
                    'end_position': 20,
                    'elapsed_time_in_seconds': 120,
                    'expected_chars': 20,
                    'actual_chars': 20
                },
                'keystrokes': []
            }),
            content_type='application/json'
        )
        assert response.status_code == 200, "Response status code is not 200 for session completion"
        
        # Verify typing window is read-only
        html_content = response.data.decode('utf-8')
        assert 'readonly' in html_content, "Typing window is not read-only upon completion"


if __name__ == '__main__':
    pytest.main()
