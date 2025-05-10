"""
Snippet Model Tester UI
----------------------
A simple PyQt5-based desktop UI for directly testing the Snippet object model (SnippetModel, SnippetManager).

- List all snippets (optionally filter by category)
- Add a new snippet
- Edit a snippet (name/content/category)
- Delete a snippet
- Show validation and error messages

Bypasses API and service layers; interacts directly with SnippetManager, SnippetModel, and CategoryManager.

Author: Cascade AI
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLineEdit, QLabel, QMessageBox, QInputDialog, QTextEdit, QComboBox
)
from PyQt5.QtCore import Qt
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.snippet import SnippetManager, SnippetModel
from models.category import CategoryManager, CategoryNotFound
from models.database_manager import DatabaseManager

DB_PATH = os.path.join(os.path.dirname(__file__), 'snippet_model_test.db')

class SnippetModelTester(QWidget):
    """
    Simple UI to test SnippetManager CRUD and validation logic.
    """
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Snippet Model Tester")
        self.setGeometry(120, 120, 700, 400)
        self.db_manager = DatabaseManager(DB_PATH)
        self.db_manager.initialize_tables()
        self.cat_mgr = CategoryManager(self.db_manager)
        self.snip_mgr = SnippetManager(self.db_manager)
        self.selected_category_id: Optional[int] = None
        self.init_ui()
        self.refresh_categories()
        self.refresh_snippets()

    def init_ui(self) -> None:
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
        self.cat_combo.blockSignals(True)
        self.cat_combo.clear()
        try:
            cats = self.cat_mgr.list_categories()
            for cat in cats:
                self.cat_combo.addItem(f"{cat.category_name} (ID {cat.category_id})", cat.category_id)
            if cats:
                self.cat_combo.setCurrentIndex(0)  # Select first category by default
        except Exception as e:
            self.set_status(f"Error loading categories: {e}")
        self.cat_combo.blockSignals(False)

    def refresh_snippets(self) -> None:
        self.list_widget.clear()
        try:
            cat_id = self.cat_combo.currentData()
            if cat_id is not None:
                snippets = self.snip_mgr.list_snippets(category_id=cat_id)
                for snip in snippets:
                    self.list_widget.addItem(f"{snip.snippet_id}: [{snip.category_id}] {snip.snippet_name} - {snip.content[:40]}{'...' if len(snip.content)>40 else ''}")
        except Exception as e:
            self.set_status(f"Error loading snippets: {e}")

    def on_category_filter(self) -> None:
        self.refresh_snippets()

    def add_snippet(self) -> None:
        cats = self.cat_mgr.list_categories()
        if not cats:
            self.set_status("No categories available. Add a category first.")
            return
        cat_names = [f"{c.category_name} (ID {c.category_id})" for c in cats]
        cat_idx, ok = QInputDialog.getItem(self, "Select Category", "Category:", cat_names, 0, False)
        if not ok:
            return
        cat_id = cats[cat_names.index(cat_idx)].category_id
        name, ok = QInputDialog.getText(self, "Snippet Name", "Enter snippet name:")
        if not ok or not name:
            return
        content, ok = QInputDialog.getMultiLineText(self, "Snippet Content", "Enter snippet content:")
        if not ok or not content:
            return
        try:
            self.snip_mgr.create_snippet(category_id=cat_id, snippet_name=name, content=content)
            self.set_status("Snippet added.", error=False)
            self.refresh_snippets()
        except Exception as e:
            self.set_status(f"Error adding snippet: {e}")

    def get_selected_snippet_id(self) -> Optional[int]:
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
        snip_id = self.get_selected_snippet_id()
        if snip_id is None:
            return
        try:
            snip = self.snip_mgr.get_snippet(snip_id)
        except Exception as e:
            self.set_status(f"Error loading snippet: {e}")
            return
        # Edit fields - Category selection dialog
        cats = self.cat_mgr.list_categories()
        cat_names = [f"{cat.category_name} (ID {cat.category_id})" for cat in cats]
        current_cat_idx = next((i for i, cat in enumerate(cats) if cat.category_id == snip.category_id), 0)
        cat_idx, ok = QInputDialog.getItem(self, "Edit Category", "Select category:", cat_names, current_cat_idx, False)
        if not ok:
            return
        new_cat_id = cats[cat_names.index(cat_idx)].category_id
        name, ok = QInputDialog.getText(self, "Edit Snippet Name", "Snippet name:", text=snip.snippet_name)
        if not ok or not name:
            return
        content, ok = QInputDialog.getMultiLineText(self, "Edit Snippet Content", "Snippet content:", text=snip.content)
        if not ok or not content:
            return
        try:
            self.snip_mgr.edit_snippet(snippet_id=snip_id, snippet_name=name, content=content, category_id=new_cat_id)
            self.set_status("Snippet updated.", error=False)
            self.refresh_snippets()
        except Exception as e:
            self.set_status(f"Error updating snippet: {e}")

    def delete_snippet(self) -> None:
        snip_id = self.get_selected_snippet_id()
        if snip_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Delete this snippet? This cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.snip_mgr.delete_snippet(snip_id)
                self.set_status("Snippet deleted.", error=False)
                self.refresh_snippets()
            except Exception as e:
                self.set_status(f"Error deleting snippet: {e}")

    def set_status(self, msg: str, error: bool = True) -> None:
        self.status_label.setText(msg)
        if error:
            self.status_label.setStyleSheet("color: red;")
        else:
            self.status_label.setStyleSheet("color: green;")


def main() -> None:
    app = QApplication(sys.argv)
    tester = SnippetModelTester()
    tester.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
