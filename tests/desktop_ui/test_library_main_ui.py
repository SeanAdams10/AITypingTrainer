"""
Tests for the LibraryMainWindow UI class in desktop_ui/library_main.py
"""
from __future__ import annotations

from typing import List
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot  # type: ignore[import-untyped]

from db.database_manager import DatabaseManager
from desktop_ui.library_main import LibraryMainWindow
from models.snippet import Snippet


class TestLibraryMainWindow:
    """Test cases for LibraryMainWindow UI functionality."""

    def test_initialization(self, qtbot: QtBot, db_manager: DatabaseManager) -> None:
        """Test that the window initializes correctly."""
        window = LibraryMainWindow(db_manager=db_manager, testing_mode=True)
        qtbot.addWidget(window)
        
        assert window.windowTitle() == "Snippets Library"
        assert hasattr(window, 'categoryList')
        assert hasattr(window, 'snippetList')
        
        # Verify initial button states
        assert not window.editCatBtn.isEnabled()
        assert not window.delCatBtn.isEnabled()
        assert not window.editSnipBtn.isEnabled()
        assert not window.delSnipBtn.isEnabled()
        
        window.close()

    def test_load_data_creates_defaults(self, qtbot: QtBot, db_manager: DatabaseManager) -> None:
        """Test that loading data creates default category and snippet if none exist."""
        window = LibraryMainWindow(db_manager=db_manager, testing_mode=True)
        qtbot.addWidget(window)
        
        # Verify at least one category exists
        assert window.categoryList.count() > 0
        
        # Select the first category and verify snippets
        window.categoryList.setCurrentRow(0)
        assert window.snippetList.count() > 0
        
        window.close()

    @pytest.mark.parametrize("button_name,expected_dialog", [
        ("addCatBtn", "CategoryDialog"),
        ("editCatBtn", "CategoryDialog"),
        ("addSnipBtn", "SnippetDialog"),
        ("editSnipBtn", "SnippetDialog"),
    ])
    def test_dialog_buttons(
        self,
        qtbot: QtBot,
        db_manager: DatabaseManager,
        button_name: str,
        expected_dialog: str,
    ) -> None:
        """Test that dialog buttons open the correct dialogs."""
        window = LibraryMainWindow(db_manager=db_manager, testing_mode=True)
        qtbot.addWidget(window)
        
        # Select a category and snippet to enable edit buttons
        if button_name in ["editCatBtn", "editSnipBtn"]:
            window.categoryList.setCurrentRow(0)
            if button_name == "editSnipBtn":
                window.snippetList.setCurrentRow(0)
        
        with patch(f"desktop_ui.library_main.{expected_dialog}") as mock_dialog:
            # Click the button
            button = getattr(window, button_name)
            qtbot.mouseClick(button, Qt.LeftButton)
            
            # Verify dialog was created
            mock_dialog.assert_called_once()
        
        window.close()

    def test_add_category(self, qtbot: QtBot, db_manager: DatabaseManager) -> None:
        """Test adding a new category through the UI."""
        window = LibraryMainWindow(db_manager=db_manager, testing_mode=True)
        qtbot.addWidget(window)
        
        initial_count = window.categoryList.count()
        
        with patch('desktop_ui.library_main.CategoryDialog') as mock_dialog:
            # Configure the mock dialog
            mock_dialog.return_value.exec.return_value = QMessageBox.Accepted
            mock_dialog.return_value.get_category_name.return_value = "New Category"
            
            # Click the add category button
            qtbot.mouseClick(window.addCatBtn, Qt.LeftButton)
            
            # Process events to handle dialog
            qtbot.waitUntil(lambda: window.categoryList.count() == initial_count + 1)
            
            # Verify the new category was added
            assert window.categoryList.count() == initial_count + 1
            assert "New Category" in [window.categoryList.item(i).text() 
                                    for i in range(window.categoryList.count())]
        
        window.close()

    def test_delete_category(self, qtbot: QtBot, db_manager: DatabaseManager) -> None:
        """Test deleting a category through the UI."""
        window = LibraryMainWindow(db_manager=db_manager, testing_mode=True)
        qtbot.addWidget(window)
        
        # Add a test category
        with patch('PySide6.QtWidgets.QMessageBox.question', 
                  return_value=QMessageBox.Yes):
            with patch('desktop_ui.library_main.CategoryDialog') as mock_dialog:
                mock_dialog.return_value.exec.return_value = QMessageBox.Accepted
                mock_dialog.return_value.get_category_name.return_value = "Test Delete"
                qtbot.mouseClick(window.addCatBtn, Qt.LeftButton)
                qtbot.waitUntil(lambda: window.categoryList.count() > 1)
        
        # Select the category to delete
        for i in range(window.categoryList.count()):
            if window.categoryList.item(i).text() == "Test Delete":
                window.categoryList.setCurrentRow(i)
                break
                
        initial_count = window.categoryList.count()
        
        # Delete the category
        with patch('PySide6.QtWidgets.QMessageBox.question', 
                  return_value=QMessageBox.Yes):
            qtbot.mouseClick(window.delCatBtn, Qt.LeftButton)
            qtbot.waitUntil(lambda: window.categoryList.count() == initial_count - 1)
            
            # Verify the category was deleted
            assert window.categoryList.count() == initial_count - 1
            assert "Test Delete" not in [window.categoryList.item(i).text() 
                                      for i in range(window.categoryList.count())]
        
        window.close()

    def test_search_snippets(
        self, qtbot: QtBot, db_manager: DatabaseManager, test_snippets: List[Snippet]
    ) -> None:
        """Test searching for snippets."""
        window = LibraryMainWindow(db_manager=db_manager, testing_mode=True)
        qtbot.addWidget(window)
        
        # Wait for initial load
        qtbot.wait(100)
        
        # Search for a specific snippet
        window.search_input.setText("Snippet 1")
        
        # Verify only matching snippets are shown
        qtbot.wait(100)  # Allow time for search to process
        assert window.snippetList.count() == 1
        assert window.snippetList.item(0).text() == "Snippet 1"
        
        # Clear search
        window.search_input.clear()
        qtbot.wait(100)  # Allow time for search to process
        
        # Verify all snippets are shown again
        assert window.snippetList.count() >= 2
        
        window.close()

    def test_button_states(self, qtbot: QtBot, db_manager: DatabaseManager) -> None:
        """Test that buttons are properly enabled/disabled based on selection."""
        window = LibraryMainWindow(db_manager=db_manager, testing_mode=True)
        qtbot.addWidget(window)
        
        # Initially, only Add Category and Add Snippet should be enabled
        assert window.addCatBtn.isEnabled()
        assert not window.editCatBtn.isEnabled()
        assert not window.delCatBtn.isEnabled()
        assert not window.addSnipBtn.isEnabled()
        assert not window.editSnipBtn.isEnabled()
        assert not window.delSnipBtn.isEnabled()
        
        # Select a category
        window.categoryList.setCurrentRow(0)
        qtbot.wait(100)  # Allow time for category selection to process
        
        # Verify buttons after category selection
        assert window.addCatBtn.isEnabled()
        assert window.editCatBtn.isEnabled()
        assert window.delCatBtn.isEnabled()
        assert window.addSnipBtn.isEnabled()
        assert not window.editSnipBtn.isEnabled()
        assert not window.delSnipBtn.isEnabled()
        
        # Select a snippet
        if window.snippetList.count() > 0:
            window.snippetList.setCurrentRow(0)
            qtbot.wait(100)  # Allow time for snippet selection to process
            
            # Verify buttons after snippet selection
            assert window.addCatBtn.isEnabled()
            assert window.editCatBtn.isEnabled()
            assert window.delCatBtn.isEnabled()
            assert window.addSnipBtn.isEnabled()
            assert window.editSnipBtn.isEnabled()
            assert window.delSnipBtn.isEnabled()
        
        window.close()
