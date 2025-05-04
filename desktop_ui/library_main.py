"""
PyQt5 Desktop UI for the Snippets Library
- Fullscreen main window, maximized dialogs
- Category and snippet management with validation and error dialogs
"""
import sys
from typing import List, Dict, Any, Optional, Tuple, Union

# Direct explicit imports from PyQt5 modules to fix linting issues
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QLineEdit, QMessageBox, 
    QSizePolicy, QFrame, QGridLayout, QSpacerItem, QSplitter
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon

# Direct imports from PyQt5 already specified above

# Try relative imports first, then fall back to direct imports
try:
    from .graphql_client import GraphQLClient
    from .modern_dialogs import CategoryDialog, SnippetDialog
    from .view_snippet_dialog import ViewSnippetDialog
    from .library_service import LibraryService, Category, Snippet
    from .api_server_manager import APIServerManager
except ImportError:
    # For direct script execution
    from graphql_client import GraphQLClient
    from modern_dialogs import CategoryDialog, SnippetDialog
    from view_snippet_dialog import ViewSnippetDialog
    from library_service import LibraryService, Category, Snippet
    from api_server_manager import APIServerManager

class LibraryMainWindow(QMainWindow):
    """
    Modern Windows 11-style Snippets Library main window (PyQt5).
    Uses Fusion style, Segoe UI font, QSS for rounded corners, drop shadows, icons, and a modern color palette.
    """
    def __init__(self) -> None:
        # Initialize API server manager to ensure the GraphQL server is running
        self.api_server_manager = APIServerManager()
        super().__init__()
        self.setWindowTitle("Snippets Library")
        self.setWindowState(Qt.WindowMaximized)
        self.setMinimumSize(900, 600)
        
        # Use the robust service layer instead of direct GraphQL client
        self.service = LibraryService()
        
        # Init data attributes
        self.categories = []
        self.snippets = []
        self.selected_category = None
        self.selected_snippet = None
        
        # Setup UI first, then ensure server and load data
        self.setup_ui()
        self.ensure_server_running()
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
        self.categoryList.itemSelectionChanged.connect(self.load_snippets)
        self.snippetList.itemDoubleClicked.connect(self.view_snippet)

        # Nothing to do here - data already initialized in __init__

    def ensure_server_running(self) -> None:
        """Ensure the GraphQL API server is running, starting it if necessary."""
        if not self.api_server_manager.is_server_running():
            # Show a message that we're starting the server
            QMessageBox.information(
                self,
                "Starting Server",
                "The GraphQL API server is not running. Starting it automatically..."
            )
            
            # Start the server
            success = self.api_server_manager.start_server()
            
            if not success:
                QMessageBox.critical(
                    self,
                    "Server Error",
                    "Failed to start the GraphQL API server. Please start it manually."
                )
            else:
                QMessageBox.information(
                    self,
                    "Server Started",
                    "The GraphQL API server has been started successfully."
                )
    
    def load_data(self) -> None:
        """Load initial data from the server."""
        self.refresh_categories()
        
    def show_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Error", msg)
        self.status.setText(f"Error: {msg}")

    def show_info(self, msg: str) -> None:
        QMessageBox.information(self, "Info", msg)
        self.status.setText(msg)

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
        """Fetch categories from the API and update the list widget."""
        try:
            # Use the service layer to get categories with error handling and caching
            categories = self.service.get_categories()
            self.categories = [cat.model_dump() for cat in categories]
            
            # Update UI
            self.categoryList.clear()
            for category in self.categories:
                self.categoryList.addItem(category["category_name"])
                
        except Exception as e:
            self.show_error(f"Error loading categories: {str(e)}")

    def load_snippets(self) -> None:
        """Fetch snippets for the selected category from the API."""
        if not self.selected_category:
            return
            
        try:
            # Use the service layer to get snippets with error handling and caching
            snippets = self.service.get_snippets(self.selected_category["category_id"])
            self.snippets = [snippet.model_dump() for snippet in snippets]
            
            # Update UI
            self.snippetList.clear()
            for snippet in self.snippets:
                self.snippetList.addItem(snippet["snippet_name"])
                
        except Exception as e:
            self.show_error(f"Error loading snippets: {str(e)}")

    def add_category(self) -> None:
        """Show a modern dialog to add a new category with validation."""
        dlg = CategoryDialog("Add Category", "Category Name:", parent=self)
        if dlg.exec_() != dlg.Accepted:
            return
            
        name = dlg.get_value()
        
        # Use the service layer to add a category with validation and error handling
        result = self.service.add_category(name)
        
        if result["success"]:
            # Success - refresh the category list
            self.refresh_categories()
            self.show_info(f"Category '{name}' added successfully")
        else:
            # Error during category creation
            self.show_error(result["error"] or "Unknown error creating category")

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
        
        # Use the service layer to edit the category with validation and error handling
        result = self.service.edit_category(old["category_id"], name)
        
        if result["success"]:
            # Success - refresh the category list
            self.refresh_categories()
            self.show_info(f"Category renamed to '{name}' successfully")
        else:
            # Error during category rename
            self.show_error(result["error"] or "Unknown error renaming category")

    def delete_category(self) -> None:
        """Delete the selected category with confirmation dialog."""
        if not self.selected_category:
            self.show_error("Please select a category to delete")
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion",
            f"Are you sure you want to delete the category '{self.selected_category['category_name']}'?\n\nThis will also delete all snippets in this category!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Use the service layer to delete the category with validation and error handling
        result = self.service.delete_category(self.selected_category["category_id"])
        
        if result["success"]:
            # Success - refresh the category list
            self.refresh_categories()
            # Clear the snippet list since the category is gone
            self.snippetList.clear()
            self.selected_category = None
            self.show_info("Category deleted successfully")
        else:
            # Error during category deletion
            self.show_error(result["error"] or "Unknown error deleting category")

    def add_snippet(self) -> None:
        """Show a modern dialog to add a new snippet with multi-line content editing and validation."""
        if not self.selected_category:
            self.show_error("Please select a category first")
            return
            
        cat = self.selected_category
        dlg = SnippetDialog("Add Snippet", "Snippet Name:", "Snippet Content:", parent=self)
        if dlg.exec_() != dlg.Accepted:
            return
            
        name, content = dlg.get_values()
        
        # Use the service layer to add a snippet with validation and error handling
        result = self.service.add_snippet(cat["category_id"], name, content)
        
        if result["success"]:
            # Success - refresh the snippets list
            self.load_snippets()
            self.show_info(f"Snippet '{name}' added successfully")
        else:
            # Error during snippet creation
            self.show_error(result["error"] or "Unknown error creating snippet")

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
        
        # Use the service layer to edit the snippet with validation and error handling
        result = self.service.edit_snippet(
            old["snippet_id"],
            name,
            content
        )
        
        if result["success"]:
            # Success - refresh the snippets list
            self.load_snippets()
            self.show_info(f"Snippet updated successfully")
        else:
            # Error during snippet update
            self.show_error(result["error"] or "Unknown error updating snippet")

    def delete_snippet(self) -> None:
        """Delete the selected snippet with confirmation dialog."""
        if not self.selected_snippet:
            self.show_error("Please select a snippet to delete")
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion",
            f"Are you sure you want to delete the snippet '{self.selected_snippet['snippet_name']}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Use the service layer to delete the snippet with validation and error handling
        result = self.service.delete_snippet(self.selected_snippet["snippet_id"])
        
        if result["success"]:
            # Success - refresh the snippets list
            self.load_snippets()
            self.selected_snippet = None
            self.show_info("Snippet deleted successfully")
        else:
            # Error during snippet deletion
            self.show_error(result["error"] or "Unknown error deleting snippet")

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
