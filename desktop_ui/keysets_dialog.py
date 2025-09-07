"""Keysets Editor Dialog.

Allows users to add/edit/delete keysets for a keyboard and manage the keys in a keyset.
Provides a callable method `return_keyset_keys()` that returns a list of (key_char, is_new_key).

This dialog uses KeysetManager (application-managed history) and DatabaseManager.
It honors DebugUtil quiet/loud mode for debug messages.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from db.database_manager import DatabaseManager
from helpers.debug_util import DebugUtil
from models.keyset import Keyset, KeysetKey
from models.keyset_manager import KeysetManager


class KeysetsDialog(QDialog):
    """Dialog to manage Keysets for a specific keyboard.

    Args:
        db_manager: Active database manager
        keyboard_id: The target keyboard id
        parent: Optional parent widget
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        keyboard_id: str,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        """Initialize the dialog.

        Args:
            db_manager: Active database manager instance.
            keyboard_id: Target keyboard id.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.debug_util = DebugUtil()
        self.db = db_manager
        self.keyboard_id = keyboard_id
        self.manager = KeysetManager(self.db, self.debug_util)

        # Preload all keysets and keys for this keyboard into manager cache
        self.manager.preload_keysets_for_keyboard(self.keyboard_id)

        self.setWindowTitle("Keysets Editor")
        self.setMinimumSize(700, 500)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)

        # In-memory staged keysets keyed by item id (real keyset_id or temp-*)
        self._staged: dict[str, Keyset] = {}
        self._dirty: bool = False

        # Left: Keysets list
        self.keysets_list = QListWidget()
        self.keysets_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # Refresh on any selection-related change to avoid stale RHS state
        self.keysets_list.currentRowChanged.connect(self._on_keyset_selected)
        self.keysets_list.itemSelectionChanged.connect(self._on_list_selection_changed)
        self.keysets_list.currentItemChanged.connect(
            lambda _cur, _prev: self._on_list_selection_changed()
        )
        self.keysets_list.itemClicked.connect(lambda _item: self._on_list_selection_changed())

        # Right: Editor
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self._on_form_changed)
        self.order_spin = QSpinBox()
        self.order_spin.setMinimum(1)
        self.order_spin.valueChanged.connect(self._on_form_changed)
        self.keys_list = QListWidget()
        self.keys_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        add_key_btn = QPushButton("Add Key")
        add_key_btn.clicked.connect(self._on_add_key)
        add_string_btn = QPushButton("Add String…")
        add_string_btn.clicked.connect(self._on_add_string)
        add_from_other_btn = QPushButton("Add from other keyset…")
        add_from_other_btn.clicked.connect(self._on_add_from_other)
        del_key_btn = QPushButton("Delete Key")
        del_key_btn.clicked.connect(self._on_delete_key)
        toggle_new_btn = QPushButton("Toggle Emphasis")
        toggle_new_btn.clicked.connect(self._on_toggle_new)

        self.edit_details_btn = QPushButton("Edit Details")
        self.edit_details_btn.clicked.connect(self._on_edit_details)

        # Initialize save button before using it in the layout
        self.save_current_btn = QPushButton("Save")
        try:
            # Attempt to use a standard save icon if available
            self.save_current_btn.setIcon(
                self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton)
            )
        except Exception:
            pass
        self.save_current_btn.clicked.connect(self._on_save_current)
        # Initially disabled until there are changes
        self.save_current_btn.setEnabled(False)

        # Buttons for keysets
        new_btn = QPushButton("New Keyset")
        new_btn.clicked.connect(self._on_new_keyset)
        save_btn = QPushButton("Save Keyset")
        save_btn.clicked.connect(self._on_save_keyset)
        self.delete_btn = QPushButton("Delete Keyset")
        self.delete_btn.clicked.connect(self._on_delete_keyset)
        promote_btn = QPushButton("Promote")
        promote_btn.clicked.connect(self._on_promote)
        use_selected_btn = QPushButton("Use Selected")
        use_selected_btn.clicked.connect(self._on_use_selected)

        # Layouts
        left_group = QGroupBox("Keysets")
        left_v = QVBoxLayout(left_group)
        left_v.addWidget(self.keysets_list)
        left_v.addWidget(new_btn)
        left_v.addWidget(promote_btn)
        left_v.addWidget(self.delete_btn)
        left_v.addWidget(self.edit_details_btn)
        left_v.addWidget(use_selected_btn)

        right_group = QGroupBox("Editor")
        right_form = QFormLayout(right_group)
        right_form.addRow(QLabel("Name"), self.name_edit)
        right_form.addRow(QLabel("Order"), self.order_spin)
        right_form.addRow(QLabel("Keys"), self.keys_list)
        keys_btn_row = QHBoxLayout()
        keys_btn_row.addWidget(add_key_btn)
        keys_btn_row.addWidget(add_string_btn)
        keys_btn_row.addWidget(add_from_other_btn)
        keys_btn_row.addWidget(toggle_new_btn)
        keys_btn_row.addWidget(del_key_btn)
        right_form.addRow(keys_btn_row)

        # Save and Close buttons row
        save_close_row = QHBoxLayout()
        save_close_row.addStretch(1)  # Push buttons to the right
        save_close_row.addWidget(self.save_current_btn)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self._attempt_close)
        save_close_row.addWidget(close_btn)

        right_form.addRow(save_close_row)

        main = QHBoxLayout()
        main.addWidget(left_group, 1)
        main.addWidget(right_group, 2)

        # Main layout without the bottom button box (since we moved buttons into the right panel)
        self.setLayout(main)

        # Load data
        self._load_keysets()
        self._update_save_buttons()
        self._update_selection_dependent_buttons()

    # Public API
    def return_keyset_keys(self) -> List[Tuple[str, bool]]:
        """Return the keys (char, is_new_key) for the currently selected keyset."""
        item = self.keysets_list.currentItem()
        if not item:
            return []
        kid = str(item.data(QtCore.Qt.ItemDataRole.UserRole))
        # Prefer staged data if present
        staged = self._staged.get(kid)
        if staged is not None:
            return [(k.key_char, bool(k.is_new_key)) for k in staged.keys]
        return self.manager.get_keys_for_keyset(kid)

    def _on_use_selected(self) -> None:
        """Accept the dialog, indicating caller should read current selection."""
        if self._dirty:
            resp = QtWidgets.QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to use the selection without saving?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if resp != QtWidgets.QMessageBox.StandardButton.Yes:
                return
        self.accept()

    # Internals
    def _load_keysets(self) -> None:
        self.keysets_list.clear()
        keysets = self.manager.list_keysets_for_keyboard(self.keyboard_id)
        for ks in keysets:
            # Stage loaded keysets - ensure keyset_id is not None
            if ks.keyset_id:
                self._staged[ks.keyset_id] = ks
                it = QListWidgetItem(self._format_label(int(ks.progression_order), ks.keyset_name))
                it.setData(QtCore.Qt.ItemDataRole.UserRole, ks.keyset_id)
                self.keysets_list.addItem(it)
        if self.keysets_list.count() > 0:
            self.keysets_list.setCurrentRow(0)

    def _on_keyset_selected(self, row: int) -> None:
        item = self.keysets_list.item(row)
        if not item:
            self.name_edit.clear()
            self.order_spin.setValue(1)
            self.keys_list.clear()
            self._update_selection_dependent_buttons()
            return
        keyset_id = str(item.data(QtCore.Qt.ItemDataRole.UserRole))
        # Prefer staged version if exists
        ks = self._staged.get(keyset_id) or self.manager.get_keyset(keyset_id)
        if ks:
            self.name_edit.setText(ks.keyset_name)
            self.order_spin.setValue(int(ks.progression_order))
            self._render_keys(ks.keys)
        # Ensure buttons reflect that an item is selected
        self._update_selection_dependent_buttons()

    def _on_list_selection_changed(self) -> None:
        """Wrapper to refresh RHS and buttons whenever selection/click/current changes.

        This ensures that editing uses the currently selected item's details even if
        the user re-clicks the same row or selection changes via different signals.
        """
        self._on_keyset_selected(self.keysets_list.currentRow())

    def _render_keys(self, keys: List[KeysetKey]) -> None:
        self.keys_list.clear()
        # Sort keys alphabetically by key_char for display
        sorted_keys = sorted(keys, key=lambda x: str(x.key_char).lower())
        for k in sorted_keys:
            label = f"{k.key_char}  ({'new' if k.is_new_key else 'old'})"
            it = QListWidgetItem(label)
            it.setData(QtCore.Qt.ItemDataRole.UserRole, (k.key_id, k.key_char, k.is_new_key))
            self.keys_list.addItem(it)

    def _on_new_keyset(self) -> None:
        # Prompt for details first
        next_order = self._next_priority()
        details = self._prompt_details(initial_name="", initial_order=next_order)
        if details is None:
            return
        name, order = details
        self.name_edit.setText(name)
        self.order_spin.setValue(order)
        self.keys_list.clear()
        self.keysets_list.clearSelection()
        # todo changes needed here - don't do the next order in the UI, instead get this from the underlying classes

        # Create a staged keyset with temporary id
        temp_id = f"temp-{self.keysets_list.count() + 1}"
        staged = Keyset(
            keyset_id=None,  # Will be auto-generated when saved
            keyboard_id=self.keyboard_id,
            keyset_name=name,
            progression_order=int(order),
            keys=[],
        )
        staged.is_dirty = True
        self._staged[temp_id] = staged
        it = QListWidgetItem(self._format_label(int(order), name))
        it.setData(QtCore.Qt.ItemDataRole.UserRole, temp_id)
        self.keysets_list.addItem(it)
        self.keysets_list.setCurrentItem(it)
        self._dirty = True
        self._update_save_buttons()

    def _on_add_string(self) -> None:
        """Prompt for a string of keys and add unique characters as old keys."""
        text, ok = QtWidgets.QInputDialog.getText(self, "Add Keys", "Characters (string):")
        if not ok:
            return
        s = text
        if not s:
            return
        existing_chars = set()
        for i in range(self.keys_list.count()):
            _, key_char, _ = self.keys_list.item(i).data(QtCore.Qt.ItemDataRole.UserRole)
            existing_chars.add(str(key_char))

        # Collect new characters to add
        new_chars = []
        for ch in s:
            if len(ch) != 1:
                continue
            if ch in existing_chars:
                continue
            new_chars.append(ch)
            existing_chars.add(ch)

        # Sort new characters alphabetically
        new_chars.sort(key=str.lower)

        # Add each character in alphabetical order
        for ch in new_chars:
            it = QListWidgetItem(f"{ch}  (old)")
            it.setData(QtCore.Qt.ItemDataRole.UserRole, (None, ch, False))

            # Find the correct position to insert alphabetically
            insert_pos = 0
            for i in range(self.keys_list.count()):
                _, existing_char, _ = self.keys_list.item(i).data(QtCore.Qt.ItemDataRole.UserRole)
                if str(existing_char).lower() > ch.lower():
                    break
                insert_pos = i + 1

            self.keys_list.insertItem(insert_pos, it)

        if new_chars:
            self._sync_form_to_staged()
            self._dirty = True
            self._update_save_buttons()

    def _on_save_keyset(self) -> None:
        """Save the current keyset using the staged model."""
        self._sync_form_to_staged()
        item = self.keysets_list.currentItem()
        if not item:
            return
        kid = str(item.data(QtCore.Qt.ItemDataRole.UserRole))
        ks = self._staged.get(kid)
        if not ks or not ks.keyset_name:
            QtWidgets.QMessageBox.warning(self, "Validation", "Name is required")
            return

        try:
            # Use save_all_keysets with a single keyset for consistency
            success = self.manager.save_all_keysets([ks])
            if not success:
                QtWidgets.QMessageBox.warning(self, "Error", "Failed to save keyset")
                return

            QtWidgets.QMessageBox.information(self, "Saved", "Keyset saved successfully.")
            self._load_keysets()
            self._dirty = False
            self._update_save_buttons()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to save keyset: {e}")

    def _on_delete_keyset(self) -> None:
        item = self.keysets_list.currentItem()
        if not item:
            return
        kid = str(item.data(QtCore.Qt.ItemDataRole.UserRole))
        success = self.manager.delete_keyset(kid)
        if not success:
            QtWidgets.QMessageBox.warning(self, "Error", "Delete failed")
            return
        # Remove from staged as well
        self._staged.pop(kid, None)
        self._load_keysets()

    def _on_promote(self) -> None:
        item = self.keysets_list.currentItem()
        if not item:
            return
        kid = str(item.data(QtCore.Qt.ItemDataRole.UserRole))
        success = self.manager.promote_keyset(self.keyboard_id, kid)
        if not success:
            QtWidgets.QMessageBox.warning(self, "Error", "Promote failed")
        self._load_keysets()

    def _on_add_key(self) -> None:
        text, ok = QtWidgets.QInputDialog.getText(self, "Add Key", "Character:")
        if not ok:
            return
        ch = text.strip()
        if len(ch) != 1:
            QtWidgets.QMessageBox.warning(self, "Validation", "Key must be a single character")
            return
        # Check for duplicates
        for i in range(self.keys_list.count()):
            _, existing_char, _ = self.keys_list.item(i).data(QtCore.Qt.ItemDataRole.UserRole)
            if str(existing_char) == ch:
                QtWidgets.QMessageBox.warning(self, "Validation", "Key already exists")
                return

        # Insert in alphabetical order
        it = QListWidgetItem(f"{ch}  (old)")
        it.setData(QtCore.Qt.ItemDataRole.UserRole, (None, ch, False))

        # Find the correct position to insert alphabetically
        insert_pos = 0
        for i in range(self.keys_list.count()):
            _, existing_char, _ = self.keys_list.item(i).data(QtCore.Qt.ItemDataRole.UserRole)
            if str(existing_char).lower() > ch.lower():
                break
            insert_pos = i + 1

        self.keys_list.insertItem(insert_pos, it)
        self._sync_form_to_staged()
        self._dirty = True
        self._update_save_buttons()

    def _on_delete_key(self) -> None:
        row = self.keys_list.currentRow()
        if row >= 0:
            self.keys_list.takeItem(row)
            self._sync_form_to_staged()
            self._dirty = True
            self._update_save_buttons()

    def _on_toggle_new(self) -> None:
        item = self.keys_list.currentItem()
        if not item:
            return
        key_id, key_char, is_new = item.data(QtCore.Qt.ItemDataRole.UserRole)
        new_flag = not bool(is_new)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, (key_id, key_char, new_flag))
        item.setText(f"{key_char}  ({'new' if new_flag else 'old'})")
        self._sync_form_to_staged()
        self._dirty = True
        self._update_save_buttons()

    def _on_add_from_other(self) -> None:
        """Open a picker to select another staged keyset and import its keys."""
        if not self._staged:
            return
        current_item = self.keysets_list.currentItem()
        current_id = str(current_item.data(QtCore.Qt.ItemDataRole.UserRole)) if current_item else ""
        # Build selection dialog listing staged keysets (exclude current)
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Keyset to Import From")
        layout = QVBoxLayout(dlg)
        listw = QListWidget()
        id_by_row: list[str] = []
        for ks_id, ks in self._staged.items():
            if ks_id == current_id:
                continue
            listw.addItem(self._format_label(int(ks.progression_order), ks.keyset_name))
            id_by_row.append(ks_id)
        layout.addWidget(listw)

        # Preview label shows how many keys will be added / skipped
        preview = QLabel("Select a keyset to see preview…")
        layout.addWidget(preview)

        def update_preview() -> None:
            row = listw.currentRow()
            if row < 0 or row >= len(id_by_row):
                preview.setText("Select a keyset to see preview…")
                return
            src = self._staged.get(id_by_row[row])
            if not src:
                preview.setText("Select a keyset to see preview…")
                return
            existing_chars = set()
            for i in range(self.keys_list.count()):
                _, key_char, _ = self.keys_list.item(i).data(QtCore.Qt.ItemDataRole.UserRole)
                existing_chars.add(str(key_char))
            total = len(src.keys)
            to_add = sum(1 for k in src.keys if k.key_char not in existing_chars)
            skipped = total - to_add
            preview.setText(f"Will add {to_add} key(s), skip {skipped} duplicate(s)")

        listw.currentRowChanged.connect(lambda _idx: update_preview())
        update_preview()

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        row = listw.currentRow()
        if row < 0 or row >= len(id_by_row):
            return
        src_id = id_by_row[row]
        src = self._staged.get(src_id)
        if not src:
            return
        # Merge keys from src into current (avoid duplicates by key_char)
        existing_chars = set()
        for i in range(self.keys_list.count()):
            _, key_char, _ = self.keys_list.item(i).data(QtCore.Qt.ItemDataRole.UserRole)
            existing_chars.add(str(key_char))

        # Collect new keys to add and sort them alphabetically
        new_keys = []
        for k in src.keys:
            if k.key_char in existing_chars:
                continue
            new_keys.append(k)

        # Sort by key character alphabetically
        new_keys.sort(key=lambda x: str(x.key_char).lower())

        # Add each key in alphabetical order
        for k in new_keys:
            it = QListWidgetItem(f"{k.key_char}  ({'new' if k.is_new_key else 'old'})")
            it.setData(QtCore.Qt.ItemDataRole.UserRole, (None, k.key_char, bool(k.is_new_key)))

            # Find the correct position to insert alphabetically
            insert_pos = 0
            for i in range(self.keys_list.count()):
                _, existing_char, _ = self.keys_list.item(i).data(QtCore.Qt.ItemDataRole.UserRole)
                if str(existing_char).lower() > str(k.key_char).lower():
                    break
                insert_pos = i + 1

            self.keys_list.insertItem(insert_pos, it)

        if new_keys:
            self._sync_form_to_staged()
            self._dirty = True

    # --- Details dialog helpers ---
    def _prompt_details(self, initial_name: str, initial_order: int) -> Optional[tuple[str, int]]:
        """Open a simple dialog to edit keyset name and order."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Keyset Details")
        form = QFormLayout(dlg)
        name_edit = QLineEdit()
        name_edit.setText(initial_name)
        order_spin = QSpinBox()
        order_spin.setMinimum(1)
        order_spin.setValue(initial_order)
        form.addRow("Name", name_edit)
        form.addRow("Order", order_spin)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        form.addRow(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = name_edit.text().strip()
            if not name:
                return None
            return (name, int(order_spin.value()))
        return None

    def _on_edit_details(self) -> None:
        """Edit details for the currently selected keyset or current form."""
        # Prefer selected list item; if none, use current form values
        current_name = self.name_edit.text().strip()
        current_order = int(self.order_spin.value())
        details = self._prompt_details(initial_name=current_name, initial_order=current_order)
        if details is None:
            return
        name, order = details
        self.name_edit.setText(name)
        self.order_spin.setValue(order)
        # Update staged model and left list label
        self._sync_form_to_staged()
        item = self.keysets_list.currentItem()
        if item:
            item.setText(self._format_label(int(order), name))
        self._dirty = True
        self._update_save_buttons()
        self._update_selection_dependent_buttons()

    def _sync_form_to_staged(self) -> None:
        """Update the staged model for the currently selected keyset from the form."""
        item = self.keysets_list.currentItem()
        if not item:
            return
        kid = str(item.data(QtCore.Qt.ItemDataRole.UserRole))
        name = self.name_edit.text().strip()
        order = int(self.order_spin.value())
        keys: List[KeysetKey] = []
        for i in range(self.keys_list.count()):
            _, key_char, is_new = self.keys_list.item(i).data(QtCore.Qt.ItemDataRole.UserRole)
            keys.append(KeysetKey(key_char=str(key_char), is_new_key=bool(is_new)))
        staged = self._staged.get(kid)
        if staged is None:
            staged = Keyset(
                keyset_id=kid if not kid.startswith("temp-") else None,  # Use None for temp IDs
                keyboard_id=self.keyboard_id,
                keyset_name=name,
                progression_order=order,
                keys=keys,
            )
            self._staged[kid] = staged
        else:
            staged.keyset_name = name
            staged.progression_order = order
            staged.keys = keys
        # Any sync from the form means staged model differs from DB
        staged.is_dirty = True

    def _on_form_changed(self) -> None:
        """Mark dialog as dirty and sync staged on form edits."""
        self._dirty = True
        self._sync_form_to_staged()
        self._update_save_buttons()
        # todo: the form should not hold the dirty flag - that should be based on the class

    def _on_save_all(self) -> None:
        """Persist all staged keysets and their keys to the database."""
        try:
            # Ensure current form is synced
            self._sync_form_to_staged()

            # Use the new save_all_keysets method which handles INSERT vs UPDATE automatically
            keysets_to_save = list(self._staged.values())
            success = self.manager.save_all_keysets(keysets_to_save)

            if not success:
                QtWidgets.QMessageBox.critical(self, "Save Error", "Failed to save keysets")
                return

            QtWidgets.QMessageBox.information(self, "Saved", "All keysets saved successfully.")
            # Reload from DB to ensure UI is in sync and ordered
            self._load_keysets()
            self._dirty = False
            self._update_save_buttons()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save Error", f"Failed to save keysets: {e}")

    def _on_save_current(self) -> None:
        """Persist only the currently selected keyset and its keys."""
        try:
            self._sync_form_to_staged()
            item = self.keysets_list.currentItem()
            if not item:
                return
            kid = str(item.data(QtCore.Qt.ItemDataRole.UserRole))
            ks = self._staged.get(kid)
            if not ks or not ks.keyset_name:
                return

            # Use save_all_keysets with a single keyset
            success = self.manager.save_all_keysets([ks])
            if not success:
                QtWidgets.QMessageBox.critical(self, "Save Error", "Failed to save keyset")
                return

            QtWidgets.QMessageBox.information(self, "Saved", "Keyset saved.")
            self._load_keysets()
            self._dirty = False
            self._update_save_buttons()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save Error", f"Failed to save keyset: {e}")

    # --- Priority helpers and formatting ---
    def _next_priority(self) -> int:
        """Return next progression order as max(existing)+1 from staged and DB-loaded."""
        max_order = 0
        # Consider anything already staged
        for ks in self._staged.values():
            try:
                max_order = max(max_order, int(ks.progression_order))
            except Exception:
                pass
        if max_order == 0:
            # As a fallback, peek DB if staged was empty
            try:
                existing = self.manager.list_keysets_for_keyboard(self.keyboard_id)
                for ks in existing:
                    max_order = max(max_order, int(ks.progression_order))
            except Exception:
                pass
        return max_order + 1

    def _format_label(self, order: int, name: str) -> str:
        """Format left list label as zero-padded priority with name, e.g., '01: Home Keys'."""
        return f"{order:02d}: {name}"

    def _attempt_close(self) -> None:
        """Confirm close when unsaved changes exist."""
        if not self._dirty:
            self.accept()
            return
        resp = QtWidgets.QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Do you want to close without saving?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if resp == QtWidgets.QMessageBox.StandardButton.Yes:
            self.accept()

    def reject(self) -> None:  # noqa: D401
        """Override reject to warn on unsaved changes."""
        self._attempt_close()

    def closeEvent(self, event: QtCore.QEvent) -> None:  # type: ignore[override]
        """Warn on unsaved changes when window close is requested."""
        if self._dirty:
            resp = QtWidgets.QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to close without saving?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if resp != QtWidgets.QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()

    def _update_save_buttons(self) -> None:
        """Enable/disable save button based on dirty state."""
        self.save_current_btn.setEnabled(bool(self._dirty))

    def _update_selection_dependent_buttons(self) -> None:
        """Enable/disable buttons that require a selected keyset.

        - Delete Keyset
        - Edit Details
        """
        has_selection = self.keysets_list.currentItem() is not None
        try:
            self.delete_btn.setEnabled(has_selection)
            self.edit_details_btn.setEnabled(has_selection)
        except Exception:
            # If widgets not yet created or in unexpected state, fail safe to disabled
            pass
