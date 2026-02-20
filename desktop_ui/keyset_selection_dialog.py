"""Keyset Selection Dialog.

A simple modal dialog that allows users to select a keyset for a given keyboard.
Returns either None (if cancelled) or a tuple of two sorted lists: (mastered_keys, current_keys).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from adapters.keyset_manager_adapter import KeysetManagerAdapter
from db.database_manager import DatabaseManager
from helpers.debug_util import DebugUtil


class KeysetSelectionDialog(QDialog):
    """Dialog to select a keyset and retrieve its mastered and current keys.

    Args:
        keyboard_id: The keyboard ID to list keysets for
        db_manager: Active database manager
        parent: Optional parent widget
    """

    def __init__(
        self,
        *,
        keyboard_id: str,
        db_manager: DatabaseManager,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        """Initialize the keyset selection dialog.

        Args:
            keyboard_id: The keyboard ID to list keysets for (named parameter).
            db_manager: Active database manager instance.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.debug_util = DebugUtil()
        self.db = db_manager
        self.keyboard_id = keyboard_id
        self.manager = KeysetManagerAdapter(db=self.db, debug_util=self.debug_util)

        # Store the result
        self._selected_mastered_keys: Optional[List[str]] = None
        self._selected_current_keys: Optional[List[str]] = None

        self.setWindowTitle("Select Keyset")
        self.setMinimumSize(400, 300)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
        self.setModal(True)

        # Load keysets for this keyboard
        self.manager.preload_keysets_for_keyboard(keyboard_id=self.keyboard_id)
        self.keysets = self.manager.get_cached_keysets()

        # Build UI
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title label
        title_label = QLabel("<h2>Select a Keyset</h2>")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Instruction label
        instruction_label = QLabel(
            "Choose a keyset to get its mastered keys (from earlier keysets) "
            "and current keys (from this keyset)."
        )
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)

        # List of keysets
        self.keysets_list = QListWidget()
        self.keysets_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )

        # Populate the list
        if not self.keysets:
            item = QListWidgetItem("No keysets available for this keyboard")
            item.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
            self.keysets_list.addItem(item)
        else:
            for keyset in self.keysets:
                # Display: "Order 1: Home Row (4 keys)"
                key_count = len(keyset.keys)
                plural = "s" if key_count != 1 else ""
                display_text = (
                    f"Order {keyset.progression_order}: "
                    f"{keyset.keyset_name} ({key_count} key{plural})"
                )
                item = QListWidgetItem(display_text)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, keyset.keyset_id)
                self.keysets_list.addItem(item)

        # Select the first item by default if available
        if self.keysets:
            self.keysets_list.setCurrentRow(0)

        layout.addWidget(self.keysets_list)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        # Disable OK button if no keysets
        if not self.keysets:
            button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        layout.addWidget(button_box)

    def _on_accept(self) -> None:
        """Handle OK button click - retrieve keys and accept dialog."""
        current_item = self.keysets_list.currentItem()
        if not current_item:
            self.reject()
            return

        keyset_id = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not keyset_id:
            self.reject()
            return

        # Get mastered and current keys
        mastered_keys, current_keys = self.manager.get_mastered_and_current_keys(
            keyboard_id=self.keyboard_id,
            keyset_id=keyset_id,
        )

        # Sort both lists
        self._selected_mastered_keys = sorted(mastered_keys)
        self._selected_current_keys = sorted(current_keys)

        self.accept()

    def get_selected_keys(self) -> Optional[Tuple[List[str], List[str]]]:
        """Get the selected keyset's keys.

        Returns:
            Tuple of (mastered_keys, current_keys) if a keyset was selected,
            None if the dialog was cancelled.
            Both lists are sorted alphabetically.
        """
        if self._selected_mastered_keys is None or self._selected_current_keys is None:
            return None
        return (self._selected_mastered_keys, self._selected_current_keys)


def select_keyset_keys(
    *,
    keyboard_id: str,
    db_manager: DatabaseManager,
    parent: Optional[QtWidgets.QWidget] = None,
) -> Optional[Tuple[List[str], List[str]]]:
    """Show keyset selection dialog and return selected keys.

    Convenience function that shows the dialog and returns the result in one call.

    Args:
        keyboard_id: The keyboard ID to list keysets for (named parameter).
        db_manager: Active database manager instance.
        parent: Optional parent widget.

    Returns:
        Tuple of (mastered_keys, current_keys) if a keyset was selected and OK was clicked,
        None if the dialog was cancelled or no selection was made.
        Both lists are sorted alphabetically.

    Example:
        >>> result = select_keyset_keys(keyboard_id="some-uuid", db_manager=db)
        >>> if result:
        >>>     mastered, current = result
        >>>     print(f"Mastered: {mastered}, Current: {current}")
    """
    dialog = KeysetSelectionDialog(
        keyboard_id=keyboard_id,
        db_manager=db_manager,
        parent=parent,
    )

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_selected_keys()
    return None
