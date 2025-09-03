"""Tests for the UsersAndKeyboards dialog in the AI Typing Trainer application.

Updated to use PySide6 instead of PyQt5.
"""

from typing import Generator, List, Tuple
from unittest.mock import MagicMock, patch

import pytest
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from db.database_manager import DatabaseManager
from desktop_ui.users_and_keyboards import UsersAndKeyboards
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager
from models.user import User
from models.user_manager import UserManager

# Test data constants
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_KEYBOARD_ID = "550e8400-e29b-41d4-a716-446655440001"
TEST_CREATED_AT = "2023-01-01T00:00:00.000000"


@pytest.fixture
def test_user() -> User:
    """Create a test user for tests."""
    return User(
        user_id=TEST_USER_ID,
        first_name="Test",
        surname="User",
        email_address="test@example.com",
        created_at=TEST_CREATED_AT,
    )


@pytest.fixture
def test_keyboard() -> Keyboard:
    """Create a test keyboard for tests."""
    return Keyboard(
        keyboard_id=TEST_KEYBOARD_ID,
        user_id=TEST_USER_ID,
        keyboard_name="Test Keyboard",
        keyboard_type="QWERTY",
        created_at=TEST_CREATED_AT,
    )


# Test user data for new user
NEW_USER_DATA = {"first_name": "New", "surname": "User", "email_address": "new@example.com"}

# Test keyboard data for new keyboard
NEW_KEYBOARD_DATA = {"keyboard_name": "New Keyboard", "keyboard_type": "DVORAK"}


@pytest.fixture
def mock_db_manager() -> MagicMock:
    """Create a mock database manager."""
    mock = MagicMock(spec=DatabaseManager)
    mock.begin_transaction = MagicMock()
    mock.commit_transaction = MagicMock()
    mock.rollback_transaction = MagicMock()
    return mock


@pytest.fixture
def mock_user_manager(mock_db_manager: MagicMock, test_user: User) -> MagicMock:
    """Create a simplified stateful mock user manager."""
    mock = MagicMock(spec=UserManager)
    mock.db_manager = mock_db_manager

    # Create a single instance of state that will be captured by all closures
    state = {"users": [test_user]}

    # Define static return values for list_all_users to avoid potential infinite recursion
    mock.list_all_users.return_value = state["users"]

    # Define side effect for get_user_by_id
    def get_user_by_id(user_id: str) -> User:
        for user in state["users"]:
            if user.user_id == user_id:
                return user
        from models.exceptions import UserNotFound

        raise UserNotFound(f"User {user_id} not found")

    # Define side effect for save_user
    def save_user(user: User) -> User:
        # Check if this is an update or a new user
        for i, existing in enumerate(state["users"]):
            if existing.user_id == user.user_id:
                # Update existing user
                state["users"][i] = user
                return user

        # Add new user
        state["users"].append(user)
        # Update the list_all_users return value
        mock.list_all_users.return_value = state["users"]
        return user

    # Define side effect for delete_user
    def delete_user(user_id: str) -> bool:
        for i, user in enumerate(state["users"]):
            if user.user_id == user_id:
                del state["users"][i]
                # Update the list_all_users return value
                mock.list_all_users.return_value = state["users"]
                return True
        return False

    # Assign side effects to methods
    mock.get_user_by_id.side_effect = get_user_by_id
    mock.save_user.side_effect = save_user
    mock.delete_user.side_effect = delete_user

    return mock


@pytest.fixture
def mock_keyboard_manager(mock_db_manager: MagicMock, test_keyboard: Keyboard) -> MagicMock:
    """Create a stateful mock keyboard manager."""
    mock = MagicMock(spec=KeyboardManager)
    mock.db_manager = mock_db_manager

    # Create empty dictionaries for state
    state = {
        "keyboards": {
            test_keyboard.keyboard_id: test_keyboard,
        },
        "keyboards_by_user": {TEST_USER_ID: [test_keyboard]},
    }

    # Define side effects that maintain state
    def list_keyboards_for_user(user_id: str) -> List[Keyboard]:
        return state["keyboards_by_user"].get(user_id, [])

    def get_keyboard_by_id(keyboard_id: str) -> Keyboard:
        for keyboards in state["keyboards_by_user"].values():
            for keyboard in keyboards:
                if keyboard.keyboard_id == keyboard_id:
                    return keyboard
        from models.exceptions import KeyboardNotFound

        raise KeyboardNotFound(f"Keyboard {keyboard_id} not found")

    def save_keyboard(keyboard: Keyboard) -> Keyboard:
        user_id = keyboard.user_id
        # Ensure user has a keyboard list
        if user_id not in state["keyboards_by_user"]:
            state["keyboards_by_user"][user_id] = []

        # Check if this is an update or a new keyboard
        for i, existing in enumerate(state["keyboards_by_user"][user_id]):
            if existing.keyboard_id == keyboard.keyboard_id:
                # Update existing
                state["keyboards_by_user"][user_id][i] = keyboard
                return keyboard

        # Add new keyboard
        state["keyboards_by_user"][user_id].append(keyboard)
        return keyboard

    def delete_keyboard(keyboard_id: str) -> bool:
        for user_id, keyboards in state["keyboards_by_user"].items():
            for i, keyboard in enumerate(keyboards):
                if keyboard.keyboard_id == keyboard_id:
                    del state["keyboards_by_user"][user_id][i]
                    return True
        return False

    # Assign side effects
    mock.list_keyboards_for_user.side_effect = list_keyboards_for_user
    mock.get_keyboard_by_id.side_effect = get_keyboard_by_id
    mock.save_keyboard.side_effect = save_keyboard
    mock.delete_keyboard.side_effect = delete_keyboard

    return mock


@pytest.fixture
def users_and_keyboards_dialog(
    qtbot: QtBot,
    mock_db_manager: MagicMock,
    mock_user_manager: MagicMock,
    mock_keyboard_manager: MagicMock,
) -> Generator[Tuple[UsersAndKeyboards, MagicMock, MagicMock], None, None]:
    """Create and return a UsersAndKeyboards dialog for testing.

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
        assert dialog.windowTitle() == "Users and Keyboards"
        mock_user_manager.list_all_users.assert_called_once()

    def test_load_users(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        test_user: User,
    ) -> None:
        """Test that users are loaded correctly."""
        dialog, mock_user_manager, _ = users_and_keyboards_dialog
        assert dialog.users_list.count() == 1

        expected_text = f"{test_user.first_name} {test_user.surname} ({test_user.email_address})"
        assert dialog.users_list.item(0).text() == expected_text
        mock_user_manager.list_all_users.assert_called_once()

    def test_load_keyboards_for_user(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        test_user: User,
        test_keyboard: Keyboard,
    ) -> None:
        """Test that keyboards are loaded for the selected user."""
        dialog, _, mock_keyboard_manager = users_and_keyboards_dialog

        # Select the first user
        dialog.users_list.setCurrentRow(0)

        # Check that keyboards are loaded
        mock_keyboard_manager.list_keyboards_for_user.assert_called_once_with(test_user.user_id)
        assert dialog.keyboards_list.count() == 1
        assert dialog.keyboards_list.item(0).text() == test_keyboard.keyboard_name

    def test_add_user(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        qtbot: QtBot,
        test_user: User,
    ) -> None:
        """Test adding a new user."""
        dialog, mock_user_manager, _ = users_and_keyboards_dialog
        initial_count = dialog.users_list.count()

        # Create a new user that will be returned by the mocked dialog
        new_user = User(
            user_id="550e8400-e29b-41d4-a716-446655440001",  # Different ID from test_user
            first_name=NEW_USER_DATA["first_name"],
            surname=NEW_USER_DATA["surname"],
            email_address=NEW_USER_DATA["email_address"],
        )

        # Mock the UserDialog
        with patch("desktop_ui.users_and_keyboards.UserDialog") as mock_dialog:
            # Configure the mock to return the expected values when called
            mock_dialog.return_value.exec_.return_value = QtWidgets.QDialog.DialogCode.Accepted
            mock_dialog.return_value.get_user.return_value = new_user

            # Click the add user button
            qtbot.mouseClick(dialog.add_user_btn, QtCore.Qt.MouseButton.LeftButton)

            # Check that the user manager was called to save the user
            assert mock_user_manager.save_user.call_count > 0, "save_user was not called"
            assert dialog.users_list.count() == initial_count + 1, "User count did not increase"

            # Verify the new user is in the list
            found = False
            for i in range(dialog.users_list.count()):
                item = dialog.users_list.item(i)
                item_text = item.text()
                if (
                    NEW_USER_DATA["first_name"] in item_text
                    and NEW_USER_DATA["email_address"] in item_text
                ):
                    found = True
                    break
            assert found, "New user was not added to the list"

    def test_edit_user(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        qtbot: QtBot,
        test_user: User,
    ) -> None:
        """Test editing an existing user."""
        dialog, mock_user_manager, _ = users_and_keyboards_dialog

        # Create a modified user that will be returned by the mocked dialog
        modified_user = User(
            user_id=test_user.user_id,  # Same ID since we're editing
            first_name="Updated",
            surname=test_user.surname,
            email_address="updated@example.com",
        )

        # Make sure we can find the test user in the list first
        test_user_idx = -1
        for i in range(dialog.users_list.count()):
            item = dialog.users_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == test_user.user_id:
                test_user_idx = i
                break

        assert test_user_idx >= 0, "Test user not found in list"

        # Select the user we want to edit
        dialog.users_list.setCurrentRow(test_user_idx)

        # Mock the UserDialog
        with patch("desktop_ui.users_and_keyboards.UserDialog") as mock_dialog:
            # Configure the mock to return the expected values when called
            mock_dialog.return_value.exec_.return_value = QtWidgets.QDialog.DialogCode.Accepted
            mock_dialog.return_value.get_user.return_value = modified_user

            # Click the edit user button
            qtbot.mouseClick(dialog.edit_user_btn, QtCore.Qt.MouseButton.LeftButton)

            # Check that the user manager was called to save the user
            assert mock_user_manager.save_user.call_count > 0, "save_user was not called"

            # Make sure we stay at the same index
            dialog.users_list.setCurrentRow(test_user_idx)

            # Verify the user in the list was updated
            current_item = dialog.users_list.currentItem()
            assert current_item is not None
            assert "Updated" in current_item.text()
            assert "updated@example.com" in current_item.text()

    def test_delete_user(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        qtbot: QtBot,
        test_user: User,
    ) -> None:
        """Test deleting a user."""
        dialog, mock_user_manager, _ = users_and_keyboards_dialog

        # Select the first user
        dialog.users_list.setCurrentRow(0)

        # Patch QMessageBox.question to return Yes
        with patch(
            "PySide6.QtWidgets.QMessageBox.question",
            return_value=QtWidgets.QMessageBox.StandardButton.Yes,
        ):
            # Click the delete user button
            qtbot.mouseClick(dialog.delete_user_btn, QtCore.Qt.MouseButton.LeftButton)

            # Check that the user manager was called to delete
            mock_user_manager.delete_user.assert_called_once_with(test_user.user_id)

            # Verify the user was removed from the list
            assert dialog.users_list.count() == 0

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
        with patch("PySide6.QtWidgets.QMessageBox.question") as mock_question:
            mock_question.return_value = QtWidgets.QMessageBox.StandardButton.No

            # Click the delete user button
            qtbot.mouseClick(dialog.delete_user_btn, QtCore.Qt.MouseButton.LeftButton)

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
        test_keyboard: Keyboard,
    ) -> None:
        """Test adding a new keyboard."""
        dialog, _, mock_keyboard_manager = users_and_keyboards_dialog

        # Select the first user
        dialog.users_list.setCurrentRow(0)

        # Create a new keyboard that will be returned by the dialog
        # Use a different ID to ensure it's treated as a new keyboard
        new_keyboard = Keyboard(
            keyboard_id="550e8400-e29b-41d4-a716-446655440002",  # Unique ID different from test_keyboard
            user_id=TEST_USER_ID,
            keyboard_name="New Keyboard",
            keyboard_type="AZERTY",
        )

        # Mock the KeyboardDialog
        with patch("desktop_ui.users_and_keyboards.KeyboardDialog") as mock_dialog:
            mock_dialog.return_value.exec_.return_value = QtWidgets.QDialog.DialogCode.Accepted
            mock_dialog.return_value.get_keyboard.return_value = new_keyboard

            # Click the add keyboard button
            qtbot.mouseClick(dialog.add_keyboard_btn, QtCore.Qt.MouseButton.LeftButton)

            # After dialog.accept() is called, the save_keyboard should have been called
            mock_keyboard_manager.save_keyboard.assert_called_once()

            # Verify a keyboard was added to the list
            assert dialog.keyboards_list.count() == 2

            # Verify the new keyboard is in the list
            found = False
            for i in range(dialog.keyboards_list.count()):
                item = dialog.keyboards_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == new_keyboard.keyboard_id:
                    found = True
                    break
            assert found, "New keyboard was not added to the list"

    def test_delete_keyboard(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        qtbot: QtBot,
        test_keyboard: Keyboard,
    ) -> None:
        """Test deleting a keyboard."""
        dialog, _, mock_keyboard_manager = users_and_keyboards_dialog

        # Select the first user
        dialog.users_list.setCurrentRow(0)

        # Now that a user is selected, the keyboard list should be populated
        # Select the first keyboard
        dialog.keyboards_list.setCurrentRow(0)

        # Mock the confirmation dialog
        with patch(
            "PySide6.QtWidgets.QMessageBox.question",
            return_value=QtWidgets.QMessageBox.StandardButton.Yes,
        ):
            # Click the delete keyboard button
            qtbot.mouseClick(dialog.delete_keyboard_btn, QtCore.Qt.MouseButton.LeftButton)

            # Check that the keyboard manager was called with the correct user ID
            mock_keyboard_manager.list_keyboards_for_user.assert_called_with(TEST_USER_ID)

            # Check that the keyboard was deleted
            mock_keyboard_manager.delete_keyboard.assert_called_once_with(test_keyboard.keyboard_id)

            # Verify the keyboard list is refreshed (should be called at least twice)
            assert mock_keyboard_manager.list_keyboards_for_user.call_count >= 2

    def test_edit_keyboard(
        self,
        users_and_keyboards_dialog: Tuple[UsersAndKeyboards, MagicMock, MagicMock],
        qtbot: QtBot,
        test_keyboard: Keyboard,
    ) -> None:
        """Test editing a keyboard."""
        dialog, _, mock_keyboard_manager = users_and_keyboards_dialog

        # Find the test keyboard's index in the list
        # First select the user that owns the keyboard
        user_idx = -1
        for i in range(dialog.users_list.count()):
            item = dialog.users_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == TEST_USER_ID:
                user_idx = i
                break

        assert user_idx >= 0, "Test user not found in list"
        dialog.users_list.setCurrentRow(user_idx)

        # Now find the keyboard
        keyboard_idx = -1
        for i in range(dialog.keyboards_list.count()):
            item = dialog.keyboards_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == test_keyboard.keyboard_id:
                keyboard_idx = i
                break

        assert keyboard_idx >= 0, "Test keyboard not found in list"
        dialog.keyboards_list.setCurrentRow(keyboard_idx)

        # Create an updated keyboard that will be returned by the dialog
        updated_keyboard = Keyboard(
            keyboard_id=test_keyboard.keyboard_id,
            user_id=TEST_USER_ID,
            keyboard_name="Updated Keyboard",
            keyboard_type="DVORAK",
        )

        # Mock the KeyboardDialog
        with patch("desktop_ui.users_and_keyboards.KeyboardDialog") as mock_dialog:
            mock_dialog.return_value.exec_.return_value = QtWidgets.QDialog.DialogCode.Accepted
            mock_dialog.return_value.get_keyboard.return_value = updated_keyboard

            # Click the edit keyboard button
            qtbot.mouseClick(dialog.edit_keyboard_btn, QtCore.Qt.MouseButton.LeftButton)

            # Check that the keyboard was updated
            mock_keyboard_manager.save_keyboard.assert_called_once()
            saved_keyboard = mock_keyboard_manager.save_keyboard.call_args[0][0]
            assert saved_keyboard.keyboard_id == test_keyboard.keyboard_id
            assert saved_keyboard.keyboard_name == "Updated Keyboard"

            # Make sure we maintain the selection
            dialog.keyboards_list.setCurrentRow(keyboard_idx)

            # Verify the keyboard in the list was updated
            current_item = dialog.keyboards_list.currentItem()
            assert current_item is not None
            assert "Updated Keyboard" in current_item.text()
