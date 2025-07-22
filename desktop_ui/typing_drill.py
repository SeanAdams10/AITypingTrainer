# ruff: noqa: E501
"""
TypingDrillScreen - Interactive typing practice UI with real-time feedback.
Implements full typing drill functionality including timing, statistics, and session persistence.
"""

# Move all imports to the top of the file for PEP8 compliance
import datetime
import logging
import time
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPalette, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models.keyboard_manager import KeyboardManager, KeyboardNotFound
from models.keystroke import Keystroke
from models.keystroke_manager import KeystrokeManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager
from models.session import Session
from models.session_manager import SessionManager
from models.user_manager import UserManager, UserNotFound

if TYPE_CHECKING:
    from db.database_manager import DatabaseManager


class PersistSummary(QDialog):
    """
    Dialog shown after persistence operations complete.
    Displays the results of saving session data including record counts.
    """

    def __init__(self, persist_results: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        """
        Initialize the persistence summary dialog.

        Args:
            persist_results (Dict[str, Any]): Results of persistence operations.
            parent (Optional[QWidget]): Parent widget for the dialog.
        """
        super().__init__(parent)
        self.setWindowTitle("Session Saved")
        self.setMinimumSize(400, 300)
        self.setModal(True)

        # Store results
        self.persist_results = persist_results

        # Create layout
        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("<h2>Session Data Saved</h2>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Results grid
        results_grid = QGridLayout()
        row = 0

        # Session save status
        if persist_results.get("session_saved"):
            self._add_result_row(results_grid, row, "Session:", "✓ Saved successfully")
            row += 1
        else:
            error_msg = persist_results.get("session_error", "Unknown error")
            self._add_result_row(results_grid, row, "Session:", f"✗ Failed: {error_msg}")
            row += 1

        # Keystroke save status
        keystroke_count = persist_results.get("keystroke_count", 0)
        if persist_results.get("keystrokes_saved"):
            self._add_result_row(results_grid, row, "Keystrokes:", f"✓ {keystroke_count} saved")
            row += 1
        else:
            error_msg = persist_results.get("keystroke_error", "Unknown error")
            self._add_result_row(results_grid, row, "Keystrokes:", f"✗ Failed: {error_msg}")
            row += 1

        # N-gram save status
        ngram_count = persist_results.get("ngram_count", 0)
        if persist_results.get("ngrams_saved"):
            self._add_result_row(results_grid, row, "N-grams:", f"✓ {ngram_count} saved")
            row += 1
        else:
            error_msg = persist_results.get("ngram_error", "Unknown error")
            self._add_result_row(results_grid, row, "N-grams:", f"✗ Failed: {error_msg}")
            row += 1

        layout.addLayout(results_grid)
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Close button
        button_layout = QHBoxLayout()
        close_button = QPushButton("&Close")
        close_button.setToolTip("Close persistence summary (Alt+C)")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        close_button.setFocus()

        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

    def _add_result_row(self, grid: QGridLayout, row: int, label: str, status: str) -> None:
        """
        Add a row to the results grid with label and status.

        Args:
            grid (QGridLayout): The grid layout to add the row to.
            row (int): The row index.
            label (str): The label text.
            status (str): The status text.
        """
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Arial", 10, QFont.Bold))
        status_widget = QLabel(status)
        status_widget.setFont(QFont("Arial", 10))

        # Set color based on status
        if status.startswith("✓"):
            status_widget.setStyleSheet("color: green;")
        elif status.startswith("✗"):
            status_widget.setStyleSheet("color: red;")

        grid.addWidget(label_widget, row, 0)
        grid.addWidget(status_widget, row, 1)


class CompletionDialog(QDialog):
    """
    Dialog shown when the typing session is completed.
    Displays typing statistics and provides options to retry or close.
    """

    def __init__(self, stats: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        """
        Initialize the completion dialog with typing statistics and parent widget.

        Args:
            stats (Dict[str, Any]): Typing statistics to display.
            parent (Optional[QWidget]): Parent widget for the dialog.
        """
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
        results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        save_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        save_status_layout.addWidget(save_status_label)

        if stats.get("session_id"):
            # Break up long line for status_text
            status_text = (
                f"<span style='color:green'>Session saved successfully! "
                f"(ID: {stats['session_id']})</span>"
            )
        elif stats.get("save_error"):
            status_text = (
                f"<span style='color:red'>Error saving session: {stats['save_error']}</span>"
            )
        else:
            status_text = (
                "<span style='color:orange'>Session not saved (no database connection)</span>"
            )

        status_info = QLabel(status_text)
        status_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        """
        Add a row to the stats grid with label and value.

        Args:
            grid (QGridLayout): The grid layout to add the row to.
            row (int): The row index.
            label (str): The label text.
            value (str): The value text.
        """
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Arial", 10, QFont.Bold))
        value_widget = QLabel(value)
        value_widget.setFont(QFont("Arial", 10))

        grid.addWidget(label_widget, row, 0)
        grid.addWidget(value_widget, row, 1)

    def _on_retry(self) -> None:
        """
        Handle retry button click.
        """
        self.done(2)  # Custom return code for retry


class TypingDrillScreen(QDialog):
    """
    TypingDrillScreen handles the typing drill UI and session persistence for desktop.
    Implements real-time feedback, timing, statistics, and session recording.

    Args:
        snippet_id (int): ID of the snippet being practiced (-1 for manual text)
        start (int): Starting index in the snippet
        end (int): Ending index in the snippet
        content (str): Content to type (substring of snippet between start and end)
        db_manager (Optional[Any]): Database manager instance
        parent (Optional[QWidget]): Parent widget
    """

    def __init__(
        self,
        snippet_id: int,
        start: int,
        end: int,
        content: str,
        db_manager: Optional["DatabaseManager"] = None,
        user_id: Optional[str] = None,
        keyboard_id: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Initialize the TypingDrillScreen dialog and session state.

        Args:
            snippet_id (int): ID of the snippet being practiced (-1 for manual text)
            start (int): Starting index in the snippet
            end (int): Ending index in the snippet
            content (str): Content to type (substring of snippet between start and end)
            db_manager (Optional[DatabaseManager]): Database manager instance
            user_id (Optional[str]): ID of the current user
            keyboard_id (Optional[str]): ID of the keyboard being used
            parent (Optional[QWidget]): Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Typing Drill")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        # Fix setWindowFlags to use WindowFlags type
        # Use int() cast for WindowFlags to avoid type error
        flags = int(self.windowFlags()) & ~int(Qt.WindowType.WindowContextHelpButtonHint)
        self.setWindowFlags(Qt.WindowType(flags))

        # Store parameters
        self.snippet_id: int = snippet_id
        self.start: int = start
        self.end: int = end
        self.content: str = content
        self.db_manager = db_manager
        self.user_id = user_id
        self.keyboard_id = keyboard_id

        # Create the SessionManager object local to this form
        self.session_manager = SessionManager(self.db_manager) if self.db_manager else None

        # Create the Session object for this drill (local property)
        self.session: Session = self._create_new_session()

        # Store user and keyboard IDs in session if provided
        if user_id:
            self.session.user_id = user_id
        if keyboard_id:
            self.session.keyboard_id = keyboard_id

        # Initialize user and keyboard managers and fetch objects if DB is available
        self.current_user = None
        self.current_keyboard = None
        if self.db_manager:
            self.user_manager = UserManager(self.db_manager)
            self.keyboard_manager = KeyboardManager(self.db_manager)

            # Fetch user and keyboard information
            try:
                if user_id:
                    self.current_user = self.user_manager.get_user_by_id(user_id)
                if keyboard_id:
                    self.current_keyboard = self.keyboard_manager.get_keyboard_by_id(keyboard_id)
            except (UserNotFound, KeyboardNotFound, Exception) as e:
                # Log the error but continue - status bar will show limited info
                print(f"Error loading user or keyboard: {str(e)}")

        # Initialize typing state
        self.timer_running: bool = False
        self.start_time: float = 0.0
        self.elapsed_time: float = 0.0
        self.completion_dialog: Optional[CompletionDialog] = None

        # Tracking lists for session data
        self.keystrokes: List[Dict[str, Any]] = []
        self.error_records: List[Dict[str, Any]] = []
        self.session_start_time: datetime.datetime = datetime.datetime.now()
        self.session_end_time: Optional[datetime.datetime] = None

        # Preprocess content to handle special characters
        self.display_content: str = self._preprocess_content(content)

        # Setup UI Components
        self._setup_ui()

        # Create timer for updating stats
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(100)  # Update every 100ms

        # Update status bar with user and keyboard info
        self._update_status_bar()

        # Set focus to typing input
        self.typing_input.setFocus()

        # Save last used keyboard (LSTKBD) setting for this user
        if self.user_id and self.keyboard_id and self.db_manager:
            try:
                from models.setting_manager import SettingManager

                setting_manager = SettingManager(self.db_manager)
                # related_entity_id is user_id, value is keyboard_id
                setting = setting_manager.get_setting(
                    "LSTKBD", str(self.user_id), default_value=str(self.keyboard_id)
                )
                setting.setting_value = str(self.keyboard_id)
                setting_manager.save_setting(setting)
            except Exception as e:
                # Log but do not interrupt UI
                logging.warning(f"Failed to save LSTKBD setting: {e}")

        # Move attribute definitions to __init__
        self.errors = 0
        self.session_save_status = ""
        self.session_completed = False
        self.ngram_manager = NGramManager(self.db_manager)
        self.ngram_analysis = NGramAnalyticsService(self.db_manager, self.ngram_manager)

    def _update_status_bar(self) -> None:
        """
        Update status bar with user and keyboard information.
        """
        status_text = ""
        if self.current_user:
            # Use first_name and surname instead of username
            user_name = f"{self.current_user.first_name} {self.current_user.surname}".strip()
            user_display = f"User: {user_name or self.current_user.user_id}"
            status_text += user_display
        if self.current_keyboard:
            if status_text:
                status_text += " | "
            keyboard_display = f"Keyboard: {self.current_keyboard.keyboard_name or self.current_keyboard.keyboard_id}"
            status_text += keyboard_display
        if status_text:
            self.status_bar.showMessage(status_text)
        else:
            self.status_bar.showMessage("No user or keyboard selected")

    def _create_new_session(self) -> Session:
        """
        Helper to create a new Session object for this typing drill.

        Returns:
            Session: A new Session instance with the current configuration.
        """

        def ensure_uuid(val):
            try:
                return str(uuid.UUID(str(val)))
            except Exception:
                return str(uuid.uuid4())

        snippet_id = ensure_uuid(self.snippet_id)
        user_id = ensure_uuid(self.user_id) if self.user_id else str(uuid.uuid4())
        keyboard_id = ensure_uuid(self.keyboard_id) if self.keyboard_id else str(uuid.uuid4())

        return Session(
            session_id=str(uuid.uuid4()),
            snippet_id=snippet_id,
            snippet_index_start=self.start,
            snippet_index_end=self.end,
            content=self.content,
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now(),
            actual_chars=0,
            errors=0,
            user_id=user_id,
            keyboard_id=keyboard_id,
        )

    def _preprocess_content(self, content: str) -> str:
        """
        Preprocess content to make whitespace and special characters visible for display.

        Args:
            content (str): Original text content to preprocess.

        Returns:
            str: Preprocessed content with visible whitespace markers for display.
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
        """
        Set up the UI components for the typing drill screen.

        Returns:
            None: This method does not return a value.
        """
        # Main layout
        main_layout = QVBoxLayout(self)

        # Create status bar for user and keyboard info
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        main_layout.addWidget(self.status_bar)

        # Title
        title_label = QLabel("<h1>Typing Drill</h1>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Stats area (split into two rows for better fit)
        stats_widget = QWidget()
        stats_grid = QGridLayout(stats_widget)
        stats_grid.setContentsMargins(0, 0, 0, 0)
        stats_grid.setHorizontalSpacing(20)
        stats_grid.setVerticalSpacing(2)

        # First row: WPM, CPM, Accuracy, Time
        self.wpm_label = QLabel("WPM: 0.0")
        self.wpm_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_grid.addWidget(self.wpm_label, 0, 0)

        self.cpm_label = QLabel("CPM: 0")
        self.cpm_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_grid.addWidget(self.cpm_label, 0, 1)

        self.accuracy_label = QLabel("Accuracy: 100%")
        self.accuracy_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_grid.addWidget(self.accuracy_label, 0, 2)

        self.timer_label = QLabel("Time: 0.0s")
        self.timer_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_grid.addWidget(self.timer_label, 0, 3)

        # Second row: Efficiency, Correctness, Errors, ms/keystroke
        self.efficiency_label = QLabel("Efficiency: 100%")
        self.efficiency_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_grid.addWidget(self.efficiency_label, 1, 0)

        self.correctness_label = QLabel("Correctness: 100%")
        self.correctness_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_grid.addWidget(self.correctness_label, 1, 1)

        self.errors_label = QLabel("Errors: 0")
        self.errors_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_grid.addWidget(self.errors_label, 1, 2)

        self.ms_per_keystroke_label = QLabel("ms/keystroke: 0.0")
        self.ms_per_keystroke_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_grid.addWidget(self.ms_per_keystroke_label, 1, 3)

        main_layout.addWidget(stats_widget)

        # Text to type (display)
        main_layout.addWidget(QLabel("<h3>Type the following text:</h3>"))

        self.display_text = QTextEdit()
        self.display_text.setReadOnly(True)
        self.display_text.setFont(QFont("Courier New", 12))
        self.display_text.setText(self.display_content)
        self.display_text.setMinimumHeight(150)
        main_layout.addWidget(self.display_text)

        # Progress bars container
        progress_container = QVBoxLayout()

        # Character progress bar
        char_progress_layout = QHBoxLayout()
        char_progress_layout.addWidget(QLabel("Progress: "))
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, len(self.content))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        char_progress_layout.addWidget(self.progress_bar, 1)
        progress_container.addLayout(char_progress_layout)

        # Error progress bar
        error_progress_layout = QHBoxLayout()
        error_progress_layout.addWidget(QLabel("Errors: "))
        self.error_progress = QProgressBar()
        self.error_progress.setTextVisible(True)
        self.error_progress.setRange(0, int(len(self.content) * 0.05))  # 5% threshold
        self.error_progress.setValue(0)
        self.error_progress.setFormat("%p%")
        self.error_progress.setStyleSheet("""
            QProgressBar::chunk {
                background-color: #ff6b6b;
            }
        """)
        error_progress_layout.addWidget(self.error_progress, 1)
        progress_container.addLayout(error_progress_layout)

        # Speed progress bar (WPM) - Range based on 2x target speed from keyboard
        speed_progress_layout = QHBoxLayout()
        speed_progress_layout.addWidget(QLabel("Speed (WPM): "))
        self.speed_progress = QProgressBar()
        self.speed_progress.setTextVisible(True)
        
        # Calculate target WPM from keyboard's target_ms_per_keystroke
        target_wpm = 60  # Default fallback
        if self.current_keyboard and hasattr(self.current_keyboard, 'target_ms_per_keystroke'):
            # Convert ms per keystroke to WPM (assuming 5 characters per word)
            chars_per_minute = 60000 / self.current_keyboard.target_ms_per_keystroke
            target_wpm = chars_per_minute / 5
        
        # Set range to 2x target WPM
        max_wpm = int(target_wpm * 2)
        self.speed_progress.setRange(0, max_wpm)
        self.speed_progress.setValue(0)
        self.speed_progress.setFormat("%v WPM")
        self.speed_progress.setStyleSheet("""
            QProgressBar::chunk {
                background-color: #4e9af1;
            }
        """)
        speed_progress_layout.addWidget(self.speed_progress, 1)
        progress_container.addLayout(speed_progress_layout)
        
        # Store target WPM for later use in color calculations
        self.target_wpm = target_wpm

        main_layout.addLayout(progress_container)

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

        # Add type annotation for error_positions as a class attribute
        self.error_positions: list[int] = []

    def _on_text_changed(self) -> None:
        """
        Handle text changes in the typing input and update session state, stats, and UI.

        Returns:
            None: This method does not return a value.
        """
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
        # Fix typed_chars type errors by using len(self.typing_input.toPlainText())
        current_typed_len = len(self.typing_input.toPlainText())
        if len(current_text) < current_typed_len:
            # Text got shorter - backspace or delete was pressed
            deleted_pos = current_pos  # Position where character was deleted
            is_backspace = True

            # Create a keystroke record for the backspace
            # (using fields expected by KeystrokeInputData)
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
            logging.debug(
                "Recorded BACKSPACE at position %d, time_since_previous=%dms",
                deleted_pos,
                time_since_previous,
            )

        # Handle regular character input (including when backspace was used but we have new text)
        if len(current_text) > 0 and (
            not is_backspace or len(current_text) > current_typed_len - 1
        ):
            new_char_pos = len(current_text) - 1
            typed_char = current_text[new_char_pos] if new_char_pos < len(current_text) else ""
            expected_char = self.content[new_char_pos] if new_char_pos < len(self.content) else ""

            # Only record if this is a new character (not part of backspace handling)
            if not is_backspace or new_char_pos >= current_typed_len:
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
                logging.debug(
                    "Recorded keystroke: pos=%d, char='%s', expected='%s', is_correct=%s, time_since_previous=%dms",
                    new_char_pos,
                    typed_char,
                    expected_char,
                    is_correct,
                    time_since_previous,
                )

        # Update character count
        # self.typed_chars = len(current_text)  # Remove this line
        self.session.actual_chars = len(current_text)

        # Process the typing input
        self._process_typing_input()

        # Calculate and update stats
        self._update_stats()

        # Check for completion
        if self.session.actual_chars >= len(self.content):
            self.session.end_time = datetime.datetime.now()
            self._check_completion()
            return

    def _process_typing_input(self) -> None:
        """
        Process the current typing input, check progress, and update UI highlighting and
        progress bar.

        Returns:
            None: This method does not return a value.
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
        Handles newlines and special characters correctly.

        Args:
            current_text (str): Current text input by the user.

        Returns:
            None: This method does not return a value.
        """
        # Block signals temporarily to avoid recursive updates
        self.display_text.blockSignals(True)

        # Create a new document for the display
        document = QTextDocument()
        document.setDefaultFont(QFont("Courier New", 12))
        cursor = QTextCursor(document)

        # Set up character formats
        correct_format = QTextCharFormat()
        correct_format.setForeground(QColor(0, 128, 0))  # Green
        correct_format.setBackground(QColor(220, 255, 220))  # Light green background

        error_format = QTextCharFormat()
        error_format.setForeground(QColor(255, 0, 0))  # Red
        error_format.setBackground(QColor(255, 220, 220))  # Light red background

        # Clear previous error positions
        self.error_positions = []

        # Process each character in the expected content
        for i in range(len(self.content)):
            # Get the current character from both texts
            expected_char = self.content[i]
            typed_char = current_text[i] if i < len(current_text) else ""

            # Determine if this character is correct
            is_correct = typed_char == expected_char

            # Apply the appropriate format
            cursor.insertText(expected_char, correct_format if is_correct else error_format)

            # Record errors
            if not is_correct and typed_char:
                self.error_positions.append(i)
                self.error_records.append(
                    {
                        "char_position": i,
                        "expected_char": expected_char,
                        "typed_char": typed_char,
                    }
                )

        # Update the display
        self.display_text.setDocument(document)
        self.display_text.blockSignals(False)

        # Ensure the view updates
        self.display_text.viewport().update()

        # Update the error count
        self.errors = len(self.error_positions)

    def _update_timer(self) -> None:
        """
        Update timer and stats display during the typing session.

        Returns:
            None: This method does not return a value.
        """
        if self.timer_running:
            self.elapsed_time = time.time() - self.start_time
            self.timer_label.setText(f"Time: {self.elapsed_time:.1f}s")
            self._update_stats()

    def _calculate_efficiency(self, total_keystrokes: int) -> float:
        """Calculate typing efficiency (ratio of expected to actual keystrokes)."""
        if total_keystrokes == 0:
            return 100.0
        expected_keystrokes = len(self.content)
        return (
            min(100.0, (expected_keystrokes / total_keystrokes) * 100)
            if total_keystrokes > 0
            else 100.0
        )

    def _calculate_correctness(self, correct_chars: int, total_typed: int) -> float:
        """Calculate typing correctness (ratio of correct to total characters)."""
        return (correct_chars / total_typed * 100) if total_typed > 0 else 100.0

    def _calculate_ms_per_keystroke(self) -> float:
        """Calculate milliseconds per keystroke."""
        if not self.keystrokes or self.elapsed_time <= 0:
            return 0.0
        return (self.elapsed_time * 1000) / len(self.keystrokes)

    def _update_progress_bars(self, wpm: float, errors: int):
        """Update all progress bars with current values."""
        # Character progress
        typed_chars = len(self.typing_input.toPlainText())
        self.progress_bar.setValue(typed_chars)

        # Error progress (shows percentage of 5% threshold)
        error_percent = (errors / (len(self.content) * 0.05)) * 100
        self.error_progress.setValue(int(error_percent * self.error_progress.maximum() / 100))

        # Update error progress bar color based on threshold
        if error_percent >= 100:  # Exceeded error threshold
            self.error_progress.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #ff0000;
                }
            """)
        else:
            self.error_progress.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #ff6b6b;
                }
            """)

        # Speed progress bar with color coding based on target speed
        self.speed_progress.setValue(int(wpm))
        # Use target speed from keyboard for color thresholds
        target_speed_threshold = getattr(self, 'target_wpm', 60) * 0.75  # 75% of target
        if wpm < target_speed_threshold:  # Below 75% of target
            color = "#ffa500"  # Orange
        else:  # At or above target
            color = "#4caf50"  # Green
        self.speed_progress.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)

    def _update_stats(self) -> None:
        """
        Calculate and update all typing statistics for the session in real-time.

        Returns:
            None: This method does not return a value.
        """
        if not self.timer_running or self.elapsed_time < 0.1:
            return

        # Calculate basic metrics
        minutes = self.elapsed_time / 60.0
        typed_text = self.typing_input.toPlainText()
        total_typed = len(typed_text)
        correct_chars = total_typed - len(self.error_positions)

        # Calculate WPM and CPM
        wpm = (total_typed / 5.0) / minutes if minutes > 0 else 0
        cpm = total_typed / minutes if minutes > 0 else 0

        # Calculate advanced metrics
        accuracy = (
            self._calculate_correctness(correct_chars, total_typed) if total_typed > 0 else 100.0
        )
        efficiency = self._calculate_efficiency(len(self.keystrokes))
        ms_per_keystroke = self._calculate_ms_per_keystroke()

        # Update session object
        self.session.actual_chars = total_typed
        self.session.errors = len(self.error_positions)
        self.session.end_time = datetime.datetime.now()

        # Update UI
        self.wpm_label.setText(f"WPM: {wpm:.1f}")
        self.cpm_label.setText(f"CPM: {int(cpm)}")
        self.accuracy_label.setText(f"Accuracy: {accuracy:.1f}%")
        self.efficiency_label.setText(f"Efficiency: {efficiency:.1f}%")
        self.correctness_label.setText(f"Correctness: {accuracy:.1f}%")
        self.errors_label.setText(f"Errors: {len(self.error_positions)}")
        self.ms_per_keystroke_label.setText(f"ms/keystroke: {ms_per_keystroke:.1f}")

        # Update progress bars
        self._update_progress_bars(wpm, len(self.error_positions))

    def _check_completion(self) -> None:
        """
        Check and handle completion of the typing session, including saving session data
        and showing completion dialog.

        Returns:
            None: This method does not return a value.
        """
        logging.debug("Entering _check_completion")
        if getattr(self, "session_completed", False):
            logging.warning("Session already completed, skipping save.")
            self._show_completion_dialog(self.session)
            return
        self.timer_running = False
        self.session.end_time = datetime.datetime.now()
        self.typing_input.setReadOnly(True)
        palette = self.typing_input.palette()
        palette.setColor(QPalette.Base, QColor(230, 255, 230))
        self.typing_input.setPalette(palette)
        self.session_save_status = "Session not saved (no database connection)"
        if self.session_manager is not None:
            try:
                success = self.save_session()
                if not success:
                    raise Exception("Session save failed (SessionManager returned False)")
                self.session_completed = True
                logging.info("Session saved with session_id=%s", self.session.session_id)
            except Exception as e:
                error_msg = str(e)
                self.session_save_status = f"Error saving session: {error_msg}"
                self.session_completed = True
        else:
            self.session_completed = True
        # Save last used keyboard (LSTKBD) for this user
        try:
            if self.user_id and self.keyboard_id and self.db_manager:
                from models.setting import Setting
                from models.setting_manager import SettingManager

                setting = Setting(
                    setting_type_id="LSTKBD",
                    setting_value=self.keyboard_id,
                    related_entity_id=self.user_id,
                )
                setting_manager = SettingManager(self.db_manager)
                setting_manager.save_setting(setting)
        except Exception as e:
            logging.warning(f"Failed to save LSTKBD setting: {e}")
        self._show_completion_dialog(self.session)
        logging.debug("Exiting _check_completion")

    def save_session(self) -> bool:
        """
        Save the session using the local Session object and session_manager.

        Returns:
            bool: True if the session was saved successfully, otherwise raises an exception.
        """
        logging.debug("Entering save_session with session: %s", self.session)
        try:
            if self.session_manager is None:
                raise ValueError("SessionManager is not initialized.")
            result = self.session_manager.save_session(self.session)
            if not result:
                raise Exception("SessionManager.save_session returned False")
            self.session_save_status = "Session data saved successfully"
            logging.debug("Session saved with ID: %s", self.session.session_id)

            # Automatically summarize session ngrams after successful save
            try:
                ngram_manager = NGramManager(self.db_manager)
                analytics_service = NGramAnalyticsService(self.db_manager, ngram_manager)
                records_inserted = analytics_service.summarize_session_ngrams()
                logging.info(
                    f"Session ngram summarization completed: {records_inserted} records inserted"
                )

                # Update speed summary after ngram summarization
                try:
                    catchup_results = analytics_service.catchup_speed_summary()
                    logging.info(
                        f"Speed summary catchup completed: {catchup_results.get('total_sessions', 0)} sessions processed"
                    )
                except Exception as catchup_error:
                    # Log the error but don't fail the session save
                    logging.warning(f"Failed to update speed summary: {str(catchup_error)}")

            except Exception as ngram_error:
                # Log the error but don't fail the session save
                logging.warning(f"Failed to summarize session ngrams: {str(ngram_error)}")

            return True
        except Exception as e:
            error_message = f"Error saving session data: {str(e)}"
            logging.error("Exception in save_session: %s", e)
            self.session_save_status = error_message
            raise ValueError(error_message) from e

    def _persist_session_data(self, session: Session) -> Dict[str, Any]:
        """
        Persist the session, keystrokes, and n-grams to the database and return a summary dict.
        """
        results = {
            "session_saved": False,
            "session_error": None,
            "keystrokes_saved": False,
            "keystroke_error": None,
            "keystroke_count": 0,
            "ngrams_saved": False,
            "ngram_error": None,
            "ngram_count": 0,
        }
        # Save session
        try:
            if self.session_manager is None:
                raise Exception("SessionManager not initialized")
            self.session_manager.save_session(session)
            results["session_saved"] = True
        except Exception as e:
            results["session_error"] = str(e)
            return results  # If session fails, skip the rest

        # Save keystrokes
        try:
            keystroke_manager = KeystrokeManager(self.db_manager)
            keystroke_objs = []
            for kdict in self.keystrokes:
                kdict["session_id"] = session.session_id
                # Map fields for Keystroke model
                kdict["keystroke_char"] = kdict.get("char_typed", kdict.get("keystroke_char", ""))
                kdict["expected_char"] = kdict.get("expected_char", "")
                kdict["keystroke_time"] = kdict.get("timestamp", datetime.datetime.now())
                kdict["is_error"] = not kdict.get("is_correct", True)
                keystroke_objs.append(Keystroke.from_dict(kdict))
            for k in keystroke_objs:
                keystroke_manager.add_keystroke(k)
            if not keystroke_manager.save_keystrokes():
                raise Exception("KeystrokeManager.save_keystrokes returned False")
            results["keystrokes_saved"] = True
            results["keystroke_count"] = len(keystroke_objs)
        except Exception as e:
            results["keystroke_error"] = str(e)
            return results

        # Generate and save n-grams
        try:
            ngram_manager = NGramManager(self.db_manager)
            ngram_total = 0
            for n in range(2, 21):
                ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystroke_objs, n)
                for ng in ngrams:
                    if ngram_manager.save_ngram(ng, session.session_id):
                        ngram_total += 1
            results["ngrams_saved"] = True
            results["ngram_count"] = ngram_total
        except Exception as e:
            results["ngram_error"] = str(e)

        # now do the summary of this.
        self.ngram_analysis.summarize_session_ngrams()
        self.ngram_analysis.add_speed_summary_for_session(session.session_id)

        return results

    def _show_completion_dialog(self, session: Session) -> None:
        """
        Show the completion dialog with the given session object and handle persistence.

        Args:
            session (Session): The Session object containing session results.

        Returns:
            None: This method does not return a value.
        """
        # Calculate final stats
        stats = self._calculate_stats()

        # Add session save status to stats
        stats["session_id"] = session.session_id if hasattr(session, "session_id") else None
        if hasattr(self, "session_save_status"):
            if "successfully" in self.session_save_status:
                stats["session_id"] = session.session_id
            else:
                stats["save_error"] = self.session_save_status

        # Show completion dialog with typing stats
        completion_dialog = CompletionDialog(stats, self)
        result = completion_dialog.exec_()

        if result == 2:  # Retry
            self._reset_session()
        elif result == QDialog.Accepted:  # Close
            # Perform persistence operations
            persist_results = self._persist_session_data(session)

            # Show persistence summary
            persist_summary = PersistSummary(persist_results, self)
            persist_summary.exec_()

            # Close the typing drill
            self.accept()

    def _reset_session(self) -> None:
        """
        Reset the typing session to its initial state.
        """
        self.session = self._create_new_session()
        self.timer_running = False
        self.start_time = 0.0
        self.elapsed_time = 0.0
        self.keystrokes.clear()
        self.error_records.clear()
        self.session_start_time = datetime.datetime.now()
        self.session_end_time = None
        self.typing_input.clear()
        self.typing_input.setReadOnly(False)
        self.progress_bar.setValue(0)
        self.display_text.setText(self.display_content)
        self.errors_label.setText("Errors: 0")
        self.wpm_label.setText("WPM: 0.0")
        self.accuracy_label.setText("Accuracy: 100%")
        palette = self.typing_input.palette()
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        self.typing_input.setPalette(palette)
        self.typing_input.setFocus()

    def _calculate_stats(self) -> Dict[str, Any]:
        """
        Calculate and return typing statistics for the session.
        Returns:
            Dict[str, Any]: Dictionary of stats for the completion dialog.
        """
        total_time = (
            (self.session.end_time - self.session.start_time).total_seconds()
            if self.session.end_time and self.session.start_time
            else 0.0
        )
        expected_chars = self.session.snippet_index_end - self.session.snippet_index_start
        actual_chars = self.session.actual_chars
        correct_chars = actual_chars - self.session.errors
        wpm = (actual_chars / 5.0) / (total_time / 60.0) if total_time > 0 else 0.0
        cpm = (actual_chars) / (total_time / 60.0) if total_time > 0 else 0.0
        accuracy = (correct_chars / actual_chars * 100.0) if actual_chars > 0 else 100.0
        efficiency = (expected_chars / actual_chars * 100.0) if actual_chars > 0 else 100.0
        correctness = (correct_chars / expected_chars * 100.0) if expected_chars > 0 else 100.0
        return {
            "total_time": total_time,
            "wpm": wpm,
            "cpm": cpm,
            "expected_chars": expected_chars,
            "actual_chars": actual_chars,
            "correct_chars": correct_chars,
            "errors": self.session.errors,
            "accuracy": accuracy,
            "efficiency": efficiency,
            "correctness": correctness,
            "total_keystrokes": len(self.keystrokes),
            "backspace_count": sum(1 for k in self.keystrokes if k.get("is_backspace")),
            "error_positions": self.error_positions,
        }
