# ruff: noqa: E402
"""Snippet Model Tester UI.

----------------------
A simple PySide6-based desktop UI for directly testing the Snippet object
model (SnippetModel, SnippetManager).

- List all snippets (optionally filter by category)
- Add a new snippet
- Edit a snippet (name/content/category)
- Delete a snippet
- Show validation and error messages

Bypasses API and service layers; interacts directly with SnippetManager,
SnippetModel, and CategoryManager.

Author: Cascade AI
"""

import os
import sys
from typing import Optional

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db.database_manager import DatabaseManager
from models.category_manager import CategoryManager
from models.snippet_manager import SnippetManager

DB_PATH = os.path.join(os.path.dirname(__file__), "snippet_model_test.db")


class SnippetModelTester(QWidget):
    """Simple UI to test SnippetManager CRUD and validation logic."""

    def __init__(self) -> None:
        """Initialize the snippet model tester UI."""
        super().__init__()
        self.setWindowTitle("Snippet Model Tester")
        self.setGeometry(120, 120, 700, 400)
        self.db_manager = DatabaseManager(DB_PATH)
        self.db_manager.init_tables()
        self.cat_mgr = CategoryManager(self.db_manager)
        self.snip_mgr = SnippetManager(self.db_manager)
        self.selected_category_id: Optional[int] = None
        self.init_ui()
        self.refresh_categories()
        self.refresh_snippets()

    def init_ui(self) -> None:
        """Initialize the user interface components."""
        layout = QVBoxLayout()

        # Category filter
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("Filter by Category:"))
        self.cat_combo = QComboBox()
        self.cat_combo.currentIndexChanged.connect(self.on_category_filter)
        cat_layout.addWidget(self.cat_combo)
        layout.addLayout(cat_layout)

        # Snippet List
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Snippets:"))
        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Snippet")
        self.btn_edit = QPushButton("Edit Snippet")
        self.btn_delete = QPushButton("Delete Snippet")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

        # Status/Error label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.btn_add.clicked.connect(self.add_snippet)
        self.btn_edit.clicked.connect(self.edit_snippet)
        self.btn_delete.clicked.connect(self.delete_snippet)

    def refresh_categories(self) -> None:
        """Refresh the category dropdown with current categories from database."""
        self.cat_combo.blockSignals(True)
        self.cat_combo.clear()
        try:
            cats = self.cat_mgr.list_all_categories()
            for cat in cats:
                self.cat_combo.addItem(
                    f"{cat.category_name} (ID {cat.category_id})", cat.category_id
                )
            if cats:
                self.cat_combo.setCurrentIndex(0)  # Select first category by default
        except Exception as e:
            self.set_status(f"Error loading categories: {e}")
        self.cat_combo.blockSignals(False)

    def refresh_snippets(self) -> None:
        """Refresh the snippets list based on the selected category."""
        self.list_widget.clear()
        try:
            cat_id = self.cat_combo.currentData()
            if cat_id is not None:
                snippets = self.snip_mgr.list_snippets_by_category(category_id=cat_id)
                for snip in snippets:
                    content_str = snip.content or ""
                    content_preview = content_str[:40]
                    if len(content_str) > 40:
                        content_preview += "..."
                    item_text = (
                        f"{snip.snippet_id}: [{snip.category_id}] "
                        f"{snip.snippet_name} - {content_preview}"
                    )
                    self.list_widget.addItem(item_text)
        except Exception as e:
            self.set_status(f"Error loading snippets: {e}")

    def on_category_filter(self) -> None:
        """Handle category filter change event."""
        self.refresh_snippets()

    def add_snippet(self) -> None:
        """Add a new snippet through dialog prompts."""
        cats = self.cat_mgr.list_all_categories()
        if not cats:
            self.set_status("No categories available. Add a category first.")
            return
        cat_names = [f"{c.category_name} (ID {c.category_id})" for c in cats]
        cat_idx, ok = QInputDialog.getItem(
            self, "Select Category", "Category:", cat_names, 0, False
        )
        if not ok:
            return
        cat_id = cats[cat_names.index(cat_idx)].category_id
        if cat_id is None:
            self.set_status("Selected category has invalid ID.")
            return
        name, ok = QInputDialog.getText(self, "Snippet Name", "Enter snippet name:")
        if not ok or not name:
            return
        content, ok = QInputDialog.getMultiLineText(
            self, "Snippet Content", "Enter snippet content:"
        )
        if not ok or not content:
            return
        try:
            from models.snippet import Snippet

            new_snippet = Snippet(
                category_id=cat_id,
                snippet_name=name,
                content=content,
                description="Created via tester",
            )
            self.snip_mgr.save_snippet(new_snippet)
            self.set_status("Snippet added.", error=False)
            self.refresh_snippets()
        except Exception as e:
            self.set_status(f"Error adding snippet: {e}")

    def get_selected_snippet_id(self) -> Optional[int]:
        """Get the ID of the currently selected snippet from the list widget."""
        item = self.list_widget.currentItem()
        if not item:
            self.set_status("No snippet selected.")
            return None
        try:
            snip_id = int(item.text().split(":")[0])
            return snip_id
        except Exception:
            self.set_status("Failed to parse snippet id.")
            return None

    def edit_snippet(self) -> None:
        """Edit the selected snippet via dialogs for category, name and content."""
        snip_id = self.get_selected_snippet_id()
        if snip_id is None:
            return
        try:
            snip = self.snip_mgr.get_snippet_by_id(str(snip_id))
            if snip is None:
                self.set_status("Snippet not found")
                return
        except Exception as e:
            self.set_status(f"Error loading snippet: {e}")
            return

        # Edit fields - Category selection dialog
        cats = self.cat_mgr.list_all_categories()
        cat_names = [f"{cat.category_name} (ID {cat.category_id})" for cat in cats]
        current_cat_idx = next(
            (i for i, cat in enumerate(cats) if cat.category_id == snip.category_id), 0
        )
        cat_idx, ok = QInputDialog.getItem(
            self, "Edit Category", "Select category:", cat_names, current_cat_idx, False
        )
        if not ok:
            return
        new_cat_id = cats[cat_names.index(cat_idx)].category_id
        if new_cat_id is None:
            self.set_status("Selected category has invalid ID.")
            return
        name, ok = QInputDialog.getText(
            self, "Edit Snippet Name", "Snippet name:", text=snip.snippet_name or ""
        )
        if not ok or not name:
            return
        content, ok = QInputDialog.getMultiLineText(
            self, "Edit Snippet Content", "Snippet content:", text=snip.content or ""
        )
        if not ok or not content:
            return
        try:
            # Update the snippet object and save it
            snip.snippet_name = name
            snip.content = content
            # mypy: after None-check, this is a str
            snip.category_id = new_cat_id
            self.snip_mgr.save_snippet(snip)
            self.set_status("Snippet updated.", error=False)
            self.refresh_snippets()
        except Exception as e:
            self.set_status(f"Error updating snippet: {e}")

    def delete_snippet(self) -> None:
        """Delete the selected snippet after user confirmation."""
        snip_id = self.get_selected_snippet_id()
        if snip_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Delete this snippet? This cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.snip_mgr.delete_snippet(str(snip_id))
                self.set_status("Snippet deleted.", error=False)
                self.refresh_snippets()
            except Exception as e:
                self.set_status(f"Error deleting snippet: {e}")

    def set_status(self, msg: str, error: bool = True) -> None:
        """Set status message in the status label with color coding.

        Args:
            msg: Status message to display
            error: If True, displays in red; if False, displays in green
        """
        self.status_label.setText(msg)
        if error:
            self.status_label.setStyleSheet("color: red;")
        else:
            self.status_label.setStyleSheet("color: green;")


def main() -> None:
    """Run the snippet model tester application."""
    app = QApplication(sys.argv)
    tester = SnippetModelTester()
    tester.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
