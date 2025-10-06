# ruff: noqa: E501
"""TypingDrillScreen - Interactive typing practice UI with real-time feedback.

Implements full typing drill functionality including timing, statistics, and session persistence.
"""

# Move all imports to the top of the file for PEP8 compliance
import datetime
import logging
import time
import traceback
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
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

from helpers.debug_util import DebugUtil
from models.keyboard_manager import KeyboardManager, KeyboardNotFound
from models.keystroke import Keystroke
from models.keystroke_collection import KeystrokeCollection
from models.ngram import SpeedNGram
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager
from models.session import Session
from models.session_manager import SessionManager
from models.user_manager import UserManager, UserNotFound

if TYPE_CHECKING:
    from db.database_manager import DatabaseManager


class PersistSummary(QDialog):
    """Dialog shown after persistence operations complete.

    Displays the results of saving session data including record counts.
    """

    def __init__(self, persist_results: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        """Initialize the persistence summary dialog.

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

        # Raw keystroke count
        raw_keystroke_count = persist_results.get("keystrokes_saved_raw", 0)
        if raw_keystroke_count > 0:
            self._add_result_row(
                results_grid, row, "Raw Keystrokes:", f"✓ {raw_keystroke_count} saved"
            )
        else:
            self._add_result_row(results_grid, row, "Raw Keystrokes:", "✗ 0 saved")
        row += 1

        # Net keystroke save status
        keystroke_count = persist_results.get("keystroke_count", 0)
        if persist_results.get("keystrokes_saved"):
            self._add_result_row(results_grid, row, "Net Keystrokes:", f"✓ {keystroke_count} saved")
            row += 1
        else:
            error_msg = persist_results.get("keystroke_error", "Unknown error")
            self._add_result_row(results_grid, row, "Net Keystrokes:", f"✗ Failed: {error_msg}")
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

        # Session n-gram summary status
        session_summary_rows = int(persist_results.get("session_summary_rows", 0))
        self._add_result_row(
            results_grid,
            row,
            "Session N-gram Summary:",
            (
                f"✓ {session_summary_rows} rows inserted"
                if session_summary_rows > 0
                else "✓ No new rows"
            ),
        )
        row += 1

        # Speed summary updates (curr + hist)
        curr_updated = int(persist_results.get("curr_updated", 0))
        hist_inserted = int(persist_results.get("hist_inserted", 0))
        self._add_result_row(
            results_grid,
            row,
            "Speed Summary (curr):",
            f"✓ {curr_updated} updated",
        )
        row += 1
        self._add_result_row(
            results_grid,
            row,
            "Speed Summary (hist):",
            f"✓ {hist_inserted} inserted",
        )
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
        """Add a row to the results grid with label and status.

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
    """Dialog shown when the typing session is completed.

    Displays typing statistics and provides options to retry or close.
    """

    def __init__(self, stats: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        """Initialize the completion dialog with typing statistics and parent widget.

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
        # MS per keystroke (summary spec: total ms / expected chars)
        if "ms_per_keystroke" in stats:
            self._add_stat_row(
                stats_grid, 2, "MS per Keystroke:", f"{stats['ms_per_keystroke']:.0f} ms"
            )
            base_row = 3
        else:
            base_row = 2
        self._add_stat_row(stats_grid, base_row + 0, "Accuracy:", f"{stats['accuracy']:.1f}%")
        self._add_stat_row(stats_grid, base_row + 1, "Efficiency:", f"{stats['efficiency']:.1f}%")
        self._add_stat_row(stats_grid, base_row + 2, "Correctness:", f"{stats['correctness']:.1f}%")
        self._add_stat_row(stats_grid, base_row + 3, "Errors:", f"{stats['errors']}")
        self._add_stat_row(stats_grid, base_row + 4, "Time:", f"{stats['total_time']:.1f} seconds")

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
        """Add a row to the stats grid with label and value.

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
        """Handle retry button click."""
        self.done(2)  # Custom return code for retry


class TypingDrillScreen(QDialog):
    """TypingDrillScreen handles the typing drill UI and session persistence for desktop.

    Implements real-time feedback, timing, statistics, and session recording.

    Args:
        snippet_id (str): ID of the snippet being practiced (UUID string; "-1" for manual text)
        start (int): Starting index in the snippet
        end (int): Ending index in the snippet
        content (str): Content to type (substring of snippet between start and end)
        db_manager (Optional[Any]): Database manager instance
        parent (Optional[QWidget]): Parent widget
    """

    def __init__(
        self,
        snippet_id: str,
        start: int,
        end: int,
        content: str,
        db_manager: Optional["DatabaseManager"] = None,
        user_id: Optional[str] = None,
        keyboard_id: Optional[str] = None,
        focus_ngrams: Optional[List[SpeedNGram]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the TypingDrillScreen dialog and session state.

        Args:
            snippet_id (int): ID of the snippet being practiced (-1 for manual text)
            start (int): Starting index in the snippet
            end (int): Ending index in the snippet
            content (str): Content to type (substring of snippet between start and end)
            db_manager (Optional[DatabaseManager]): Database manager instance
            user_id (Optional[str]): ID of the current user
            keyboard_id (Optional[str]): ID of the keyboard being used
            focus_ngrams (Optional[List[SpeedNGram]]): List of n-grams to highlight for focus
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
        self.snippet_id: str = snippet_id
        self.start: int = start
        self.end: int = end
        # Normalize content newlines to "\n" and store original content for comparisons
        self.content: str = content.replace("\r\n", "\n").replace("\r", "\n")
        self.db_manager = db_manager
        self.user_id = user_id
        self.keyboard_id = keyboard_id
        self.focus_ngrams = focus_ngrams or []
        self.debug_util = DebugUtil()

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
                traceback.print_exc()
                self.debug_util.debugMessage(f"Error loading user or keyboard: {str(e)}")
                print(f"Error loading user or keyboard: {str(e)}")

        # Initialize typing state
        self.timer_running: bool = False
        self.start_time: float = 0.0
        self.elapsed_time: float = 0.0
        self.completion_dialog: Optional[CompletionDialog] = None

        # Tracking keystroke collection and error records for session data
        self.keystroke_col: KeystrokeCollection = KeystrokeCollection()
        self.error_records: List[Dict[str, Any]] = []
        self.session_start_time: datetime.datetime = datetime.datetime.now()
        self.session_end_time: Optional[datetime.datetime] = None

        # Preprocess content to handle special characters and build index map
        self.display_index_map: List[int] = []  # maps content index -> display index
        self.display_content: str = self._preprocess_content(self.content)

        # Initialize drill thresholds before building UI
        # Error budget per spec: 5% of expected chars, minimum 1
        self.error_budget: int = max(1, int(round(len(self.content) * 0.05)))
        # Speed target derived from keyboard if available (WPM), else default 40 WPM
        self.target_wpm: int = 40
        if self.current_keyboard and getattr(
            self.current_keyboard, "target_ms_per_keystroke", None
        ):
            try:
                # target WPM = 60000 ms per minute / (ms_per_keystroke * 5 chars/word)
                ms_per_keystroke = int(self.current_keyboard.target_ms_per_keystroke)
                if ms_per_keystroke > 0:
                    self.target_wpm = max(1, int(round(60000 / (ms_per_keystroke * 5))))
            except Exception:
                pass
        self.current_wpm: float = 0.0

        # Setup UI Components (uses error_budget and target_wpm)
        self._setup_ui()

        # Create timer for updating stats
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(100)  # Update every 100ms

        # Update status bar with user and keyboard info
        self._update_status_bar()

        # Set focus to typing input
        self.typing_input.setFocus()

        # Save last used keyboard (DFKBD) setting for this user
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
                traceback.print_exc()
                self.debug_util.debugMessage(f"Failed to save LSTKBD setting: {e}")
                logging.warning(f"Failed to save LSTKBD setting: {e}")

        # Move attribute definitions to __init__ (post-UI simple state fields)
        self.errors = 0
        self.session_save_status = ""
        self.session_completed = False
        self.prev_text: str = ""  # used to detect backspace reliably

    def _update_status_bar(self) -> None:
        """Update status bar with user and keyboard information."""
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
        """Helper to create a new Session object for this typing drill.

        Returns:
            Session: A new Session instance with the current configuration.
        """

        def ensure_uuid(val: object) -> str:
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
        """Preprocess content to make whitespace and special characters visible for display.

        Args:
            content (str): Original text content to preprocess.

        Returns:
            str: Preprocessed content with visible whitespace markers for display.
        """
        # Build display string and index map so that each content index maps to a display index
        display_chars: List[str] = []
        self.display_index_map = []

        for ch in content:
            # Record the display index where this content char starts
            self.display_index_map.append(len(display_chars))
            if ch == " ":
                display_chars.append("␣")
            elif ch == "\t":
                display_chars.append("⮾")
            elif ch == "\n":
                # Show return symbol then an actual newline; treat as one expected char
                display_chars.append("↵")
                display_chars.append("\n")
            else:
                display_chars.append(ch)

        return "".join(display_chars)

    def _setup_ui(self) -> None:
        """Set up the UI components for the typing drill screen.

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

        # Stats bar (Time, WPM, Accuracy, Errors, ms/keystroke)
        stats_layout = QHBoxLayout()

        # Timer
        self.timer_label = QLabel("Time: 0.0s")
        self.timer_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_layout.addWidget(self.timer_label)

        # WPM
        self.wpm_label = QLabel("WPM: 0.0")
        self.wpm_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_layout.addWidget(self.wpm_label)

        # Accuracy
        self.accuracy_label = QLabel("Accuracy: 100%")
        self.accuracy_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_layout.addWidget(self.accuracy_label)

        # Errors (accumulated)
        self.errors_label = QLabel("Errors: 0")
        self.errors_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_layout.addWidget(self.errors_label)

        # ms per keystroke (rolling average)
        self.ms_per_key_label = QLabel("ms/keystroke: 0")
        self.ms_per_key_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_layout.addWidget(self.ms_per_key_label)

        main_layout.addLayout(stats_layout)

        # Text to type (display)
        main_layout.addWidget(QLabel("<h3>Type the following text:</h3>"))

        self.display_text = QTextEdit()
        self.display_text.setReadOnly(True)
        self.display_text.setFont(QFont("Courier New", 12))
        self.display_text.setText(self.display_content)
        self.display_text.setMinimumHeight(150)
        main_layout.addWidget(self.display_text)

        # Progress bars container (Completion, Errors, Speed)
        progress_layout = QVBoxLayout()

        # Completion progress (characters present vs expected)
        self.completion_bar = QProgressBar()
        self.completion_bar.setTextVisible(True)
        self.completion_bar.setRange(0, len(self.content))
        self.completion_bar.setValue(0)
        self.completion_bar.setFormat("Completion: %v/%m")
        progress_layout.addWidget(self.completion_bar)

        # Errors progress (current errors vs error budget)
        self.error_bar = QProgressBar()
        self.error_bar.setTextVisible(True)
        self.error_bar.setRange(0, self.error_budget)
        self.error_bar.setValue(0)
        self.error_bar.setFormat(f"Errors: %v/{self.error_budget}")
        progress_layout.addWidget(self.error_bar)

        # Speed progress (WPM from 0 to 2x target)
        self.speed_bar = QProgressBar()
        self.speed_bar.setTextVisible(True)
        self.speed_bar.setRange(0, max(1, self.target_wpm * 2))
        self.speed_bar.setValue(0)
        self.speed_bar.setFormat(f"Speed: %v WPM (target {self.target_wpm})")
        progress_layout.addWidget(self.speed_bar)

        main_layout.addLayout(progress_layout)

        # Typing input
        main_layout.addWidget(QLabel("<h3>Your typing:</h3>"))

        self.typing_input = QTextEdit()
        self.typing_input.setFont(QFont("Courier New", 12))
        self.typing_input.setMinimumHeight(150)
        self.typing_input.textChanged.connect(self._on_text_changed)
        main_layout.addWidget(self.typing_input)

        # Focus NGrams section (if provided)
        if self.focus_ngrams:
            main_layout.addWidget(QLabel("<h3>Focus NGrams:</h3>"))

            # Create a text display for focus ngrams
            self.focus_ngrams_display = QTextEdit()
            self.focus_ngrams_display.setReadOnly(True)
            self.focus_ngrams_display.setFont(QFont("Courier New", 11))
            self.focus_ngrams_display.setMaximumHeight(80)
            self.focus_ngrams_display.setMinimumHeight(60)

            # Format focus ngrams as space-separated text
            focus_text = "  ".join([ngram.text for ngram in self.focus_ngrams])
            self.focus_ngrams_display.setText(focus_text)

            main_layout.addWidget(self.focus_ngrams_display)

            # Extend window height slightly when focus ngrams are present
            current_height = self.minimumHeight()
            self.setMinimumSize(self.minimumWidth(), current_height + 100)

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

        # Flag to track if highlighting has been initialized
        self._highlighting_initialized: bool = False

        # Initialize text formats once for reuse in highlighting
        self._init_text_formats()

    def _init_text_formats(self) -> None:
        """Initialize text character formats for correct and incorrect typing.

        This method sets up the QTextCharFormat objects that will be reused
        for highlighting correct and incorrect characters during typing.
        """
        # Set up character formats (per spec: correct = green italic, incorrect = red bold)
        self.correct_format = QTextCharFormat()
        self.correct_format.setForeground(QColor(0, 128, 0))  # Green
        self.correct_format.setBackground(QColor(220, 255, 220))  # Light green background
        self.correct_format.setFontItalic(True)

        self.error_format = QTextCharFormat()
        self.error_format.setForeground(QColor(255, 0, 0))  # Red
        self.error_format.setBackground(QColor(255, 220, 220))  # Light red background
        self.error_format.setFontWeight(QFont.Weight.Bold)

        # Default format for untyped characters (neutral/original appearance)
        self.default_format = QTextCharFormat()
        self.default_format.setForeground(QColor(0, 0, 0))  # Black text
        self.default_format.setBackground(QColor(255, 255, 255))  # White background
        self.default_format.setFontItalic(False)
        self.default_format.setFontWeight(QFont.Weight.Normal)

    def _on_text_changed(self) -> None:
        """Handle text changes in the typing input and update session state, stats, and UI.

        Returns:
            None: This method does not return a value.
        """
        # Normalize typed text line endings to "\n" for comparison
        current_text = self.typing_input.toPlainText().replace("\r\n", "\n").replace("\r", "\n")

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
        if self.keystroke_col.get_raw_count() > 0:
            last_keystroke = self.keystroke_col.raw_keystrokes[-1]
            last_time = last_keystroke.keystroke_time
            delta_ms = int((now - last_time).total_seconds() * 1000)
            time_since_previous = delta_ms

        # Determine if this was a backspace or delete using previous text snapshot
        is_backspace = False
        prev_len = len(self.prev_text)
        if len(current_text) < prev_len:
            # Text got shorter - backspace or delete was pressed
            deleted_pos = current_pos  # Position where character was deleted
            is_backspace = True

            # Create a keystroke record for the backspace
            keystroke = Keystroke(
                session_id=self.session.session_id,
                keystroke_char="\b",  # Backspace character
                expected_char=self.content[deleted_pos] if deleted_pos < len(self.content) else "",
                keystroke_time=now,
                is_error=True,  # Backspaces are always errors
                text_index=deleted_pos,
                key_index=self.keystroke_col.get_raw_count(),  # Sequential order
            )
            self.keystroke_col.add_keystroke(keystroke)

            # Log the backspace keystroke
            logging.debug(
                "Recorded BACKSPACE at position %d, time_since_previous=%dms",
                deleted_pos,
                time_since_previous,
            )

        # Handle regular character input (including when backspace was used but we have new text)
        if len(current_text) > 0 and (not is_backspace or len(current_text) >= prev_len):
            new_char_pos = len(current_text) - 1
            typed_char = current_text[new_char_pos] if new_char_pos < len(current_text) else ""
            expected_char = self.content[new_char_pos] if new_char_pos < len(self.content) else ""

            # Only record if this is a new character (not part of backspace handling)
            if not is_backspace or new_char_pos >= prev_len:
                is_correct = typed_char == expected_char

                # Create keystroke using Keystroke model
                keystroke = Keystroke(
                    session_id=self.session.session_id,
                    keystroke_char=typed_char,
                    expected_char=expected_char,
                    keystroke_time=now,
                    is_error=not is_correct,
                    text_index=new_char_pos,
                    key_index=self.keystroke_col.get_raw_count(),  # Sequential order
                )
                self.keystroke_col.add_keystroke(keystroke)

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

        # Update previous text snapshot for next change detection
        self.prev_text = current_text

    def _process_typing_input(self) -> None:
        """Process the current typing input, check progress, and update UI highlighting and progress bar.

        Returns:
            None: This method does not return a value.
        """
        # Normalize typed text line endings for consistent indexing
        current_text = self.typing_input.toPlainText().replace("\r\n", "\n").replace("\r", "\n")

        # Update completion progress bar (characters present vs expected)
        self.completion_bar.setMaximum(len(self.content))
        self.completion_bar.setValue(min(len(current_text), len(self.content)))

        # Update text highlighting (only last 3 characters for performance)
        self._update_highlighting(current_text)

        # Update error count efficiently
        self._update_error_count(current_text)

        # Note: Completion check moved exclusively to _on_text_changed to prevent duplicate dialog

    def _update_highlighting_old(self, current_text: str) -> None:
        """Original update highlighting method - kept as backup.

        Args:
            current_text (str): Current text input by the user.

        Returns:
            None: This method does not return a value.
        """
        # Block signals temporarily to avoid recursive calls
        self.display_text.blockSignals(True)

        # Create a new QTextDocument for better performance
        # Remove document.clone() and use self.display_text.document() directly if needed
        document = self.display_text.document()

        # Apply formatting based on current input (using pre-initialized formats)
        self.error_positions = []
        cursor = QTextCursor(document)

        # First reset the document to show the original content
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(self.display_content)

        # Apply formatting for each character
        for i, char in enumerate(current_text):
            if i >= len(self.content):
                break

            # Map content index i to display index (accounts for "↵" inserted before newlines)
            disp_i = self.display_index_map[i] if i < len(self.display_index_map) else i
            cursor.setPosition(disp_i)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)

            if char == self.content[i]:
                cursor.setCharFormat(self.correct_format)
            else:
                cursor.setCharFormat(self.error_format)
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

    def _update_highlighting(self, current_text: str) -> None:
        """Update the display text highlighting for the last 3 characters typed and 2 characters ahead.

        This optimized method updates formatting for the most recently typed characters plus
        the next 2 characters (for backspace support), providing efficient highlighting updates.

        Args:
            current_text (str): Current text input by the user.

        Returns:
            None: This method does not return a value.
        """
        # Block signals temporarily to avoid recursive calls
        self.display_text.blockSignals(True)

        document = self.display_text.document()
        cursor = QTextCursor(document)

        # Initialize the document with original content if this is the first call
        if not hasattr(self, "_highlighting_initialized") or not self._highlighting_initialized:
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.insertText(self.display_content)
            self._highlighting_initialized = True

        # Determine the range to update (last 3 characters + 2 characters ahead)
        current_len = len(current_text)
        start_update_pos = max(0, current_len - 3)
        end_update_pos = min(current_len + 2, len(self.content))

        # Update formatting for the extended range
        for i in range(start_update_pos, end_update_pos):
            # Map content index to display index
            disp_i = self.display_index_map[i] if i < len(self.display_index_map) else i
            cursor.setPosition(disp_i)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)

            if i < current_len:
                # Character has been typed - apply appropriate formatting
                char = current_text[i]
                expected_char = self.content[i]

                if char == expected_char:
                    cursor.setCharFormat(self.correct_format)
                else:
                    cursor.setCharFormat(self.error_format)
            else:
                # Character has not been typed yet - reset to default format
                cursor.setCharFormat(self.default_format)

        # Unblock signals and update display
        self.display_text.blockSignals(False)
        self.display_text.update()

    def _update_error_count(self, current_text: str) -> None:
        """Efficiently update error count and error positions.

        This method calculates errors without reformatting the entire text,
        focusing on performance for long texts.

        Args:
            current_text (str): Current text input by the user.
        """
        # Clear previous error tracking
        self.error_positions = []
        self.error_records = []

        # Check each character for errors
        for i, char in enumerate(current_text):
            if i >= len(self.content):
                break

            expected_char = self.content[i]
            if char != expected_char:
                self.error_positions.append(i)

                # Record error data for analysis
                error_record = {
                    "char_position": i,
                    "expected_char": expected_char,
                    "typed_char": char,
                }
                self.error_records.append(error_record)

        # Update the error count
        self.errors = len(self.error_positions)

    def _update_timer(self) -> None:
        """Update timer and stats display during the typing session.

        Returns:
            None: This method does not return a value.
        """
        if self.timer_running:
            self.elapsed_time = time.time() - self.start_time
            self.timer_label.setText(f"Time: {self.elapsed_time:.1f}s")
            self._update_stats()

    def _update_stats(self) -> None:
        """Calculate and update WPM, CPM, and accuracy statistics for the session.

        Returns:
            None: This method does not return a value.
        """
        if not self.timer_running or self.elapsed_time < 0.1:
            return
        minutes = self.elapsed_time / 60.0
        typed_text = self.typing_input.toPlainText().replace("\r\n", "\n").replace("\r", "\n")
        wpm = (len(typed_text) / 5.0) / minutes if minutes > 0 else 0
        # Accumulated errors: count all incorrect non-backspace keystrokes (spec excludes backspaces)
        accumulated_errors = sum(
            1 for k in self.keystroke_col.raw_keystrokes if k.is_error and k.keystroke_char != "\b"
        )
        correct_chars = max(0, len(typed_text) - len(self.error_positions))
        accuracy = (
            correct_chars / len(self.typing_input.toPlainText()) * 100
            if len(self.typing_input.toPlainText()) > 0
            else 100
        )
        # Average ms per keystroke (ignore zero or missing intervals)
        intervals = [
            k.time_since_previous
            for k in self.keystroke_col.raw_keystrokes
            if k.time_since_previous is not None and k.time_since_previous > 0
        ]
        avg_ms_per_key = (sum(intervals) / len(intervals)) if intervals else 0.0
        # Update session object fields
        self.session.actual_chars = len(self.typing_input.toPlainText())
        # Store accumulated errors in session to align with UI and summary
        self.session.errors = int(accumulated_errors)
        self.session.end_time = datetime.datetime.now()
        # Optionally, add more stats to session if model supports
        self.current_wpm = wpm
        self.wpm_label.setText(f"WPM: {wpm:.1f}")
        self.accuracy_label.setText(f"Accuracy: {accuracy:.1f}%")
        self.errors_label.setText(f"Errors: {accumulated_errors}")
        self.ms_per_key_label.setText(f"ms/keystroke: {avg_ms_per_key:.0f}")

        # Update errors progress bar and colorize when exceeding budget
        self.error_bar.setMaximum(self.error_budget)
        self.error_bar.setValue(min(self.session.errors, self.error_budget))
        if self.session.errors > self.error_budget:
            self.error_bar.setStyleSheet(
                "QProgressBar::chunk{background-color:#cc0000;} QProgressBar{text-align:center;}"
            )
        else:
            self.error_bar.setStyleSheet("")

        # Update speed bar and color thresholds
        speed_max = max(1, self.target_wpm * 2)
        self.speed_bar.setMaximum(speed_max)
        self.speed_bar.setValue(int(min(wpm, speed_max)))
        if wpm >= self.target_wpm:
            # Green when at/above target
            self.speed_bar.setStyleSheet(
                "QProgressBar::chunk{background-color:#0a8a0a;} QProgressBar{text-align:center;}"
            )
        elif wpm < self.target_wpm * 0.75:
            # Orange when below 75% of target
            self.speed_bar.setStyleSheet(
                "QProgressBar::chunk{background-color:#ff8800;} QProgressBar{text-align:center;}"
            )
        else:
            self.speed_bar.setStyleSheet("")

    def _check_completion(self) -> None:
        """Check and handle completion of the typing session, including saving session data and showing completion dialog.

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
        """Save the session using the local Session object and session_manager.

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
            return True
        except Exception as e:
            error_message = f"Error saving session data: {str(e)}"
            logging.error("Exception in save_session: %s", e)
            self.session_save_status = error_message
            raise ValueError(error_message) from e

    def _persist_session_data(self, session: Session) -> Dict[str, Any]:
        """Persist the session, keystrokes, n-grams, and analytics via orchestrator and return a summary dict."""
        results: Dict[str, Any] = {
            "session_saved": False,
            "session_error": None,
            "keystrokes_saved": False,
            "keystroke_error": None,
            "keystroke_count": 0,
            "ngrams_saved": False,
            "ngram_error": None,
            "ngram_count": 0,
        }
        try:
            if self.db_manager is None:
                raise Exception("DatabaseManager not initialized")
            # Build orchestrator and run full pipeline
            ngram_manager = NGramManager(self.db_manager)
            analytics = NGramAnalyticsService(self.db_manager, ngram_manager)
            orch_res = analytics.process_end_of_session(
                session,
                self.keystroke_col,  # Use raw keystrokes from collection
                save_session_first=False,  # session already saved in _check_completion
            )

            # Map orchestrator results to UI summary schema
            results["session_saved"] = bool(orch_res.get("session_saved", False))
            results["keystrokes_saved_raw"] = int(orch_res.get("keystrokes_saved_raw", 0))
            results["keystrokes_saved_net"] = int(orch_res.get("keystrokes_saved_net", 0))
            results["keystrokes_saved"] = (
                results["keystrokes_saved_net"] > 0 and results["keystrokes_saved_raw"] > 0
            )
            results["ngrams_saved"] = bool(orch_res.get("ngrams_saved", False))
            results["ngram_count"] = int(orch_res.get("ngram_count", 0))
            results["session_summary_rows"] = int(orch_res.get("session_summary_rows", 0))
            results["curr_updated"] = int(orch_res.get("curr_updated", 0))
            results["hist_inserted"] = int(orch_res.get("hist_inserted", 0))
            # We can infer keystroke_count from keystroke collection
            results["keystroke_count"] = self.keystroke_col.get_raw_count()
        except Exception as e:
            # Attribute error to the first failing stage based on partial flags
            if not results["session_saved"]:
                results["session_error"] = str(e)
            elif not results["keystrokes_saved"]:
                results["keystroke_error"] = str(e)
            else:
                results["ngram_error"] = str(e)
        return results

    def _show_completion_dialog(self, session: Session) -> None:
        """Show the completion dialog with the given session object and handle persistence.

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
        """Reset the typing session to its initial state."""
        self.session = self._create_new_session()
        self.timer_running = False
        self.start_time = 0.0
        self.elapsed_time = 0.0
        self.keystroke_col.clear()
        self.error_records.clear()
        self.session_start_time = datetime.datetime.now()
        self.session_end_time = None
        self.typing_input.clear()
        self.typing_input.setReadOnly(False)
        # Reset progress bars
        if hasattr(self, "completion_bar"):
            self.completion_bar.setMaximum(len(self.content))
            self.completion_bar.setValue(0)
        if hasattr(self, "error_bar"):
            self.error_bar.setRange(0, self.error_budget)
            self.error_bar.setValue(0)
            self.error_bar.setStyleSheet("")
        if hasattr(self, "speed_bar"):
            self.speed_bar.setRange(0, max(1, self.target_wpm * 2))
            self.speed_bar.setValue(0)
            self.speed_bar.setStyleSheet("")
        self.display_text.setText(self.display_content)
        # Reset highlighting initialization flag
        self._highlighting_initialized = False
        self.errors_label.setText("Errors: 0")
        self.wpm_label.setText("WPM: 0.0")
        self.accuracy_label.setText("Accuracy: 100%")
        self.ms_per_key_label.setText("ms/keystroke: 0")
        palette = self.typing_input.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        self.typing_input.setPalette(palette)
        self.typing_input.setFocus()

    def _calculate_stats(self) -> Dict[str, Any]:
        """Calculate and return typing statistics for the session.

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
        ms_per_keystroke = (total_time * 1000.0) / max(1, expected_chars)
        return {
            "total_time": total_time,
            "wpm": wpm,
            "cpm": cpm,
            "ms_per_keystroke": ms_per_keystroke,
            "expected_chars": expected_chars,
            "actual_chars": actual_chars,
            "correct_chars": correct_chars,
            "errors": self.session.errors,
            "accuracy": accuracy,
            "efficiency": efficiency,
            "correctness": correctness,
            "total_keystrokes": self.keystroke_col.get_raw_count(),
            "backspace_count": sum(
                1 for k in self.keystroke_col.raw_keystrokes if k.keystroke_char == "\b"
            ),
            "error_positions": self.error_positions,
        }
