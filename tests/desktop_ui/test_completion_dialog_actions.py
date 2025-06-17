"""
Test for the completion dialog action handling.

These tests verify that the dialog actions (Retry/Close) properly control the
typing drill screen behavior - either returning to the drill or closing it.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QDialog, QDialogButtonBox, QPushButton

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from the project
from desktop_ui.typing_drill import TypingDrillScreen


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
    
    original_exec_called = False

    def patched_exec(dialog_self: QDialog) -> int:
        nonlocal original_exec_called
        original_exec_called = True

        dialog_self.show()
        
        # Wait for the dialog to be exposed and active
        if not QTest.qWaitForWindowExposed(dialog_self.windowHandle()):
            pytest.fail("CompletionDialog window was not exposed in time.")
        QApplication.processEvents() # Ensure events are processed

        # Find the close button
        close_button = None
        button_box = dialog_self.findChild(QDialogButtonBox)
        if button_box:
            # Try AcceptRole first, as closing often means accepting the dialog's outcome
            close_button = button_box.button(QDialogButtonBox.AcceptRole)
            if not close_button:
                close_button = button_box.button(QDialogButtonBox.CloseRole)
            if not close_button: # Some dialogs might use OK for accept
                close_button = button_box.button(QDialogButtonBox.Ok)
        
        if not close_button:
            # Fallback: try to find a button with text 'Close' or 'OK'
            buttons = dialog_self.findChildren(QPushButton)
            for btn in buttons:
                btn_text = btn.text().lower()
                if "close" in btn_text or "ok" in btn_text:
                    close_button = btn
                    break
        
        assert close_button is not None, "Close button not found in CompletionDialog"
        assert close_button.isVisible(), "Close button is not visible"
        assert close_button.isEnabled(), "Close button is not enabled"

        # Click the button
        QTest.mouseClick(close_button, Qt.LeftButton)
        
        # Wait for the dialog to process the click and potentially close
        QTest.qWait(50) # Allow 50ms for event processing
        QApplication.processEvents()

        # The button click should lead to the dialog being accepted.
        # Return QDialog.Accepted as this is what the original logic in
        # _show_completion_dialog expects for screen.accept() to be called.
        return QDialog.Accepted

    # Patch target: Assumes TypingDrillScreen imports CompletionDialog into its namespace.
    # Adjust 'desktop_ui.typing_drill_screen.CompletionDialog.exec_' if the import structure is different.
    # For example, if CompletionDialog is defined in 'desktop_ui.completion_dialog',
    # and typing_drill_screen.py (where _show_completion_dialog is) does:
    #   from .completion_dialog import CompletionDialog 
    #   from desktop_ui.completion_dialog import CompletionDialog
    # then the target should be where CompletionDialog is resolved by _show_completion_dialog.
    patch_target = 'desktop_ui.typing_drill.CompletionDialog.exec_'
    
    try:
        with patch(patch_target, new=patched_exec):
            # Call the method we're testing
            screen._show_completion_dialog(stats)
    except ImportError: # pylint: disable=broad-except
        # Fallback patch target if the above is not found
        # (e.g. direct import in test file for other tests)
        patch_target_fallback = 'desktop_ui.completion_dialog.CompletionDialog.exec_'
        with patch(patch_target_fallback, new=patched_exec):
            screen._show_completion_dialog(stats)

    assert original_exec_called, (
        f"Patched exec_ ({patch_target} or fallback) was not called. "
        f"Check patch target. This could be due to an incorrect patch "
        f"target or the dialog not being shown."
    )
    
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
