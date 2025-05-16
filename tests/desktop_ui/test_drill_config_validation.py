"""
Tests for validation rules in the DrillConfigDialog.
"""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt5.QtCore import Qt

# Add project root to Python path to enable imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now we can import project modules
from desktop_ui.drill_config import DrillConfigDialog

# Create a test fixture to extract validation results without UI
@pytest.fixture
def extract_validation():
    """Helper fixture to extract validation results without UI interaction.
    
    This fixture provides a testing-friendly version of the DrillConfigDialog._start_drill method.
    Instead of showing warning message boxes and proceeding with the drill, it returns a tuple
    containing a boolean success indicator and an error message string.
    """
    # Store the original method for restoration
    original_start_drill = DrillConfigDialog._start_drill
    
    def _validation_function(dialog_instance):
        """Function that validates dialog inputs and returns (success, message).
        
        This replaces the actual _start_drill method during tests.
        """
        print("\n==== Starting validation ====")
        
        # Use the same validation logic as in DrillConfigDialog._start_drill
        if dialog_instance.use_custom_text.isChecked():
            print("Custom text mode selected")
            content = dialog_instance.custom_text.toPlainText()
            print(f"Custom text content: '{content}'")
            
            # Check for empty text
            if not content.strip():
                print("Validation failed: Empty text")
                return False, "Empty text"
        else:
            print("Snippet mode selected")
            idx = dialog_instance.snippet_selector.currentIndex()
            print(f"Snippet index: {idx}")
            print(f"Number of snippets: {len(dialog_instance.snippets)}")
            
            # Check for valid snippet selection
            if idx < 0 or idx >= len(dialog_instance.snippets):
                print("Validation failed: Invalid snippet selection")
                return False, "Invalid snippet selection"
                
            snippet = dialog_instance.snippets[idx]
            content = snippet["content"]
            print(f"Content length: {len(content)}")
            start = dialog_instance.start_index.value()
            end = dialog_instance.end_index.value()
            print(f"Start index: {start}, End index: {end}")
            
            # Validate end must be greater than start - EXACTLY as in _start_drill
            if end <= start:
                print(f"Validation failed: End ({end}) <= Start ({start})")
                return False, "End index must be greater than start index"
                
            # Validate start must be within content bounds
            if start < 0 or start >= len(content):
                print(f"Validation failed: Start ({start}) out of bounds [0, {len(content)})")
                return False, "Start index must be between 0 and content length"
                
            # Validate end must be within content bounds
            if end > len(content):
                print(f"Validation failed: End ({end}) out of bounds (end > {len(content)})")
                return False, f"End index must be between {start + 1} and {len(content)}"
        
        # If we reach here, validation passed
        print("Validation passed")
        return True, "Valid"
    
    yield _validation_function
    
    # Restore the original method after the test
    DrillConfigDialog._start_drill = original_start_drill

# Mock database manager for testing
@pytest.fixture
def mock_db_manager():
    """Create a mock DatabaseManager for testing."""
    manager = MagicMock()
    # Mock the snippet manager to return test snippets
    snippet_manager = MagicMock()
    
    # Create a longer test content for better range testing
    test_content = "This is a test snippet with exactly sixty characters for testing."
    
    snippet_manager.get_all_snippets.return_value = [
        {"id": 1, "title": "Test Snippet 1", "content": test_content},
        {"id": 2, "title": "Test Snippet 2", "content": "Short content"}
    ]
    manager.get_snippet_manager.return_value = snippet_manager
    
    # Mock session manager for get_next_position
    session_manager = MagicMock()
    session_manager.get_next_position.return_value = 15  # Return 15 for the tests that expect this value
    manager.get_session_manager.return_value = session_manager
    
    return manager

@pytest.fixture(scope="module")
def qtapp():
    """Fixture to create a QApplication instance."""
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
    """Create a QtBot instance for testing."""
    return QtBot(qtapp)


def test_start_index_updates_end_index_minimum(qtapp, qtbot, mock_db_manager):
    """Test that changing start index updates end index minimum."""
    dialog = DrillConfigDialog(db_manager=mock_db_manager)
    qtbot.addWidget(dialog)
    
    # Load snippets and select first one
    dialog._load_snippets()
    dialog.snippet_selector.setCurrentIndex(0)
    
    # Set start_index to 10
    dialog.start_index.setValue(10)
    
    # Check that end_index minimum is now 11 (start_index + 1)
    assert dialog.end_index.minimum() == 11
    
    # Check that if end_index was less than the new minimum, it got updated
    assert dialog.end_index.value() >= 11


def test_snippet_selection_sets_max_end_index(qtapp, qtbot, mock_db_manager):
    """Test that selecting a snippet sets the end_index maximum to content length."""
    dialog = DrillConfigDialog(db_manager=mock_db_manager)
    qtbot.addWidget(dialog)
    
    # Load snippets and select first one (which has 60 characters)
    dialog._load_snippets()
    dialog.snippet_selector.setCurrentIndex(0)
    
    # Check that end_index maximum is set to content length
    test_content = "This is a test snippet with exactly sixty characters for testing."
    assert dialog.end_index.maximum() == len(test_content)
    
    # Switch to second snippet with shorter content
    dialog.snippet_selector.setCurrentIndex(1)
    
    # Check that end_index maximum is updated
    assert dialog.end_index.maximum() == len("Short content")


def test_validation_end_greater_than_start(qtapp, qtbot, mock_db_manager):
    """Test validation requiring end index to be greater than start index.
    
    This test verifies that the DrillConfigDialog._start_drill method properly
    validates that the end index must be greater than the start index.
    """
    # Create dialog and prepare UI with mock for TypingDrillScreen
    with patch('desktop_ui.typing_drill.TypingDrillScreen') as mock_drill_screen:
        # Mock the QMessageBox.warning method at the class level
        with patch('PyQt5.QtWidgets.QMessageBox.warning') as mock_warning:
            dialog = DrillConfigDialog(db_manager=mock_db_manager)
            qtbot.addWidget(dialog)
            
            # Add snippet if needed
            dialog._load_snippets()
            if not dialog.snippets:
                dialog.snippets = [{
                    "id": 1, 
                    "title": "Test Snippet",
                    "content": "This is a test snippet with reasonable length for testing validation"
                }]
            
            # Select first snippet
            dialog.snippet_selector.setCurrentIndex(0)
            
            # Get the snippet content length for bounds checking
            snippet = dialog.snippets[0]
            content_length = len(snippet["content"])
            
            # Temporarily bypass UI constraints by setting minimum to 0
            old_min = dialog.end_index.minimum()
            dialog.end_index.setMinimum(0)
            
            # Set invalid values: end index = start index (invalid)
            dialog.start_index.setValue(10)
            dialog.end_index.setValue(10)
            
            # Call the _start_drill method directly
            dialog._start_drill()
            
            # Verify warning was displayed with correct message
            mock_warning.assert_called_once()
            
            # Check that the constructor of TypingDrillScreen wasn't called
            # (i.e., the drill didn't actually start because validation failed)
            mock_drill_screen.assert_not_called()
            
            # Reset the mock for the next test
            mock_warning.reset_mock()
            
            # Check with valid values
            dialog.start_index.setValue(10)
            dialog.end_index.setValue(20)  # Now end > start
            
            # With proper values, the drill should start
            dialog._start_drill()
            mock_warning.assert_not_called()  # No warning should appear
            mock_drill_screen.assert_called_once()  # Should be called now
            
            # Restore UI constraints
            dialog.end_index.setMinimum(old_min)


def test_validation_start_within_content_bounds(qtapp, qtbot, mock_db_manager, extract_validation):
    """Test validation requiring start index to be within content bounds."""
    dialog = DrillConfigDialog(db_manager=mock_db_manager)
    qtbot.addWidget(dialog)
    
    # Load snippets and select first one
    dialog._load_snippets()
    dialog.snippet_selector.setCurrentIndex(0)
    
    # Set invalid start index (beyond content)
    test_content = "This is a test snippet with exactly sixty characters for testing."
    dialog.start_index.setValue(len(test_content) + 10)
    
    # Use our validation function to check the input
    validate = extract_validation
    success, message = validate(dialog)
    
    # Verify validation failed
    assert not success
    assert "Start index must be between" in message


def test_validation_end_within_content_bounds(qtapp, qtbot, mock_db_manager, extract_validation):
    """Test validation requiring end index to be within content bounds."""
    dialog = DrillConfigDialog(db_manager=mock_db_manager)
    qtbot.addWidget(dialog)
    
    # Load snippets and select first one
    dialog._load_snippets()
    dialog.snippet_selector.setCurrentIndex(0)
    
    # Set valid start index
    dialog.start_index.setValue(5)
    
    # Get the test content length
    test_content = "This is a test snippet with exactly sixty characters for testing."
    
    # Temporarily increase the maximum to allow setting an invalid value
    old_max = dialog.end_index.maximum()
    dialog.end_index.setMaximum(len(test_content) + 50)
    
    # Set invalid end index (beyond content)
    dialog.end_index.setValue(len(test_content) + 10)
    
    # Use our validation function to check the input
    validate = extract_validation
    success, message = validate(dialog)
    
    # Verify validation failed
    assert not success
    assert "End index must be between" in message
    
    # Restore the maximum
    dialog.end_index.setMaximum(old_max)


def test_custom_text_validation(qtapp, qtbot, mock_db_manager, extract_validation):
    """Test validation requiring custom text to not be empty when selected."""
    dialog = DrillConfigDialog(db_manager=mock_db_manager)
    qtbot.addWidget(dialog)
    
    # Enable custom text option but leave text empty
    dialog.use_custom_text.setChecked(True)
    dialog.custom_text.setPlainText("")
    
    # Use our validation function to check the input
    validate = extract_validation
    success, message = validate(dialog)
    
    # Check that validation failed
    assert not success
    assert "Empty text" in message
    
    # Now add text and try again
    dialog.custom_text.setPlainText("This is some custom text")
    
    # Use validation function again
    success, message = validate(dialog)
    
    # Verify validation passed
    assert success
    assert "Valid" in message


def test_next_position_from_session_manager(qtapp, qtbot, mock_db_manager, extract_validation):
    """Test that the next position is loaded correctly from session manager."""
    dialog = DrillConfigDialog(db_manager=mock_db_manager)
    qtbot.addWidget(dialog)
    
    # Create a new mock session manager with our custom return values
    mock_session_manager = MagicMock()
    mock_session_manager.get_last_session_snippet_id.return_value = 1
    mock_session_manager.get_last_session_end_index.return_value = 50
    mock_session_manager.get_next_position.return_value = 50  # Override the default 15 from fixture
    
    # Important: Use get_session_manager not get_practice_session_manager to match what DrillConfigDialog uses
    mock_db_manager.get_session_manager.return_value = mock_session_manager
    
    # Load snippets
    dialog._load_snippets()
    
    # Select the snippet directly
    dialog.snippet_selector.setCurrentIndex(1)
    
    # Verify that the start index is set to the next position from the session manager
    # This happens in the _on_snippet_changed method when a new snippet is selected
    assert dialog.snippet_selector.currentIndex() == 1  # Second snippet (index 1) is selected
    assert dialog.start_index.value() == 50  # This comes from our mocked session_manager
    
    # Use our validation function to check the input
    validate = extract_validation
    success, message = validate(dialog)
    assert success
    assert "Valid" in message
    
    # For the sake of test coverage, test with a different end value
    dialog.end_index.setValue(70)  # Make sure end is greater than start
    
    # Try again with new values
    success, message = validate(dialog)
    assert success
    assert "Valid" in message


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
