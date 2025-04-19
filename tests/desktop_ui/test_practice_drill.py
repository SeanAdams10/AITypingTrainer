"""
Test module for practice drill functionality in AITypingTrainer.

This module contains tests for validating the practice drill feature including:
- Creating practice sessions
- Logging keystrokes
- Tracking errors
- Calculating performance metrics
"""
import tempfile
import pytest
from typing import Dict, List, Any, Optional

from models.practice_session import PracticeSession
from models.keystroke import Keystroke
from models.snippet import Snippet
from db.database_manager import DatabaseManager
from app import create_app


@pytest.fixture
def client():
    """Fixture to provide a test client for the Flask app."""
    app = create_app({'TESTING': True})
    with app.test_client() as client:
        yield client


class TestPracticeDrill:
    """Test case for practice drill functionality."""
    
    @pytest.fixture
    def test_db_file(self) -> str:
        """Create a temporary database file for testing."""
        # Create a temporary file for our test database
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        
        # Close the file descriptor (we'll use the path)
        os.close(db_fd)
        
        # Return the path to the temp file
        yield db_path
        
        # Clean up after the test
        os.unlink(db_path)
    
    @pytest.fixture
    def setup_database(self, test_db_file: str) -> None:
        """Set up the test database with required tables."""
        # Create a connection to the temp database
        conn = sqlite3.connect(test_db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Create practice_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS practice_sessions (
                session_id TEXT PRIMARY KEY,
                snippet_id INTEGER NOT NULL,
                snippet_index_start INTEGER DEFAULT 0,
                snippet_index_end INTEGER DEFAULT 0,
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
        ''')
        
        # Create practice_session_keystrokes table
        cursor.execute('''
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
        ''')
        
        # Create practice_session_errors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS practice_session_errors (
                session_id TEXT,
                error_id INTEGER,
                keystroke_id INTEGER,
                keystroke_char TEXT NOT NULL,
                expected_char TEXT NOT NULL,
                PRIMARY KEY (session_id, error_id)
            )
        ''')
        
        # Create text_snippets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS text_snippets (
                snippet_id INTEGER PRIMARY KEY,
                category_id INTEGER NOT NULL,
                snippet_name TEXT NOT NULL
            )
        ''')
        
        # Create snippet_content table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snippet_content (
                snippet_id INTEGER PRIMARY KEY,
                content TEXT NOT NULL
            )
        ''')
        
        # Add a test snippet
        cursor.execute(
            "INSERT INTO text_snippets (snippet_id, category_id, snippet_name) VALUES (1, 1, 'Test Snippet')"
        )
        
        cursor.execute(
            "INSERT INTO snippet_content (snippet_id, content) VALUES (1, 'This is a test snippet for typing practice.')"
        )
        
        conn.commit()
        conn.close()
        
        # Setup the database manager to use our test database
        manager = DatabaseManager()
        manager.db_path = test_db_file
        DatabaseManager._instance = manager
        
        return None
    
    def test_create_practice_session(self, test_db_file: str, setup_database: None) -> None:
        """Test creating a practice session with various options."""
        # Create a practice session
        session = PracticeSession(
            snippet_id=1,
            snippet_index_start=0,
            snippet_index_end=10,
            practice_type='beginning'
        )
        
        # Start the session
        success = session.start()
        
        # Verify session was created
        assert success, "Failed to start practice session"
        assert session.session_id is not None, "Session ID should be generated"
        
        # Check database record
        db = DatabaseManager()
        results = db.execute_query(
            "SELECT * FROM practice_sessions WHERE session_id = ?", 
            (session.session_id,)
        )
        assert len(results) == 1, "Session record should exist in database"
        
        session_record = results[0]
        assert session_record['snippet_id'] == 1, "Snippet ID should match"
        assert session_record['practice_type'] == 'beginning', "Practice type should match"
    
    def test_custom_practice_type(self, test_db_file: str, setup_database: None) -> None:
        """Test creating a practice session with a custom practice type."""
        # Create a practice session with custom type
        custom_session = PracticeSession(
            snippet_id=1,
            snippet_index_start=5,
            snippet_index_end=15,
            practice_type='custom'
        )
        
        # Start the session
        success = custom_session.start()
        assert success, "Failed to start custom practice session"
        
        # Check database record
        db = DatabaseManager()
        results = db.execute_query(
            "SELECT * FROM practice_sessions WHERE session_id = ?", 
            (custom_session.session_id,)
        )
        assert len(results) == 1, "Custom session record should exist in database"
        
        custom_record = results[0]
        assert custom_record['practice_type'] == 'custom', "Custom practice type should be stored"
    
    def test_log_keystrokes(self, test_db_file: str, setup_database: None) -> None:
        """Test logging keystrokes during a practice session."""
        # Create and start a practice session
        session = PracticeSession(snippet_id=1)
        session.start()
        
        # Create keystroke objects
        keystrokes = [
            {
                'session_id': session.session_id,
                'keystroke_id': 0,
                'keystroke_char': 'T',
                'expected_char': 'T',
                'is_correct': True,
                'keystroke_time': datetime.datetime.now().isoformat(),
                'time_since_previous': None
            },
            {
                'session_id': session.session_id,
                'keystroke_id': 1,
                'keystroke_char': 'g',
                'expected_char': 'h',
                'is_correct': False,
                'keystroke_time': datetime.datetime.now().isoformat(),
                'time_since_previous': 100
            },
            {
                'session_id': session.session_id,
                'keystroke_id': 2,
                'keystroke_char': 'i',
                'expected_char': 'i',
                'is_correct': True,
                'keystroke_time': datetime.datetime.now().isoformat(),
                'time_since_previous': 110
            }
        ]
        
        # Use the class method to save keystrokes
        success = Keystroke.save_many(session.session_id, keystrokes)
        assert success, "Failed to save keystrokes"
        
        # Check the database records
        db = DatabaseManager()
        results = db.execute_query(
            "SELECT * FROM practice_session_keystrokes WHERE session_id = ? ORDER BY keystroke_id",
            (session.session_id,)
        )
        
        assert len(results) == 3, "Should have 3 keystroke records"
        
        # Check incorrect keystroke
        assert results[1]['keystroke_char'] == 'g', "Incorrect character should be logged"
        assert results[1]['expected_char'] == 'h', "Expected character should be logged"
        assert results[1]['is_correct'] == 0, "Should be marked as incorrect"
    
    def test_end_session_metrics(self, test_db_file: str, setup_database: None) -> None:
        """Test ending a practice session and calculating metrics."""
        # Create and start a practice session
        session = PracticeSession(snippet_id=1)
        session.start()
        
        # Create keystrokes with timestamps
        start_time = datetime.datetime.now()
        keystrokes = []
        
        # Add 4 keystrokes, one with an error
        for i, (char, expected, is_correct) in enumerate([
            ('T', 'T', True),    # Correct
            ('h', 'h', True),    # Correct
            ('o', 'i', False),   # Error
            ('s', 's', True)     # Correct
        ]):
            # Create keystroke 1 second apart
            keystroke_time = start_time + datetime.timedelta(seconds=i)
            
            keystrokes.append({
                'session_id': session.session_id,
                'keystroke_id': i,
                'keystroke_char': char,
                'expected_char': expected,
                'is_correct': is_correct,
                'keystroke_time': keystroke_time.isoformat(),
                'time_since_previous': 1000 if i > 0 else None
            })
        
        # Save the keystrokes
        Keystroke.save_many(session.session_id, keystrokes)
        
        # End the session after 4 seconds
        stats = {
            'wpm': 15.0,  # 60 * 4 characters / 5 characters per word / 4 seconds
            'cpm': 60.0,  # 4 characters / 4 seconds * 60
            'expected_chars': 4,
            'actual_chars': 4,  # Changed from 'typed_chars' to 'actual_chars'
            'errors': 1,  # Changed from 'error_count' to 'errors'
            'accuracy': 75.0  # 3 correct out of 4 = 75%
        }
        
        success = session.end(stats)
        
        assert success, "Failed to complete session"
        
        # Verify metrics
        db = DatabaseManager()
        results = db.execute_query(
            "SELECT * FROM practice_sessions WHERE session_id = ?", 
            (session.session_id,)
        )
        
        session_record = results[0]
        
        assert session_record['total_time'] is not None, "Total time should be recorded"
        assert session_record['errors'] == 1, "Should have 1 error"
        
        # Accuracy should be 75% (3 correct out of 4)
        assert session_record['accuracy'] is not None, "Accuracy should be calculated"
        assert 70 <= float(session_record['accuracy']) <= 80, "Accuracy should be approximately 75%"
        
        # WPM should be calculated
        assert session_record['session_wpm'] is not None, "WPM should be calculated"
        assert float(session_record['session_wpm']) > 0, "WPM should be positive"


@pytest.fixture
def setup_test_database():
    """Set up a test database and tear it down after tests."""
    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()

    # Create practice_sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_sessions (
            session_id TEXT PRIMARY KEY,
            snippet_id INTEGER NOT NULL,
            snippet_index_start INTEGER NOT NULL,
            snippet_index_end INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            total_time REAL,
            session_wpm REAL,
            session_cpm REAL,
            expected_chars INTEGER,
            actual_chars INTEGER,
            errors INTEGER,
            accuracy REAL,
            practice_type TEXT NOT NULL
        )
    """)

    conn.commit()
    yield conn  # Provide the connection to the test

    # Tear down the database
    cursor.execute("DROP TABLE IF EXISTS practice_sessions")
    conn.commit()
    conn.close()

def test_start_practice_session(setup_test_database):
    """Test that a new practice session is correctly inserted into the database."""
    conn = setup_test_database
    session = PracticeSession(
        snippet_id=1,
        snippet_index_start=0,
        snippet_index_end=100,
        practice_type='standard'
    )

    # Start the session
    success = session.start()
    assert success, "Failed to start the practice session."

    # Verify the session is in the database
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM practice_sessions WHERE session_id = ?", (session.session_id,))
    result = cursor.fetchone()

    assert result is not None, "Session was not inserted into the practice_sessions table."
    assert result['snippet_id'] == 1, "Snippet ID does not match."
    assert result['snippet_index_start'] == 0, "Snippet start index does not match."
    assert result['snippet_index_end'] == 100, "Snippet end index does not match."
    assert result['practice_type'] == 'standard', "Practice type does not match."
    assert result['start_time'] is not None, "Start time is not set."

def test_start_drill_endpoint(client, setup_test_database, mocker):
    """Test the /start-drill endpoint to ensure it creates a new session."""
    conn = setup_test_database

    # Mock snippet retrieval
    snippet_id = 1
    snippet_content = "This is a test snippet."
    with mocker.patch('db.models.snippet.Snippet.get_by_id', return_value=mocker.MagicMock(content=snippet_content)):
        response = client.post(
            '/start-drill',
            data={
                'snippet_id': snippet_id,
                'start_index': 0,
                'end_index': len(snippet_content),
                'practice_type': 'standard'
            }
        )

        assert response.status_code == 200, "Failed to start drill via endpoint."

        # Verify the session is in the database
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM practice_sessions WHERE snippet_id = ?", (snippet_id,))
        result = cursor.fetchone()

        assert result is not None, "Session was not inserted into the practice_sessions table via endpoint."
        assert result['snippet_index_start'] == 0, "Snippet start index does not match via endpoint."
        assert result['snippet_index_end'] == len(snippet_content), "Snippet end index does not match via endpoint."
