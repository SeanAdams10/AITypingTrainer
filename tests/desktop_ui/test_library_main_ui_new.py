"""
Tests for DrillConfigDialog UI component.

This test suite aims to achieve 95% test coverage for desktop_ui/drill_config.py.
"""

import os
import tempfile
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from pytestqt.qtbot import QtBot

from db.database_manager import DatabaseManager
from desktop_ui.drill_config import DrillConfigDialog
from models.category import Category
from models.category_manager import CategoryManager
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager
from models.user import User
from models.user_manager import UserManager

# ===== Fixtures =====


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Provide a path to a temporary SQLite database file."""
    # Create a temporary file and immediately close it to release the handle
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
        # Close the file handle immediately
        tmp.close()

    try:
        # Yield the path to the test
        yield tmp_path
    finally:
        # Clean up the temp file after test
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception as e:
            print(f"Warning: Failed to remove temporary database file: {e}")


@pytest.fixture
def db_manager(temp_db: str) -> Generator[DatabaseManager, None, None]:
    """
    Provide a DatabaseManager instance with a temporary database.

    Args:
        temp_db: Path to the temporary database file

    Yields:
        DatabaseManager: A database manager instance connected to the temp database
    """
    db = None
    try:
        db = DatabaseManager(temp_db)
        # Initialize all required tables
        db.init_tables()
        yield db
    finally:
        # Ensure the database connection is properly closed
        if db is not None:
            try:
                db.close()
            except Exception as e:
                print(f"Warning: Error closing database connection: {e}")


@pytest.fixture
def category_manager(db_manager: DatabaseManager) -> CategoryManager:
    """Provide a CategoryManager instance."""
    return CategoryManager(db_manager)


@pytest.fixture
def snippet_manager(db_manager: DatabaseManager) -> SnippetManager:
    """Provide a SnippetManager instance."""
    return SnippetManager(db_manager)


@pytest.fixture
def user_manager(db_manager: DatabaseManager) -> UserManager:
    """Provide a UserManager instance."""
    return UserManager(db_manager)


@pytest.fixture
def keyboard_manager(db_manager: DatabaseManager) -> KeyboardManager:
    """Provide a KeyboardManager instance."""
    return KeyboardManager(db_manager)


@pytest.fixture
def test_user(user_manager: UserManager) -> User:
    """Create and provide a test User instance with a database-generated ID."""
    # Create a new User instance
    user = User(first_name="Test", surname="User", email_address="test@example.com")
    # Save to database
    success = user_manager.save_user(user)
    assert success, "Failed to save test user"
    # Verify the user has an ID
    assert user.user_id is not None, "User ID should not be None after saving"
    return user


@pytest.fixture
def test_keyboard(keyboard_manager: KeyboardManager, test_user: User) -> Keyboard:
    """Create and provide a test Keyboard instance with a database-generated ID."""
    # Create a new Keyboard instance with the test user's ID
    keyboard = Keyboard(
        user_id=test_user.user_id,
        keyboard_name="Test Keyboard (QWERTY)"
    )
    # Save to database
    success = keyboard_manager.save_keyboard(keyboard)
    assert success, "Failed to save test keyboard"
    # Verify the keyboard has an ID
    assert keyboard.keyboard_id is not None, "Keyboard ID should not be None after saving"
    return keyboard


@pytest.fixture
def test_categories(category_manager: CategoryManager) -> list[Category]:
    """Create and provide test Category instances with database-generated IDs."""
    # Create test category data
    category_data = [
        {"category_name": "Test Category 1", "description": "Test Description 1"},
        {"category_name": "Test Category 2", "description": "Test Description 2"},
    ]

    # Save categories to database and collect the saved objects
    saved_categories = []
    for data in category_data:
        # Create a new Category instance
        category = Category(category_name=data["category_name"], description=data["description"])
        # Save to database
        success = category_manager.save_category(category)
        assert success, f"Failed to save category: {data['category_name']}"
        # Verify the category has an ID
        assert category.category_id is not None, "Category ID should not be None after saving"
        saved_categories.append(category)

    # Verify we have the expected number of categories
    assert len(saved_categories) == 2, "Expected 2 test categories"
    return saved_categories


@pytest.fixture
def test_snippets(
    snippet_manager: SnippetManager, test_categories: list[Category]
) -> list[Snippet]:
    """Create and provide test Snippet instances."""
    # Ensure we have at least 2 categories
    assert len(test_categories) >= 2, "Need at least 2 categories for testing"

    # Get the category IDs after they've been saved to the database
    category1_id = test_categories[0].category_id
    category2_id = test_categories[1].category_id

    # Verify category IDs are not None
    assert category1_id is not None, "Category 1 ID is None"
    assert category2_id is not None, "Category 2 ID is None"

    # Create snippets with the valid category IDs
    snippets = [
        Snippet(
            category_id=category1_id,
            snippet_name="Test Snippet 1",
            content=(
                "This is test snippet content 1. It needs to be long enough for testing."
            ),
            description="Test snippet description 1",
        ),
        Snippet(
            category_id=category1_id,
            snippet_name="Test Snippet 2",
            content=(
                "This is another test snippet with different content. It also needs to be "
                "sufficiently long."
            ),
            description="Test snippet description 2",
        ),
        # Second category snippet
        Snippet(
            category_id=category2_id,
            snippet_name="Test Snippet 3",
            content=(
                "This snippet belongs to the second category. This content should be "
                "unique."
            ),
            description="Test snippet description 3",
        ),
    ]

    # Save each snippet to the database
    saved_snippets = []
    for snippet in snippets:
        # Save the snippet
        success = snippet_manager.save_snippet(snippet)
        assert success, f"Failed to save snippet: {snippet.snippet_name}"
        # Verify the snippet has an ID
        assert snippet.snippet_id is not None, "Snippet ID should not be None after saving"
        saved_snippets.append(snippet)

    # Verify we have the expected number of snippets
    assert len(saved_snippets) == 3, "Expected 3 test snippets"
    return saved_snippets


@pytest.fixture
def drill_config_dialog(
    db_manager: DatabaseManager,
    test_user: User,
    test_keyboard: Keyboard,
    test_categories: list[Category],
    test_snippets: list[Snippet],
    qtbot: QtBot,  # type: ignore
) -> Generator[DrillConfigDialog, None, None]:
    """Provide a DrillConfigDialog instance with test data."""
    # Initialize the dialog with our test database, user and keyboard
    dialog = DrillConfigDialog(
        db_manager=db_manager, user_id=test_user.user_id, keyboard_id=test_keyboard.keyboard_id
    )
    qtbot.addWidget(dialog)
    return dialog


# Helper functions
def wait_for_ui_updates() -> None:
    """Wait for UI updates to process."""
    """Process pending events to ensure UI updates are complete."""
    QApplication.instance().processEvents()


# ===== Tests =====


def test_init_with_valid_user_and_keyboard(
    db_manager: DatabaseManager, test_user: User, test_keyboard: Keyboard, qtbot: QtBot
) -> None:
    """Test dialog initialization with valid user and keyboard."""
    """Test initialization with valid user and keyboard IDs."""
    assert 1 == 1
    dialog = DrillConfigDialog(
        db_manager=db_manager, user_id=test_user.user_id, keyboard_id=test_keyboard.keyboard_id
    )
    qtbot.addWidget(dialog)

    # Verify dialog properties
    assert dialog.user_id == test_user.user_id
    assert dialog.keyboard_id == test_keyboard.keyboard_id
    assert dialog.current_user is not None
    assert dialog.current_keyboard is not None
    assert dialog.db_manager == db_manager


def test_init_with_empty_user_and_keyboard(
    db_manager: DatabaseManager, qtbot: QtBot
) -> None:
    """Test dialog initialization with empty user and keyboard."""
    """Test initialization with empty user and keyboard IDs."""
    dialog = DrillConfigDialog(db_manager=db_manager, user_id="", keyboard_id="")
    qtbot.addWidget(dialog)

    # Verify dialog properties
    assert dialog.user_id == ""
    assert dialog.keyboard_id == ""
    assert dialog.current_user is None
    assert dialog.current_keyboard is None


def test_load_categories(
    drill_config_dialog: DrillConfigDialog, test_categories: list[Category]
) -> None:
    """Test that categories are loaded into the dialog."""
    """Test that categories are correctly loaded into the UI."""
    print("\n[TEST] Starting test_load_categories")
    print(f"[TEST] test_categories: {test_categories}")

    try:
        # Verify dialog was initialized with the test user and keyboard
        print(f"[TEST] dialog.user_id: {drill_config_dialog.user_id}")
        print(f"[TEST] dialog.keyboard_id: {drill_config_dialog.keyboard_id}")
        print(f"[TEST] dialog.current_user: {drill_config_dialog.current_user}")
        print(f"[TEST] dialog.current_keyboard: {drill_config_dialog.current_keyboard}")

        # Verify category selector exists and is populated
        category_selector = drill_config_dialog.category_selector
        print(f"[TEST] category_selector: {category_selector}")
        print(f"[TEST] category_selector.count(): {category_selector.count()}")
        print(f"[TEST] len(test_categories): {len(test_categories)}")

        # Categories should be loaded during initialization
        assert category_selector.count() == len(test_categories), (
            f"Expected {len(test_categories)} categories, got {category_selector.count()}"
        )

        # Get category names from the selector
        category_names = []
        for i in range(category_selector.count()):
            name = category_selector.itemText(i)
            category_data = category_selector.itemData(i)
            print(f"[TEST] Category {i}: name='{name}', data={category_data}")
            category_names.append(name)

        # Get expected category names
        expected_names = [category.category_name for category in test_categories]
        print(f"[TEST] Expected category names: {expected_names}")
        print(f"[TEST] Found category names: {category_names}")

        # Verify category names match (order doesn't matter)
        expected_str = f"Category names don't match. Expected {sorted(expected_names)}"
        assert sorted(category_names) == sorted(expected_names), (
            f"{expected_str}, got {sorted(category_names)}"
        )

        print("[TEST] test_load_categories passed successfully")
    except Exception as e:
        print(f"[TEST ERROR] Exception in test_load_categories: {str(e)}")
        print(f"[TEST ERROR] Type: {type(e).__name__}")
        import traceback
        print(f"[TEST ERROR] Traceback: {traceback.format_exc()}")
        raise


def test_category_selection_loads_snippets(
    drill_config_dialog: DrillConfigDialog,
    test_categories: list[Category],
    test_snippets: list[Snippet],
) -> None:
    """Test that selecting a category loads its snippets."""
    """Test that selecting a category loads the corresponding snippets."""
    # Select the first category
    drill_config_dialog.category_selector.setCurrentIndex(0)
    wait_for_ui_updates()

    # Count snippets in the first category
    first_category_snippets = [
        s for s in test_snippets if s.category_id == test_categories[0].category_id
    ]

    # Verify snippet count in the selector
    assert drill_config_dialog.snippet_selector.count() == len(first_category_snippets)

    # Verify snippet names
    snippet_names = [
        drill_config_dialog.snippet_selector.itemText(i)
        for i in range(drill_config_dialog.snippet_selector.count())
    ]
    expected_names = [s.snippet_name for s in first_category_snippets]
    assert sorted(snippet_names) == sorted(expected_names)

    # Select the second category
    drill_config_dialog.category_selector.setCurrentIndex(1)
    wait_for_ui_updates()

    # Count snippets in the second category
    second_category_snippets = [
        s for s in test_snippets if s.category_id == test_categories[1].category_id
    ]

    # Verify snippet count in the selector
    assert drill_config_dialog.snippet_selector.count() == len(second_category_snippets)


def test_snippet_selection_updates_preview(
    drill_config_dialog: DrillConfigDialog, test_snippets: list[Snippet]
) -> None:
    """Test that selecting a snippet updates the preview."""
    """Test that selecting a snippet updates the preview text area."""
    # Ensure first category is selected
    drill_config_dialog.category_selector.setCurrentIndex(0)
    wait_for_ui_updates()

    # Select the first snippet
    drill_config_dialog.snippet_selector.setCurrentIndex(0)
    wait_for_ui_updates()

    # Start and end indices should be set
    start_idx = drill_config_dialog.start_index.value()
    end_idx = drill_config_dialog.end_index.value()

    # The preview should contain the snippet text from start to end index
    first_snippet = test_snippets[0]
    expected_preview = first_snippet.content[start_idx:end_idx]
    assert drill_config_dialog.snippet_preview.toPlainText() == expected_preview


def test_index_changes_update_preview(
    drill_config_dialog: DrillConfigDialog, test_snippets: list[Snippet]
) -> None:
    """Test that changing indices updates the preview."""
    """Test that changing start/end indices updates the preview."""
    # Ensure first category is selected
    drill_config_dialog.category_selector.setCurrentIndex(0)
    wait_for_ui_updates()

    # Select the first snippet
    drill_config_dialog.snippet_selector.setCurrentIndex(0)
    wait_for_ui_updates()

    # Change start index
    new_start = 5
    drill_config_dialog.start_index.setValue(new_start)
    wait_for_ui_updates()

    # Change end index
    new_end = 15
    drill_config_dialog.end_index.setValue(new_end)
    wait_for_ui_updates()

    # Verify preview content matches the new range
    expected_preview = test_snippets[0].content[new_start:new_end]
    assert drill_config_dialog.snippet_preview.toPlainText() == expected_preview


def test_start_index_change_adjusts_end_index_minimum(
    drill_config_dialog: DrillConfigDialog,
) -> None:
    """Test that changing start index adjusts end index minimum."""
    """Test that changing the start index adjusts the end index minimum value."""
    # Ensure first category is selected
    drill_config_dialog.category_selector.setCurrentIndex(0)
    wait_for_ui_updates()

    # Select the first snippet
    drill_config_dialog.snippet_selector.setCurrentIndex(0)
    wait_for_ui_updates()

    # Set a larger start index
    new_start = 10
    drill_config_dialog.start_index.setValue(new_start)
    wait_for_ui_updates()

    # Verify the end index minimum is adjusted
    assert drill_config_dialog.end_index.minimum() == new_start + 1


def test_custom_text_toggle(drill_config_dialog: DrillConfigDialog) -> None:
    """Test toggling custom text mode."""
    """Test toggling custom text functionality."""
    # Initially, custom text should be disabled and snippet selector enabled
    assert not drill_config_dialog.custom_text.isEnabled()
    assert drill_config_dialog.snippet_selector.isEnabled()

    # Enable custom text
    drill_config_dialog.use_custom_text.setChecked(True)
    wait_for_ui_updates()

    # Custom text should now be enabled, snippet selector disabled
    assert drill_config_dialog.custom_text.isEnabled()
    assert not drill_config_dialog.snippet_selector.isEnabled()
    assert not drill_config_dialog.start_index.isEnabled()
    assert not drill_config_dialog.end_index.isEnabled()

    # Disable custom text
    drill_config_dialog.use_custom_text.setChecked(False)
    wait_for_ui_updates()

    # Back to initial state
    assert not drill_config_dialog.custom_text.isEnabled()
    assert drill_config_dialog.snippet_selector.isEnabled()
    assert drill_config_dialog.start_index.isEnabled()
    assert drill_config_dialog.end_index.isEnabled()


def test_custom_text_updates_preview(
    drill_config_dialog: DrillConfigDialog,
) -> None:
    """Test that custom text updates the preview."""
    """Test that entering custom text updates the preview."""
    # Enable custom text
    drill_config_dialog.use_custom_text.setChecked(True)
    wait_for_ui_updates()

    # Enter custom text
    custom_text = "This is a custom test snippet for typing practice."
    drill_config_dialog.custom_text.setPlainText(custom_text)
    wait_for_ui_updates()

    # Verify preview shows the custom text
    assert drill_config_dialog.snippet_preview.toPlainText() == custom_text


@patch("desktop_ui.drill_config.TypingDrillScreen")
@patch.object(QDialog, "accept")
def test_start_drill_with_snippet(
    mock_accept: MagicMock,
    mock_typing_drill: MagicMock,
    drill_config_dialog: DrillConfigDialog,
    test_snippets: list[Snippet],
) -> None:
    """Test starting a drill with a selected snippet."""
    """Test starting a drill with a selected snippet."""
    # Ensure first category is selected
    drill_config_dialog.category_selector.setCurrentIndex(0)
    wait_for_ui_updates()

    # Select the first snippet
    drill_config_dialog.snippet_selector.setCurrentIndex(0)
    wait_for_ui_updates()

    # Set indices
    drill_config_dialog.start_index.setValue(0)
    drill_config_dialog.end_index.setValue(20)
    wait_for_ui_updates()

    # Start the drill
    drill_config_dialog._start_drill()

    # Verify TypingDrillScreen was created with correct parameters
    mock_typing_drill.assert_called_once()
    # Check arguments
    args, kwargs = mock_typing_drill.call_args
    assert kwargs["db_manager"] == drill_config_dialog.db_manager
    assert kwargs["snippet_id"] == test_snippets[0].snippet_id
    assert kwargs["start"] == 0
    assert kwargs["end"] == 20
    assert kwargs["content"] == test_snippets[0].content[0:20]

    # Verify dialog was accepted
    mock_accept.assert_called_once()


@patch("desktop_ui.drill_config.TypingDrillScreen")
@patch.object(QDialog, "accept")
def test_start_drill_with_custom_text(
    mock_accept: MagicMock,
    mock_typing_drill: MagicMock,
    drill_config_dialog: DrillConfigDialog,
    category_manager: CategoryManager,
) -> None:
    """Test starting a drill with custom text."""
    """Test starting a drill with custom text."""
    # Enable custom text
    drill_config_dialog.use_custom_text.setChecked(True)
    wait_for_ui_updates()

    # Enter custom text
    custom_text = "This is a custom test snippet for typing practice."
    drill_config_dialog.custom_text.setPlainText(custom_text)
    wait_for_ui_updates()

    # Start the drill
    drill_config_dialog._start_drill()

    # Verify TypingDrillScreen was created with correct parameters
    mock_typing_drill.assert_called_once()

    # Check arguments
    args, kwargs = mock_typing_drill.call_args
    assert kwargs["db_manager"] == drill_config_dialog.db_manager
    assert kwargs["content"] == custom_text

    # Verify "Custom Snippets" category was created
    custom_category = category_manager.get_category_by_name("Custom Snippets")
    assert custom_category is not None

    # Verify dialog was accepted
    mock_accept.assert_called_once()


@patch.object(QMessageBox, "warning")
def test_start_drill_with_empty_custom_text(
    mock_warning: MagicMock, drill_config_dialog: DrillConfigDialog
) -> None:
    """Test starting a drill with empty custom text shows warning."""
    """Test error handling when starting a drill with empty custom text."""
    # Enable custom text
    drill_config_dialog.use_custom_text.setChecked(True)
    wait_for_ui_updates()

    # Leave custom text empty
    drill_config_dialog.custom_text.setPlainText("")
    wait_for_ui_updates()

    # Start the drill
    drill_config_dialog._start_drill()

    # Verify warning was shown
    mock_warning.assert_called_once()
    args, kwargs = mock_warning.call_args
    assert "empty" in args[1].lower()  # Error message should mention "empty"


@patch.object(QDialog, "reject")
def test_cancel_button_rejects_dialog(
    mock_reject: MagicMock, drill_config_dialog: DrillConfigDialog, qtbot: QtBot
) -> None:
    """Test that cancel button rejects the dialog."""  """Test that the cancel button rejects the dialog."""
    # Click the cancel button
    cancel_btn = drill_config_dialog.findChild(QtWidgets.QPushButton, "Cancel")
    qtbot.mouseClick(
        cancel_btn,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    # Verify dialog was rejected with the correct call
    mock_reject.assert_called_once_with()


def test_status_bar_shows_user_and_keyboard_info(
    db_manager: DatabaseManager,
    test_user: User,
    test_keyboard: Keyboard,
    qtbot: QtBot,
) -> None:
    """Test that status bar shows user and keyboard info."""
    """Test that status bar shows user and keyboard information."""
    dialog = DrillConfigDialog(
        db_manager=db_manager, user_id=test_user.user_id, keyboard_id=test_keyboard.keyboard_id
    )
    qtbot.addWidget(dialog)

    # Get status message
    status_text = dialog.status_bar.currentMessage()

    # Verify user and keyboard info is in the status message
    assert test_user.first_name in status_text
    assert test_user.surname in status_text
    assert test_keyboard.keyboard_name in status_text


def test_no_user_or_keyboard_status_message(db_manager: DatabaseManager, qtbot: QtBot) -> None:
    """Test status message when no user or keyboard is selected."""  """Test status message when no user or keyboard is provided."""
    dialog = DrillConfigDialog(db_manager=db_manager, user_id="", keyboard_id="")
    qtbot.addWidget(dialog)

    # Verify status shows default message
    assert dialog.status_bar.currentMessage() == "No user or keyboard selected"


@patch.object(QMessageBox, "warning")
def test_start_index_greater_than_end_index_error(
    mock_warning: MagicMock, drill_config_dialog: DrillConfigDialog
) -> None:
    """Test error when start index is greater than end index."""
    """Test error handling when start index is greater than end index."""
    # Set up a situation where start > end might occur
    drill_config_dialog.category_selector.setCurrentIndex(0)
    wait_for_ui_updates()

    drill_config_dialog.snippet_selector.setCurrentIndex(0)
    wait_for_ui_updates()

    # Manually force an invalid state (this shouldn't happen in UI but test for robustness)
    with patch.object(drill_config_dialog.start_index, "value", return_value=20):
        with patch.object(drill_config_dialog.end_index, "value", return_value=10):
            drill_config_dialog._start_drill()

    # Verify warning was shown
    mock_warning.assert_called_once()
    args, kwargs = mock_warning.call_args
    assert "start" in args[1].lower() and "end" in args[1].lower()


def test_empty_categories_handling(db_manager: DatabaseManager, qtbot: QtBot) -> None:
    """Test handling of empty categories list."""  """Test behavior when no categories are available."""
    # Create dialog with empty database
    dialog = DrillConfigDialog(db_manager=db_manager, user_id="", keyboard_id="")
    qtbot.addWidget(dialog)

    # Verify category selector is empty and disabled
    assert dialog.category_selector.count() == 0
    assert not dialog.category_selector.isEnabled()

    # Snippet selector should also be empty and disabled
    assert dialog.snippet_selector.count() == 0
    assert not dialog.snippet_selector.isEnabled()
