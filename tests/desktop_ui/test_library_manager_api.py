import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from PyQt5.QtWidgets import QApplication, QMessageBox, QInputDialog, QDialog
from PyQt5.QtCore import Qt
from desktop_ui.library_manager import LibraryManagerUI
from desktop_ui.library_service import LibraryService, Category, Snippet


@pytest.fixture
def app(qtbot):
    """Create a QApplication and LibraryManagerUI instance with mocked service."""
    test_app = LibraryManagerUI(service=None)
    qtbot.addWidget(test_app)
    yield test_app
    test_app.close()


@pytest.fixture
def mock_service():
    """Create a mocked LibraryService that returns predictable values."""
    service = MagicMock(spec=LibraryService)
    
    # Mock category data
    test_categories = [
        Category(1, "Test Category 1"),
        Category(2, "Test Category 2")
    ]
    service.get_categories.return_value = test_categories
    
    # Mock snippet data
    test_snippets = {
        1: [Snippet(1, "Test Snippet 1", "Content 1"), 
            Snippet(2, "Test Snippet 2", "Content 2")],
        2: [Snippet(3, "Test Snippet 3", "Content 3")]
    }
    service.get_snippets.side_effect = lambda category_id: test_snippets.get(category_id, [])
    
    # Mock snippet parts data
    service.get_snippet_parts.side_effect = lambda snippet_id: {
        1: ["Content 1"],
        2: ["Content 2"],
        3: ["Content 3"]
    }.get(snippet_id, [])
    
    return service


def test_api_service_initialization(qtbot, mock_service):
    """Test that the LibraryManagerUI initializes correctly with API service."""
    with patch('desktop_ui.library_manager.LibraryManagerUI._load_categories') as mock_load:
        ui = LibraryManagerUI(service=mock_service)
        qtbot.addWidget(ui)
        
        assert ui.service == mock_service
        mock_load.assert_called_once()


def test_api_load_categories(qtbot, mock_service):
    """Test loading categories from API service."""
    ui = LibraryManagerUI(service=mock_service)
    qtbot.addWidget(ui)
    
    # Clear categories and load again to verify mock was called
    ui.cat_list.clear()
    ui._load_categories()
    
    mock_service.get_categories.assert_called_once()
    assert ui.cat_list.count() == 2
    assert ui.cat_list.item(0).text() == "Test Category 1"
    assert ui.cat_list.item(1).text() == "Test Category 2"


def test_api_load_snippets(qtbot, mock_service):
    """Test loading snippets from API service when category is selected."""
    ui = LibraryManagerUI(service=mock_service)
    qtbot.addWidget(ui)
    
    # Select first category
    ui.cat_list.setCurrentRow(0)
    
    mock_service.get_snippets.assert_called_with(1)  # Category ID 1
    assert ui.snip_list.count() == 2
    assert ui.snip_list.item(0).text() == "Test Snippet 1"
    assert ui.snip_list.item(1).text() == "Test Snippet 2"


def test_api_add_category(qtbot, mock_service, monkeypatch):
    """Test adding a category through API service."""
    ui = LibraryManagerUI(service=mock_service)
    qtbot.addWidget(ui)
    
    # Patch QInputDialog to return a new category name
    monkeypatch.setattr(QInputDialog, 'getText', lambda *args, **kwargs: ("New API Category", True))
    
    # Patch _validate_category_name to return True
    monkeypatch.setattr(ui, '_validate_category_name', lambda *args, **kwargs: True)
    
    # Click add category button
    qtbot.mouseClick(ui.btn_add_cat, Qt.LeftButton)
    
    mock_service.add_category.assert_called_once_with("New API Category")
    mock_service.get_categories.assert_called()  # Should refresh after add


def test_api_edit_category(qtbot, mock_service, monkeypatch):
    """Test editing a category through API service."""
    ui = LibraryManagerUI(service=mock_service)
    qtbot.addWidget(ui)
    
    # Select first category
    ui.cat_list.setCurrentRow(0)
    
    # Patch QInputDialog to return edited category name
    monkeypatch.setattr(QInputDialog, 'getText', lambda *args, **kwargs: ("Edited API Category", True))
    
    # Patch _validate_category_name to return True
    monkeypatch.setattr(ui, '_validate_category_name', lambda *args, **kwargs: True)
    
    # Click edit category button
    qtbot.mouseClick(ui.btn_edit_cat, Qt.LeftButton)
    
    mock_service.edit_category.assert_called_once_with(1, "Edited API Category")
    mock_service.get_categories.assert_called()  # Should refresh after edit


def test_api_delete_category(qtbot, mock_service, monkeypatch):
    """Test deleting a category through API service."""
    ui = LibraryManagerUI(service=mock_service)
    qtbot.addWidget(ui)
    
    # Select first category
    ui.cat_list.setCurrentRow(0)
    
    # Patch QMessageBox to return 'Yes'
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.Yes)
    
    # Click delete category button
    qtbot.mouseClick(ui.btn_del_cat, Qt.LeftButton)
    
    mock_service.delete_category.assert_called_once_with(1)
    mock_service.get_categories.assert_called()  # Should refresh after delete


def test_api_error_handling(qtbot, mock_service, monkeypatch):
    """Test proper error handling when API service throws an exception."""
    ui = LibraryManagerUI(service=mock_service)
    qtbot.addWidget(ui)
    
    # Make add_category raise an exception
    mock_service.add_category.side_effect = Exception("API service error")
    
    # Patch QInputDialog and QMessageBox
    monkeypatch.setattr(QInputDialog, 'getText', lambda *args, **kwargs: ("New Category", True))
    monkeypatch.setattr(ui, '_validate_category_name', lambda *args, **kwargs: True)
    
    # Mock QMessageBox.critical to capture error messages
    critical_messages = []
    monkeypatch.setattr(QMessageBox, 'critical', 
                        lambda *args, **kwargs: critical_messages.append(args[2]))
    
    # Click add category button to trigger error
    qtbot.mouseClick(ui.btn_add_cat, Qt.LeftButton)
    
    # Verify error was shown to user
    assert len(critical_messages) == 1
    assert "API service error" in critical_messages[0]


def test_api_view_snippet(qtbot, mock_service, monkeypatch):
    """Test viewing a snippet's full content through API service."""
    ui = LibraryManagerUI(service=mock_service)
    qtbot.addWidget(ui)
    
    # Select first category and snippet
    ui.cat_list.setCurrentRow(0)
    ui.snip_list.setCurrentRow(0)
    
    # Mock dialog accept
    monkeypatch.setattr(QDialog, 'exec_', lambda self: None)
    
    # Mock QTextEdit with a spy to check content
    text_content = []
    original_set_plain_text = QtWidgets.QTextEdit.setPlainText
    def spy_set_plain_text(self, text):
        text_content.append(text)
        return original_set_plain_text(self, text)
    monkeypatch.setattr(QtWidgets.QTextEdit, 'setPlainText', spy_set_plain_text)
    
    # Click view snippet button
    qtbot.mouseClick(ui.btn_view_snip, Qt.LeftButton)
    
    # Verify API was called to get content
    mock_service.get_snippet_parts.assert_called_with(1)
    
    # Wait for text to be set
    qtbot.wait(100)


def test_api_fallback_behavior(qtbot):
    """Test that UI gracefully handles missing API service."""
    # Create UI with no service
    ui = LibraryManagerUI(service=None)
    qtbot.addWidget(ui)
    
    # Categories should be empty but UI should not crash
    assert ui.cat_list.count() == 0
    
    # Try operations that would normally use the API
    ui._load_categories()  # Should not crash
    ui._load_snippets()  # Should not crash
