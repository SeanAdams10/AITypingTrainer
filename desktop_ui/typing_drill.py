"""
TypingDrillScreen - Interactive typing practice UI with real-time feedback.
Implements full typing drill functionality including timing, statistics, and session persistence.
"""

import datetime
import os
import sys
import time
from typing import Any, Dict, List, Optional

# Add project root to path for direct script execution
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPalette, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Remove all legacy imports and usage
# Use only:
from models.session import Session
from models.session_manager import SessionManager


class CompletionDialog(QDialog):
    """
    Dialog shown when the typing session is completed.
    Displays typing statistics and provides options to retry or close.
    """

    def __init__(self, stats: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Typing Session Completed")
        self.setMinimumSize(400, 350)  # Increased height to accommodate save status
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
        self._add_stat_row(stats_grid, 3, "Efficiency:", f"{stats['efficiency']:.1f}%")
        self._add_stat_row(stats_grid, 4, "Correctness:", f"{stats['correctness']:.1f}%")
        self._add_stat_row(stats_grid, 5, "Errors:", f"{stats['errors']}")
        self._add_stat_row(stats_grid, 6, "Time:", f"{stats['total_time']:.1f} seconds")

        layout.addLayout(stats_grid)

        # Add session save status info
        save_status_layout = QVBoxLayout()
        save_status_label = QLabel("<h3>Session Save Status</h3>")
        save_status_label.setAlignment(Qt.AlignCenter)
        save_status_layout.addWidget(save_status_label)

        if stats.get("session_id"):
            status_text = f"<span style='color:green'>Session saved successfully! (ID: {stats['session_id']})</span>"
        elif stats.get("save_error"):
            status_text = (
                f"<span style='color:red'>Error saving session: {stats['save_error']}</span>"
            )
        else:
            status_text = (
                "<span style='color:orange'>Session not saved (no database connection)</span>"
            )

        status_info = QLabel(status_text)
        status_info.setAlignment(Qt.AlignCenter)
        status_info.setWordWrap(True)
        save_status_layout.addWidget(status_info)

        layout.addLayout(save_status_layout)
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Buttons
        button_layout = QHBoxLayout()

        retry_button = QPushButton("&Retry")  # & creates Alt+R shortcut
        retry_button.setToolTip("Retry typing session (Alt+R)")
        retry_button.clicked.connect(self._on_retry)

        close_button = QPushButton("&Close")  # & creates Alt+C shortcut
        close_button.setToolTip("Close typing session (Alt+C)")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)  # Make it the default button (respond to Enter key)
        close_button.setFocus()  # Give it focus initially

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
        db_manager: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Typing Drill")
        self.setMinimumSize(800, 600)  # As per requirements
        self.setModal(True)

        # Move to center of screen (per requirements)
        # Remove context help button from dialog window
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Store parameters
        self.snippet_id: int = snippet_id
        self.start: int = start
        self.end: int = end
        self.content: str = content
        self.db_manager = db_manager

        # Initialize typing state
        self.timer_running: bool = False
        self.start_time: float = 0.0
        self.elapsed_time: float = 0.0
        self.typed_chars: int = 0
        self.errors: int = 0
        self.error_positions: List[int] = []
        self.completion_dialog: Optional[CompletionDialog] = None

        # Initialize tracking lists for session data
        self.keystrokes: List[Dict[str, Any]] = []
        self.error_records: List[Dict[str, Any]] = []
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
        result = content.replace(" ", "␣")  # Visible space character

        # Replace tabs with visible tab character
        result = result.replace("\t", "⮾")  # Tab symbol

        # Replace newlines with return symbol
        result = result.replace("\n", "↵\n")  # Return symbol + actual newline

        # Make underscores more visible by adding background
        result = result.replace("_", "_")

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
        current_text = self.typing_input.toPlainText()

        # Start timer on first keystroke
        if not self.timer_running and len(current_text) > 0:
            self.timer_running = True
            self.start_time = time.time()

        # Get the current cursor position
        cursor = self.typing_input.textCursor()
        current_pos = cursor.position()

        # Record keystroke data for all changes, including backspaces
        now = datetime.datetime.now()

        # Calculate time since previous keystroke
        time_since_previous = 0
        if self.keystrokes:
            last_keystroke = self.keystrokes[-1]
            last_time = last_keystroke["timestamp"]
            delta_ms = int((now - last_time).total_seconds() * 1000)
            time_since_previous = delta_ms

        # Determine if this was a backspace or delete
        is_backspace = False
        if len(current_text) < self.typed_chars:
            # Text got shorter - backspace or delete was pressed
            deleted_pos = current_pos  # Position where character was deleted
            is_backspace = True

            # Create a keystroke record for the backspace (using fields expected by KeystrokeInputData)
            keystroke = {
                "char_position": deleted_pos,
                "char_typed": "\b",  # Backspace character
                "expected_char": self.content[deleted_pos]
                if deleted_pos < len(self.content)
                else "",
                "timestamp": now,
                "time_since_previous": time_since_previous,
                "is_correct": False,  # Backspaces are always errors
                "is_backspace": True,  # Extra field for our internal tracking
            }
            self.keystrokes.append(keystroke)

            # Log the backspace keystroke
            import logging

            logging.debug(
                f"Recorded BACKSPACE at position {deleted_pos}, time_since_previous={time_since_previous}ms"
            )

        # Handle regular character input (including when backspace was used but we have new text)
        if len(current_text) > 0 and (not is_backspace or len(current_text) > self.typed_chars - 1):
            new_char_pos = len(current_text) - 1
            typed_char = current_text[new_char_pos] if new_char_pos < len(current_text) else ""
            expected_char = self.content[new_char_pos] if new_char_pos < len(self.content) else ""

            # Only record if this is a new character (not part of backspace handling)
            if not is_backspace or new_char_pos >= self.typed_chars:
                is_correct = typed_char == expected_char

                # Create keystroke with fields matching KeystrokeInputData
                keystroke = {
                    "char_position": new_char_pos,
                    "char_typed": typed_char,
                    "expected_char": expected_char,
                    "timestamp": now,
                    "time_since_previous": time_since_previous,
                    "is_correct": is_correct,
                    "is_backspace": False,  # Extra field for our internal tracking
                }
                self.keystrokes.append(keystroke)

                # Log keystroke for debugging
                import logging

                logging.debug(
                    f"Recorded keystroke: pos={new_char_pos}, char='{typed_char}', expected='{expected_char}', is_correct={is_correct}, time_since_previous={time_since_previous}ms"
                )

        # Update character count
        self.typed_chars = len(current_text)

        # Process the typing input
        self._process_typing_input()

        # Calculate and update stats
        self._update_stats()

        # Check for completion
        if self.typed_chars >= len(self.content):
            self._check_completion()
            return

    def _process_typing_input(self) -> None:
        """
        Process the current typing input, check progress, and update UI.

        This method handles checking the current typing input against expected content,
        updates progress tracking, and checks for completion.
        """
        current_text = self.typing_input.toPlainText()

        # Update progress bar
        progress = min(100, int(len(current_text) / len(self.content) * 100))
        self.progress_bar.setValue(progress)

        # Update text highlighting (only once)
        self._update_highlighting(current_text)

        # Note: Completion check moved exclusively to _on_text_changed to prevent duplicate dialog

    def _update_highlighting(self, current_text: str) -> None:
        """
        Update the display text with highlighting based on typing accuracy.

        Args:
            current_text: Current text input by the user
        """
        # Block signals temporarily to avoid recursive calls
        self.display_text.blockSignals(True)

        # Create a new QTextDocument for better performance
        # Remove document.clone() and use self.display_text.document() directly if needed
        document = self.display_text.document()

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

                # Record error data for analysis
                error_record = {
                    "char_position": i,
                    "expected_char": self.content[i],
                    "typed_char": char,
                }
                self.error_records.append(error_record)

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
        """Check and handle completion of the typing session. Only save one row per session unless user retries."""
        import logging

        logging.debug("Entering _check_completion")
        if getattr(self, "session_completed", False):
            logging.warning("Session already completed, skipping save.")
            # Show dialog with last stats (do not resave)
            self._show_completion_dialog(self._calculate_stats())
            return
        # Stop the timer
        self.timer_running = False
        self.session_end_time = datetime.datetime.now()
        # Mark typing as complete and disable input
        self.typing_input.setReadOnly(True)
        palette = self.typing_input.palette()
        palette.setColor(QPalette.Base, QColor(230, 255, 230))  # Light green
        self.typing_input.setPalette(palette)
        # Calculate final stats
        stats = self._calculate_stats()
        # Initialize session save status
        self.session_save_status = "Session not saved (no database connection)"
        # Save session data if we have a database manager
        if self.db_manager:
            try:
                # Use the new SessionManager for session persistence
                session_manager = SessionManager(self.db_manager)
                session_id = self.save_session(stats, session_manager)
                stats["session_id"] = session_id
                stats["save_status"] = self.session_save_status
                self.session_completed = True
                logging.info(f"Session saved with session_id={session_id}")
            except Exception as e:
                error_msg = str(e)
                stats["save_error"] = error_msg
                self.session_save_status = f"Error saving session: {error_msg}"
                stats["save_status"] = self.session_save_status
        else:
            self.session_completed = True
        # Show completion dialog
        self._show_completion_dialog(stats)
        logging.debug("Exiting _check_completion")

    def _calculate_stats(self) -> Dict[str, Any]:
        """
        Calculate final statistics for the typing session.

        Accuracy is calculated as efficiency * correctness, where:
        - efficiency = expected characters / keystrokes excluding backspaces
        - correctness = correct characters in final text / expected characters

        Returns:
            Dict containing session statistics including WPM, CPM, accuracy, and errors.
        """
        # Calculate total stats for the session
        total_time = time.time() - self.start_time if self.start_time > 0 else 0.0
        if total_time == 0:
            total_time = 0.1  # Avoid division by zero

        # Calculate WPM: (chars typed / 5) / minutes
        minutes = total_time / 60.0
        wpm = (self.typed_chars / 5.0) / minutes

        # Calculate CPM: chars typed / minutes
        cpm = self.typed_chars / minutes

        # Calculate keystrokes excluding backspaces
        expected_chars = len(self.content)

        # Count keystrokes
        keystrokes_excluding_backspaces = 0  # For efficiency calculation
        actual_chars_count = 0  # For actual_chars metric (all keystrokes excluding backspaces)
        backspace_count = 0

        for ks in self.keystrokes:
            if ks.get("char_typed") == "\b":
                backspace_count += 1
            else:
                keystrokes_excluding_backspaces += 1
                actual_chars_count += 1  # Count all non-backspace keystrokes

        # Calculate total keystrokes (including backspaces)
        total_keystrokes = len(self.keystrokes)

        # Avoid division by zero
        if keystrokes_excluding_backspaces == 0:
            keystrokes_excluding_backspaces = 1

        # Calculate efficiency as a percentage (0.0 to 100.0)
        # This is the ratio of expected characters to actual keystrokes (excluding backspaces)
        efficiency = min(100.0, (expected_chars / keystrokes_excluding_backspaces) * 100.0)

        # Calculate for correctness: correct chars in final text / expected chars
        current_text = self.typing_input.toPlainText()
        correct_chars = sum(1 for a, b in zip(current_text, self.content, strict=False) if a == b)
        # Correctness is also capped at 100% (cannot have more correct chars than expected)
        correctness = min(
            100.0, (correct_chars / expected_chars) * 100.0 if expected_chars > 0 else 100.0
        )

        # Calculate final accuracy as efficiency * correctness / 100 (as percentages)
        # This will naturally be capped at 100% since both inputs are capped
        accuracy = (efficiency * correctness) / 100.0

        # Record session end time
        self.session_end_time = datetime.datetime.now()

        return {
            "wpm": wpm,
            "cpm": cpm,
            "accuracy": accuracy,
            "efficiency": efficiency,
            "correctness": correctness,
            "errors": self.errors,
            "total_time": total_time,
            "total_keystrokes": total_keystrokes,
            "backspace_count": backspace_count,
            "expected_chars": expected_chars,
            "actual_chars": actual_chars_count,  # Using the count of all keystrokes excluding backspaces
            "correct_chars": correct_chars,
        }

    def _show_completion_dialog(self, stats: Dict[str, Any]) -> None:
        """Show completion dialog and handle user's choice to retry or close.

        Args:
            stats: Dictionary containing typing session statistics

        The CompletionDialog returns:
        - 2: When the Retry button is clicked
        - QDialog.Accepted (1): When the Close button is clicked (it's connected to accept())
        - QDialog.Rejected (0): When dialog is closed by other means (X button, Esc key)
        """
        self.completion_dialog = CompletionDialog(stats, self)
        result = self.completion_dialog.exec_()

        if result == 2:  # Custom return code for retry button
            # User clicked Retry button, reset session but keep drill screen open
            self._reset_session()
        else:  # QDialog.Accepted (1) or QDialog.Rejected (0) - any form of Close
            # User clicked Close button or closed dialog - close the entire drill screen
            self.accept()

    def _reset_session(self) -> None:
        """
        Reset the typing session to start over. Allows a new row to be saved for retry.
        """
        import logging

        # Reset state
        self.timer_running = False
        self.start_time = 0.0
        self.elapsed_time = 0.0
        self.typed_chars = 0
        self.errors = 0
        self.error_positions = []
        # Reset keystroke and error tracking
        self.keystrokes = []
        self.error_records = []
        self.session_start_time = datetime.datetime.now()
        self.session_end_time = None
        self.session_completed = False
        logging.info("Session reset for retry.")
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

    def save_session(self, stats: dict, session_manager) -> str:
        import logging

        logging.debug("Entering save_session with stats: %s", stats)
        session_id = None
        try:
            # Create and save session using new Session model
            session = Session(
                snippet_id=self.snippet_id,
                snippet_index_start=self.start,
                snippet_index_end=self.end,
                content=self.content,
                start_time=self.session_start_time,
                end_time=self.session_end_time or datetime.datetime.now(),
                actual_chars=stats["actual_chars"],
                errors=stats["errors"],
            )
            logging.debug("Session object created: %s", session)
            # Save the session and get session_id
            session_id = session_manager.save_session(session)
            logging.debug("Session saved with ID: %s", session_id)
            self.session_save_status = "Session data saved successfully"
        except Exception as e:
            error_message = f"Error saving session data: {str(e)}"
            logging.error("Exception in save_session: %s", e)
            self.session_save_status = error_message
            raise ValueError(error_message) from e
        logging.debug("Exiting save_session with session_id: %s", session_id)
        return session_id

    def save_session_data(self, session_manager, session_id: str, keystrokes, error_records):
        # This method is now a no-op or can be removed, as keystrokes are not saved in the new model
        return True
