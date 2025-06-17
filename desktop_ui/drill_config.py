"""
Drill Configuration Dialog for AI Typing Trainer.

This module provides a dialog for configuring typing drill parameters,
including snippet selection, index ranges, and launches the typing drill.
"""

import os
from typing import List, Optional

# Third-party imports
from PyQt5 import QtCore, QtWidgets

# Local application imports
from db.database_manager import DatabaseManager
from models.category import Category
from models.category_manager import CategoryManager
from models.session_manager import SessionManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager

# Import TypingDrillScreen at the top level to avoid circular imports
from desktop_ui.typing_drill import TypingDrillScreen

# Define project_root if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(project_root, "typing_data.db")


class DrillConfigDialog(QtWidgets.QDialog):
    """
    Dialog for configuring typing drill parameters.

    Allows users to:
    - Select a category
    - Select a snippet from the chosen category
    - Set start and end indices for partial snippets
    - Launch the typing drill with configured parameters

    Args:
        db_manager: Database manager instance to access categories and snippets
        parent: Optional parent widget
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        user_id: str,
        keyboard_id: str,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_id = user_id
        self.keyboard_id = keyboard_id
        self.category_manager = CategoryManager(self.db_manager)
        self.snippet_manager = SnippetManager(self.db_manager)
        self.session_manager = SessionManager(self.db_manager)

        self.categories: List[Category] = []
        self.snippets: List[Snippet] = []

        self.setWindowTitle("Configure Typing Drill")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self._setup_ui()
        self._load_categories()
        # Ensure spinbox ranges are set after initial load
        self._on_snippet_changed()

    def _setup_ui(self) -> None:
        """Set up the UI components of the dialog."""
        main_layout = QtWidgets.QVBoxLayout(self)

        # Category selection group
        category_group = QtWidgets.QGroupBox("Select Category")
        category_layout = QtWidgets.QVBoxLayout(category_group)

        self.category_selector = QtWidgets.QComboBox()
        self.category_selector.setMinimumWidth(400)
        self.category_selector.currentIndexChanged.connect(self._on_category_changed)
        category_layout.addWidget(QtWidgets.QLabel("Category:"))
        category_layout.addWidget(self.category_selector)
        main_layout.addWidget(category_group)

        # Snippet selection group
        snippet_group = QtWidgets.QGroupBox("Select Snippet")
        snippet_layout = QtWidgets.QVBoxLayout(snippet_group)

        # Snippet selector
        self.snippet_selector = QtWidgets.QComboBox()
        self.snippet_selector.setMinimumWidth(400)
        self.snippet_selector.currentIndexChanged.connect(self._on_snippet_changed)
        snippet_layout.addWidget(QtWidgets.QLabel("Snippet:"))
        snippet_layout.addWidget(self.snippet_selector)

        # Snippet preview
        self.snippet_preview = QtWidgets.QTextEdit()
        self.snippet_preview.setReadOnly(True)
        self.snippet_preview.setMinimumHeight(120)
        snippet_layout.addWidget(QtWidgets.QLabel("Preview:"))
        snippet_layout.addWidget(self.snippet_preview)

        main_layout.addWidget(snippet_group)

        # Range selection group
        range_group = QtWidgets.QGroupBox("Text Range")
        range_layout = QtWidgets.QFormLayout(range_group)

        # Start and end index inputs
        self.start_index = QtWidgets.QSpinBox()
        self.start_index.setMinimum(0)
        self.start_index.setMaximum(9999)
        self.start_index.setValue(0)
        self.start_index.valueChanged.connect(self._on_start_index_changed)

        self.end_index = QtWidgets.QSpinBox()
        self.end_index.setMinimum(1)
        self.end_index.setMaximum(9999)
        self.end_index.setValue(100)
        self.end_index.valueChanged.connect(self._update_preview)

        range_layout.addRow("Start Index:", self.start_index)
        range_layout.addRow("End Index:", self.end_index)

        # Custom text option
        self.use_custom_text = QtWidgets.QCheckBox("Use custom text instead")
        self.use_custom_text.toggled.connect(self._toggle_custom_text)
        range_layout.addRow("", self.use_custom_text)

        self.custom_text = QtWidgets.QTextEdit()
        self.custom_text.setPlaceholderText("Enter custom text for typing practice...")
        self.custom_text.setEnabled(False)
        self.custom_text.textChanged.connect(self._update_preview)
        range_layout.addRow("Custom Text:", self.custom_text)

        main_layout.addWidget(range_group)

        # Buttons area
        button_box = QtWidgets.QDialogButtonBox()
        self.start_button = QtWidgets.QPushButton("Start Typing Drill")
        self.start_button.clicked.connect(self._start_drill)
        button_box.addButton(self.start_button, QtWidgets.QDialogButtonBox.AcceptRole)

        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addButton(cancel_button, QtWidgets.QDialogButtonBox.RejectRole)

        main_layout.addWidget(button_box)

    def _load_categories(self) -> None:
        """Load categories from the database and populate the category selector."""
        try:
            self.categories = self.category_manager.list_all_categories()
            self.category_selector.clear()
            for category in self.categories:
                self.category_selector.addItem(category.category_name, category)
            if self.categories:
                self.category_selector.setEnabled(True)
                self._on_category_changed()
            else:
                self.category_selector.setEnabled(False)
                self.snippet_selector.clear()
                self.snippet_selector.setEnabled(False)
                self.snippet_preview.clear()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load categories: {e}")
            self.categories = []
            self.category_selector.clear()
            self.category_selector.setEnabled(False)

    def _on_category_changed(self) -> None:
        """Handle changes when a category is selected."""
        selected_category_data = self.category_selector.currentData()
        if isinstance(selected_category_data, Category):
            self._load_snippets_for_category(selected_category_data.category_id)
        else:
            self.snippet_selector.clear()
            self.snippet_selector.setEnabled(False)
            self.snippet_preview.clear()

    def _load_snippets_for_category(self, category_id: str) -> None:
        """Load snippets for the given category_id and populate the snippet selector."""
        self.snippets = []
        try:
            self.snippets = self.snippet_manager.list_snippets_by_category(category_id)
            # print(
            #     "[DEBUG] _load_snippets: snippet_manager returned "
            #     f"{len(self.snippets)} snippets."
            # )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load snippets: {e}")
            self.snippets = []
        self.snippet_selector.clear()
        if not self.snippets:
            self.snippet_selector.setEnabled(False)
            self.snippet_preview.clear()
            return
        self.snippet_selector.setEnabled(True)
        for snippet in self.snippets:
            self.snippet_selector.addItem(snippet.snippet_name, snippet)
        if self.snippets:
            self.snippet_selector.setCurrentIndex(0)
        # Always call _on_snippet_changed to ensure spinbox ranges are set
        self._on_snippet_changed()

    def _update_preview(self) -> None:
        """Update the preview based on selected snippet and range."""
        if self.use_custom_text.isChecked():
            text = self.custom_text.toPlainText()
            self.snippet_preview.setPlainText(text)
        else:
            idx = self.snippet_selector.currentIndex()
            if self.snippets and 0 <= idx < len(self.snippets):
                snippet = self.snippets[idx]
                start = self.start_index.value()
                end = self.end_index.value()
                preview_text = snippet.content[start:end]
                self.snippet_preview.setPlainText(preview_text)
            else:
                self.snippet_preview.clear()

    def _on_snippet_changed(self) -> None:
        """Handle changes when a snippet is selected from the dropdown."""
        # Commented out debug prints to avoid stdout spam
        # print(f"[DEBUG] _on_snippet_changed: snippet_selector count="
        #       f"{self.snippet_selector.count()} currentIndex="
        #       f"{self.snippet_selector.currentIndex()}")
        # for i in range(self.snippet_selector.count()):
        #     data = self.snippet_selector.itemData(i)
        #     print(f"[DEBUG] snippet_selector item {i}: type={type(data)} value={data}")
        idx = self.snippet_selector.currentIndex()
        if self.snippets and 0 <= idx < len(self.snippets):
            selected_snippet_data = self.snippet_selector.itemData(idx)
            if isinstance(selected_snippet_data, Snippet):
                self.start_index.setMaximum(len(selected_snippet_data.content) - 1)
                self.end_index.setMaximum(len(selected_snippet_data.content))
                self.end_index.setValue(min(100, len(selected_snippet_data.content)))
                self._update_preview()
            else:
                self.snippet_preview.clear()
        else:
            self.snippet_preview.clear()
        # print(f"[DEBUG] _on_snippet_changed: type={type(self.snippet_selector.currentData())} "
        #       f"value={self.snippet_selector.currentData()}")

    def _load_snippets(self) -> None:
        """Load snippets for the currently selected category (for test compatibility)."""
        selected_category_data = self.category_selector.currentData()
        print(
            f"[DEBUG] _load_snippets: type={type(selected_category_data)} "
            f"value={selected_category_data}"
        )
        if isinstance(selected_category_data, Category):
            category_id = selected_category_data.category_id
            try:
                self.snippets = self.snippet_manager.list_snippets_by_category(category_id)
                print(
                    f"[DEBUG] _load_snippets: snippet_manager returned {len(self.snippets)} snippets."
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error Loading Snippets",
                    f"Failed to load snippets: {e}",
                )
        else:
            self.snippets = []
        self.snippet_selector.clear()
        if not self.snippets:
            self.snippet_selector.setEnabled(False)
            self.snippet_preview.clear()
            return
        self.snippet_selector.setEnabled(True)
        for snippet in self.snippets:
            self.snippet_selector.addItem(snippet.snippet_name, snippet)
        if self.snippets:
            self.snippet_selector.setCurrentIndex(0)
        self._on_snippet_changed()

    def _on_start_index_changed(self) -> None:
        """Handle changes when the start index is modified."""
        new_start_index = self.start_index.value()
        new_end_index_min = new_start_index + 1
        # Get the current snippet's content length
        idx = self.snippet_selector.currentIndex()
        content_length = 1
        if self.snippets and 0 <= idx < len(self.snippets):
            snippet = self.snippets[idx]
            if isinstance(snippet, dict):
                content_length = len(snippet.get("content", ""))
            elif isinstance(snippet, Snippet):
                content_length = len(snippet.content)
        print(
            f"[DEBUG] Start index changed: {new_start_index}, "
            f"setting end_index minimum to {new_end_index_min}, max to {content_length}"
        )
        self.end_index.setMinimum(new_end_index_min)
        self.end_index.setMaximum(content_length)
        if self.end_index.value() < new_end_index_min:
            print(
                f"[DEBUG] end_index value {self.end_index.value()} < new minimum "
                f"{new_end_index_min}, updating value."
            )
            self.end_index.setValue(new_end_index_min)
        if self.end_index.value() > content_length:
            print(
                f"[DEBUG] end_index value {self.end_index.value()} > max {content_length}, "
                "updating value."
            )
            self.end_index.setValue(content_length)
        print(
            f"[DEBUG] After change: start_index value={self.start_index.value()} "
            f"min={self.start_index.minimum()} max={self.start_index.maximum()}"
        )
        print(
            f"[DEBUG] After change: end_index value={self.end_index.value()} "
            f"min={self.end_index.minimum()} max={self.end_index.maximum()}"
        )
        self._update_preview()

    def _toggle_custom_text(self, checked: bool) -> None:
        """Toggle between snippet selection and custom text."""
        self.custom_text.setEnabled(checked)
        self.start_index.setEnabled(not checked)
        self.end_index.setEnabled(not checked)
        self.snippet_selector.setEnabled(not checked)
        self._update_preview()

    def _start_drill(self) -> None:
        """Gather configuration and start the typing drill."""
        if self.use_custom_text.isChecked():
            drill_text = self.custom_text.toPlainText()
            if not drill_text.strip():
                QtWidgets.QMessageBox.warning(self, "Input Error", "Custom text cannot be empty.")
                return
            # For custom text, we don't have a real snippet_id or category_id from the DB
            # We can use placeholders or specific values like -1 or None if stats tracking
            # needs them.
            snippet_id_for_stats = -1
        else:
            selected_snippet_data = self.snippet_selector.currentData()
            if not isinstance(selected_snippet_data, Snippet):
                QtWidgets.QMessageBox.warning(
                    self, "Selection Error", "Please select a valid snippet."
                )
                return

            content = selected_snippet_data.content
            snippet_id_for_stats = selected_snippet_data.snippet_id

            start_idx = self.start_index.value()
            end_idx = self.end_index.value()

            if start_idx >= end_idx:
                QtWidgets.QMessageBox.warning(
                    self, "Input Error", "Start index must be less than end index."
                )
                return

            drill_text = content[start_idx:end_idx]
            if not drill_text.strip():
                QtWidgets.QMessageBox.warning(
                    self, "Input Error", "Selected range results in empty text."
                )
                return

        # Store configuration for the typing drill screen
        try:
            # Create the typing drill screen with all required parameters
            drill = TypingDrillScreen(
                db_manager=self.db_manager,
                snippet_id=snippet_id_for_stats,
                start=0,
                end=len(drill_text),
                content=drill_text,
                user_id=self.user_id,
                keyboard_id=self.keyboard_id,
                parent=self,
            )

            # This accepts and closes the config dialog
            self.accept()

            # Show the typing drill dialog
            drill.exec_()

        except (ImportError, RuntimeError, ValueError) as e:
            QtWidgets.QMessageBox.warning(
                self, "Error Starting Drill", f"Failed to start typing drill: {str(e)}"
            )


if __name__ == "__main__":
    from db.database_manager import DatabaseManager

    app = QtWidgets.QApplication([])

    # Test with real database
    db_path = os.path.join(project_root, "typing_data.db")
    db_manager_instance = DatabaseManager(db_path)

    dialog = DrillConfigDialog(db_manager=db_manager_instance)
    dialog.exec_()
