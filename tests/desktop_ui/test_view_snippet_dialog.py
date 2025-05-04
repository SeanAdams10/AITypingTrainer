"""
Test for the View Snippet Dialog in the desktop UI
"""
import os
import sys
import pytest
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

# Add the project root to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from desktop_ui.view_snippet_dialog import ViewSnippetDialog


@pytest.mark.qt
class TestViewSnippetDialog:
    """Test view snippet dialog functionality"""
    
    @pytest.fixture
    def qtapp(self):
        """Create a Qt application instance"""
        app = QApplication([])
        yield app
        app.quit()
    
    def test_dialog_initializes_correctly(self, qtapp):
        """Test that the dialog initializes with the correct snippet content"""
        # Test data
        title = "Test Snippet"
        snippet_name = "Example Snippet"
        content = "This is an example snippet content."
        
        # Create dialog
        dialog = ViewSnippetDialog(title, snippet_name, content)
        
        # Verify dialog properties
        assert dialog.windowTitle() == title
        assert dialog.name_label.text() == f"<h1>{snippet_name}</h1>"
        assert dialog.content_display.toPlainText() == content
        assert dialog.content_display.isReadOnly() is True
        
        # Clean up
        dialog.close()
    
    def test_dialog_close_button(self, qtapp):
        """Test that the close button works correctly"""
        # Create dialog and connect a test signal handler
        dialog = ViewSnippetDialog("Test", "Test Name", "Test Content")
        
        # Use a flag to track dialog closure instead of mocking (which causes the SIP error)
        closed = False
        
        def on_dialog_accepted():
            nonlocal closed
            closed = True
        
        # Connect our handler to the accepted signal
        dialog.accepted.connect(on_dialog_accepted)
        
        # Simulate clicking the close button
        dialog.closeBtn.click()
        
        # Process Qt events to ensure signals are delivered
        qtapp.processEvents()
        
        # Verify our signal handler was called
        assert closed is True
        
        # Clean up
        dialog.close()
    
    def test_dialog_maximized_state(self, qtapp):
        """Test that the dialog opens in maximized state"""
        # Create dialog
        dialog = ViewSnippetDialog("Test", "Test Name", "Test Content")
        
        # Check window state before showing
        assert dialog.windowState() & Qt.WindowMaximized
        
        # Clean up
        dialog.close()
        
    def test_dialog_content_formatting(self, qtapp):
        """Test that the content is properly formatted in the display"""
        # Test with multiline content
        content = "Line 1\nLine 2\nLine 3"
        
        # Create dialog
        dialog = ViewSnippetDialog("Test", "Test Name", content)
        
        # Verify content is displayed correctly with line breaks
        assert dialog.content_display.toPlainText() == content
        
        # Verify font is set to monospace
        font = dialog.content_display.font()
        assert font.family() == "Consolas"  # Should be a monospace font
        
        # Clean up
        dialog.close()
