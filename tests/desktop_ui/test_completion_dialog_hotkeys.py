"""
Test the CompletionDialog hotkey and default button functionality.

This test verifies that the CompletionDialog has proper keyboard shortcuts configured
and that the Close button is set as the default button.
"""

import os
import sys
import pytest
from typing import Any, Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QPushButton

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from the project
from desktop_ui.typing_drill import CompletionDialog


@pytest.fixture
def app() -> QApplication:
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_completion_dialog_hotkeys_and_default(app: QApplication) -> None:
    """
    Test that the CompletionDialog has proper hotkey configuration.
    
    This test verifies:
    1. The Retry button has Alt+R shortcut
    2. The Close button has Alt+C shortcut
    3. The Close button is set as the default button
    4. The Close button has focus initially
    
    Args:
        app: The QApplication instance
    """
    # Sample stats for the dialog
    stats = {
        "wpm": 60.0,
        "cpm": 300.0,
        "accuracy": 98.5,
        "efficiency": 98.0,  # Added efficiency metric
        "correctness": 99.0,  # Added correctness metric
        "errors": 3,
        "total_time": 30.0,
        "total_chars": 150,
        "expected_chars": 150,
        "actual_chars": 150
    }
    
    # Create the dialog
    dialog = CompletionDialog(stats)
    
    try:
        # Show the dialog for real focus handling
        dialog.show()

        # Process events to ensure focus is set
        app.processEvents()

        # Find buttons
        buttons = dialog.findChildren(QPushButton)
        retry_button = None
        close_button = None
        
        for button in buttons:
            if "Retry" in button.text():
                retry_button = button
            elif "Close" in button.text():
                close_button = button
        
        # Verify buttons exist
        assert retry_button is not None, "Retry button not found"
        assert close_button is not None, "Close button not found"
        
        # Verify hotkey text for buttons (& ampersand indicates shortcut)
        assert "&Retry" == retry_button.text(), "Retry button should have Alt+R shortcut"
        assert "&Close" == close_button.text(), "Close button should have Alt+C shortcut"
        
        # Verify Close is default button
        assert close_button.isDefault(), "Close button should be the default button"
        
        # Get button that has focus
        app.processEvents()  # Ensure focus is set
        focused_widget = dialog.focusWidget()
        assert focused_widget == close_button, "Close button should have initial focus"
        
    finally:
        # Clean up
        dialog.close()
