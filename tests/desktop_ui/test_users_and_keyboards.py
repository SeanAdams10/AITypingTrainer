"""
Tests for the UsersAndKeyboards dialog in the AI Typing Trainer application.
"""
import sys
from typing import Generator, Tuple
from unittest.mock import MagicMock, patch

import pytest
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from pytestqt.qtbot import QtBot

from db.database_manager import DatabaseManager
from desktop_ui.users_and_keyboards import UsersAndKeyboards
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager
from models.user import User
from models.user_manager import UserManager

# Test data
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_KEYBOARD_ID = "550e8400-e29b-41d4-a716-446655440001"
TEST_CREATED_AT = "2023-01-01T00:00:00.000000"

# Test user data
TEST_USER = User(
    user_id=TEST_USER_ID,
    first_name="Test",
    surname="User",
    email_address="test@example.com",
    created_at=TEST_CREATED_AT,
)

# Test keyboard data
TEST_KEYBOARD = Keyboard(
    keyboard_id=TEST_KEYBOARD_ID,
    user_id=TEST_USER_ID,
    keyboard_name="Test Keyboard",
    keyboard_type="QWERTY",
    created_at=TEST_CREATED_AT,
)

# Test user data for new user
NEW_USER_DATA = {
    "first_name": "New",
    "surname": "User",
    "email_address": "new@example.com"
}

# Test keyboard data for new keyboard
NEW_KEYBOARD_DATA = {
    "keyboard_name": "New Keyboard",
    "keyboard_type": "DVORAK"
}


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
    """Create a mock user manager."""
    mock = MagicMock(spec=UserManager)
    mock.db_manager = mock_db_manager
    
    # Setup return values for all methods used in the implementation
    mock.list_all_users.return_value = [TEST_USER]
    mock.get_user_by_id.return_value = TEST_USER
    mock.save_user.side_effect = lambda user: user  # Return the user that was saved
    mock.delete_user.return_value = True
    
    return mock


@pytest.fixture
def mock_keyboard_manager(mock_db_manager: MagicMock) -> MagicMock:
    """Create a mock keyboard manager."""
    mock = MagicMock(spec=KeyboardManager)
    mock.db_manager = mock_db_manager
    
    # Setup return values for all methods used in the implementation
    mock.list_keyboards_for_user.return_value = [TEST_KEYBOARD]
    mock.get_keyboard_by_id.return_value = TEST_KEYBOARD
    mock.save_keyboard.side_effect = lambda kb: kb  # Return the keyboard that was saved
    mock.delete_keyboard.return_value = True
    
    return mock


@pytest.fixture
def users_and_keyboards_dialog(
    qtbot: QtBot,
    mock_db_manager: MagicMock,
    mock_user_manager: MagicMock,
    mock_keyboard_manager: MagicMock,
) -> Generator[Tuple[UsersAndKeyboards, MagicMock, MagicMock], None, None]:
    """
    Create and return a UsersAndKeyboards dialog for testing.
    
    Yields:
        A tuple containing the dialog and the mock managers.
    """
    with (
        patch("desktop_ui.users_and_keyboards.UserManager", return_value=mock_user_manager),
        patch(
            "desktop_ui.users_and_keyboards.KeyboardManager",
            return_value=mock_keyboard_manager,
        ),
    ):
        dialog = UsersAndKeyboards(db_manager=mock_db_manager)
        dialog.show()
        qtbot.addWidget(dialog)
        yield dialog, mock_user_manager, mock_keyboard_manager
        dialog.close()


class TestUsersAndKeyboards:
    """Test cases for the UsersAndKeyboards dialog."""

    def test_initialization(
        self, users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock]
    ) -> None:
        """Test that the dialog initializes correctly."""
        dialog, mock_user_manager, _ = users_and_keyboards_dialog
        assert dialog.windowTitle() == "Manage Users & Keyboards"
        mock_user_manager.list_all_users.assert_called_once()

    def test_load_users(
        self, users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock]
    ) -> None:
        """Test that users are loaded correctly."""
        dialog, mock_user_manager, _ = users_and_keyboards_dialog
        assert dialog.user_list.count() == 1
        
        expected_text = (
            f"{TEST_USER.first_name} {TEST_USER.surname} ({TEST_USER.email_address})"
        )
        assert dialog.user_list.item(0).text() == expected_text
        mock_user_manager.list_all_users.assert_called_once()

    def test_load_keyboards_for_user(
        self, users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock]
    ) -> None:
        """Test that keyboards are loaded for the selected user."""
        dialog, _, mock_keyboard_manager = users_and_keyboards_dialog
        
        # Select the first user
        dialog.user_list.setCurrentRow(0)
        
        # Check that keyboards are loaded
        mock_keyboard_manager.list_keyboards_for_user.assert_called_once_with(
            TEST_USER.user_id
        )
        assert dialog.keyboard_list.count() == 1
        assert dialog.keyboard_list.item(0).text() == TEST_KEYBOARD.keyboard_name

    def test_add_user(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        qtbot: QtBot,
    ) -> None:
        """Test adding a new user."""
        dialog, mock_user_manager, _ = users_and_keyboards_dialog
        initial_count = dialog.users_list.count()
        
        # Create a new user that will be returned by the dialog
        new_user = User(
            user_id="new-user-id",
            first_name=NEW_USER_DATA["first_name"],
            surname=NEW_USER_DATA["surname"],
            email_address=NEW_USER_DATA["email_address"]
        )
        
        # Mock the UserDialog
        with patch("desktop_ui.users_and_keyboards.UserDialog") as mock_dialog:
            mock_dialog.return_value.exec_.return_value = QtWidgets.QDialog.Accepted
            mock_dialog.return_value.get_user.return_value = new_user
            
            # Click the add user button
            qtbot.mouseClick(dialog.add_user_btn, QtCore.Qt.LeftButton)
            
            # Check that the user was saved
            mock_user_manager.save_user.assert_called_once()
            assert dialog.users_list.count() == initial_count + 1  # Original + new user
            
            # Verify the new user is in the list
            found = False
            for i in range(dialog.users_list.count()):
                item = dialog.users_list.item(i)
                if item.data(Qt.UserRole) == new_user.user_id:
                    found = True
                    break
            assert found, "New user was not added to the list"

    def test_edit_user(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        qtbot: QtBot,
    ) -> None:
        """Test editing an existing user."""
        dialog, mock_user_manager, _ = users_and_keyboards_dialog
        
        # Select the first user
        dialog.users_list.setCurrentRow(0)
        
        # Create an updated user that will be returned by the dialog
        updated_user = User(
            user_id=TEST_USER_ID,
            first_name="Updated",
            surname=TEST_USER.surname,
            email_address="updated@example.com"
        )
        
        # Mock the UserDialog
        with patch("desktop_ui.users_and_keyboards.UserDialog") as mock_dialog:
            mock_dialog.return_value.exec_.return_value = QtWidgets.QDialog.Accepted
            mock_dialog.return_value.get_user.return_value = updated_user
            
            # Click the edit user button
            qtbot.mouseClick(dialog.edit_user_btn, QtCore.Qt.LeftButton)
            
            # Check that the user was updated
            mock_user_manager.save_user.assert_called_once()
            
            # Verify the user in the list was updated
            current_item = dialog.users_list.currentItem()
            assert current_item is not None
            assert "Updated" in current_item.text()
            assert "updated@example.com" in current_item.text()

    def test_delete_user(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        qtbot: QtBot,
    ) -> None:
        """Test deleting a user with confirmation."""
        dialog, mock_user_manager, _ = users_and_keyboards_dialog
        initial_count = dialog.users_list.count()
        
        # Select the user
        dialog.users_list.setCurrentRow(0)
        
        # Mock the confirmation dialog to return Yes
        with patch("PyQt5.QtWidgets.QMessageBox.question") as mock_question:
            mock_question.return_value = QtWidgets.QMessageBox.Yes
            
            # Click the delete user button
            qtbot.mouseClick(dialog.delete_user_btn, QtCore.Qt.LeftButton)
            
            # Check that the confirmation dialog was shown
            mock_question.assert_called_once()
            
            # Check that the user was deleted
            mock_user_manager.delete_user.assert_called_once_with(TEST_USER.user_id)
            
            # Verify the user was removed from the list
            assert dialog.users_list.count() == initial_count - 1
    
    def test_delete_user_cancelled(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        qtbot: QtBot,
    ) -> None:
        """Test cancelling user deletion."""
        dialog, mock_user_manager, _ = users_and_keyboards_dialog
        initial_count = dialog.users_list.count()
        
        # Select the user
        dialog.users_list.setCurrentRow(0)
        
        # Mock the confirmation dialog to return No
        with patch("PyQt5.QtWidgets.QMessageBox.question") as mock_question:
            mock_question.return_value = QtWidgets.QMessageBox.No
            
            # Click the delete user button
            qtbot.mouseClick(dialog.delete_user_btn, QtCore.Qt.LeftButton)
            
            # Check that the confirmation dialog was shown
            mock_question.assert_called_once()
            
            # Check that delete was not called
            mock_user_manager.delete_user.assert_not_called()
            
            # Verify the user is still in the list
            assert dialog.users_list.count() == initial_count

    def test_add_keyboard(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        qtbot: QtBot,
    ) -> None:
        """Test adding a new keyboard."""
        dialog, _, mock_keyboard_manager = users_and_keyboards_dialog
        initial_count = dialog.keyboards_list.count()
        
        # Select the user first
        dialog.users_list.setCurrentRow(0)
        
        # Create a new keyboard that will be returned by the dialog
        new_keyboard = Keyboard(
            keyboard_id="new-keyboard-id",
            user_id=TEST_USER_ID,
            keyboard_name=NEW_KEYBOARD_DATA["keyboard_name"],
            keyboard_type=NEW_KEYBOARD_DATA["keyboard_type"]
        )
        
        # Mock the KeyboardDialog
        with patch("desktop_ui.users_and_keyboards.KeyboardDialog") as mock_dialog:
            mock_dialog.return_value.exec_.return_value = QtWidgets.QDialog.Accepted
            mock_dialog.return_value.get_keyboard.return_value = new_keyboard
            
            # Click the add keyboard button
            qtbot.mouseClick(dialog.add_keyboard_btn, QtCore.Qt.LeftButton)
            
            # Check that the keyboard was saved
            mock_keyboard_manager.save_keyboard.assert_called_once()
            
            # Verify the new keyboard is in the list
            found = False
            for i in range(dialog.keyboards_list.count()):
                item = dialog.keyboards_list.item(i)
                if item.data(Qt.UserRole) == new_keyboard.keyboard_id:
                    found = True
                    break
            assert found, "New keyboard was not added to the list"

    def test_delete_keyboard(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        qtbot: QtBot,
    ) -> None:
        """Test deleting a keyboard."""
        dialog, _, mock_keyboard_manager = users_and_keyboards_dialog
        
        # Select the user first
        dialog.user_list.setCurrentRow(0)
        
        # Select the keyboard
        dialog.keyboard_list.setCurrentRow(0)
        
        # Mock the confirmation dialog
        with patch(
            "PyQt5.QtWidgets.QMessageBox.question",
            return_value=QtWidgets.QMessageBox.Yes,
        ) as mock_question:
            # Click the delete keyboard button
            qtbot.mouseClick(dialog.delete_keyboard_btn, QtCore.Qt.LeftButton)
            
            # Check that the confirmation dialog was shown with the correct message
            mock_question.assert_called_once()
            args, _ = mock_question.call_args
            assert "Confirm Deletion" in args[1]  # Title
            assert "Are you sure you want to delete the keyboard" in args[2]
            
            # Check that the keyboard was deleted
            mock_keyboard_manager.delete_keyboard.assert_called_once_with(
                TEST_KEYBOARD.keyboard_id
            )
            
            # Verify the keyboard list is refreshed
            mock_keyboard_manager.list_keyboards_for_user.assert_called_with(TEST_USER_ID)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--capture=no"]))
