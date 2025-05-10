"""PyQt5 Desktop UI for the Snippets Library
- Fullscreen main window, maximized dialogs
- Category and snippet management with validation and error dialogs
- Direct integration with the model layer (no GraphQL)
"""
import sys
import os
from typing import List, Dict, Any, Optional, Tuple, Union

# Direct explicit imports from PyQt5 modules to fix linting issues
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QLineEdit, QMessageBox, 
    QSizePolicy, QFrame, QGridLayout, QSpacerItem, QSplitter
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon

# Import core models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Add project root to path
from models.category import CategoryManager, Category, CategoryValidationError, CategoryNotFound
from models.snippet import SnippetManager, SnippetModel
from db.database_manager import DatabaseManager

# Try relative imports first, then fall back to direct imports
try:
    from .modern_dialogs import CategoryDialog, SnippetDialog
    from .view_snippet_dialog import ViewSnippetDialog
except ImportError:
    # For direct script execution
    from modern_dialogs import CategoryDialog, SnippetDialog
    from view_snippet_dialog import ViewSnippetDialog

class LibraryMainWindow(QMainWindow):
    """
    Modern Windows 11-style Snippets Library main window (PyQt5).
    Uses Fusion style, Segoe UI font, QSS for rounded corners, drop shadows, icons, and a modern color palette.
    Direct integration with model layer (no GraphQL).
    Supports a 'testing_mode' flag to suppress modal dialogs and enable headless automated UI testing.
    """
    def __init__(self, testing_mode: bool = False) -> None:
        """
        Initialize the LibraryMainWindow.
        :param testing_mode: If True, suppress modal dialogs for automated testing.
        """
        super().__init__()
        self.testing_mode = testing_mode
        self.setWindowTitle("Snippets Library")
        self.setWindowState(Qt.WindowMaximized)
        self.setMinimumSize(900, 600)
        # Initialize database and model managers
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_data.db")
        self.db_manager = DatabaseManager(db_path)
        self.category_manager = CategoryManager(self.db_manager)
        self.snippet_manager = SnippetManager(self.db_manager)
        # Init data attributes
        self.categories = []
        self.snippets = []
        self.selected_category = None
        self.selected_snippet = None
        # Initially disable snippet-related buttons until a category is selected
        self.addSnipBtn = None  # Will be initialized in setup_ui
        # Setup UI and load data
        self.setup_ui()
        self.load_data()


    
    def setup_ui(self) -> None:
        """Set up the user interface components."""
        # Apply Windows 11-like Fusion style and palette
        QApplication.setStyle("Fusion")
        font = QFont("Segoe UI", 11)
        QApplication.instance().setFont(font)
        self.setStyleSheet(_modern_qss())

        # Central layout with QSplitter for resizable panes
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.layout = QHBoxLayout()
        self.central.setLayout(self.layout)
        splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(splitter)

        # Category List panel
        cat_panel = QWidget()
        cat_layout = QVBoxLayout()
        cat_panel.setLayout(cat_layout)
        cat_label = QLabel("Categories")
        cat_label.setObjectName("PanelTitle")
        cat_layout.addWidget(cat_label)
        self.categoryList = QListWidget()
        self.categoryList.setObjectName("CategoryList")
        self.categoryList.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cat_layout.addWidget(self.categoryList)
        splitter.addWidget(cat_panel)
        splitter.setStretchFactor(0, 1)

        # Snippet List panel with search
        snip_panel = QWidget()
        snip_layout = QVBoxLayout()
        snip_panel.setLayout(snip_layout)
        
        # Header with label and search
        snip_header = QHBoxLayout()
        snip_label = QLabel("Snippets")
        snip_label.setObjectName("PanelTitle")
        snip_header.addWidget(snip_label)
        
        # Add search bar
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
        self.snippetList.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        snip_layout.addWidget(self.snippetList)
        splitter.addWidget(snip_panel)
        splitter.setStretchFactor(1, 2)

        # Buttons panel (vertical, with icons)
        btn_panel = QWidget()
        btns = QVBoxLayout()
        btn_panel.setLayout(btns)
        btns.setSpacing(14)
        self.addCatBtn = QPushButton(QIcon.fromTheme("list-add"), "Add Category")
        self.editCatBtn = QPushButton(QIcon.fromTheme("document-edit"), "Edit Category")
        self.delCatBtn = QPushButton(QIcon.fromTheme("edit-delete"), "Delete Category")
        self.addSnipBtn = QPushButton(QIcon.fromTheme("list-add"), "Add Snippet")
        self.editSnipBtn = QPushButton(QIcon.fromTheme("document-edit"), "Edit Snippet")
        self.delSnipBtn = QPushButton(QIcon.fromTheme("edit-delete"), "Delete Snippet")
        
        # Set initial state (will be enabled when a category is selected)
        self.addSnipBtn.setEnabled(False)
        for btn in [self.addCatBtn, self.editCatBtn, self.delCatBtn, self.addSnipBtn, self.editSnipBtn, self.delSnipBtn]:
            btn.setMinimumHeight(38)
            btn.setCursor(Qt.PointingHandCursor)  # Use Qt from PyQt5.QtCore
            btn.setStyleSheet("font-size: 15px; font-weight: 500;")
            btns.addWidget(btn)
        btns.addStretch(1)
        self.layout.addWidget(btn_panel)

        # Status bar
        self.status = QLabel()
        self.status.setObjectName("StatusBar")
        self.layout.addWidget(self.status)

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
        
        # Initially disable snippet-related buttons until a category is selected
        self.update_snippet_buttons_state(False)
        self.editSnipBtn.setEnabled(False)
        self.delSnipBtn.setEnabled(False)

        # Nothing to do here - data already initialized in __init__


    
    def load_data(self) -> None:
        """Load initial data from the server."""
        self.refresh_categories()
        
    def show_error(self, msg: str) -> None:
        """
        Show an error message. If in testing mode, only set the status bar.
        
        Args:
            msg: The error message to show
        """
        self.status.setText(f"Error: {msg}")  # Always update status for tests
        if not self.testing_mode:
            QMessageBox.critical(self, "Error", msg)

    def show_info(self, msg: str) -> None:
        """
        Show an informational message. If in testing mode, only set the status bar.
        
        Args:
            msg: The informational message to show
        """
        self.status.setText(msg)  # Always update status for tests
        if not self.testing_mode:
            QMessageBox.information(self, "Info", msg)

    def filter_snippets(self, search_text: str) -> None:
        """
        Filter snippets based on search text input.
        Hides snippets that don't match the search criteria.
        
        Args:
            search_text: Text to search for in snippet names
        """
        for i in range(self.snippetList.count()):
            item = self.snippetList.item(i)
            if not search_text or search_text.lower() in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def view_snippet(self, item: QListWidgetItem) -> None:
        """
        Open the view snippet dialog when a snippet is double-clicked.
        
        Args:
            item: Selected snippet item from the list
        """
        # Find the snippet data
        snippet_name = item.text()
        snippet_data = None
        for snippet in self.snippets:
            if snippet["snippet_name"] == snippet_name:
                snippet_data = snippet
                break
        
        if not snippet_data:
            self.show_error(f"Could not find snippet data for '{snippet_name}'")
            return
        
        # Open the view dialog with the snippet content
        dialog = ViewSnippetDialog(
            "View Snippet", 
            snippet_data["snippet_name"], 
            snippet_data["content"],
            self
        )
        dialog.exec_()
    
    def refresh_categories(self) -> None:
        """Fetch categories from the database and update the list widget."""
        try:
            # Get categories directly from the category manager
            categories = self.category_manager.list_categories()
            self.categories = []
            
            # Update UI
            self.categoryList.clear()
            for category in categories:
                self.categories.append({
                    "category_id": category.category_id,
                    "category_name": category.category_name
                })
                self.categoryList.addItem(category.category_name)
                
        except Exception as e:
            self.show_error(f"Error loading categories: {str(e)}")

    def on_category_selection_changed(self) -> None:
        """Handle category selection changes and update the selected category."""
        selected_items = self.categoryList.selectedItems()
        if not selected_items:
            self.selected_category = None
            self.update_snippet_buttons_state(False)
            self.snippetList.clear()
            self.status.setText("Select a category to view snippets")
            return
            
        # Get the selected category name
        category_name = selected_items[0].text()
        
        # Find the category in our list
        for category in self.categories:
            if category["category_name"] == category_name:
                self.selected_category = category
                self.update_snippet_buttons_state(True)
                self.load_snippets()
                self.status.setText(f"Category: {category_name}")
                return
                
        # If we get here, something went wrong
        self.selected_category = None
        self.update_snippet_buttons_state(False)
        self.status.setText("Error: Selected category not found")
    
    def update_snippet_buttons_state(self, enabled: bool) -> None:
        """Enable or disable snippet-related buttons based on category selection.
        
        Args:
            enabled: True to enable the Add Snippet button, False to disable it
        """
        self.addSnipBtn.setEnabled(enabled)
    
    def on_snippet_selection_changed(self, item: QListWidgetItem) -> None:
        """Handle snippet selection changes and update the selected snippet.
        
        Args:
            item: The selected QListWidgetItem from the snippets list
        """
        if not item:
            self.selected_snippet = None
            self.editSnipBtn.setEnabled(False)
            self.delSnipBtn.setEnabled(False)
            return
            
        # Get the selected snippet name
        snippet_name = item.text()
        
        # Find the snippet in our list
        for snippet in self.snippets:
            if snippet["snippet_name"] == snippet_name:
                self.selected_snippet = snippet
                self.editSnipBtn.setEnabled(True)
                self.delSnipBtn.setEnabled(True)
                self.status.setText(f"Selected: {snippet_name}")
                return
                
        # If we get here, something went wrong
        self.selected_snippet = None
        self.editSnipBtn.setEnabled(False)
        self.delSnipBtn.setEnabled(False)
    
    def load_snippets(self) -> None:
        """Fetch snippets for the selected category from the database."""
        if not self.selected_category:
            return
            
        try:
            # Use the snippet manager to get snippets directly
            snippets = self.snippet_manager.list_snippets(self.selected_category["category_id"])
            self.snippets = []
            self.selected_snippet = None
            
            # Update UI
            self.snippetList.clear()
            self.editSnipBtn.setEnabled(False)
            self.delSnipBtn.setEnabled(False)
            
            if not snippets:
                self.status.setText(f"No snippets in category '{self.selected_category['category_name']}'")
                return
                
            # Add snippets to the list
            for snippet in snippets:
                self.snippets.append({
                    "snippet_id": snippet.snippet_id,
                    "category_id": snippet.category_id,
                    "snippet_name": snippet.snippet_name,
                    "content": snippet.content
                })
                self.snippetList.addItem(snippet.snippet_name)
                
            self.status.setText(f"Loaded {len(snippets)} snippet(s) from '{self.selected_category['category_name']}'")
                
        except Exception as e:
            self.show_error(f"Error loading snippets: {str(e)}")

    def add_category(self) -> None:
        """Show a modern dialog to add a new category with validation."""
        dlg = CategoryDialog("Add Category", "Category Name:", parent=self)
        if dlg.exec_() != dlg.Accepted:
            return
            
        name = dlg.get_value()
        
        try:
            # Use the category manager to add a category directly
            self.category_manager.create_category(name)
            
            # Success - refresh the category list
            self.refresh_categories()
            self.show_info(f"Category '{name}' added successfully")
            
        except CategoryValidationError as e:
            # Error during category validation
            self.show_error(f"Validation error: {str(e)}")
        except Exception as e:
            # Unknown error
            self.show_error(f"Error creating category: {str(e)}")

    def edit_category(self) -> None:
        """Show a modern dialog to edit the selected category name with validation."""
        if not self.selected_category:
            self.show_error("Please select a category to edit")
            return
            
        old = self.selected_category
        dlg = CategoryDialog("Edit Category", "New Name:", old["category_name"], parent=self)
        if dlg.exec_() != dlg.Accepted:
            return
            
        name = dlg.get_value()
        
        try:
            # Use the category manager to rename the category directly
            category = self.category_manager.rename_category(old["category_id"], name)
            
            # Success - refresh the category list
            self.refresh_categories()
            self.show_info(f"Category renamed to '{name}' successfully")
            
        except CategoryValidationError as e:
            # Error during category validation
            self.show_error(f"Validation error: {str(e)}")
        except CategoryNotFound as e:
            # Category not found
            self.show_error(f"Category not found: {str(e)}")
        except Exception as e:
            # Unknown error
            self.show_error(f"Error renaming category: {str(e)}")

    def delete_category(self) -> None:
        """Delete the selected category with confirmation dialog."""
        if not self.selected_category:
            self.show_error("Please select a category to delete")
            return
            
        # Confirm deletion
        if self.testing_mode:
            reply = QMessageBox.Yes  # Auto-confirm in testing
        else:
            reply = QMessageBox.question(
                self, 
                "Confirm Deletion",
                f"Are you sure you want to delete the category '{self.selected_category['category_name']}'?\n\nThis will also delete all snippets in this category!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Use the category manager to delete the category directly
            self.category_manager.delete_category(self.selected_category["category_id"])
            
            # Success - refresh the category list
            self.refresh_categories()
            # Clear the snippet list since the category is gone
            self.snippetList.clear()
            self.selected_category = None
            self.show_info("Category deleted successfully")
            
        except CategoryNotFound as e:
            # Category not found
            self.show_error(f"Category not found: {str(e)}")
            
    def add_snippet(self) -> None:
        """Show a modern dialog to add a new snippet with validation."""
        if not self.selected_category:
            self.show_error("Please select a category first")
            return
            
        dlg = SnippetDialog("Add Snippet", "Snippet Name:", "Snippet Content:", parent=self)
        if dlg.exec_() != dlg.Accepted:
            return
            
        name, content = dlg.get_values()
        
        # UI-side validation for empty values - ensures error is shown regardless of backend validation
        if not name or not name.strip():
            self.show_error("Validation error: Snippet name cannot be empty")
            return
            
        if not content or not content.strip():
            self.show_error("Validation error: Snippet content cannot be empty")
            return
        
        try:
            # Use the snippet manager to create a snippet directly
            self.snippet_manager.create_snippet(
                category_id=self.selected_category["category_id"],
                snippet_name=name,
                content=content
            )
            
            # Success - refresh the snippets list
            self.load_snippets()
            self.show_info(f"Snippet '{name}' added successfully")
            
        except ValueError as e:
            # Validation error
            self.show_error(f"Validation error: {str(e)}")
        except Exception as e:
            # Unknown error
            self.show_error(f"Error creating snippet: {str(e)}")
    
    def edit_snippet(self) -> None:
        """Show a modern dialog to edit the selected snippet name/content with validation."""
        if not self.selected_snippet:
            self.show_error("Please select a snippet to edit")
            return
            
        old = self.selected_snippet
        dlg = SnippetDialog(
            "Edit Snippet", 
            "New Name:", 
            "Content:", 
            old["snippet_name"], 
            old["content"], 
            parent=self
        )
        if dlg.exec_() != dlg.Accepted:
            return
            
        name, content = dlg.get_values()
        
        # UI-side validation for empty values
        if not name or not name.strip():
            self.show_error("Validation error: Snippet name cannot be empty")
            return
            
        if not content or not content.strip():
            self.show_error("Validation error: Snippet content cannot be empty")
            return
        
        try:
            # Use the snippet manager to edit the snippet directly
            self.snippet_manager.edit_snippet(
                snippet_id=old["snippet_id"],
                snippet_name=name,
                content=content
            )
            
            # Success - refresh the snippets list (which also reloads selected_snippet)
            self.load_snippets()
            # Select the edited snippet in the list
            for i in range(self.snippetList.count()):
                if self.snippetList.item(i).text() == name:
                    self.snippetList.setCurrentRow(i)
                    break
            self.show_info(f"Snippet updated successfully")
            
        except ValueError as e:
            # Validation error
            self.show_error(f"Validation error: {str(e)}")
        except Exception as e:
            # Unknown error
            self.show_error(f"Error updating snippet: {str(e)}")

    def delete_snippet(self) -> None:
        """Delete the selected snippet with confirmation dialog."""
        if not self.selected_snippet:
            self.show_error("Please select a snippet to delete")
            return
            
        # Confirm deletion
        if self.testing_mode:
            reply = QMessageBox.Yes  # Auto-confirm in testing
        else:
            reply = QMessageBox.question(
                self, 
                "Confirm Deletion",
                f"Are you sure you want to delete the snippet '{self.selected_snippet['snippet_name']}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Store snippet ID before deleting it
            snippet_id = self.selected_snippet["snippet_id"]
            
            # Use the snippet manager to delete the snippet directly
            self.snippet_manager.delete_snippet(snippet_id)
            
            # Success - clear selection first to avoid issues when reloading
            self.selected_snippet = None
            self.snippetList.clearSelection()
            
            # Then reload the snippets list
            self.load_snippets()
            self.show_info("Snippet deleted successfully")
            
        except ValueError as e:
            # Validation error
            self.show_error(f"Validation error: {str(e)}")
        except Exception as e:
            # Unknown error
            self.show_error(f"Error deleting snippet: {str(e)}")

    # The view_snippet functionality is implemented above

def _modern_qss() -> str:
    """Return QSS for a modern Windows 11 look (rounded corners, subtle shadows, modern palette)."""
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
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e8e8ef, stop:1 #d1d1e0);
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
    
    # Attempt to shut down the server if we started it
    try:
        win.api_server_manager.shutdown_server()
    except Exception:
        pass
        
    sys.exit(exit_code)
