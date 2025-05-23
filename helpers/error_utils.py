"""
Error handling utilities for the AITypingTrainer application.

This module provides utility functions for displaying error messages and handling
errors in a user-friendly way across the application.
"""

import logging
from typing import Optional

from PyQt5.QtWidgets import QMessageBox

# Configure logging
logger = logging.getLogger(__name__)


def ErrorMsgBox(
    error_message: str,
    title: str = "Error",
    details: Optional[str] = None,
    parent=None
) -> None:
    """Display an error message box with the given error information.
    
    Args:
        error_message: The main error message to display
        title: The window title for the error dialog
        details: Optional detailed error information to show in the dialog
        parent: Optional parent widget for the message box
    """
    try:
        msg = QMessageBox(parent)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(error_message)
        
        if details:
            msg.setInformativeText(details)
            
        msg.exec_()
    except Exception as e:
        # If showing the message box fails, log the error
        logger.error("Failed to display error message box: %s", str(e))
        # Also log the original error that we were trying to display
        logger.error("Original error: %s", error_message)
        if details:
            logger.error("Error details: %s", details)
