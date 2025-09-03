"""Keyboard dialog for adding/editing keyboards."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from models.keyboard import Keyboard


class KeyboardDialog(QDialog):
    """Dialog for adding or editing a keyboard."""

    def __init__(
        self,
        user_id: str,
        keyboard: Optional[Keyboard] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the keyboard dialog.

        Args:
            user_id: ID of the user this keyboard belongs to.
            keyboard: Optional keyboard to edit. If None, create a new keyboard.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.user_id = user_id
        self.keyboard = keyboard
        self.setWindowTitle("Edit Keyboard" if keyboard else "Add Keyboard")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Form layout for keyboard details
        form_layout = QFormLayout()

        # Keyboard name field
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter keyboard name")
        form_layout.addRow("Keyboard Name:", self.name_edit)

        # Speed input mode selection
        speed_mode_layout = QHBoxLayout()
        self.ms_radio = QRadioButton("Milliseconds per keystroke")
        self.wpm_radio = QRadioButton("Words per minute (WPM)")
        self.ms_radio.setChecked(True)  # Default to ms mode
        
        # Button group to ensure only one is selected
        self.speed_mode_group = QButtonGroup()
        self.speed_mode_group.addButton(self.ms_radio)
        self.speed_mode_group.addButton(self.wpm_radio)
        
        speed_mode_layout.addWidget(self.ms_radio)
        speed_mode_layout.addWidget(self.wpm_radio)
        form_layout.addRow("Speed Input Mode:", speed_mode_layout)

        # Target speed fields (both ms and WPM)
        self.target_ms_spinbox = QSpinBox()
        self.target_ms_spinbox.setMinimum(50)  # Reasonable minimum (very fast)
        self.target_ms_spinbox.setMaximum(5000)  # Reasonable maximum (very slow)
        self.target_ms_spinbox.setValue(600)  # Default value
        self.target_ms_spinbox.setSuffix(" ms")  # Add ms suffix
        self.target_ms_spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.target_ms_spinbox.setToolTip("Target milliseconds per keystroke (speed goal)")

        self.target_wpm_spinbox = QDoubleSpinBox()
        self.target_wpm_spinbox.setMinimum(12.0)  # Corresponds to 1000ms (60000/(1000*5))
        self.target_wpm_spinbox.setMaximum(240.0)  # Corresponds to 50ms (60000/(50*5))
        self.target_wpm_spinbox.setValue(20.0)  # Default value (corresponds to 600ms)
        self.target_wpm_spinbox.setSuffix(" WPM")
        self.target_wpm_spinbox.setDecimals(1)
        self.target_wpm_spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.target_wpm_spinbox.setToolTip("Target words per minute (speed goal)")
        self.target_wpm_spinbox.setVisible(False)  # Initially hidden

        form_layout.addRow("Target Speed:", self.target_ms_spinbox)
        form_layout.addRow("", self.target_wpm_spinbox)  # Empty label for WPM field

        # Connect radio button changes to update UI
        self.ms_radio.toggled.connect(self._on_speed_mode_changed)
        self.wpm_radio.toggled.connect(self._on_speed_mode_changed)
        
        # Connect value changes to sync between fields
        self.target_ms_spinbox.valueChanged.connect(self._on_ms_value_changed)
        self.target_wpm_spinbox.valueChanged.connect(self._on_wpm_value_changed)

        # Populate fields if editing
        if self.keyboard:
            self.name_edit.setText(self.keyboard.keyboard_name or "")
            self.target_ms_spinbox.setValue(self.keyboard.target_ms_per_keystroke)
            # Update WPM field to match
            wpm_value = Keyboard.ms_per_keystroke_to_wpm(self.keyboard.target_ms_per_keystroke)
            self.target_wpm_spinbox.setValue(wpm_value)

        layout.addLayout(form_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _on_speed_mode_changed(self) -> None:
        """Handle speed input mode change between ms and WPM."""
        if self.ms_radio.isChecked():
            self.target_ms_spinbox.setVisible(True)
            self.target_wpm_spinbox.setVisible(False)
        else:
            self.target_ms_spinbox.setVisible(False)
            self.target_wpm_spinbox.setVisible(True)

    def _on_ms_value_changed(self, value: int) -> None:
        """Handle ms per keystroke value change - update WPM field."""
        try:
            wpm_value = Keyboard.ms_per_keystroke_to_wpm(value)
            # Temporarily disconnect to avoid circular updates
            self.target_wpm_spinbox.valueChanged.disconnect()
            self.target_wpm_spinbox.setValue(wpm_value)
            self.target_wpm_spinbox.valueChanged.connect(self._on_wpm_value_changed)
        except ValueError:
            # Handle edge cases where conversion might fail
            pass

    def _on_wpm_value_changed(self, value: float) -> None:
        """Handle WPM value change - update ms per keystroke field."""
        try:
            ms_value = Keyboard.wpm_to_ms_per_keystroke(value)
            # Temporarily disconnect to avoid circular updates
            self.target_ms_spinbox.valueChanged.disconnect()
            self.target_ms_spinbox.setValue(ms_value)
            self.target_ms_spinbox.valueChanged.connect(self._on_ms_value_changed)
        except ValueError:
            # Handle edge cases where conversion might fail
            pass

    def validate_and_accept(self) -> None:
        """Validate input and accept the dialog if valid."""
        name = self.name_edit.text().strip()
        
        # Always use the ms value as the source of truth (it's what gets stored)
        target_ms = self.target_ms_spinbox.value()

        if not name:
            QMessageBox.warning(self, "Validation Error", "Keyboard name is required.")
            self.name_edit.setFocus()
            return

        # Validate target ms value
        if target_ms < 50 or target_ms > 5000:
            QMessageBox.warning(
                self, "Validation Error", "Target speed must be between 50 and 5000 milliseconds."
            )
            # Focus on the currently visible field
            if self.ms_radio.isChecked():
                self.target_ms_spinbox.setFocus()
            else:
                self.target_wpm_spinbox.setFocus()
            return

        # Create or update keyboard object
        if self.keyboard:
            self.keyboard.keyboard_name = name
            self.keyboard.target_ms_per_keystroke = target_ms
        else:
            self.keyboard = Keyboard(
                keyboard_id="",  # Will be generated by the manager
                user_id=self.user_id,
                keyboard_name=name,
                target_ms_per_keystroke=target_ms,
            )

        self.accept()

    def get_keyboard(self) -> Optional[Keyboard]:
        """Get the keyboard object with updated values.

        Returns:
            The updated or new keyboard object, or None if dialog was cancelled.
        """
        return self.keyboard
