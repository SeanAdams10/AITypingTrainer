"""Category Model Tester UI.

-----------------------
A simple PySide6-based desktop UI for directly testing the Category object model (Category, CategoryManager).

- List all categories
- Add a new category
- Rename a category
- Delete a category (with cascade warning)
- Show validation and error messages

Bypasses API and service layers; interacts directly with CategoryManager and DatabaseManager.

Author: Cascade AI
"""

import os
import sys
from typing import Optional

from PySide6.QtWidgets import (
    QApplication,
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
from models.category_manager import CategoryManager, CategoryNotFound, CategoryValidationError

# DB_PATH = os.path.join(os.path.dirname(__file__), 'category_model_test.db')
DB_PATH = os.path.join(os.path.dirname(__file__), "snippet_model_test.db")


class CategoryModelTester(QWidget):
    """Simple UI to test CategoryManager CRUD and validation logic."""

    def __init__(self) -> None:
        """Initialize the Category Model Tester widget."""
        super().__init__()
        self.setWindowTitle("Category Model Tester")
        self.setGeometry(100, 100, 480, 360)
        self.db_manager = DatabaseManager(DB_PATH)
        self.db_manager.init_tables()
        self.cat_mgr = CategoryManager(self.db_manager)
        self.init_ui()
        self.refresh_categories()

    def init_ui(self) -> None:
        """Initialize the user interface components."""
        layout = QVBoxLayout()

        # Category List
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Categories:"))
        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Category")
        self.btn_rename = QPushButton("Rename Category")
        self.btn_delete = QPushButton("Delete Category")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_rename)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

        # Status/Error label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.btn_add.clicked.connect(self.add_category)
        self.btn_rename.clicked.connect(self.rename_category)
        self.btn_delete.clicked.connect(self.delete_category)

    def refresh_categories(self) -> None:
        """Reload and display all categories from the database."""
        self.list_widget.clear()
        try:
            cats = self.cat_mgr.list_all_categories()
            for cat in cats:
                self.list_widget.addItem(f"{cat.category_id}: {cat.category_name}")
        except Exception as e:
            self.set_status(f"Error loading categories: {e}")

    def add_category(self) -> None:
        """Add a new category through user input dialog."""
        name, ok = QInputDialog.getText(self, "Add Category", "Enter category name:")
        if ok and name:
            try:
                from models.category import Category
                new_category = Category(category_name=name, description="Created via tester")
                self.cat_mgr.save_category(new_category)
                self.set_status("Category added.", error=False)
                self.refresh_categories()
            except CategoryValidationError as e:
                self.set_status(f"Validation error: {e}")
            except Exception as e:
                self.set_status(f"Error: {e}")

    def get_selected_category_id(self) -> Optional[int]:
        """Return the currently selected category id, or None if none selected.

        Parses the selected list item text to extract the leading id.
        """
        item = self.list_widget.currentItem()
        if not item:
            self.set_status("No category selected.")
            return None
        try:
            cat_id = int(item.text().split(":")[0])
            return cat_id
        except Exception:
            self.set_status("Failed to parse category id.")
            return None

    def rename_category(self) -> None:
        """Prompt for a new name and rename the selected category."""
        cat_id = self.get_selected_category_id()
        if cat_id is None:
            return
        new_name, ok = QInputDialog.getText(self, "Rename Category", "Enter new name:")
        if ok and new_name:
            try:
                # Get the category, modify it, and save it
                category = self.cat_mgr.get_category_by_id(cat_id)
                category.category_name = new_name
                self.cat_mgr.save_category(category)
                self.set_status("Category renamed.", error=False)
                self.refresh_categories()
            except CategoryValidationError as e:
                self.set_status(f"Validation error: {e}")
            except CategoryNotFound as e:
                self.set_status(f"Not found: {e}")
            except Exception as e:
                self.set_status(f"Error: {e}")

    def delete_category(self) -> None:
        """Delete the selected category after user confirmation."""
        cat_id = self.get_selected_category_id()
        if cat_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Delete this category and all related snippets? This cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.cat_mgr.delete_category(cat_id)
                self.set_status("Category deleted.", error=False)
                self.refresh_categories()
            except CategoryNotFound as e:
                self.set_status(f"Not found: {e}")
            except Exception as e:
                self.set_status(f"Error: {e}")

    def set_status(self, msg: str, error: bool = True) -> None:
        """Set status message with color coding.
        
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
    app = QApplication(sys.argv)
    tester = CategoryModelTester()
    tester.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
