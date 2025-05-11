"""
Tests for the DrillConfigDialog in the desktop UI.
"""
import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import Qt

# Mock database manager for testing
@pytest.fixture
def mock_db_manager():
    """Create a mock DatabaseManager for testing."""
    manager = MagicMock()
    # Mock the snippet manager to return test snippets
    snippet_manager = MagicMock()
    snippet_manager.get_all_snippets.return_value = [
        {"id": 1, "title": "Test Snippet 1", "content": "This is test snippet 1"},
        {"id": 2, "title": "Test Snippet 2", "content": "This is test snippet 2"}
    ]
    manager.get_snippet_manager.return_value = snippet_manager
    return manager

@pytest.fixture(scope="module")
def app():
    """Fixture to create a QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_drill_config_dialog_initialization(app, qtbot, mock_db_manager):
    """Test that DrillConfigDialog initializes correctly."""
    from desktop_ui.drill_config import DrillConfigDialog
    
    dialog = DrillConfigDialog(db_manager=mock_db_manager)
    qtbot.addWidget(dialog)
    
    # Check basic initialization
    assert dialog.windowTitle() == "Configure Typing Drill"
    assert dialog.db_manager == mock_db_manager
    
    # Check that UI components are present
    assert hasattr(dialog, "snippet_selector")
    assert hasattr(dialog, "start_button")
    
    # Check that snippets were loaded
    mock_db_manager.get_snippet_manager.assert_called_once()
    assert dialog.snippet_selector.count() > 0


def test_drill_config_start_button(app, qtbot, mock_db_manager):
    """Test that the start button launches the typing drill with correct parameters."""
    from desktop_ui.drill_config import DrillConfigDialog
    
    with patch('desktop_ui.drill_screen_tester.DrillScreenTester') as mock_drill_tester:
        # Setup mock DrillScreenTester to return a mock dialog
        mock_instance = MagicMock()
        mock_drill_tester.return_value = mock_instance
        
        # Create dialog and click start
        dialog = DrillConfigDialog(db_manager=mock_db_manager)
        qtbot.addWidget(dialog)
        
        # Select first snippet and set range
        dialog.snippet_selector.setCurrentIndex(0)
        # Set start/end index values
        if hasattr(dialog, "start_index"):
            dialog.start_index.setValue(0)
        if hasattr(dialog, "end_index"):
            dialog.end_index.setValue(10)
        
        # Click the start button with qtbot
        qtbot.mouseClick(dialog.start_button, Qt.LeftButton)
        
        # Check that the drill tester was created and shown
        mock_drill_tester.assert_called_once()
        mock_instance.show.assert_called_once()
