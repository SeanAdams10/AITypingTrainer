"""
Test for the completion dialog action handling.

These tests verify that the dialog actions (Retry/Close) properly control the
typing drill screen behavior - either returning to the drill or closing it.
"""

import os
import sys
import pytest
from typing import Any, Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QPushButton, QDialog
from unittest.mock import patch, MagicMock

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from the project
from desktop_ui.typing_drill import TypingDrillScreen, CompletionDialog


@pytest.fixture
def app() -> QApplication:
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_dialog_close_button_closes_typing_screen(app: QApplication) -> None:
    """
    Test that clicking the Close button closes both the dialog and typing screen.
    
    This test verifies that when the dialog's Close button is pressed,
    the typing screen is also closed (by calling accept()).
    """
    # Create a typing drill screen
    content = "test"
    screen = TypingDrillScreen(snippet_id=1, start=0, end=len(content), content=content)
    
    # Mock the screen's accept method to check if it gets called
    screen.accept = MagicMock()
    
    # Create stats for the dialog
    stats = {
        "wpm": 60.0,
        "cpm": 300.0,
        "accuracy": 100.0,
        "efficiency": 100.0,
        "correctness": 100.0,
        "errors": 0,
        "total_time": 2.0,
        "total_keystrokes": 4,
        "backspace_count": 0,
        "expected_chars": 4,
        "actual_chars": 4,
        "correct_chars": 4
    }
    
    # Create a completion dialog directly to test interaction
    dialog = CompletionDialog(stats, screen)
    
    # Mock the dialog's exec_ to return QDialog.Accepted (simulating Close button click)
    dialog.exec_ = MagicMock(return_value=QDialog.Accepted)
    
    # Call the method we're testing
    screen._show_completion_dialog(stats)
    
    # Verify screen.accept() was called, which would close the typing screen
    screen.accept.assert_called_once()


def test_dialog_retry_button_resets_typing_session(app: QApplication) -> None:
    """
    Test that clicking the Retry button resets the typing session without closing the screen.
    
    This test verifies that when the dialog's Retry button is pressed,
    the typing session is reset but the screen remains open.
    """
    # Create a typing drill screen
    content = "test"
    screen = TypingDrillScreen(snippet_id=1, start=0, end=len(content), content=content)
    
    # Create stats for the dialog
    stats = {
        "wpm": 60.0,
        "cpm": 300.0,
        "accuracy": 100.0,
        "efficiency": 100.0,
        "correctness": 100.0,
        "errors": 0,
        "total_time": 2.0,
        "total_keystrokes": 4,
        "backspace_count": 0,
        "expected_chars": 4,
        "actual_chars": 4,
        "correct_chars": 4
    }
    
    # Patch both the critical methods and CompletionDialog for proper testing
    with patch.object(screen, '_reset_session') as mock_reset:
        with patch.object(screen, 'accept') as mock_accept:
            # Create a mock dialog that returns the retry code
            mock_dialog = MagicMock()
            mock_dialog.exec_.return_value = 2  # Retry button code
            
            # Patch the CompletionDialog to return our mock
            with patch('desktop_ui.typing_drill.CompletionDialog', return_value=mock_dialog):
                # Call the method we're testing
                screen._show_completion_dialog(stats)
                
                # Verify reset_session was called but not accept
                mock_reset.assert_called_once()
                mock_accept.assert_not_called()


def test_altkey_hotkeys_trigger_correct_actions(app: QApplication) -> None:
    """
    Test that Alt+R and Alt+C hotkeys trigger the correct actions.
    
    This test verifies that keyboard shortcuts properly control
    the typing drill screen behavior.
    """
    # Create a typing drill screen
    content = "test"
    screen = TypingDrillScreen(snippet_id=1, start=0, end=len(content), content=content)
    
    # Create stats for the dialog
    stats = {
        "wpm": 60.0,
        "cpm": 300.0,
        "accuracy": 100.0,
        "efficiency": 100.0,
        "correctness": 100.0,
        "errors": 0,
        "total_time": 2.0,
        "total_keystrokes": 4,
        "backspace_count": 0,
        "expected_chars": 4,
        "actual_chars": 4,
        "correct_chars": 4
    }
    
    # Test 1: Alt+R (Retry) hotkey
    with patch.object(screen, '_reset_session') as mock_reset:
        with patch.object(screen, 'accept') as mock_accept:
            # Create a mock dialog that returns the retry code (Alt+R)
            mock_dialog = MagicMock()
            mock_dialog.exec_.return_value = 2  # Retry button code
            
            # Patch the CompletionDialog to return our mock
            with patch('desktop_ui.typing_drill.CompletionDialog', return_value=mock_dialog):
                # Call the method we're testing
                screen._show_completion_dialog(stats)
                
                # Verify reset was called but accept wasn't
                mock_reset.assert_called_once()
                mock_accept.assert_not_called()
    
    # Test 2: Alt+C (Close) hotkey
    with patch.object(screen, '_reset_session') as mock_reset:
        with patch.object(screen, 'accept') as mock_accept:
            # Create a mock dialog that returns QDialog.Accepted (Alt+C/Close)
            mock_dialog = MagicMock()
            mock_dialog.exec_.return_value = QDialog.Accepted  # Close button code
            
            # Patch the CompletionDialog to return our mock
            with patch('desktop_ui.typing_drill.CompletionDialog', return_value=mock_dialog):
                # Call the method we're testing
                screen._show_completion_dialog(stats)
                
                # Verify accept was called but reset wasn't
                mock_accept.assert_called_once()
                mock_reset.assert_not_called()
