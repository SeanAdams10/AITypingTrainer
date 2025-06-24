"""
Test file to isolate fixture issues in the users_and_keyboards tests.
"""
import pytest
from unittest.mock import MagicMock, patch
from typing import Generator, List, Tuple

from PySide6 import QtCore, QtWidgets
from pytestqt.qtbot import QtBot

from db.database_manager import DatabaseManager
from models.user import User
from models.keyboard import Keyboard
from models.user_manager import UserManager
from models.keyboard_manager import KeyboardManager

# Test data
TEST_USER_ID = "test-user-id"
TEST_USER = User(
    user_id=TEST_USER_ID,
    first_name="Test",
    surname="User",
    email_address="test@example.com"
)

@pytest.fixture
def mock_db_manager() -> MagicMock:
    """Create a mock database manager."""
    mock = MagicMock(spec=DatabaseManager)
    mock.begin_transaction = MagicMock()
    mock.commit_transaction = MagicMock()
    mock.rollback_transaction = MagicMock()
    return mock

@pytest.fixture
def mock_user_manager(mock_db_manager: MagicMock) -> MagicMock:
    """Create a simplified stateful mock user manager."""
    mock = MagicMock(spec=UserManager)
    mock.db_manager = mock_db_manager
    
    # Create a single instance of state that will be captured by all closures
    state = {"users": [TEST_USER]}
    
    # Define static return values for list_all_users
    mock.list_all_users.return_value = state["users"]
    
    return mock

@pytest.fixture
def mock_keyboard_manager(mock_db_manager: MagicMock) -> MagicMock:
    """Create a simplified mock keyboard manager."""
    mock = MagicMock(spec=KeyboardManager)
    mock.db_manager = mock_db_manager
    
    # Create empty dictionaries for state
    keyboards = {}
    
    # Define simple return value for list_keyboards_for_user
    mock.list_keyboards_for_user.return_value = []
    
    return mock

def test_fixture_setup(mock_user_manager, mock_keyboard_manager, qtbot):
    """Test that fixtures can be set up correctly."""
    # Create a simple widget to test qtbot
    widget = QtWidgets.QLabel("Test")
    qtbot.addWidget(widget)
    
    # Test that mock_user_manager works
    users = mock_user_manager.list_all_users()
    assert len(users) == 1
    assert users[0].user_id == TEST_USER_ID
    
    # Test that mock_keyboard_manager works
    keyboards = mock_keyboard_manager.list_keyboards_for_user(TEST_USER_ID)
    assert isinstance(keyboards, list)
