"""
TypingDrillScreen - Interactive typing practice UI with real-time feedback.
Implements full typing drill functionality including timing, statistics, and session persistence.
"""

import os
import sys
import time
import datetime
from typing import Optional, List, Dict, Any, Tuple

# Add project root to path for direct script execution
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QProgressBar, QWidget, QDialog, QGridLayout, 
    QSpacerItem, QSizePolicy, QApplication
)
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QTextCharFormat, QColor, QFont, QTextCursor, QPalette

# Try to import models properly regardless of how script is run
try:
    from models.practice_session import PracticeSession, PracticeSessionManager
except ImportError:
    # Will use sys.path if project_root was added above
    from models.practice_session import PracticeSession, PracticeSessionManager


class CompletionDialog(QDialog):
    """
    Dialog shown when the typing session is completed.
    Displays typing statistics and provides options to retry or close.
    """
    def __init__(
        self,
        stats: Dict[str, Any],
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Typing Session Completed")
        self.setMinimumSize(400, 300)
        self.setModal(True)
        
        # Store stats
        self.stats = stats
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Results section
        results_label = QLabel("<h2>Typing Results</h2>")
        results_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(results_label)
        
        # Stats grid
        stats_grid = QGridLayout()
        self._add_stat_row(stats_grid, 0, "Words Per Minute (WPM):", f"{stats['wpm']:.1f}")
        self._add_stat_row(stats_grid, 1, "Characters Per Minute (CPM):", f"{stats['cpm']:.1f}")
        self._add_stat_row(stats_grid, 2, "Accuracy:", f"{stats['accuracy']:.1f}%")
        self._add_stat_row(stats_grid, 3, "Errors:", f"{stats['errors']}")
        self._add_stat_row(stats_grid, 4, "Time:", f"{stats['total_time']:.1f} seconds")
        
        layout.addLayout(stats_grid)
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Buttons
        button_layout = QHBoxLayout()
        
        retry_button = QPushButton("Retry")
        retry_button.clicked.connect(self._on_retry)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(retry_button)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def _add_stat_row(self, grid: QGridLayout, row: int, label: str, value: str) -> None:
        """Add a row to the stats grid with label and value."""
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Arial", 10, QFont.Bold))
        value_widget = QLabel(value)
        value_widget.setFont(QFont("Arial", 10))
        
        grid.addWidget(label_widget, row, 0)
        grid.addWidget(value_widget, row, 1)
    
    def _on_retry(self) -> None:
        """Handle retry button click."""
        self.done(2)  # Custom return code for retry


class TypingDrillScreen(QDialog):
    """
    TypingDrillScreen handles the typing drill UI and session persistence for desktop.
    Implements real-time feedback, timing, statistics, and session recording.
    
    Args:
        snippet_id: ID of the snippet being practiced (-1 for manual text)
        start: Starting index in the snippet
        end: Ending index in the snippet
        content: Content to type (substring of snippet between start and end)
        parent: Parent widget
    """

    def __init__(
        self,
        snippet_id: int,
        start: int,
        end: int,
        content: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Typing Drill")
        self.setMinimumSize(800, 600)  # As per requirements
        self.setModal(True)
        
        # Move to center of screen (per requirements)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # Store parameters
        self.snippet_id: int = snippet_id
        self.start: int = start
        self.end: int = end
        self.content: str = content
        
        # Initialize typing state
        self.timer_running: bool = False
        self.start_time: float = 0.0
        self.elapsed_time: float = 0.0
        self.typed_chars: int = 0
        self.errors: int = 0
        self.error_positions: List[int] = []
        self.session_start_time: datetime.datetime = datetime.datetime.now()
        self.session_end_time: Optional[datetime.datetime] = None
        
        # Preprocess content to handle special characters
        # Replace tabs, newlines and spaces with visible characters for display
        self.display_content: str = self._preprocess_content(content)
        
        # Setup UI Components
        self._setup_ui()
        
        # Create timer for updating stats
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(100)  # Update every 100ms
        
        # Set focus to typing input
        self.typing_input.setFocus()
    
    def _preprocess_content(self, content: str) -> str:
        """
        Preprocess content to make whitespace and special chars visible.
        Per requirements, we show special symbols but compare against original text.
        
        Args:
            content: Original text content
            
        Returns:
            Preprocessed content with visible whitespace markers
        """
        # Replace spaces with visible space character (using subscript up arrow as specified)
        result = content.replace(' ', '␣')  # Visible space character
        
        # Replace tabs with visible tab character
        result = result.replace('\t', '⮾')  # Tab symbol
        
        # Replace newlines with return symbol
        result = result.replace('\n', '↵\n')  # Return symbol + actual newline
        
        # Make underscores more visible by adding background
        result = result.replace('_', '_')
        
        return result
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("<h1>Typing Drill</h1>")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Stats bar (WPM, Accuracy, Time)
        stats_layout = QHBoxLayout()
        
        # Timer
        self.timer_label = QLabel("Time: 0.0s")
        self.timer_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.timer_label)
        
        # WPM
        self.wpm_label = QLabel("WPM: 0.0")
        self.wpm_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.wpm_label)
        
        # Accuracy
        self.accuracy_label = QLabel("Accuracy: 100%")
        self.accuracy_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.accuracy_label)
        
        # Errors
        self.errors_label = QLabel("Errors: 0")
        self.errors_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.errors_label)
        
        main_layout.addLayout(stats_layout)
        
        # Text to type (display)
        main_layout.addWidget(QLabel("<h3>Type the following text:</h3>"))
        
        self.display_text = QTextEdit()
        self.display_text.setReadOnly(True)
        self.display_text.setFont(QFont("Courier New", 12))
        self.display_text.setText(self.display_content)
        self.display_text.setMinimumHeight(150)
        main_layout.addWidget(self.display_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, len(self.content))
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Typing input
        main_layout.addWidget(QLabel("<h3>Your typing:</h3>"))
        
        self.typing_input = QTextEdit()
        self.typing_input.setFont(QFont("Courier New", 12))
        self.typing_input.setMinimumHeight(150)
        self.typing_input.textChanged.connect(self._on_text_changed)
        main_layout.addWidget(self.typing_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self._reset_session)
        button_layout.addWidget(self.reset_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)
        
        main_layout.addLayout(button_layout)
    
    def _on_text_changed(self) -> None:
        """Handle text changes in the typing input."""
        # Start the timer on first character
        if not self.timer_running and self.typing_input.toPlainText():
            self.timer_running = True
            self.start_time = time.time()
            self.session_start_time = datetime.datetime.now()
        
        # Get current input and immediately process it
        current_text = self.typing_input.toPlainText()
        self.typed_chars = len(current_text)
        
        # Process any pending events to ensure UI is responsive
        QApplication.processEvents()
        
        # Update progress bar
        self.progress_bar.setValue(min(self.typed_chars, len(self.content)))
        
        # Check for completion
        if self.typed_chars >= len(self.content):
            self._check_completion()
            return
        
        # Update display text highlighting immediately
        self._update_highlighting(current_text)
        
        # Calculate and update stats
        self._update_stats()
    
    def _update_highlighting(self, current_text: str) -> None:
        """
        Update the display text with highlighting based on typing accuracy.
        
        Args:
            current_text: Current text input by the user
        """
        # Block signals temporarily to avoid recursive calls
        self.display_text.blockSignals(True)
        
        # Create a new QTextDocument for better performance
        document = self.display_text.document().clone()
        
        # Set up character formats
        correct_format = QTextCharFormat()
        correct_format.setForeground(QColor(0, 128, 0))  # Green
        correct_format.setBackground(QColor(220, 255, 220))  # Light green background
        
        error_format = QTextCharFormat()
        error_format.setForeground(QColor(255, 0, 0))  # Red
        error_format.setBackground(QColor(255, 220, 220))  # Light red background
        
        # Apply formatting based on current input
        self.error_positions = []
        cursor = QTextCursor(document)
        
        # First reset the document to show the original content
        cursor.select(QTextCursor.Document)
        cursor.insertText(self.display_content)
        
        # Apply formatting for each character
        for i, char in enumerate(current_text):
            if i >= len(self.content):
                break
                
            cursor.setPosition(i)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            
            if char == self.content[i]:
                cursor.setCharFormat(correct_format)
            else:
                cursor.setCharFormat(error_format)
                if i not in self.error_positions:
                    self.error_positions.append(i)
        
        # Update the error count
        self.errors = len(self.error_positions)
        
        # Set the document and unblock signals
        self.display_text.setDocument(document)
        self.display_text.blockSignals(False)
        
        # Ensure display updates immediately
        self.display_text.update()
    
    def _update_timer(self) -> None:
        """Update timer and stats display."""
        if self.timer_running:
            self.elapsed_time = time.time() - self.start_time
            self.timer_label.setText(f"Time: {self.elapsed_time:.1f}s")
            self._update_stats()
    
    def _update_stats(self) -> None:
        """Calculate and update WPM, CPM, and accuracy stats."""
        if not self.timer_running or self.elapsed_time < 0.1:
            return
        
        # Calculate WPM (standard 5 chars = 1 word)
        minutes = self.elapsed_time / 60.0
        wpm = (self.typed_chars / 5.0) / minutes if minutes > 0 else 0
        
        # Calculate CPM
        cpm = self.typed_chars / minutes if minutes > 0 else 0
        
        # Calculate accuracy
        correct_chars = self.typed_chars - len(self.error_positions)
        accuracy = (correct_chars / self.typed_chars * 100) if self.typed_chars > 0 else 100
        
        # Update labels
        self.wpm_label.setText(f"WPM: {wpm:.1f}")
        self.accuracy_label.setText(f"Accuracy: {accuracy:.1f}%")
        self.errors_label.setText(f"Errors: {len(self.error_positions)}")
    
    def _check_completion(self) -> None:
        """Check if the typing session is complete and handle completion."""
        current_text = self.typing_input.toPlainText()
        
        # Consider completed if all content is typed
        if len(current_text) >= len(self.content):
            # Check for match
            match = current_text[:len(self.content)] == self.content
            
            # Stop timer
            self.timer_running = False
            self.session_end_time = datetime.datetime.now()
            
            # Calculate final stats
            stats = self._calculate_stats()
            
            # Disable typing input
            self.typing_input.setReadOnly(True)
            palette = self.typing_input.palette()
            palette.setColor(QPalette.Base, QColor(240, 240, 240))  # Grey out
            self.typing_input.setPalette(palette)
            
            # Process any pending events to ensure UI updates
            QApplication.processEvents()
            
            # Show completion dialog
            self._show_completion_dialog(stats)
    
    def _calculate_stats(self) -> Dict[str, Any]:
        """
        Calculate final statistics for the typing session.
        
        Returns:
            Dictionary with stats (wpm, cpm, accuracy, etc.)
        """
        # Calculate time
        minutes = self.elapsed_time / 60.0
        
        # Calculate WPM
        wpm = (self.typed_chars / 5.0) / minutes if minutes > 0 else 0
        
        # Calculate CPM
        cpm = self.typed_chars / minutes if minutes > 0 else 0
        
        # Calculate accuracy
        correct_chars = self.typed_chars - len(self.error_positions)
        accuracy = (correct_chars / self.typed_chars * 100) if self.typed_chars > 0 else 100
        
        return {
            "total_time": self.elapsed_time,
            "wpm": wpm,
            "cpm": cpm,
            "expected_chars": len(self.content),
            "actual_chars": self.typed_chars,
            "errors": len(self.error_positions),
            "accuracy": accuracy,
            "error_positions": self.error_positions
        }
    
    def _show_completion_dialog(self, stats: Dict[str, Any]) -> None:
        """
        Show the completion dialog with typing results.
        
        Args:
            stats: Dictionary with session statistics
        """
        self.completion_dialog = CompletionDialog(stats, self)
        self.completion_dialog.show()  # Make dialog visible for tests
        result = self.completion_dialog.exec_()
        
        if result == 2:  # Retry
            self._reset_session()
        else:  # Close
            self.accept()
    
    def _reset_session(self) -> None:
        """Reset the typing session to start over."""
        # Reset state
        self.timer_running = False
        self.start_time = 0.0
        self.elapsed_time = 0.0
        self.typed_chars = 0
        self.errors = 0
        self.error_positions = []
        self.session_start_time = datetime.datetime.now()
        self.session_end_time = None
        
        # Reset UI
        self.typing_input.clear()
        self.typing_input.setReadOnly(False)
        palette = self.typing_input.palette()
        palette.setColor(QPalette.Base, QColor(255, 255, 255))  # White
        self.typing_input.setPalette(palette)
        
        self.progress_bar.setValue(0)
        self.timer_label.setText("Time: 0.0s")
        self.wpm_label.setText("WPM: 0.0")
        self.accuracy_label.setText("Accuracy: 100%")
        self.errors_label.setText("Errors: 0")
        
        # Reset text highlighting
        self.display_text.setText(self.display_content)
        
        # Set focus to typing input
        self.typing_input.setFocus()
    
    def save_session(self, stats: dict, session_manager) -> None:
        """
        Persist the typing session using the provided PracticeSessionManager.
        
        Args:
            stats: Dict with session metrics (total_time, wpm, cpm, expected_chars, actual_chars, errors, accuracy)
            session_manager: PracticeSessionManager instance
            
        Raises:
            ValueError: If required stats fields are missing or invalid.
        """
        # Validate required stats
        required = [
            "total_time",
            "wpm",
            "cpm",
            "expected_chars",
            "actual_chars",
            "errors",
            "accuracy",
        ]
        for key in required:
            if key not in stats:
                raise ValueError(f"Missing required stat: {key}")
        
        # Create and save session
        session = PracticeSession(
            session_id=None,
            snippet_id=self.snippet_id,
            snippet_index_start=self.start,
            snippet_index_end=self.end,
            content=self.content,
            start_time=self.session_start_time,
            end_time=self.session_end_time or datetime.datetime.now(),
            total_time=stats["total_time"],
            session_wpm=stats["wpm"],
            session_cpm=stats["cpm"],
            expected_chars=stats["expected_chars"],
            actual_chars=stats["actual_chars"],
            errors=stats["errors"],
            accuracy=stats["accuracy"],
        )
        
        return session_manager.create_session(session)
    
    def save_session_with_manager(self, session_manager) -> int:
        """
        Calculate stats and save session with the provided manager.
        
        Args:
            session_manager: PracticeSessionManager instance
            
        Returns:
            Created session ID
            
        Raises:
            ValueError: If session cannot be saved
        """
        stats = self._calculate_stats()
        return self.save_session(stats, session_manager)
