# ruff: noqa: E501
"""ConsistencyTypingScreen - Interactive typing practice UI focused on rhythm consistency.

Implements consistency-focused typing drill with metronome and variability tracking.
"""

import datetime
import statistics
import time
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPalette, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from db.database_manager import DatabaseManager


class ConsistencyTypingScreen(QDialog):
    """ConsistencyTypingScreen handles consistency-focused typing practice.
    
    Emphasizes rhythm and timing consistency over speed or accuracy.
    
    Supports two modes:
    - Metronome-Led: User sets target pace with audible metronome
    - User-Led: System adapts to user's natural rhythm
    """

    def __init__(
        self,
        snippet_id: str,
        start: int,
        end: int,
        content: str,
        db_manager: Optional[DatabaseManager] = None,
        user_id: Optional[str] = None,
        keyboard_id: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the consistency typing screen.
        
        Args:
            snippet_id: ID of the snippet being typed
            start: Start position in the snippet
            end: End position in the snippet  
            content: Text content to be typed
            db_manager: Optional database manager instance
            user_id: Optional user identifier
            keyboard_id: Optional keyboard identifier
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Core parameters
        self.snippet_id: str = snippet_id
        self.start = start
        self.end = end
        self.content = content
        self.db_manager = db_manager
        self.user_id = user_id
        self.keyboard_id = keyboard_id
        
        # Preprocess content for display
        self.expected_text = content
        self.display_text = self._preprocess_content(content)
        
        # Session state
        self.session_start_time: Optional[datetime.datetime] = datetime.datetime.now()
        self.session_end_time: Optional[datetime.datetime] = None
        self.session_completed = False
        self.keystrokes: List[Dict[str, Any]] = []
        self.keystroke_intervals: List[float] = []
        self.total_errors = 0
        self.total_keystrokes = 0
        self.last_keystroke_time: Optional[float] = None
        
        # Consistency tracking
        self.mode = "user_led"  # "metronome_led" or "user_led"
        self.target_pace_ms = 400  # milliseconds per keystroke
        self.current_variability = 0.0
        self.rolling_intervals: List[float] = []  # For calculating variability
        self.rolling_window_size = 15
        
        # Metronome state
        self.metronome_timer = QTimer()
        self.metronome_timer.timeout.connect(self._metronome_beat)
        self.metronome_frequency = 1  # 1, 4, or 8
        self.metronome_volume = 50
        self.metronome_enabled = True
        self.beat_counter = 0
        
        # UI setup
        self.setWindowTitle("Consistency Typing Practice")
        self.setMinimumSize(800, 700)
        self.setModal(True)
        
        self._setup_ui()
        self._reset_session()

    def _preprocess_content(self, content: str) -> str:
        """Preprocess content to make whitespace visible for display."""
        return content.replace('\n', '↵\n').replace('\t', '→')

    def _setup_ui(self) -> None:
        """Set up the UI components for the consistency typing screen."""
        layout = QVBoxLayout(self)
        
        # Mode selection section
        mode_group = QGroupBox("Practice Mode")
        mode_layout = QHBoxLayout(mode_group)
        
        self.mode_group = QButtonGroup()
        self.metronome_radio = QRadioButton("Metronome-Led")
        self.user_led_radio = QRadioButton("User-Led")
        self.user_led_radio.setChecked(True)
        
        self.mode_group.addButton(self.metronome_radio, 0)
        self.mode_group.addButton(self.user_led_radio, 1)
        self.mode_group.buttonClicked.connect(self._on_mode_changed)
        
        mode_layout.addWidget(self.metronome_radio)
        mode_layout.addWidget(self.user_led_radio)
        layout.addWidget(mode_group)
        
        # Metronome settings (initially hidden)
        self.metronome_settings = QGroupBox("Metronome Settings")
        metronome_layout = QGridLayout(self.metronome_settings)
        
        # Target pace
        metronome_layout.addWidget(QLabel("Target Pace (ms/keystroke):"), 0, 0)
        self.pace_spinbox = QSpinBox()
        self.pace_spinbox.setRange(200, 2000)
        self.pace_spinbox.setValue(400)
        self.pace_spinbox.valueChanged.connect(self._on_pace_changed)
        metronome_layout.addWidget(self.pace_spinbox, 0, 1)
        
        # Beat frequency
        metronome_layout.addWidget(QLabel("Beat Frequency:"), 1, 0)
        freq_layout = QHBoxLayout()
        self.freq_group = QButtonGroup()
        self.freq_1 = QRadioButton("Every keystroke")
        self.freq_4 = QRadioButton("Every 4 keystrokes")
        self.freq_8 = QRadioButton("Every 8 keystrokes")
        self.freq_4.setChecked(True)
        
        self.freq_group.addButton(self.freq_1, 1)
        self.freq_group.addButton(self.freq_4, 4)
        self.freq_group.addButton(self.freq_8, 8)
        self.freq_group.buttonClicked.connect(self._on_frequency_changed)
        
        freq_layout.addWidget(self.freq_1)
        freq_layout.addWidget(self.freq_4)
        freq_layout.addWidget(self.freq_8)
        metronome_layout.addLayout(freq_layout, 1, 1)
        
        # Volume control
        metronome_layout.addWidget(QLabel("Volume:"), 2, 0)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        metronome_layout.addWidget(self.volume_slider, 2, 1)
        
        # Mute checkbox
        self.mute_checkbox = QCheckBox("Mute")
        self.mute_checkbox.toggled.connect(self._on_mute_toggled)
        metronome_layout.addWidget(self.mute_checkbox, 2, 2)
        
        self.metronome_settings.setVisible(False)
        layout.addWidget(self.metronome_settings)
        
        # Metrics display
        metrics_group = QGroupBox("Consistency Metrics")
        metrics_layout = QGridLayout(metrics_group)
        
        # Target speed
        metrics_layout.addWidget(QLabel("Target Speed:"), 0, 0)
        self.target_speed_label = QLabel("400ms/keystroke")
        metrics_layout.addWidget(self.target_speed_label, 0, 1)
        
        # Current speed
        metrics_layout.addWidget(QLabel("Current Speed:"), 0, 2)
        self.current_speed_label = QLabel("--ms/keystroke")
        metrics_layout.addWidget(self.current_speed_label, 0, 3)
        
        # Variability display
        metrics_layout.addWidget(QLabel("Current Variability:"), 1, 0)
        self.variability_label = QLabel("±0ms")
        metrics_layout.addWidget(self.variability_label, 1, 1)
        
        # Consistency gauge
        self.consistency_bar = QProgressBar()
        self.consistency_bar.setRange(0, 200)  # 0-200ms variability range
        self.consistency_bar.setValue(0)
        self.consistency_bar.setFormat("Excellent Consistency")
        metrics_layout.addWidget(self.consistency_bar, 1, 2, 1, 2)
        
        layout.addWidget(metrics_group)
        
        # Text display
        text_group = QGroupBox("Text to Type")
        text_layout = QVBoxLayout(text_group)
        
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setPlainText(self.display_text)
        self.text_display.setMinimumHeight(150)
        text_layout.addWidget(self.text_display)
        
        layout.addWidget(text_group)
        
        # Typing input
        input_group = QGroupBox("Your Typing")
        input_layout = QVBoxLayout(input_group)
        
        self.typing_input = QTextEdit()
        self.typing_input.setMinimumHeight(100)
        self.typing_input.textChanged.connect(self._on_text_changed)
        input_layout.addWidget(self.typing_input)
        
        layout.addWidget(input_group)
        
        # Progress bars
        progress_group = QGroupBox("Progress")
        progress_layout = QGridLayout(progress_group)
        
        # Characters progress
        progress_layout.addWidget(QLabel("Characters:"), 0, 0)
        self.chars_progress = QProgressBar()
        progress_layout.addWidget(self.chars_progress, 0, 1)
        
        # Errors progress
        progress_layout.addWidget(QLabel("Errors:"), 1, 0)
        self.errors_progress = QProgressBar()
        progress_layout.addWidget(self.errors_progress, 1, 1)
        
        layout.addWidget(progress_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("&Reset")
        self.reset_button.clicked.connect(self._reset_session)
        button_layout.addWidget(self.reset_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("&Close")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)

    def _on_mode_changed(self) -> None:
        """Handle mode selection changes."""
        if self.metronome_radio.isChecked():
            self.mode = "metronome_led"
            self.metronome_settings.setVisible(True)
            self.target_pace_ms = self.pace_spinbox.value()
        else:
            self.mode = "user_led"
            self.metronome_settings.setVisible(False)
            self._stop_metronome()
        
        self._update_target_speed_display()

    def _on_pace_changed(self) -> None:
        """Handle target pace changes."""
        if self.mode == "metronome_led":
            self.target_pace_ms = self.pace_spinbox.value()
            self._update_target_speed_display()
            if self.metronome_timer.isActive():
                self._start_metronome()

    def _on_frequency_changed(self) -> None:
        """Handle metronome frequency changes."""
        button = self.freq_group.checkedButton()
        if button:
            self.metronome_frequency = self.freq_group.id(button)

    def _on_volume_changed(self) -> None:
        """Handle volume changes."""
        self.metronome_volume = self.volume_slider.value()

    def _on_mute_toggled(self, checked: bool) -> None:
        """Handle mute toggle."""
        self.metronome_enabled = not checked

    def _update_target_speed_display(self) -> None:
        """Update the target speed display."""
        if self.mode == "metronome_led":
            self.target_speed_label.setText(f"{self.target_pace_ms}ms/keystroke")
        else:
            if len(self.rolling_intervals) >= 3:
                avg_interval = statistics.mean(self.rolling_intervals[-10:])
                self.target_speed_label.setText(f"{avg_interval:.0f}ms/keystroke")
            else:
                self.target_speed_label.setText("Adapting...")

    def _start_metronome(self) -> None:
        """Start the metronome timer."""
        if self.mode == "metronome_led" and self.target_pace_ms > 0:
            self.metronome_timer.start(self.target_pace_ms)
            self.beat_counter = 0

    def _stop_metronome(self) -> None:
        """Stop the metronome timer."""
        self.metronome_timer.stop()

    def _metronome_beat(self) -> None:
        """Handle metronome beat."""
        self.beat_counter += 1
        
        # Play sound based on frequency setting
        should_beep = False
        if self.metronome_frequency == 1:
            should_beep = True
        elif self.metronome_frequency == 4:
            should_beep = (self.beat_counter % 4 == 1)
        elif self.metronome_frequency == 8:
            should_beep = (self.beat_counter % 8 == 1)
        
        if should_beep and self.metronome_enabled:
            self._play_metronome_sound()

    def _play_metronome_sound(self) -> None:
        """Play metronome sound (simplified implementation)."""
        # In a full implementation, this would use QSound or similar
        # For now, we'll use a simple system beep
        try:
            import winsound
            frequency = 800  # Hz
            duration = 100   # ms
            winsound.Beep(frequency, duration)
        except ImportError:
            # Fallback for non-Windows systems
            print('\a')  # System bell

    def _on_text_changed(self) -> None:
        """Handle text changes in the typing input."""
        current_text = self.typing_input.toPlainText()
        current_time = time.perf_counter()
        
        # Start session and metronome on first keystroke
        if len(current_text) == 1 and len(self.keystrokes) == 0:
            self.session_start_time = datetime.datetime.now()
            if self.mode == "metronome_led":
                self._start_metronome()
        
        # Record keystroke timing
        if self.last_keystroke_time is not None:
            interval_ms = (current_time - self.last_keystroke_time) * 1000
            self.keystroke_intervals.append(interval_ms)
            
            # Update rolling intervals for variability calculation
            self.rolling_intervals.append(interval_ms)
            if len(self.rolling_intervals) > self.rolling_window_size:
                self.rolling_intervals.pop(0)
        
        self.last_keystroke_time = current_time
        
        # Track keystrokes and errors
        if len(current_text) > len(self.keystrokes):
            # New character typed
            char_index = len(self.keystrokes)
            if char_index < len(self.expected_text):
                expected_char = self.expected_text[char_index]
                typed_char = current_text[char_index] if char_index < len(current_text) else ''
                
                is_correct = typed_char == expected_char
                if not is_correct:
                    self.total_errors += 1
                
                # Record keystroke
                keystroke_data = {
                    'char': typed_char,
                    'expected': expected_char,
                    'correct': is_correct,
                    'timestamp': current_time,
                    'is_backspace': False,
                    'text_index': char_index  # Position in expected text
                }
                self.keystrokes.append(keystroke_data)
        
        elif len(current_text) < len(self.keystrokes):
            # Backspace detected
            self.keystrokes = self.keystrokes[:len(current_text)]
        
        self.total_keystrokes = len(self.keystrokes)
        
        # Update UI
        self._update_highlighting()
        self._update_metrics()
        self._update_progress_bars()
        
        # Check for completion
        if current_text == self.expected_text:
            self._on_completion()

    def _update_highlighting(self) -> None:
        """Update text highlighting based on typing progress."""
        cursor = self.text_display.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        
        # Reset formatting
        format_normal = QTextCharFormat()
        format_normal.setForeground(QColor(0, 0, 0))
        format_normal.setFontWeight(QFont.Weight.Normal)
        format_normal.setFontItalic(False)
        cursor.setCharFormat(format_normal)
        
        # Apply character-by-character formatting
        current_text = self.typing_input.toPlainText()
        
        for i, _char in enumerate(self.display_text):
            cursor.setPosition(i)
            cursor.setPosition(i + 1, QTextCursor.MoveMode.KeepAnchor)
            
            if i < len(current_text):
                if i < len(self.expected_text) and current_text[i] == self.expected_text[i]:
                    # Correct character - green italic
                    format_correct = QTextCharFormat()
                    format_correct.setForeground(QColor(0, 128, 0))
                    format_correct.setFontItalic(True)
                    cursor.setCharFormat(format_correct)
                else:
                    # Incorrect character - red bold
                    format_incorrect = QTextCharFormat()
                    format_incorrect.setForeground(QColor(255, 0, 0))
                    format_incorrect.setFontWeight(QFont.Weight.Bold)
                    cursor.setCharFormat(format_incorrect)
            else:
                # Untyped character - normal black
                cursor.setCharFormat(format_normal)

    def _update_metrics(self) -> None:
        """Update consistency metrics display."""
        # Current speed
        if len(self.keystroke_intervals) > 0:
            current_speed = self.keystroke_intervals[-1]
            self.current_speed_label.setText(f"{current_speed:.0f}ms/keystroke")
        else:
            self.current_speed_label.setText("--ms/keystroke")
        
        # Variability calculation
        if len(self.rolling_intervals) >= 3:
            self.current_variability = statistics.stdev(self.rolling_intervals)
            self.variability_label.setText(f"±{self.current_variability:.0f}ms")
            
            # Update consistency bar
            variability_clamped = min(self.current_variability, 200)
            self.consistency_bar.setValue(int(variability_clamped))
            
            # Color coding and text
            if self.current_variability < 50:
                self.consistency_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
                self.consistency_bar.setFormat("Excellent Consistency")
            elif self.current_variability < 100:
                self.consistency_bar.setStyleSheet("QProgressBar::chunk { background-color: #FFEB3B; }")
                self.consistency_bar.setFormat("Good Consistency")
            elif self.current_variability < 200:
                self.consistency_bar.setStyleSheet("QProgressBar::chunk { background-color: #FF9800; }")
                self.consistency_bar.setFormat("Moderate Consistency")
            else:
                self.consistency_bar.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
                self.consistency_bar.setFormat("Poor Consistency")
        else:
            self.variability_label.setText("±0ms")
            self.consistency_bar.setValue(0)
            self.consistency_bar.setFormat("Building Data...")
        
        # Update target speed for user-led mode
        if self.mode == "user_led":
            self._update_target_speed_display()

    def _update_progress_bars(self) -> None:
        """Update progress bars."""
        expected_chars = len(self.expected_text)
        current_chars = len(self.typing_input.toPlainText())
        
        # Characters progress
        if expected_chars > 0:
            chars_progress = min(100, int((current_chars / expected_chars) * 100))
            self.chars_progress.setValue(chars_progress)
            self.chars_progress.setFormat(f"{current_chars}/{expected_chars} ({chars_progress}%)")
        
        # Errors progress
        error_budget = max(1, int(expected_chars * 0.05))  # 5% error budget
        if error_budget > 0:
            error_progress = min(100, int((self.total_errors / error_budget) * 100))
            self.errors_progress.setValue(error_progress)
            self.errors_progress.setFormat(f"{self.total_errors}/{error_budget}")
            
            # Color coding
            if self.total_errors > error_budget:
                self.errors_progress.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
            else:
                self.errors_progress.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")

    def _on_completion(self) -> None:
        """Handle completion of the typing session."""
        self.session_end_time = datetime.datetime.now()
        self.session_completed = True
        self._stop_metronome()
        
        # Calculate final stats
        if self.session_start_time is not None and self.session_end_time is not None:
            total_time = (self.session_end_time - self.session_start_time).total_seconds()
        else:
            total_time = 0.0
        
        # Consistency rating
        if self.current_variability < 50:
            consistency_rating = "Excellent"
        elif self.current_variability < 100:
            consistency_rating = "Good"
        elif self.current_variability < 200:
            consistency_rating = "Moderate"
        else:
            consistency_rating = "Poor"
        
        # Show completion dialog
        from PySide6.QtWidgets import QMessageBox
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Session Complete!")
        msg.setText("Consistency typing session completed!")
        msg.setInformativeText(
            f"Time: {total_time:.1f}s\n"
            f"Variability: ±{self.current_variability:.0f}ms\n"
            f"Consistency: {consistency_rating}\n"
            f"Errors: {self.total_errors}"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        
        self.accept()

    def _reset_session(self) -> None:
        """Reset the session to initial state."""
        self.session_start_time = datetime.datetime.now()
        self.session_end_time = None
        self.session_completed = False
        self.keystrokes.clear()
        self.keystroke_intervals.clear()
        self.rolling_intervals.clear()
        self.total_errors = 0
        self.total_keystrokes = 0
        self.last_keystroke_time = None
        self.current_variability = 0.0
        self.beat_counter = 0
        
        self._stop_metronome()
        
        # Reset UI
        self.typing_input.clear()
        self.typing_input.setReadOnly(False)
        self._update_highlighting()
        self._update_metrics()
        self._update_progress_bars()
        
        # Reset input background
        palette = self.typing_input.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        self.typing_input.setPalette(palette)
        self.typing_input.setFocus()
