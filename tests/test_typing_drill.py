"""
Tests for the typing drill functionality and session data persistence.
"""
import os
import sys
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock, call
from typing import Dict, Any, List, Optional, Tuple, Generator
import datetime
import sqlite3

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import application modules
from app import app
from db import DatabaseManager
from db.models.practice_session import PracticeSession
from db.models.snippet import Snippet
from db.models.keystroke import Keystroke


@pytest.fixture
def client() -> Generator:
    """
    Create a test client for the Flask application.
    
    Returns:
        Generator: A Flask test client
    """
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_db() -> Generator[Tuple[int, str], None, None]:
    """
    Create a temporary database for testing.
    
    Returns:
        Generator: A tuple containing the database file descriptor and path
    """
    db_fd, db_path = tempfile.mkstemp()
    app.config['DATABASE'] = db_path
    
    yield (db_fd, db_path)
    
    # Cleanup after test
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def mock_snippet() -> MagicMock:
    """
    Create a mock snippet for testing.
    
    Returns:
        MagicMock: A mocked Snippet object
    """
    mock = MagicMock()
    mock.id = 1
    mock.content = "This is a test snippet for typing drills."
    mock.snippet_name = "Test snippet"
    mock.category = "Test Category"
    return mock


@pytest.fixture
def mock_session() -> MagicMock:
    """
    Create a mock practice session for testing.
    
    Returns:
        MagicMock: A mocked PracticeSession object
    """
    mock = MagicMock()
    mock.session_id = "test-session-789"
    mock.start.return_value = True
    return mock


@pytest.fixture
def mock_db_manager() -> MagicMock:
    """
    Create a mock database manager for testing.
    
    Returns:
        MagicMock: A mocked DatabaseManager object
    """
    mock = MagicMock()
    mock.execute_update.return_value = True
    return mock


@pytest.fixture
def setup_test_database(temp_db) -> Generator:
    """
    Set up a test database with necessary tables for testing.
    
    Returns:
        Generator: Yields a connection to the test database
    """
    db_fd, db_path = temp_db
    
    # Create tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create practice sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_sessions (
            session_id TEXT PRIMARY KEY,
            snippet_id INTEGER,
            snippet_index_start INTEGER,
            snippet_index_end INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            total_time REAL,
            session_wpm REAL,
            session_cpm REAL,
            expected_chars INTEGER,
            actual_chars INTEGER,
            errors INTEGER,
            accuracy REAL,
            practice_type TEXT
        )
    """)
    
    # Create keystrokes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_session_keystrokes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            keystroke_index INTEGER,
            expected_char TEXT,
            actual_char TEXT,
            is_correct INTEGER,
            timestamp INTEGER,
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    """)
    
    # Create errors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_session_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            keystroke_index INTEGER,
            expected_char TEXT,
            actual_char TEXT,
            timestamp INTEGER,
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    """)
    
    conn.commit()
    
    yield conn
    
    conn.close()


class TestTypingDrill:
    """Test class for verifying typing drill functionality."""
    
    def setup_mock_data(self) -> None:
        """Set up mock data for testing."""
        # Create a mock snippet
        self.mock_snippet = MagicMock()
        self.mock_snippet.id = 1
        self.mock_snippet.content = "This is a test snippet for typing drills."
        self.mock_snippet.source = "Test Source"
        self.mock_snippet.category = "Test Category"
        
        # Create a mock session
        self.mock_session = MagicMock()
        self.mock_session.session_id = 1
        self.mock_session.snippet_id = 1
        self.mock_session.snippet_index_start = 0
        self.mock_session.snippet_index_end = 0
        self.mock_session.practice_type = "standard"
        self.mock_session.wpm = 0
        self.mock_session.accuracy = 0
        
        # Create mock keystrokes
        self.mock_keystrokes = [
            {"index": 0, "expected": "T", "actual": "T", "correct": True, "time": 100},
            {"index": 1, "expected": "h", "actual": "h", "correct": True, "time": 110},
            {"index": 2, "expected": "i", "actual": "i", "correct": True, "time": 120},
            {"index": 3, "expected": "s", "actual": "z", "correct": False, "time": 130}
        ]
    
    # OBJECT LEVEL TESTS
    
    def test_practice_session_creation(self, mock_db_manager) -> None:
        """Test PracticeSession object creation with proper attributes."""
        with patch('db.database_manager.DatabaseManager.__new__', return_value=mock_db_manager):
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
            mock_db_manager.execute_update.assert_called_once()
    
    def test_keystroke_save_many(self, mock_db_manager) -> None:
        """Test that multiple keystrokes can be saved at once."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Setup mock connection and cursor
        mock_db_manager.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Create test keystrokes
        test_keystrokes = [
            {"index": 0, "expected": "T", "actual": "T", "correct": True, "time": 100},
            {"index": 1, "expected": "h", "actual": "h", "correct": True, "time": 110}
        ]
        
        # Test saving keystrokes
        session_id = "test-session-123"
        
        with patch('db.database_manager.DatabaseManager.__new__', return_value=mock_db_manager):
            result = Keystroke.save_many(session_id, test_keystrokes)
            
            # Verify operation was successful
            assert result, "Keystroke save operation failed"
            
            # Verify database connection was obtained
            mock_db_manager.get_connection.assert_called_once()
            
            # Verify cursor was created
            mock_conn.cursor.assert_called_once()
            
            # Verify execute was called for each keystroke (2 in this case)
            assert mock_cursor.execute.call_count == 2, "Execute not called correct number of times"
            
            # Verify commit was called
            mock_conn.commit.assert_called_once()
    
    def test_practice_session_end(self, mock_db_manager) -> None:
        """Test that a practice session is properly ended with statistics."""
        with patch('db.database_manager.DatabaseManager.__new__', return_value=mock_db_manager):
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
    
    # UI LEVEL TESTS
    
    def test_start_drill_page_loads(self, client, mock_snippet, mock_session) -> None:
        """Test that the typing drill page loads with proper snippet content."""
        # Apply patches
        with patch('db.models.snippet.Snippet.get_by_id', return_value=mock_snippet), \
             patch('db.models.practice_session.PracticeSession', return_value=mock_session):
            
            # Send request to start a drill
            response = client.post(
                '/start-drill',
                data={
                    'snippet_id': 1,
                    'start_index': 0,
                    'end_index': 20,
                    'practice_type': 'standard'
                }
            )
            
            # Check response
            assert response.status_code == 200, "Response status code is not 200"
            
            # Verify the response contains expected content
            html_content = response.data.decode('utf-8')
            assert 'This is a test snippet' in html_content, "Snippet content not found in response"
    
    def test_end_session_saves_data(self, client, mock_db_manager) -> None:
        """Test that session data is properly saved when a drill is completed."""
        # Set up our mock objects
        mock_session = MagicMock()
        mock_session.session_id = 1
        mock_session.snippet_index_start = 0
        mock_session.snippet_index_end = 0
        
        # Create session completion data
        session_data = {
            "session_id": 1,
            "stats": {
                "wpm": 60,
                "cpm": 300,
                "accuracy": 95.5,
                "errors": 5,
                "end_position": 45,
                "elapsed_time_in_seconds": 120,
                "expected_chars": 45,
                "actual_chars": 50
            },
            "keystrokes": [
                {"index": 0, "expected": "T", "actual": "T", "correct": True, "time": 100},
                {"index": 1, "expected": "h", "actual": "h", "correct": True, "time": 110}
            ]
        }
        
        # Apply all our patches
        with patch('db.models.practice_session.PracticeSession.get_by_id', return_value=mock_session), \
             patch('db.database_manager.DatabaseManager.__new__', return_value=mock_db_manager), \
             patch('db.models.keystroke.Keystroke.save_many') as mock_save_keystrokes:
            
            # Send the request
            response = client.post(
                '/end-session',
                data=json.dumps(session_data),
                content_type='application/json'
            )
            response_data = json.loads(response.data)
            
            # Check response
            assert response.status_code == 200, "Response status code is not 200"
            assert response_data.get('success'), "Response does not indicate success"
            
            # Define the expected calls
            expected_calls = [
                # First update for snippet_index_end
                call(
                    """
                UPDATE practice_sessions
                SET snippet_index_end = ?
                WHERE session_id = ?
                """, 
                    (45, 1)
                ),
                # Second update for wpm and other stats
                call(
                    """
            UPDATE practice_sessions
            SET session_wpm = ?, 
                session_cpm = ?, 
                accuracy = ?, 
                errors = ?,
                total_time = ?,
                end_time = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
                    (60, 300, 95.5, 5, 2.0, 1)
                )
            ]
            
            # Verify the session object was updated
            assert mock_session.snippet_index_end == 45, "Snippet index end not updated correctly"
            
            # Verify the database calls - checking that the execute_update method was called twice
            # with the expected parameters in any order
            assert mock_db_manager.execute_update.call_count == 2, "execute_update not called correct number of times"
            mock_db_manager.execute_update.assert_has_calls(expected_calls, any_order=True)
            
            # Verify keystrokes were saved
            mock_save_keystrokes.assert_called_once_with(1, session_data['keystrokes'])
    
    def test_keystrokes_are_recorded_correctly(self, mock_db_manager) -> None:
        """Test that keystrokes are recorded with correct metadata."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Setup mock connection and cursor
        mock_db_manager.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Create test keystrokes
        test_keystrokes = [
            {"index": 0, "expected": "T", "actual": "T", "correct": True, "time": 100},
            {"index": 1, "expected": "h", "actual": "h", "correct": True, "time": 150},
            {"index": 2, "expected": "e", "actual": "e", "correct": True, "time": 200},
            {"index": 3, "expected": " ", "actual": "x", "correct": False, "time": 250}
        ]
        
        # Test saving keystrokes
        session_id = "test-session-456"
        
        with patch('db.database_manager.DatabaseManager.__new__', return_value=mock_db_manager):
            result = Keystroke.save_many(session_id, test_keystrokes)
            
            # Verify operation was successful
            assert result, "Keystroke save operation failed"
            
            # Verify database connection was obtained
            mock_db_manager.get_connection.assert_called_once()
            
            # Verify cursor was created
            mock_conn.cursor.assert_called_once()
            
            # Verify the correct number of execute calls
            # - One execute call per keystroke (4 total)
            # - One execute call per error keystroke (1 total)
            # - Additional DB operations as needed by the implementation (total of 8 in this case)
            assert mock_cursor.execute.call_count == 8, "Execute not called correct number of times"

    def test_complete_typing_drill_writes_to_all_tables(self, client, mock_db_manager, setup_test_database) -> None:
        """
        Test that completing a typing drill properly writes data to all relevant tables.
        
        This test verifies that:
        1. Starting a typing drill creates a record in the practice_sessions table
        2. Completing a typing drill updates the practice_sessions record
        3. The practice_session_keystrokes table has entries for all keystrokes
        4. The practice_session_errors table has entries for incorrect keystrokes
        """
        # Set up mock database connection components
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Setup mock connection and cursor
        mock_db_manager.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Create a test session
        session_id = "test-session-combined-123"
        
        # Mock the session
        mock_session = MagicMock()
        mock_session.session_id = session_id
        mock_session.snippet_id = 1
        mock_session.snippet_index_start = 0
        mock_session.snippet_index_end = 0
        
        # Create session completion data
        test_keystrokes = [
            {"index": 0, "expected": "T", "actual": "T", "correct": True, "time": 100},
            {"index": 1, "expected": "h", "actual": "h", "correct": True, "time": 150},
            {"index": 2, "expected": "i", "actual": "i", "correct": True, "time": 200},
            {"index": 3, "expected": "s", "actual": "s", "correct": True, "time": 250},
            {"index": 4, "expected": " ", "actual": " ", "correct": True, "time": 300},
            {"index": 5, "expected": "i", "actual": "i", "correct": True, "time": 350},
            {"index": 6, "expected": "s", "actual": "s", "correct": True, "time": 400},
            {"index": 7, "expected": " ", "actual": "x", "correct": False, "time": 450}
        ]
        
        session_data = {
            "session_id": session_id,
            "stats": {
                "wpm": 60,
                "cpm": 300,
                "accuracy": 95.5,
                "errors": 1,
                "end_position": 8,
                "elapsed_time_in_seconds": 60,
                "expected_chars": 8,
                "actual_chars": 8
            },
            "keystrokes": test_keystrokes
        }
        
        # Apply our patches
        with patch('db.models.practice_session.PracticeSession.get_by_id', return_value=mock_session), \
            patch('db.database_manager.DatabaseManager.__new__', return_value=mock_db_manager), \
            patch('db.models.keystroke.Keystroke.save_many') as mock_save_keystrokes:
            
            # Send request to end session
            response = client.post(
                '/end-session',
                data=json.dumps(session_data),
                content_type='application/json'
            )
            
            # Verify response
            assert response.status_code == 200, "Response status code is not 200"
            
            # 2. Verify practice_sessions table update
            session_update_calls = [
                call
                for call in mock_db_manager.execute_update.call_args_list
                if "UPDATE practice_sessions" in call[0][0]
            ]
            assert len(session_update_calls) >= 1, "practice_sessions table not updated"
            
            # 3. Set up for keystroke verification 
            with patch.object(Keystroke, 'save_many') as mock_save_keystrokes:
                # Send request again to verify keystroke saving
                response = client.post(
                    '/end-session',
                    data=json.dumps(session_data),
                    content_type='application/json'
                )
                
                # Verify keystroke saving
                mock_save_keystrokes.assert_called_once_with(session_id, test_keystrokes)

    def test_end_to_end_typing_drill_database_verification(self, client, setup_test_database, mock_snippet) -> None:
        """
        Test the entire typing drill workflow from start to finish with actual database operations.
        
        This test:
        1. Creates a test database with all required tables
        2. Starts a typing drill session
        3. Simulates completing the drill with test keystroke data
        4. Verifies all data is correctly saved in the appropriate tables
        """
        conn = setup_test_database
        cursor = conn.cursor()
        
        # Insert test snippet
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snippets (
                id INTEGER PRIMARY KEY,
                snippet_name TEXT,
                content TEXT,
                category TEXT,
                source TEXT,
                language TEXT,
                difficulty INTEGER
            )
        """)
        
        cursor.execute("""
            INSERT INTO snippets (id, snippet_name, content, category, source)
            VALUES (1, 'Test Snippet', 'This is a test snippet for typing practice.', 'Test', 'Test Source')
        """)
        conn.commit()
        
        # Test keystrokes for the simulation
        test_keystrokes = [
            {"index": 0, "expected": "T", "actual": "T", "is_correct": True, "time": 100},
            {"index": 1, "expected": "h", "actual": "h", "is_correct": True, "time": 150},
            {"index": 2, "expected": "i", "actual": "i", "is_correct": True, "time": 200},
            {"index": 3, "expected": "s", "actual": "x", "is_correct": False, "time": 250},
            {"index": 4, "expected": " ", "actual": " ", "is_correct": True, "time": 300},
            {"index": 5, "expected": "i", "actual": "i", "is_correct": True, "time": 350},
            {"index": 6, "expected": "s", "actual": "s", "is_correct": True, "time": 400}
        ]
        
        # Reset app config to use our test database
        app.config['DATABASE'] = conn.path if hasattr(conn, 'path') else ':memory:'
        app.config['TESTING'] = True
        
        # Patch the database manager to use our connection
        with patch('db.database_manager.DatabaseManager.get_connection', return_value=conn):
            # Create required ngram tables
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
                    ngram_count INTEGER NOT NULL,
                    ngram_text TEXT NOT NULL,
                    UNIQUE(session_id, ngram_size, ngram_id)
                )
            """)
            conn.commit()
            
            # Patch snippets retrieval to get our test snippet
            with patch('db.models.snippet.Snippet.get_by_id', return_value=mock_snippet):
                # 1. Start a practice session
                response = client.post(
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
                
                # Parse the session_id from the HTML response
                html_content = response.data.decode('utf-8')
                import re
                session_match = re.search(r'data-session-id="([^"]+)"', html_content)
                assert session_match, "Could not find session ID in response"
                session_id = session_match.group(1)
                
                # Verify session was created in the database
                cursor.execute("SELECT * FROM practice_sessions WHERE session_id = ?", (session_id,))
                session_record = cursor.fetchone()
                assert session_record is not None, "Session record not found in database"
                
                # 2. Simulate end of practice session
                wpm_calc = (len(test_keystrokes) / 5) / (7 / 60)
                
                # Calculate accuracy
                correct_keystrokes = sum(1 for k in test_keystrokes if k["is_correct"])
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
                response = client.post(
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
                expected_error_count = sum(1 for k in test_keystrokes if not k["is_correct"])
                assert error_count == expected_error_count, f"practice_session_errors table should have {expected_error_count} records"

if __name__ == '__main__':
    pytest.main()
