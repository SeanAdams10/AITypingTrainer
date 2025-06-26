"""PySide6 Desktop UI for the Snippets Library
- Fullscreen main window, maximized dialogs
- Category and snippet management with validation and error dialogs
- Direct integration with the model layer (no GraphQL)
"""

import os
import sys
from typing import Optional

from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from models.category import Category
from models.category_manager import CategoryManager
from models.library import DatabaseManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager

from .modern_dialogs import CategoryDialog, SnippetDialog
from .view_snippet_dialog import ViewSnippetDialog


class LibraryMainWindow(QMainWindow):
    """
    Modern Windows 11-style Snippets Library main window (PyQt5).
    Implements all category and snippet management features as per Library.md spec.
    """

    def __init__(
        self, db_manager: Optional[DatabaseManager] = None, testing_mode: bool = False
    ) -> None:
        """
        Initialize the LibraryMainWindow.
        :param db_manager: Optional DatabaseManager instance to use (for testability/
            singleton connection)
        :param testing_mode: If True, suppress modal dialogs for automated testing.
        """
        super().__init__()
        self.testing_mode = testing_mode
        self.setWindowTitle("Snippets Library")
        self.showMaximized()
        self.setMinimumSize(900, 600)
        # DB setup
        if db_manager is not None:
            self.db_manager = db_manager
        else:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_data.db")
            self.db_manager = DatabaseManager(db_path)
        self.category_manager = CategoryManager(self.db_manager)
        self.snippet_manager = SnippetManager(self.db_manager)
        # Data
        self.categories: list[Category] = []
        self.snippets: list[Snippet] = []
        self.selected_category: Optional[Category] = None
        self.selected_snippet: Optional[Snippet] = None
        # UI
        self.setup_ui()
        self.load_data()

    def setup_ui(self) -> None:
        """Set up the user interface components."""
        QApplication.setStyle("Fusion")
        font = QFont("Segoe UI", 11)
        self.setFont(font)
        self.setStyleSheet(_modern_qss())
        self.central = QWidget(self)
        self.setCentralWidget(self.central)
        self.main_layout = QHBoxLayout()
        self.central.setLayout(self.main_layout)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(splitter)
        # Category panel
        cat_panel = QWidget()
        cat_layout = QVBoxLayout()
        cat_panel.setLayout(cat_layout)
        cat_label = QLabel("Categories")
        cat_label.setObjectName("PanelTitle")
        cat_layout.addWidget(cat_label)
        self.categoryList = QListWidget()
        self.categoryList.setObjectName("CategoryList")
        self.categoryList.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        cat_layout.addWidget(self.categoryList)
        # Category buttons
        cat_btns = QHBoxLayout()
        self.addCatBtn = QPushButton(QIcon.fromTheme("list-add"), "Add")
        self.editCatBtn = QPushButton(QIcon.fromTheme("document-edit"), "Edit")
        self.delCatBtn = QPushButton(QIcon.fromTheme("edit-delete"), "Delete")
        for btn in [self.addCatBtn, self.editCatBtn, self.delCatBtn]:
            btn.setMinimumHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("font-size: 14px; font-weight: 500;")
            cat_btns.addWidget(btn)
        cat_layout.addLayout(cat_btns)
        splitter.addWidget(cat_panel)
        splitter.setStretchFactor(0, 1)
        # Snippet panel
        snip_panel = QWidget()
        snip_layout = QVBoxLayout()
        snip_panel.setLayout(snip_layout)
        snip_header = QHBoxLayout()
        snip_label = QLabel("Snippets")
        snip_label.setObjectName("PanelTitle")
        snip_header.addWidget(snip_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search snippets...")
        self.search_input.setObjectName("SearchBar")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMaximumWidth(200)
        self.search_input.textChanged.connect(self.filter_snippets)
        snip_header.addWidget(self.search_input)
        snip_layout.addLayout(snip_header)
        self.snippetList = QListWidget()
        self.snippetList.setObjectName("SnippetList")
        self.snippetList.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        snip_layout.addWidget(self.snippetList)
        # Snippet buttons
        snip_btns = QHBoxLayout()
        self.addSnipBtn = QPushButton(QIcon.fromTheme("list-add"), "Add")
        self.editSnipBtn = QPushButton(QIcon.fromTheme("document-edit"), "Edit")
        self.delSnipBtn = QPushButton(QIcon.fromTheme("edit-delete"), "Delete")
        for btn in [self.addSnipBtn, self.editSnipBtn, self.delSnipBtn]:
            btn.setMinimumHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("font-size: 14px; font-weight: 500;")
            snip_btns.addWidget(btn)
        snip_layout.addLayout(snip_btns)
        splitter.addWidget(snip_panel)
        splitter.setStretchFactor(1, 2)
        # Status bar
        self.status = QLabel("")
        self.status.setObjectName("StatusBar")
        self.status.setMinimumHeight(28)
        self.status.setStyleSheet("font-size: 13px; color: #3a3a3a;")
        self.main_layout.addWidget(self.status)
        # Connect signals
        self.addCatBtn.clicked.connect(self.add_category)
        self.editCatBtn.clicked.connect(self.edit_category)
        self.delCatBtn.clicked.connect(self.delete_category)
        self.addSnipBtn.clicked.connect(self.add_snippet)
        self.editSnipBtn.clicked.connect(self.edit_snippet)
        self.delSnipBtn.clicked.connect(self.delete_snippet)
        self.categoryList.itemSelectionChanged.connect(self.on_category_selection_changed)
        self.snippetList.itemClicked.connect(self.on_snippet_selection_changed)
        self.snippetList.itemDoubleClicked.connect(self.view_snippet)
        self.update_snippet_buttons_state(False)

    def load_data(self) -> None:
        """Load categories and snippets into the UI. Ensures at least one category and snippet exist."""
        try:
            self.categories = self.category_manager.list_all_categories()
            # Ensure at least one category exists
            if not self.categories:
                default_cat = Category(
                    category_name="Default Category",
                    description="Default auto-created category."
                )
                self.category_manager.save_category(default_cat)
                self.categories = self.category_manager.list_all_categories()
            self.refresh_categories()
            self.snippets = []
            self.snippetList.clear()
            # Ensure at least one snippet exists for the first category
            if self.categories:
                first_cat = self.categories[0]
                cat_id = str(first_cat.category_id)
                snippets = self.snippet_manager.list_snippets_by_category(cat_id)
                if not snippets:
                    default_snip = Snippet(
                        category_id=cat_id,
                        snippet_name="Default Snippet",
                        content="This is a default snippet.",
                        description="Default auto-created snippet."
                    )
                    self.snippet_manager.save_snippet(default_snip)
            # Optionally select the first category
            if self.categoryList.count() > 0:
                self.categoryList.setCurrentRow(0)
        except Exception as e:
            self.show_error(f"Error loading data: {e}")

    def show_error(self, msg: str) -> None:
        if self.testing_mode:
            print(f"ERROR: {msg}")
        else:
            QMessageBox.critical(self, "Error", msg)
        self.status.setText(msg)

    def show_info(self, msg: str) -> None:
        if self.testing_mode:
            print(f"INFO: {msg}")
        else:
            QMessageBox.information(self, "Info", msg)
        self.status.setText(msg)

    def filter_snippets(self, search_text: str) -> None:
        if not self.selected_category:
            self.snippetList.clear()
            return
        all_snippets = self.snippet_manager.list_snippets_by_category(str(self.selected_category.category_id))
        filtered = [s for s in all_snippets if search_text.lower() in s.snippet_name.lower()]
        self.snippetList.clear()
        for snip in filtered:
            item = QListWidgetItem(snip.snippet_name)
            item.setData(Qt.ItemDataRole.UserRole, snip)
            self.snippetList.addItem(item)

    def refresh_categories(self) -> None:
        self.categoryList.clear()
        for cat in self.categories:
            item = QListWidgetItem(cat.category_name)
            item.setData(Qt.ItemDataRole.UserRole, cat)
            self.categoryList.addItem(item)

    def on_category_selection_changed(self) -> None:
        items = self.categoryList.selectedItems()
        if not items:
            self.selected_category = None
            self.snippetList.clear()
            self.update_snippet_buttons_state(False)
            return
        item = items[0]
        cat = item.data(Qt.ItemDataRole.UserRole)
        self.selected_category = cat
        self.load_snippets()
        self.update_snippet_buttons_state(True)

    def update_snippet_buttons_state(self, enabled: bool) -> None:
        self.addSnipBtn.setEnabled(enabled)
        self.editSnipBtn.setEnabled(enabled)
        self.delSnipBtn.setEnabled(enabled)

    def on_snippet_selection_changed(self, item: QListWidgetItem) -> None:
        snippet: Optional[Snippet] = item.data(Qt.ItemDataRole.UserRole)
        self.selected_snippet = snippet
        # No auto-view on click; only on double-click

    def load_snippets(self) -> None:
        self.snippetList.clear()
        if not self.selected_category:
            return
        try:
            self.snippets = self.snippet_manager.list_snippets_by_category(
                str(self.selected_category.category_id)
            )
            for snip in self.snippets:
                item = QListWidgetItem(snip.snippet_name)
                item.setData(Qt.ItemDataRole.UserRole, snip)
                self.snippetList.addItem(item)
        except Exception as e:
            self.show_error(f"Error loading snippets: {e}")

    def add_category(self) -> None:
        dlg = CategoryDialog("Add Category", "Category Name", parent=self)
        if dlg.exec_() == QtWidgets.QDialog.DialogCode.Accepted:
            name = dlg.get_value()
            try:
                category = Category(category_name=name, description="")
                self.category_manager.save_category(category)
                self.categories = self.category_manager.list_all_categories()
                self.refresh_categories()
                self.show_info("Category added.")
            except Exception as e:
                self.show_error(f"Failed to add category: {e}")

    def edit_category(self) -> None:
        items = self.categoryList.selectedItems()
        if not items:
            self.show_error("No category selected.")
            return
        cat = items[0].data(Qt.ItemDataRole.UserRole)
        dlg = CategoryDialog(
            "Edit Category", "Category Name", default=cat.category_name, parent=self
        )
        if dlg.exec_() == QtWidgets.QDialog.DialogCode.Accepted:
            new_name = dlg.get_value()
            try:
                cat.category_name = new_name
                self.category_manager.save_category(cat)
                self.categories = self.category_manager.list_all_categories()
                self.refresh_categories()
                self.show_info("Category updated.")
            except Exception as e:
                self.show_error(f"Failed to update category: {e}")

    def delete_category(self) -> None:
        items = self.categoryList.selectedItems()
        if not items:
            self.show_error("No category selected.")
            return
        cat = items[0].data(Qt.ItemDataRole.UserRole)
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Delete Category",
            f"Delete category '{cat.category_name}' and all its snippets?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        try:
            self.category_manager.delete_category_by_id(cat.category_id)
            self.categories = self.category_manager.list_all_categories()
            self.refresh_categories()
            self.snippetList.clear()
            self.show_info("Category deleted.")
        except Exception as e:
            self.show_error(f"Failed to delete category: {e}")

    def add_snippet(self) -> None:
        if not self.selected_category:
            self.show_error("No category selected.")
            return
        dlg = SnippetDialog("Add Snippet", "Snippet Name", "Content", parent=self)
        if dlg.exec_() == QtWidgets.QDialog.DialogCode.Accepted:
            name, content = dlg.get_values()
            try:
                cat_id = str(self.selected_category.category_id)
                snippet = Snippet(
                    category_id=cat_id,
                    snippet_name=name,
                    content=content,
                    description=""
                )
                self.snippet_manager.save_snippet(snippet)
                self.load_snippets()
                self.show_info("Snippet added.")
            except Exception as e:
                self.show_error(f"Failed to add snippet: {e}")

    def edit_snippet(self) -> None:
        items = self.snippetList.selectedItems()
        if not items:
            self.show_error("No snippet selected.")
            return
        snippet = items[0].data(Qt.ItemDataRole.UserRole)
        dlg = SnippetDialog(
            "Edit Snippet",
            "Snippet Name",
            "Content",
            default_name=snippet.snippet_name,
            default_content=snippet.content,
            parent=self,
        )
        if dlg.exec_() == QtWidgets.QDialog.DialogCode.Accepted:
            name, content = dlg.get_values()
            try:
                snippet.snippet_name = name
                snippet.content = content
                self.snippet_manager.save_snippet(snippet)
                self.load_snippets()
                self.show_info("Snippet updated.")
            except Exception as e:
                self.show_error(f"Failed to update snippet: {e}")

    def delete_snippet(self) -> None:
        items = self.snippetList.selectedItems()
        if not items:
            self.show_error("No snippet selected.")
            return
        snippet = items[0].data(Qt.ItemDataRole.UserRole)
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Delete Snippet",
            f"Delete snippet '{snippet.snippet_name}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        try:
            self.snippet_manager.delete_snippet(snippet.snippet_id)
            self.load_snippets()
            self.show_info("Snippet deleted.")
        except Exception as e:
            self.show_error(f"Failed to delete snippet: {e}")

    def view_snippet(self, item: QListWidgetItem) -> None:
        snippet: Optional[Snippet] = item.data(Qt.ItemDataRole.UserRole)
        if snippet:
            dlg = ViewSnippetDialog(
                title="View Snippet",
                snippet_name=snippet.snippet_name,
                content=snippet.content,
                parent=self,
            )
            dlg.exec_()


def _modern_qss() -> str:
    """Return QSS for a modern Windows 11 look (rounded corners, subtle shadows,
    modern palette)."""
    return """
    QWidget {
        background: #f3f3f3;
        color: #222;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    QMainWindow {
        background: #f3f3f3;
    }
    QListWidget {
        background: #fff;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        padding: 6px;
        font-size: 14px;
    }
    QPushButton {
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1, stop:0 #e8e8ef, stop:1 #d1d1e0
        );
        border-radius: 10px;
        border: 1px solid #bfc8d6;
        padding: 8px 18px;
        font-size: 15px;
        font-weight: 500;
        min-width: 120px;
        min-height: 36px;
        color: #222;
    }
    QPushButton:hover {
        background: #e0e6f5;
        border: 1px solid #7aa2f7;
    }
    QPushButton:pressed {
        background: #d1d7e6;
    }
    QLabel#PanelTitle {
        font-size: 17px;
        font-weight: 600;
        color: #3a3a3a;
        margin-bottom: 10px;
    }
    QLabel#StatusBar {
        background: #e7eaf0;
        border-radius: 8px;
        padding: 6px 18px;
        margin: 10px;
        font-size: 13px;
        color: #3a3a3a;
    }
    QMessageBox {
        background: #fff;
        border-radius: 12px;
    }
    QInputDialog {
        background: #fff;
        border-radius: 12px;
    }
    """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = LibraryMainWindow()
    win.showMaximized()
    exit_code = app.exec_()
    sys.exit(exit_code)
