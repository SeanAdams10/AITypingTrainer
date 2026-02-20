"""Manual scaffold UI for testing multi-select keyset union behavior.

Usage:
    python Spikes/run_keyset_multi_select_scaffold.py [cloud|docker] [quiet|loud]

Examples:
    python Spikes/run_keyset_multi_select_scaffold.py
    python Spikes/run_keyset_multi_select_scaffold.py docker
    python Spikes/run_keyset_multi_select_scaffold.py cloud loud
"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from db.database_manager import ConnectionType, DatabaseManager
from desktop_ui.dynamic_config import KeysetSelectionDialog
from helpers.debug_util import DebugUtil
from repositories.keyset_repository_postgres import PostgresKeysetRepository
from use_cases.keyset_collection import KeysetCollection


class KeysetMultiSelectScaffold(QWidget):
    """Small harness for manual verification of keyset multi-selection behavior."""

    def __init__(
        self,
        *,
        connection_type: ConnectionType = ConnectionType.CLOUD,
        debug_mode: str = "loud",
    ) -> None:
        super().__init__()
        self.setWindowTitle("Keyset Multi-Select Scaffold")
        self.setMinimumWidth(640)

        if debug_mode.lower() not in ["loud", "quiet"]:
            debug_mode = "loud"
        os.environ["AI_TYPING_TRAINER_DEBUG_MODE"] = debug_mode.lower()
        self.debug_util = DebugUtil()

        self.db_manager = DatabaseManager(
            connection_type=connection_type,
            debug_util=self.debug_util,
        )
        self.keyset_collection = KeysetCollection(PostgresKeysetRepository(self.db_manager))

        self.keyboard_combo = QComboBox()
        self.select_button = QPushButton("Select Keysets")
        self.result_box = QLineEdit()
        self.result_box.setReadOnly(True)

        self._setup_ui()
        self._load_keyboards()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        keyboard_row = QHBoxLayout()
        keyboard_row.addWidget(QLabel("Keyboard:"))
        keyboard_row.addWidget(self.keyboard_combo)
        keyboard_row.addWidget(self.select_button)

        result_row = QHBoxLayout()
        result_row.addWidget(QLabel("Included Keys:"))
        result_row.addWidget(self.result_box)

        layout.addLayout(keyboard_row)
        layout.addLayout(result_row)

        self.select_button.clicked.connect(self._on_select_keysets)

    def _load_keyboards(self) -> None:
        self.keyboard_combo.clear()
        rows = self.db_manager.execute(
            query=(
                "SELECT keyboard_id, keyboard_name "
                "FROM keyboards "
                "ORDER BY keyboard_name"
            ),
            params=(),
        ).fetchall()

        for row in rows:
            keyboard_id = self._row_value(row=row, key="keyboard_id", index=0)
            keyboard_name = self._row_value(row=row, key="keyboard_name", index=1)
            self.keyboard_combo.addItem(keyboard_name, keyboard_id)

        self.select_button.setEnabled(self.keyboard_combo.count() > 0)

    def _row_value(self, *, row: object, key: str, index: int) -> str:
        """Return a row value as string for tuple- or dict-style DB rows."""
        if isinstance(row, dict):
            return str(row.get(key, ""))
        if isinstance(row, tuple):
            if 0 <= index < len(row):
                return str(row[index])
        return ""

    def _on_select_keysets(self) -> None:
        keyboard_id = self.keyboard_combo.currentData()
        if not keyboard_id:
            QMessageBox.information(self, "No Keyboard", "No keyboard selected.")
            return

        self.keyset_collection.load_for_keyboard(keyboard_id=str(keyboard_id))
        keysets = self.keyset_collection.get_keysets_ordered()
        if not keysets:
            QMessageBox.information(
                self,
                "No Keysets",
                "No keysets are available for the selected keyboard.",
            )
            return

        dialog = KeysetSelectionDialog(keysets=keysets, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            selected_keysets = dialog.get_selected_keysets()
            selected_keys = {
                key.key_char
                for keyset in selected_keysets
                for key in keyset.keys
                if key.key_char
            }
            self.result_box.setText("".join(sorted(selected_keys)))

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Close database connection when scaffold window closes."""
        try:
            self.db_manager.close()
        except Exception:
            pass
        super().closeEvent(event)


def main() -> None:
    use_cloud = True
    debug_mode = "quiet"
    unknown_args: list[str] = []

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            value = arg.lower()
            if value == "docker":
                use_cloud = False
            elif value == "cloud":
                use_cloud = True
            elif value == "loud":
                debug_mode = "loud"
            elif value == "quiet":
                debug_mode = "quiet"
            else:
                unknown_args.append(arg)

    if unknown_args:
        print(
            "Ignoring unknown args:",
            ", ".join(unknown_args),
            "| Supported: cloud|docker quiet|loud",
        )

    connection_type = ConnectionType.CLOUD if use_cloud else ConnectionType.POSTGRESS_DOCKER

    app = QApplication(sys.argv)
    window = KeysetMultiSelectScaffold(
        connection_type=connection_type,
        debug_mode=debug_mode,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
