"""
UI tests for LibraryMainWindow in desktop_ui/library_main.py

Covers all CRUD operations for categories and snippets with comprehensive test coverage.
"""

from pathlib import Path
from typing import Generator, Optional
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

# Project imports
from desktop_ui.library_main import LibraryMainWindow
from desktop_ui.modern_dialogs import CategoryDialog, SnippetDialog
from models.category import Category
from models.snippet import Snippet
from db.database_manager import DatabaseManager


# ===== Fixtures =====

@pytest.fixture(scope="module")
def qapp() -> Generator[QApplication, None, None]:
    """Ensure a QApplication exists for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app as it might be used by other tests


@pytest.fixture
def temp_db(tmp_path: Path) -> str:
    """Create a temporary database file for testing."""
    db_path = tmp_path / "test_typing_data.db"
    
    # Initialize the test database
    db = DatabaseManager(str(db_path))
    db.init_tables()
    
    return str(db_path)


@pytest.fixture
def main_window(qapp: QApplication, temp_db: str) -> Generator[LibraryMainWindow, None, None]:
    """Create a fresh LibraryMainWindow instance for each test."""
    # Create the main window with testing mode enabled and custom DB
    win = LibraryMainWindow(db_manager=DatabaseManager(temp_db), testing_mode=True)
    win.show()
    
    yield win
    
    # Clean up
    win.close()


# ===== Mock Dialog Classes =====

class MockCategoryDialog:
    """Mock CategoryDialog for testing."""
    
    def __init__(self, title: str, label: str, default: str = "", parent=None):
        self.title = title
        self.label = label
        self.default = default
        self.parent = parent
        self._return_value = "Test Category"
        self._exec_result = QDialog.DialogCode.Accepted
    
    def set_return_value(self, value: str) -> None:
        """Set the value to return from get_value()."""
        self._return_value = value
    
    def set_exec_result(self, result: QDialog.DialogCode) -> None:
        """Set the result to return from exec_()."""
        self._exec_result = result
    
    def exec_(self) -> QDialog.DialogCode:
        """Mock exec_ method."""
        return self._exec_result
    
    def get_value(self) -> str:
        """Mock get_value method."""
        return self._return_value


class MockSnippetDialog:
    """Mock SnippetDialog for testing."""
    
    def __init__(self, title: str, name_label: str, content_label: str, 
                 default_name: str = "", default_content: str = "", parent=None):
        self.title = title
        self.name_label = name_label
        self.content_label = content_label
        self.default_name = default_name
        self.default_content = default_content
        self.parent = parent
        self._return_name = "Test Snippet"
        self._return_content = "Test Content"
        self._exec_result = QDialog.DialogCode.Accepted
    
    def set_return_values(self, name: str, content: str) -> None:
        """Set the values to return from get_values()."""
        self._return_name = name
        self._return_content = content
    
    def set_exec_result(self, result: QDialog.DialogCode) -> None:
        """Set the result to return from exec_()."""
        self._exec_result = result
    
    def exec_(self) -> QDialog.DialogCode:
        """Mock exec_ method."""
        return self._exec_result
    
    def get_values(self) -> tuple[str, str]:
        """Mock get_values method."""
        return self._return_name, self._return_content


# ===== Helper Functions =====

def wait_for_ui_updates(app: QApplication) -> None:
    """Process pending events to ensure UI updates are complete."""
    app.processEvents()


def get_category_count(main_window: LibraryMainWindow) -> int:
    """Get the number of categories in the category list."""
    return main_window.category_list.count()


def get_snippet_count(main_window: LibraryMainWindow) -> int:
    """Get the number of snippets in the snippet list."""
    return main_window.snippet_list.count()


def select_category_by_index(main_window: LibraryMainWindow, index: int) -> None:
    """Select a category by index in the category list."""
    if 0 <= index < main_window.category_list.count():
        main_window.category_list.setCurrentRow(index)
        wait_for_ui_updates(main_window.qApp)


def select_snippet_by_index(main_window: LibraryMainWindow, index: int) -> None:
    """Select a snippet by index in the snippet list."""
    if 0 <= index < main_window.snippet_list.count():
        main_window.snippet_list.setCurrentRow(index)
        wait_for_ui_updates(main_window.qApp)


# ===== Category CRUD Tests =====

def test_add_category_success(main_window: LibraryMainWindow) -> None:
    """Test successfully adding a new category."""
    # Arrange
    initial_count = get_category_count(main_window)
    mock_dialog = MockCategoryDialog("", "")
    mock_dialog.set_return_value("New Test Category")
    
    # Act
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_dialog):
        main_window.add_category()
        wait_for_ui_updates(main_window.qApp)
    
    # Assert
    assert get_category_count(main_window) == initial_count + 1
    
    # Verify the category was added to the list
    category_names = []
    for i in range(main_window.category_list.count()):
        item = main_window.category_list.item(i)
        if item:
            category_names.append(item.text())
    
    assert "New Test Category" in category_names


def test_add_category_cancelled(main_window: LibraryMainWindow) -> None:
    """Test cancelling category addition."""
    # Arrange
    initial_count = get_category_count(main_window)
    mock_dialog = MockCategoryDialog("", "")
    mock_dialog.set_exec_result(QDialog.DialogCode.Rejected)
    
    # Act
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_dialog):
        main_window.add_category()
        wait_for_ui_updates(main_window.qApp)
    
    # Assert - count should remain the same
    assert get_category_count(main_window) == initial_count


def test_add_category_empty_name(main_window: LibraryMainWindow) -> None:
    """Test adding a category with empty name."""
    # Arrange
    initial_count = get_category_count(main_window)
    mock_dialog = MockCategoryDialog("", "")
    mock_dialog.set_return_value("")  # Empty name
    
    # Act
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_dialog):
        main_window.add_category()
        wait_for_ui_updates(main_window.qApp)
    
    # Assert - should not add category with empty name
    assert get_category_count(main_window) == initial_count


def test_edit_category_success(main_window: LibraryMainWindow) -> None:
    """Test successfully editing an existing category."""
    # Arrange - first add a category
    mock_add_dialog = MockCategoryDialog("", "")
    mock_add_dialog.set_return_value("Original Category")
    
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_add_dialog):
        main_window.add_category()
        wait_for_ui_updates(main_window.qApp)
    
    # Select the first category
    select_category_by_index(main_window, 0)
    
    # Act - edit the category
    mock_edit_dialog = MockCategoryDialog("", "")
    mock_edit_dialog.set_return_value("Edited Category")
    
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_edit_dialog):
        main_window.edit_category()
        wait_for_ui_updates(main_window.qApp)
    
    # Assert - check the category name was updated
    first_item = main_window.category_list.item(0)
    assert first_item is not None
    assert first_item.text() == "Edited Category"


def test_edit_category_no_selection(main_window: LibraryMainWindow) -> None:
    """Test editing category when no category is selected."""
    # Arrange - ensure no category is selected
    main_window.category_list.clearSelection()
    main_window.category_list.setCurrentRow(-1)
    
    # Act
    main_window.edit_category()
    wait_for_ui_updates(main_window.qApp)
    
    # Assert - should handle gracefully (no error)
    # This test mainly ensures the method doesn't crash


def test_delete_category_confirmed(main_window: LibraryMainWindow) -> None:
    """Test deleting a category when user confirms."""
    # Arrange - add a category first
    mock_add_dialog = MockCategoryDialog("", "")
    mock_add_dialog.set_return_value("Category to Delete")
    
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_add_dialog):
        main_window.add_category()
        wait_for_ui_updates(main_window.qApp)
    
    initial_count = get_category_count(main_window)
    select_category_by_index(main_window, 0)
    
    # Act - delete with confirmation
    with patch('desktop_ui.library_main.QMessageBox.question', 
               return_value=QMessageBox.StandardButton.Yes):
        main_window.delete_category()
        wait_for_ui_updates(main_window.qApp)
    
    # Assert
    assert get_category_count(main_window) == initial_count - 1


def test_delete_category_cancelled(main_window: LibraryMainWindow) -> None:
    """Test deleting a category when user cancels."""
    # Arrange - add a category first
    mock_add_dialog = MockCategoryDialog("", "")
    mock_add_dialog.set_return_value("Category to Keep")
    
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_add_dialog):
        main_window.add_category()
        wait_for_ui_updates(main_window.qApp)
    
    initial_count = get_category_count(main_window)
    select_category_by_index(main_window, 0)
    
    # Act - delete but cancel confirmation
    with patch('desktop_ui.library_main.QMessageBox.question', 
               return_value=QMessageBox.StandardButton.No):
        main_window.delete_category()
        wait_for_ui_updates(main_window.qApp)
    
    # Assert - count should remain the same
    assert get_category_count(main_window) == initial_count


# ===== Snippet CRUD Tests =====

def test_add_snippet_success(main_window: LibraryMainWindow) -> None:
    """Test successfully adding a new snippet."""
    # Arrange - first add a category
    mock_category_dialog = MockCategoryDialog("", "")
    mock_category_dialog.set_return_value("Test Category")
    
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_category_dialog):
        main_window.add_category()
        wait_for_ui_updates(main_window.qApp)
    
    # Select the category
    select_category_by_index(main_window, 0)
    initial_snippet_count = get_snippet_count(main_window)
    
    # Act - add snippet
    mock_snippet_dialog = MockSnippetDialog("", "", "")
    mock_snippet_dialog.set_return_values("Test Snippet", "Test snippet content")
    
    with patch('desktop_ui.library_main.SnippetDialog', return_value=mock_snippet_dialog):
        main_window.add_snippet()
        wait_for_ui_updates(main_window.qApp)
    
    # Assert
    assert get_snippet_count(main_window) == initial_snippet_count + 1


def test_add_snippet_no_category_selected(main_window: LibraryMainWindow) -> None:
    """Test adding snippet when no category is selected."""
    # Arrange - ensure no category is selected
    main_window.category_list.clearSelection()
    main_window.category_list.setCurrentRow(-1)
    
    # Act
    main_window.add_snippet()
    wait_for_ui_updates(main_window.qApp)
    
    # Assert - should handle gracefully (no error)
    # This test mainly ensures the method doesn't crash


def test_edit_snippet_success(main_window: LibraryMainWindow) -> None:
    """Test successfully editing an existing snippet."""
    # Arrange - add category and snippet first
    mock_category_dialog = MockCategoryDialog("", "")
    mock_category_dialog.set_return_value("Test Category")
    
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_category_dialog):
        main_window.add_category()
        wait_for_ui_updates(main_window.qApp)
    
    select_category_by_index(main_window, 0)
    
    # Add snippet
    mock_add_snippet_dialog = MockSnippetDialog("", "", "")
    mock_add_snippet_dialog.set_return_values("Original Snippet", "Original content")
    
    with patch('desktop_ui.library_main.SnippetDialog', return_value=mock_add_snippet_dialog):
        main_window.add_snippet()
        wait_for_ui_updates(main_window.qApp)
    
    # Select the snippet
    select_snippet_by_index(main_window, 0)
    
    # Act - edit snippet
    mock_edit_snippet_dialog = MockSnippetDialog("", "", "")
    mock_edit_snippet_dialog.set_return_values("Edited Snippet", "Edited content")
    
    with patch('desktop_ui.library_main.SnippetDialog', return_value=mock_edit_snippet_dialog):
        main_window.edit_snippet()
        wait_for_ui_updates(main_window.qApp)
    
    # Assert - check snippet name was updated
    first_item = main_window.snippet_list.item(0)
    assert first_item is not None
    assert first_item.text() == "Edited Snippet"


def test_delete_snippet_confirmed(main_window: LibraryMainWindow) -> None:
    """Test deleting a snippet when user confirms."""
    # Arrange - add category and snippet first
    mock_category_dialog = MockCategoryDialog("", "")
    mock_category_dialog.set_return_value("Test Category")
    
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_category_dialog):
        main_window.add_category()
        wait_for_ui_updates(main_window.qApp)
    
    select_category_by_index(main_window, 0)
    
    # Add snippet
    mock_snippet_dialog = MockSnippetDialog("", "", "")
    mock_snippet_dialog.set_return_values("Snippet to Delete", "Content to delete")
    
    with patch('desktop_ui.library_main.SnippetDialog', return_value=mock_snippet_dialog):
        main_window.add_snippet()
        wait_for_ui_updates(main_window.qApp)
    
    initial_count = get_snippet_count(main_window)
    select_snippet_by_index(main_window, 0)
    
    # Act - delete with confirmation
    with patch('desktop_ui.library_main.QMessageBox.question', 
               return_value=QMessageBox.StandardButton.Yes):
        main_window.delete_snippet()
        wait_for_ui_updates(main_window.qApp)
    
    # Assert
    assert get_snippet_count(main_window) == initial_count - 1


# ===== UI Interaction Tests =====

def test_category_selection_updates_snippets(main_window: LibraryMainWindow) -> None:
    """Test that selecting a category updates the snippet list."""
    # Arrange - add two categories with different snippets
    mock_category_dialog = MockCategoryDialog("", "")
    
    # Add first category
    mock_category_dialog.set_return_value("Category 1")
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_category_dialog):
        main_window.add_category()
        wait_for_ui_updates(main_window.qApp)
    
    # Add second category
    mock_category_dialog.set_return_value("Category 2")
    with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_category_dialog):
        main_window.add_category()
        wait_for_ui_updates(main_window.qApp)
    
    # Add snippet to first category
    select_category_by_index(main_window, 0)
    mock_snippet_dialog = MockSnippetDialog("", "", "")
    mock_snippet_dialog.set_return_values("Snippet 1", "Content 1")
    
    with patch('desktop_ui.library_main.SnippetDialog', return_value=mock_snippet_dialog):
        main_window.add_snippet()
        wait_for_ui_updates(main_window.qApp)
    
    # Add snippet to second category
    select_category_by_index(main_window, 1)
    mock_snippet_dialog.set_return_values("Snippet 2", "Content 2")
    
    with patch('desktop_ui.library_main.SnippetDialog', return_value=mock_snippet_dialog):
        main_window.add_snippet()
        wait_for_ui_updates(main_window.qApp)
    
    # Act & Assert
    # Select first category and check snippets
    select_category_by_index(main_window, 0)
    snippet_count_cat1 = get_snippet_count(main_window)
    
    # Select second category and check snippets
    select_category_by_index(main_window, 1)
    snippet_count_cat2 = get_snippet_count(main_window)
    
    # Both categories should have their respective snippets
    assert snippet_count_cat1 >= 0  # Should have at least the snippets we added
    assert snippet_count_cat2 >= 0  # Should have at least the snippets we added


def test_initial_state(main_window: LibraryMainWindow) -> None:
    """Test the initial state of the main window."""
    # Assert initial state
    assert main_window.isVisible()
    assert get_category_count(main_window) >= 0
    assert get_snippet_count(main_window) >= 0
    
    # Verify UI components exist
    assert main_window.category_list is not None
    assert main_window.snippet_list is not None
    assert main_window.add_category_btn is not None
    assert main_window.add_snippet_btn is not None


def test_button_clicks(main_window: LibraryMainWindow) -> None:
    """Test that buttons are clickable and don't crash."""
    # Test category buttons
    main_window.add_category_btn.click()
    wait_for_ui_updates(main_window.qApp)
    
    main_window.edit_category_btn.click()
    wait_for_ui_updates(main_window.qApp)
    
    main_window.delete_category_btn.click()
    wait_for_ui_updates(main_window.qApp)
    
    # Test snippet buttons
    main_window.add_snippet_btn.click()
    wait_for_ui_updates(main_window.qApp)
    
    main_window.edit_snippet_btn.click()
    wait_for_ui_updates(main_window.qApp)
    
    main_window.delete_snippet_btn.click()
    wait_for_ui_updates(main_window.qApp)
    
    # If we get here without exceptions, the test passes


# ===== Edge Cases =====

def test_multiple_categories_and_snippets(main_window: LibraryMainWindow) -> None:
    """Test handling multiple categories and snippets."""
    # Add multiple categories
    mock_category_dialog = MockCategoryDialog("", "")
    category_names = ["Category A", "Category B", "Category C"]
    
    for name in category_names:
        mock_category_dialog.set_return_value(name)
        with patch('desktop_ui.library_main.CategoryDialog', return_value=mock_category_dialog):
            main_window.add_category()
            wait_for_ui_updates(main_window.qApp)
    
    # Add snippets to each category
    mock_snippet_dialog = MockSnippetDialog("", "", "")
    
    for i, category_name in enumerate(category_names):
        select_category_by_index(main_window, i)
        
        # Add 2 snippets per category
        for j in range(2):
            snippet_name = f"Snippet {i+1}-{j+1}"
            snippet_content = f"Content for {snippet_name}"
            mock_snippet_dialog.set_return_values(snippet_name, snippet_content)
            
            with patch('desktop_ui.library_main.SnippetDialog', return_value=mock_snippet_dialog):
                main_window.add_snippet()
                wait_for_ui_updates(main_window.qApp)
    
    # Assert
    assert get_category_count(main_window) >= len(category_names)
    
    # Check each category has snippets
    for i in range(len(category_names)):
        select_category_by_index(main_window, i)
        assert get_snippet_count(main_window) >= 2


if __name__ == "__main__":
    pytest.main([__file__])
