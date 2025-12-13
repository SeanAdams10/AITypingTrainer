"""Spike: Keyset Selector with Modern UI.

A simple scaffold demonstrating keyset selection functionality with:
- Keyboard selection dropdown
- Selected keys text display
- Keyset selection dialog with progression-aware key accumulation

Uses the same database connection pattern as admin.py.
"""

import os
import sys

# Ensure project root is in sys.path before any project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from db.database_manager import ConnectionType, DatabaseManager
from entities.keyset import Keyset
from helpers.debug_util import DebugUtil
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager
from models.user import User
from models.user_manager import UserManager
from repositories.keyset_repository_postgres import PostgresKeysetRepository
from use_cases.keyset_collection import KeysetCollection

# Modern stylesheet for the application
MODERN_STYLESHEET = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog, QWidget#mainWidget {
    background-color: #f5f7fa;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #e0e4e8;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    background-color: white;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #2c3e50;
}

QComboBox {
    padding: 8px 12px;
    border: 1px solid #dce1e6;
    border-radius: 6px;
    background-color: white;
    min-height: 20px;
}

QComboBox:hover {
    border-color: #3498db;
}

QComboBox:focus {
    border-color: #2980b9;
    outline: none;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QLineEdit {
    padding: 10px 14px;
    border: 1px solid #dce1e6;
    border-radius: 6px;
    background-color: white;
    font-size: 14px;
}

QLineEdit:focus {
    border-color: #3498db;
}

QLineEdit:read-only {
    background-color: #f8f9fa;
    color: #495057;
}

QPushButton {
    padding: 10px 20px;
    border: none;
    border-radius: 6px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton#primaryButton {
    background-color: #3498db;
    color: white;
}

QPushButton#primaryButton:hover {
    background-color: #2980b9;
}

QPushButton#primaryButton:pressed {
    background-color: #2472a4;
}

QPushButton#secondaryButton {
    background-color: #ecf0f1;
    color: #2c3e50;
    border: 1px solid #dce1e6;
}

QPushButton#secondaryButton:hover {
    background-color: #dfe6e9;
}

QListWidget {
    border: 1px solid #dce1e6;
    border-radius: 6px;
    background-color: white;
    padding: 4px;
}

QListWidget::item {
    padding: 10px 12px;
    border-radius: 4px;
    margin: 2px 0;
}

QListWidget::item:hover {
    background-color: #f0f4f8;
}

QListWidget::item:selected {
    background-color: #3498db;
    color: white;
}

QLabel#headerLabel {
    font-size: 24px;
    font-weight: bold;
    color: #2c3e50;
    padding: 10px 0;
}

QLabel#sectionLabel {
    font-size: 13px;
    color: #7f8c8d;
    font-weight: 500;
}

QDialogButtonBox QPushButton {
    min-width: 80px;
}
"""


class KeysetSelectionDialog(QDialog):
    """Dialog for selecting a keyset from available keysets for a keyboard."""

    def __init__(
        self,
        keysets: List[Keyset],
        current_keyset_id: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the keyset selection dialog.

        Args:
            keysets: List of available keysets ordered by progression
            current_keyset_id: Currently selected keyset ID (for pre-selection)
            parent: Parent widget
        """
        super().__init__(parent)
        self.keysets = keysets
        self.selected_keyset: Optional[Keyset] = None

        self.setWindowTitle("Select Keyset")
        self.setMinimumSize(400, 450)
        self.setModal(True)

        self._setup_ui(current_keyset_id)

    def _setup_ui(self, current_keyset_id: Optional[str]) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("Select a Keyset")
        header.setObjectName("headerLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Description
        desc = QLabel("Choose a keyset to load its keys and all keys from earlier progressions.")
        desc.setObjectName("sectionLabel")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # Keyset list
        self.keyset_list = QListWidget()
        self.keyset_list.setAlternatingRowColors(True)

        selected_index = 0
        for i, keyset in enumerate(self.keysets):
            key_chars = ", ".join(sorted([k.key_char for k in keyset.keys]))
            item_text = f"{keyset.keyset_name} (Progression {keyset.progression_order})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, keyset)
            item.setToolTip(f"Keys: {key_chars}")
            self.keyset_list.addItem(item)

            if keyset.keyset_id == current_keyset_id:
                selected_index = i

        if self.keysets:
            self.keyset_list.setCurrentRow(selected_index)

        self.keyset_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.keyset_list)

        # Preview section
        preview_group = QGroupBox("Keys Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(preview_group)

        # Update preview when selection changes
        self.keyset_list.currentRowChanged.connect(self._update_preview)
        self._update_preview()

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _update_preview(self) -> None:
        """Update the preview label with accumulated keys."""
        current_item = self.keyset_list.currentItem()
        if not current_item:
            self.preview_label.setText("No keyset selected")
            return

        selected_keyset: Keyset = current_item.data(Qt.ItemDataRole.UserRole)
        accumulated_keys = self._get_accumulated_keys(selected_keyset)

        if accumulated_keys:
            self.preview_label.setText(f"Keys: {' '.join(sorted(accumulated_keys))}")
        else:
            self.preview_label.setText("No keys in selected progression")

    def _get_accumulated_keys(self, target_keyset: Keyset) -> List[str]:
        """Get all keys from target keyset and all earlier progressions."""
        keys = set()
        for keyset in self.keysets:
            if keyset.progression_order <= target_keyset.progression_order:
                for key in keyset.keys:
                    keys.add(key.key_char)
        return sorted(list(keys))

    def accept(self) -> None:
        """Handle dialog acceptance."""
        current_item = self.keyset_list.currentItem()
        if current_item:
            self.selected_keyset = current_item.data(Qt.ItemDataRole.UserRole)
        super().accept()

    def get_selected_keyset(self) -> Optional[Keyset]:
        """Get the selected keyset."""
        return self.selected_keyset


class KeysetSelectorSpike(QWidget):
    """Main window for the keyset selector spike."""

    keyset_changed = Signal(str)  # Emits the accumulated keys string

    def __init__(self) -> None:
        """Initialize the keyset selector spike window."""
        super().__init__()
        self.setWindowTitle("Keyset Selector - Spike")
        self.setMinimumSize(600, 400)
        self.setObjectName("mainWidget")

        # Initialize database connection (same pattern as admin.py)
        self.debug_util = DebugUtil()
        self.db_manager = DatabaseManager(
            connection_type=ConnectionType.CLOUD,
            debug_util=self.debug_util,
        )
        self.db_manager.init_tables()

        # Initialize managers
        self.user_manager = UserManager(db_manager=self.db_manager)
        self.keyboard_manager = KeyboardManager(db_manager=self.db_manager)

        # Initialize keyset repository and collection
        self.keyset_repo = PostgresKeysetRepository(self.db_manager)
        self.keyset_collection = KeysetCollection(self.keyset_repo)

        # State
        self.current_user: Optional[User] = None
        self.current_keyboard: Optional[Keyboard] = None
        self.current_keyset: Optional[Keyset] = None
        self.keysets: List[Keyset] = []

        self._setup_ui()
        self._load_users()
        self._center_on_screen()

    def _center_on_screen(self) -> None:
        """Center the window on screen."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def _setup_ui(self) -> None:
        """Set up the main UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QLabel("Keyset Selector")
        header.setObjectName("headerLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        # Selection group
        selection_group = QGroupBox("Selection")
        selection_layout = QVBoxLayout(selection_group)
        selection_layout.setSpacing(12)

        # User selection row
        user_row = QHBoxLayout()
        user_label = QLabel("User:")
        user_label.setObjectName("sectionLabel")
        user_label.setFixedWidth(80)
        self.user_combo = QComboBox()
        self.user_combo.currentIndexChanged.connect(self._on_user_changed)
        user_row.addWidget(user_label)
        user_row.addWidget(self.user_combo)
        selection_layout.addLayout(user_row)

        # Keyboard selection row
        keyboard_row = QHBoxLayout()
        keyboard_label = QLabel("Keyboard:")
        keyboard_label.setObjectName("sectionLabel")
        keyboard_label.setFixedWidth(80)
        self.keyboard_combo = QComboBox()
        self.keyboard_combo.setEnabled(False)
        self.keyboard_combo.currentIndexChanged.connect(self._on_keyboard_changed)
        keyboard_row.addWidget(keyboard_label)
        keyboard_row.addWidget(self.keyboard_combo)
        selection_layout.addLayout(keyboard_row)

        main_layout.addWidget(selection_group)

        # Keys group
        keys_group = QGroupBox("Selected Keys")
        keys_layout = QVBoxLayout(keys_group)
        keys_layout.setSpacing(12)

        # Keys display with select button
        keys_row = QHBoxLayout()

        self.keys_edit = QLineEdit()
        self.keys_edit.setReadOnly(True)
        self.keys_edit.setPlaceholderText("No keyset selected - click button to select")
        keys_row.addWidget(self.keys_edit)

        self.select_keyset_btn = QPushButton("  Select Keyset...")
        self.select_keyset_btn.setObjectName("primaryButton")
        self.select_keyset_btn.setEnabled(False)
        # Use a standard icon for the button
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        self.select_keyset_btn.setIcon(icon)
        self.select_keyset_btn.clicked.connect(self._on_select_keyset)
        keys_row.addWidget(self.select_keyset_btn)

        keys_layout.addLayout(keys_row)

        # Current keyset info
        self.keyset_info_label = QLabel("No keyset selected")
        self.keyset_info_label.setObjectName("sectionLabel")
        self.keyset_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        keys_layout.addWidget(self.keyset_info_label)

        main_layout.addWidget(keys_group)

        # Spacer
        main_layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondaryButton")
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(self.close)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def _load_users(self) -> None:
        """Load users into the combo box."""
        self.user_combo.clear()
        try:
            users = self.user_manager.list_all_users()
            for user in users:
                display = f"{user.first_name} {user.surname}"
                self.user_combo.addItem(display, user)

            if self.user_combo.count() > 0:
                self._on_user_changed(0)
        except Exception as e:
            print(f"Error loading users: {e}")

    def _on_user_changed(self, index: int) -> None:
        """Handle user selection change."""
        if index < 0:
            self.current_user = None
            self.keyboard_combo.clear()
            self.keyboard_combo.setEnabled(False)
            return

        self.current_user = self.user_combo.currentData()
        if self.current_user and self.current_user.user_id:
            self._load_keyboards(str(self.current_user.user_id))

    def _load_keyboards(self, user_id: str) -> None:
        """Load keyboards for the selected user."""
        self.keyboard_combo.clear()
        self.keyboard_combo.setEnabled(False)
        self.current_keyboard = None
        self._clear_keyset_selection()

        try:
            keyboards = self.keyboard_manager.list_keyboards_for_user(user_id=user_id)
            for keyboard in keyboards:
                self.keyboard_combo.addItem(keyboard.keyboard_name, keyboard)

            if self.keyboard_combo.count() > 0:
                self.keyboard_combo.setEnabled(True)
                self._on_keyboard_changed(0)
        except Exception as e:
            print(f"Error loading keyboards: {e}")

    def _on_keyboard_changed(self, index: int) -> None:
        """Handle keyboard selection change."""
        if index < 0:
            self.current_keyboard = None
            self._clear_keyset_selection()
            return

        self.current_keyboard = self.keyboard_combo.currentData()
        self._clear_keyset_selection()

        if self.current_keyboard and self.current_keyboard.keyboard_id:
            self._load_keysets(str(self.current_keyboard.keyboard_id))

    def _load_keysets(self, keyboard_id: str) -> None:
        """Load keysets for the selected keyboard."""
        try:
            self.keysets = self.keyset_collection.list_for_keyboard(keyboard_id=keyboard_id)
            self.select_keyset_btn.setEnabled(len(self.keysets) > 0)

            if not self.keysets:
                self.keyset_info_label.setText("No keysets available for this keyboard")
        except Exception as e:
            print(f"Error loading keysets: {e}")
            self.keysets = []
            self.select_keyset_btn.setEnabled(False)

    def _clear_keyset_selection(self) -> None:
        """Clear the current keyset selection."""
        self.current_keyset = None
        self.keysets = []
        self.keys_edit.clear()
        self.keyset_info_label.setText("No keyset selected")
        self.select_keyset_btn.setEnabled(False)

    def _on_select_keyset(self) -> None:
        """Handle the select keyset button click."""
        if not self.keysets:
            return

        current_keyset_id = str(self.current_keyset.keyset_id) if self.current_keyset else None

        dialog = KeysetSelectionDialog(
            keysets=self.keysets,
            current_keyset_id=current_keyset_id,
            parent=self,
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.get_selected_keyset()
            if selected:
                self.current_keyset = selected
                accumulated_keys = self._get_accumulated_keys(selected)

                # Update the keys text box
                self.keys_edit.setText(" ".join(accumulated_keys))

                # Update info label
                self.keyset_info_label.setText(
                    f"Keyset: {selected.keyset_name} (Progression {selected.progression_order}) "
                    f"- {len(accumulated_keys)} keys"
                )

                # Emit signal
                self.keyset_changed.emit(" ".join(accumulated_keys))
        # If cancelled, keys_edit remains unchanged (requirement satisfied)

    def _get_accumulated_keys(self, target_keyset: Keyset) -> List[str]:
        """Get all keys from target keyset and all earlier progressions."""
        keys = set()
        for keyset in self.keysets:
            if keyset.progression_order <= target_keyset.progression_order:
                for key in keyset.keys:
                    keys.add(key.key_char)
        return sorted(list(keys))


def main() -> None:
    """Launch the keyset selector spike application."""
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_STYLESHEET)
    app.setStyle("Fusion")

    window = KeysetSelectorSpike()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
