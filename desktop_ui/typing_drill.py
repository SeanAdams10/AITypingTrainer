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
from typing import Any, Dict, List, Optional, Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette, QTextCharFormat, QTextCursor
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

from db.database_manager import DatabaseManager
from models.keyboard_manager import KeyboardManager, KeyboardNotFound
from models.keystroke import Keystroke
from models.keystroke_manager import KeystrokeManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager
from models.session import Session
from models.session_manager import SessionManager
from models.user_manager import UserManager, UserNotFound


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
        layout.addItem(
            QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

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
        label_widget.setFont(QFont("Arial", 10, QFont.Weight.Bold))
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
        self._add_stat_row(stats_grid, 7, "ms/keystroke:", f"{stats['ms_per_keystroke']:.1f}")

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
        layout.addItem(
            QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

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
        label_widget.setFont(QFont("Arial", 10, QFont.Weight.Bold))
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
        db_manager: Optional[DatabaseManager] = None,
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
        self.db_manager: DatabaseManager = db_manager
        self.user_id: str = user_id
        self.keyboard_id: str = keyboard_id

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
        self.error_positions: List[int] = []  # For final summary

        # New state variables for enhanced tracking
        self.total_errors = (
            0  # Increments for every incorrect character typed (excluding backspace)
        )
        self.total_keystrokes = 0  # All keystrokes excluding backspace
        self.enter_key_count = 0  # Counter for newline characters
        self.error_budget = max(1, int(len(self.content) * 0.05))  # 5% of expected chars, min 1
        self.target_wpm = 100  # Default, will be fetched from keyboard settings

        self.session_start_time: datetime.datetime = datetime.datetime.now()
        self.session_end_time: Optional[datetime.datetime] = None

        # Preprocess content to handle special characters
        self.display_content: str = self._preprocess_content(content)

        # Setup UI Components
        self._setup_ui()

        # Stats are now updated in real-time on every keystroke
        # No timer needed since _on_text_changed handles all updates

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

    def _fetch_target_wpm(self) -> None:
        """Fetch the target WPM from the user's selected keyboard settings."""
        if self.current_keyboard and hasattr(self.current_keyboard, "target_wpm"):
            self.target_wpm = self.current_keyboard.target_wpm
            # Update speed progress bar range
            if hasattr(self, "speed_progress_bar"):
                self.speed_progress_bar.setMaximum(self.target_wpm * 2)
        elif self.current_keyboard and hasattr(self.current_keyboard, "target_ms_per_keystroke"):
            # Convert ms per keystroke to WPM (assuming 5 characters per word)
            chars_per_minute = 60000 / self.current_keyboard.target_ms_per_keystroke
            self.target_wpm = int(chars_per_minute / 5)
            # Update speed progress bar range
            if hasattr(self, "speed_progress_bar"):
                self.speed_progress_bar.setMaximum(self.target_wpm * 2)
        else:
            logging.warning("No keyboard target WPM found. Using default target WPM.")

    def _create_new_session(self) -> Session:
        """
        Helper to create a new Session object for this typing drill.

        Returns:
            Session: A new Session instance with the current configuration.
        """

        def ensure_uuid(val: Union[str, int, None]) -> str:
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
        self.wpm_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_grid.addWidget(self.wpm_label, 0, 0)

        self.cpm_label = QLabel("CPM: 0")
        self.cpm_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_grid.addWidget(self.cpm_label, 0, 1)

        self.accuracy_label = QLabel("Accuracy: 100%")
        self.accuracy_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_grid.addWidget(self.accuracy_label, 0, 2)

        self.timer_label = QLabel("Time: 0.0s")
        self.timer_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_grid.addWidget(self.timer_label, 0, 3)

        # Second row: Efficiency, Correctness, Errors, ms/keystroke
        self.efficiency_label = QLabel("Efficiency: 100%")
        self.efficiency_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_grid.addWidget(self.efficiency_label, 1, 0)

        self.correctness_label = QLabel("Correctness: 100%")
        self.correctness_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_grid.addWidget(self.correctness_label, 1, 1)

        self.errors_label = QLabel("Errors: 0")
        self.errors_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_grid.addWidget(self.errors_label, 1, 2)

        self.ms_per_keystroke_label = QLabel("ms/keystroke: 0.0")
        self.ms_per_keystroke_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
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

        # Store the expected text for comparison (without preprocessing)
        self.expected_text = self.content

        # Progress bars container - Three progress bars as specified
        progress_widget = QWidget()
        progress_grid = QGridLayout(progress_widget)
        progress_grid.setContentsMargins(0, 0, 0, 0)
        progress_grid.setHorizontalSpacing(10)
        progress_grid.setVerticalSpacing(5)

        # Chars Progress Bar - shows completion percentage
        progress_grid.addWidget(QLabel("Chars:"), 0, 0)
        self.chars_progress_bar = QProgressBar()
        self.chars_progress_bar.setRange(0, 100)
        self.chars_progress_bar.setValue(0)
        self.chars_progress_bar.setFormat("%p%")
        progress_grid.addWidget(self.chars_progress_bar, 0, 1)

        # Errors Progress Bar - shows current errors vs error budget
        progress_grid.addWidget(QLabel("Errors:"), 1, 0)
        self.errors_progress_bar = QProgressBar()
        self.errors_progress_bar.setRange(0, self.error_budget)
        self.errors_progress_bar.setValue(0)
        self.errors_progress_bar.setFormat(f"0/{self.error_budget}")
        progress_grid.addWidget(self.errors_progress_bar, 1, 1)

        # Speed Progress Bar - shows WPM from 0 to 2x target
        progress_grid.addWidget(QLabel("Speed (WPM):"), 2, 0)
        self.speed_progress_bar = QProgressBar()
        self.speed_progress_bar.setRange(0, self.target_wpm * 2)
        self.speed_progress_bar.setValue(0)
        self.speed_progress_bar.setFormat("0 WPM")
        progress_grid.addWidget(self.speed_progress_bar, 2, 1)

        main_layout.addWidget(progress_widget)

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

        self.games_button = QPushButton("🎮 Games")
        self.games_button.clicked.connect(self._open_games_menu)
        self.games_button.setToolTip("Open typing games menu")
        button_layout.addWidget(self.games_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

        # Add type annotation for error_positions as a class attribute
        self.error_positions: list[int] = []

        # Initialize last keystroke time for timing calculations
        self.last_keystroke_time: Optional[datetime.datetime] = None

        # Fetch target WPM from keyboard settings if available
        self._fetch_target_wpm()

    def _on_text_changed(self) -> None:
        """
        Handle text changes in the typing input and update session state, stats, and UI.
        Implements enhanced error counting and real-time statistics as per specification.
        """
        current_text = self.typing_input.toPlainText()
        current_time = datetime.datetime.now()

        # Start timer on first keystroke
        if not self.timer_running and len(current_text) > 0:
            self.timer_running = True
            self.start_time = time.time()
            self.session_start_time = current_time

        # Calculate time since previous keystroke
        time_since_previous = 0
        if self.last_keystroke_time:
            delta_ms = int((current_time - self.last_keystroke_time).total_seconds() * 1000)
            time_since_previous = delta_ms
        self.last_keystroke_time = current_time

        # Determine if this is a backspace operation
        prev_length = getattr(self, "_prev_text_length", 0)
        is_backspace = len(current_text) < prev_length
        self._prev_text_length = len(current_text)

        # Update keystroke count (excluding backspace)
        if not is_backspace:
            self.total_keystrokes += 1

            # Check if the new character is an error and increment total_errors
            # This ensures errors are counted even if later corrected
            if len(current_text) > 0:
                char_pos = len(current_text) - 1
                if char_pos < len(self.expected_text):
                    typed_char = current_text[char_pos]
                    expected_char = self.expected_text[char_pos]
                    if typed_char != expected_char:
                        self.total_errors += 1

        # Record keystroke for session persistence
        if current_text:  # Only record if there's text
            char_pos = len(current_text) - 1
            typed_char = current_text[char_pos] if char_pos >= 0 else ""
            expected_char = (
                self.expected_text[char_pos] if char_pos < len(self.expected_text) else ""
            )
            is_correct = typed_char == expected_char

            # Calculate text_index: position in the expected text being typed
            # For backspace, use the position that was just deleted
            text_index = char_pos if not is_backspace else char_pos + 1
            # Ensure text_index is within bounds and non-negative
            text_index = max(0, min(text_index, len(self.expected_text) - 1))
            
            keystroke_record = {
                "char_position": char_pos,
                "char_typed": "\b" if is_backspace else typed_char,
                "expected_char": expected_char,
                "timestamp": current_time,
                "time_since_previous": time_since_previous,
                "is_correct": False if is_backspace else is_correct,
                "is_backspace": is_backspace,
                "text_index": text_index,
            }
            self.keystrokes.append(keystroke_record)

        # Count enter keys to adjust for display differences
        self.enter_key_count = current_text.count('\n')

        # Update session state
        self.session.actual_chars = len(current_text)
        self.session.errors = self.total_errors

        # Update UI components
        self._update_highlighting()
        self._update_real_time_stats()
        self._update_progress_bars()

        # Check for completion - session ends when typed text length matches expected text length
        if len(current_text) >= len(self.expected_text):
            # Capture completion time at the exact moment the last character is typed
            completion_time = current_time
            # Also capture the precise elapsed time from the performance counter
            completion_elapsed_time = time.time() - self.start_time if self.timer_running else 0
            self._on_completion(completion_time, completion_elapsed_time)

    def _on_completion(self, completion_time: datetime.datetime, elapsed_time: float) -> None:
        """Handle completion of the typing session."""
        self.timer_running = False
        self.session.end_time = completion_time
        # Store the precise elapsed time from the performance counter for consistent calculations
        self.completion_elapsed_time = elapsed_time
        self.typing_input.setReadOnly(True)

        # Change background color to indicate completion
        palette = self.typing_input.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(230, 255, 230))
        self.typing_input.setPalette(palette)

        # Show completion dialog
        self._check_completion()

    def _update_real_time_stats(self) -> None:
        """Calculate and update all real-time statistics labels."""
        typed_text = self.typing_input.toPlainText()
        typed_len = len(typed_text)
        expected_len = len(self.expected_text)

        # Calculate elapsed time
        elapsed = time.time() - self.start_time if self.timer_running else 0

        # WPM calculation
        wpm = (typed_len / 5.0) / (elapsed / 60.0) if elapsed > 0 else 0.0
        self.wpm_label.setText(f"WPM: {wpm:.1f}")

        # CPM calculation
        cpm = typed_len / (elapsed / 60.0) if elapsed > 0 else 0.0
        self.cpm_label.setText(f"CPM: {cpm:.0f}")

        # Efficiency (Expected chars / Total keystrokes excluding backspace)
        efficiency = (
            (expected_len / self.total_keystrokes * 100.0) if self.total_keystrokes > 0 else 100.0
        )
        self.efficiency_label.setText(f"Efficiency: {efficiency:.1f}%")

        # Correctness (Correct chars / Expected chars)
        # Note: We need to calculate correct chars based on current text, not total_errors
        # because total_errors now includes all errors ever made (even if corrected)
        current_correct_chars = 0
        for i in range(min(typed_len, expected_len)):
            if i < len(typed_text) and i < len(self.expected_text):
                if typed_text[i] == self.expected_text[i]:
                    current_correct_chars += 1
        correctness = (current_correct_chars / expected_len * 100.0) if expected_len > 0 else 100.0
        self.correctness_label.setText(f"Correctness: {correctness:.1f}%")

        # Accuracy = Efficiency * Correctness (as requested)
        accuracy = (efficiency / 100.0) * (correctness / 100.0) * 100.0
        self.accuracy_label.setText(f"Accuracy: {accuracy:.1f}%")

        # Errors
        self.errors_label.setText(f"Errors: {self.total_errors}")

        # Timer
        self.timer_label.setText(f"Time: {elapsed:.1f}s")

        # MS per keystroke
        ms_per_keystroke = (elapsed * 1000 / expected_len) if expected_len > 0 else 0.0
        self.ms_per_keystroke_label.setText(f"ms/keystroke: {ms_per_keystroke:.1f}")

    def _update_progress_bars(self) -> None:
        """Update all three progress bars based on current session state."""
        typed_len = len(self.typing_input.toPlainText())
        expected_len = len(self.expected_text)

        # Chars Progress Bar - shows completion percentage
        char_progress = (typed_len / expected_len * 100) if expected_len > 0 else 0
        self.chars_progress_bar.setValue(int(char_progress))

        # Errors Progress Bar - shows current errors vs error budget
        self.errors_progress_bar.setValue(self.total_errors)
        self.errors_progress_bar.setFormat(f"{self.total_errors}/{self.error_budget}")

        # Change color to bright red when error budget exceeded
        if self.total_errors > self.error_budget:
            self.errors_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        else:
            self.errors_progress_bar.setStyleSheet("")

        # Speed Progress Bar - shows WPM with color coding
        elapsed = time.time() - self.start_time if self.timer_running else 0
        wpm = (typed_len / 5.0) / (elapsed / 60.0) if elapsed > 0 else 0.0
        self.speed_progress_bar.setValue(int(min(wpm, self.target_wpm * 2)))
        self.speed_progress_bar.setFormat(f"{wpm:.0f} WPM")

        # Color coding for speed progress bar
        if wpm >= self.target_wpm:
            self.speed_progress_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: green; }"
            )
        elif wpm >= self.target_wpm * 0.75:
            self.speed_progress_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: orange; }"
            )
        else:
            self.speed_progress_bar.setStyleSheet("")

    def _update_highlighting(self) -> None:
        """
        Update the display text with highlighting based on typing accuracy.
        - Correct characters: green, italic
        - Incorrect characters: red, bold
        - Untyped characters: black, regular
        """
        current_text = self.typing_input.toPlainText()

        # Get the document and cursor for the display text
        document = self.display_text.document()
        cursor = QTextCursor(document)

        # Clear all formatting first
        cursor.select(QTextCursor.SelectionType.Document)
        default_format = QTextCharFormat()
        default_format.setForeground(QColor(0, 0, 0))  # Black
        default_format.setFontItalic(False)
        default_format.setFontWeight(QFont.Weight.Normal)
        cursor.setCharFormat(default_format)

        # Set up character formats as specified
        correct_format = QTextCharFormat()
        correct_format.setForeground(QColor(0, 128, 0))  # Green
        correct_format.setFontItalic(True)  # Italic for correct chars

        incorrect_format = QTextCharFormat()
        incorrect_format.setForeground(QColor(255, 0, 0))  # Red
        incorrect_format.setFontWeight(QFont.Weight.Bold)  # Bold for incorrect chars

        # Apply formatting character by character
        # Account for the extra '↵' character added for each newline in the display
        enter_keys_in_expected = 0
        for i in range(len(self.expected_text)):
            # The actual position in the display text is the character index plus
            # the number of newlines encountered so far, which have an extra symbol.
            display_pos = i + enter_keys_in_expected
            cursor.setPosition(display_pos)
            cursor.movePosition(
                QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor
            )

            # If the expected character is a newline, we need to advance our count
            # of enter keys for the next iteration's position calculation.
            if self.expected_text[i] == '\n':
                enter_keys_in_expected += 1

            if i < len(current_text):
                if current_text[i] == self.expected_text[i]:
                    # Correct character - green italic
                    cursor.setCharFormat(correct_format)
                else:
                    # Incorrect character - red bold
                    cursor.setCharFormat(incorrect_format)
            else:
                # Untyped character - default black regular
                cursor.setCharFormat(default_format)

        # Clear previous error positions and rebuild
        self.error_positions.clear()
        for i in range(min(len(current_text), len(self.expected_text))):
            if current_text[i] != self.expected_text[i]:
                self.error_positions.append(i)

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
        # Note: timer_running and session.end_time are already set in _on_completion
        # with the precise completion time when the last character was typed
        self.typing_input.setReadOnly(True)
        palette = self.typing_input.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(230, 255, 230))
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
                # Ensure text_index is included in the keystroke data
                kdict["text_index"] = kdict.get("text_index", 0)
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
        if self.ngram_analysis is not None:
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
        elif result == QDialog.DialogCode.Accepted:  # Close
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
        self.error_positions.clear()

        # Reset new state variables
        self.total_errors = 0
        self.total_keystrokes = 0
        self.last_keystroke_time = None
        self.enter_key_count = 0

        self.session_start_time = datetime.datetime.now()
        self.session_end_time = None
        self.session_completed = False

        self.typing_input.clear()
        self.typing_input.setReadOnly(False)

        # Reset UI elements to initial state
        self._update_highlighting()
        self._update_real_time_stats()
        self._update_progress_bars()

        # Reset typing input background
        palette = self.typing_input.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        self.typing_input.setPalette(palette)
        self.typing_input.setFocus()

    def _calculate_stats(self) -> Dict[str, Any]:
        """
        Calculate and return typing statistics for the session.
        Returns:
            Dict[str, Any]: Dictionary of stats for the completion dialog.
        """
        # Use the stored elapsed time from the performance counter for consistency
        total_time = getattr(self, "completion_elapsed_time", 0.0)
        expected_chars = self.session.snippet_index_end - self.session.snippet_index_start
        actual_chars = self.session.actual_chars

        # Calculate current correct chars based on final text (not total_errors which includes all errors ever made)
        final_text = self.typing_input.toPlainText()
        current_correct_chars = 0
        for i in range(min(len(final_text), expected_chars)):
            if i < len(final_text) and i < len(self.expected_text):
                if final_text[i] == self.expected_text[i]:
                    current_correct_chars += 1

        wpm = (actual_chars / 5.0) / (total_time / 60.0) if total_time > 0 else 0.0
        cpm = (actual_chars) / (total_time / 60.0) if total_time > 0 else 0.0

        # Efficiency calculation must match real-time stats
        total_keystrokes_no_backspace = sum(1 for k in self.keystrokes if not k.get("is_backspace"))
        efficiency = (
            (expected_chars / total_keystrokes_no_backspace * 100.0)
            if total_keystrokes_no_backspace > 0
            else 100.0
        )

        # Correctness based on current correct chars in final text
        correctness = (
            (current_correct_chars / expected_chars * 100.0) if expected_chars > 0 else 100.0
        )

        # Accuracy = Efficiency * Correctness (as requested)
        accuracy = (efficiency / 100.0) * (correctness / 100.0) * 100.0

        # MS per keystroke calculation (matches the real-time stats)
        ms_per_keystroke = (total_time * 1000 / expected_chars) if expected_chars > 0 else 0.0

        return {
            "total_time": total_time,
            "wpm": wpm,
            "cpm": cpm,
            "expected_chars": expected_chars,
            "actual_chars": actual_chars,
            "correct_chars": current_correct_chars,
            "errors": self.total_errors,
            "accuracy": accuracy,
            "efficiency": efficiency,
            "correctness": correctness,
            "total_keystrokes": len(self.keystrokes),
            "backspace_count": sum(1 for k in self.keystrokes if k.get("is_backspace")),
            "ms_per_keystroke": ms_per_keystroke,
        }

    def _open_games_menu(self) -> None:
        """
        Open the Games Menu dialog from the typing drill.
        """
        try:
            from desktop_ui.games_menu import GamesMenu
            
            dialog = GamesMenu(parent=self)
            dialog.exec()
        except ImportError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "Games Menu", "The Games Menu UI is not yet implemented."
            )
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "Games Menu Error", f"Could not open the Games Menu: {str(e)}"
            )
