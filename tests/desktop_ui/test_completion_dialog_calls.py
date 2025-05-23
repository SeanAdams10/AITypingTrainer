"""
Test to verify the completion dialog is only shown once per typing session.

This test specifically checks for the fixed issue where _show_completion_dialog
was being called twice during a single typing session.
"""

import os
import sys
from typing import Any, Dict

import pytest
from PyQt5.QtWidgets import QApplication

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from the project
from desktop_ui.typing_drill import CompletionDialog, TypingDrillScreen


@pytest.fixture
def app() -> QApplication:
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_completion_dialog_shown_once(app: QApplication) -> None:
    """
    Test that the completion dialog is only shown once when typing session completes.
    
    This test verifies that the fix for duplicate dialog calls works correctly.
    
    Args:
        app: The QApplication instance
    """
    # Create a typing drill screen with a simple content
    content = "test"
    screen = TypingDrillScreen(
        snippet_id=-1,  # Use -1 for test snippet
        start=0,
        end=len(content),
        content=content,
        db_manager=None  # No DB manager needed for this test
    )
    
    # Mock the _show_completion_dialog method to track calls
    original_show_completion = screen._show_completion_dialog
    call_count = [0]  # Use list to allow modification in the nested function
    
    def mock_show_completion(stats: Dict[str, Any]) -> None:
        """Mock implementation that tracks calls and delegates to original."""
        call_count[0] += 1
        # Don't actually show dialog to avoid UI interaction during test
        screen.completion_dialog = CompletionDialog(stats, screen)
    
    screen._show_completion_dialog = mock_show_completion
    
    try:
        # Simulate user typing the complete text
        screen.typing_input.setPlainText(content)
        
        # Let event loop process everything
        app.processEvents()
        
        # Verify the completion dialog was shown exactly once
        assert call_count[0] == 1, f"Expected 1 call to _show_completion_dialog, got {call_count[0]}"
        
    finally:
        # Restore original method
        screen._show_completion_dialog = original_show_completion
        
        # Clean up
        screen.close()
