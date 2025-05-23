"""
Tests for the Keystroke model and related functionality.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path to allow importing from models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke

# Test data
SAMPLE_KEYSTROKES = [
    {
        'session_id': 1,
        'keystroke_time': '2025-05-20T10:00:00',
        'keystroke_char': 'a',
        'expected_char': 'a',
        'is_correct': 1,
        'time_since_previous': 0
    },
    {
        'session_id': 1,
        'keystroke_time': '2025-05-20T10:00:01',
        'keystroke_char': 'b',
        'expected_char': 'b',
        'is_correct': 1,
        'time_since_previous': 1000
    },
    {
        'session_id': 1,
        'keystroke_time': '2025-05-20T10:00:02',
        'keystroke_char': 'c',
        'expected_char': 'x',
        'is_correct': 0,
        'time_since_previous': 1000
    }
]

@pytest.fixture
def mock_db():
    """Create a mock database with test data."""
    db = MagicMock(spec=DatabaseManager)
    db.execute.return_value = None
    db.fetchall.return_value = SAMPLE_KEYSTROKES
    return db

class TestKeystroke:
    """Test cases for the Keystroke class."""
    
    def test_delete_all_keystrokes_success(self, mock_db):
        """Test that delete_all_keystrokes deletes all keystrokes."""
        # Setup
        mock_cursor = MagicMock()
        mock_db.execute.return_value = mock_cursor
        
        # Execute
        result = Keystroke.delete_all_keystrokes(mock_db)
        
        # Verify
        assert result is True
        mock_db.execute.assert_called_once_with("DELETE FROM session_keystrokes", ())
        # Note: DatabaseManager.execute() handles commit internally
    
    def test_delete_all_keystrokes_error(self, mock_db):
        """Test that delete_all_keystrokes handles database errors."""
        # Setup
        from sqlite3 import Error as SQLiteError
        mock_db.execute.side_effect = SQLiteError("Database error")
        
        # Execute
        with patch('models.keystroke.logger') as mock_logger:
            result = Keystroke.delete_all_keystrokes(mock_db)
            
            # Verify
            assert result is False
            mock_logger.error.assert_called_once()
            assert "Error deleting keystrokes" in mock_logger.error.call_args[0][0]
            assert "Database error" in str(mock_logger.error.call_args[0][1])
