"""
Tests for the DrillConfigDialog in the desktop UI.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Add project root to Python path to enable imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now we can import project modules
from desktop_ui.drill_config import DrillConfigDialog


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
def qtapp():
    """Fixture to create a QApplication instance.
    Using qtapp name to avoid conflicts with pytest-flask.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class QtBot:
    """Simple QtBot class to replace pytest-qt's qtbot when it's not available."""
    def __init__(self, app):
        self.app = app
        self.widgets = []
        
    def addWidget(self, widget):
        """Keep track of widgets to ensure they don't get garbage collected."""
        self.widgets.append(widget)
        return widget
        
    def mouseClick(self, widget, button=Qt.LeftButton, pos=None):
        """Simulate mouse click."""
        if pos is None and hasattr(widget, 'rect'):
            pos = widget.rect().center()
        # Here we would normally use QTest.mouseClick, but for our tests
        # we can just directly call the click handler if available
        if hasattr(widget, 'click'):
            widget.click()
        # Process events to make sure UI updates
        self.app.processEvents()
    
    def waitUntil(self, callback, timeout=1000):
        """Wait until the callback returns True or timeout."""
        # Simpler version, just call the callback directly since our tests are synchronous
        return callback()
        
    def wait(self, ms):
        """Wait for the specified number of milliseconds."""
        # Process events to make any pending UI updates happen
        self.app.processEvents()


@pytest.fixture
def qtbot(qtapp):
    """Create a QtBot instance for testing when pytest-qt's qtbot isn't available."""
    return QtBot(qtapp)


def test_drill_config_dialog_initialization(qtapp, qtbot, mock_db_manager):
    """Test that DrillConfigDialog initializes correctly."""
    
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


def test_drill_config_start_button(qtapp, qtbot, mock_db_manager):
    """Test that the start button launches the typing drill with correct parameters.
    This test validates that the typing drill screen appears with the correct content.
    """
    # Instead of patching DrillScreenTester, let's patch TypingDrillScreen
    with patch('desktop_ui.typing_drill.TypingDrillScreen') as mock_typing_drill:
        # Create a mock TypingDrillScreen instance with necessary methods
        mock_drill_instance = MagicMock()
        # Make exec_ return a value as if the dialog was closed
        mock_drill_instance.exec_.return_value = 0
        mock_typing_drill.return_value = mock_drill_instance
        
        # Create the drill config dialog
        dialog = DrillConfigDialog(db_manager=mock_db_manager)
        qtbot.addWidget(dialog)
        
        # Configure test data
        expected_content = "This is test snippet 1"
        
        # Ensure mock returns the correct content
        mock_db_manager.get_snippet_manager().get_all_snippets.return_value = [
            {"id": 1, "title": "Test Snippet 1", "content": expected_content},
            {"id": 2, "title": "Test Snippet 2", "content": "This is test snippet 2"}
        ]
        
        # Refresh the dialog to load our mock data
        dialog._load_snippets()
        
        # Select first snippet and set range
        dialog.snippet_selector.setCurrentIndex(0)
        # Set start/end index values to ensure we get the full content
        dialog.start_index.setValue(0)
        dialog.end_index.setValue(len(expected_content))
        
        # Directly call the start drill method instead of clicking the button
        # This is more reliable in the test environment
        dialog._start_drill()
        
        # Verify the dialog was properly created with the right parameters
        mock_typing_drill.assert_called_once()
        
        # Check the TypingDrillScreen was created with the correct parameters
        call_args = mock_typing_drill.call_args[1]  # Get the keyword arguments
        assert call_args['snippet_id'] == 1
        assert call_args['start'] == 0
        assert call_args['end'] == len(expected_content)
        assert call_args['content'] == expected_content
        assert call_args['db_manager'] == mock_db_manager
        
        # Verify the drill screen's exec_ method was called to display it
        mock_drill_instance.exec_.assert_called_once()
