"""PySide6-based development scaffold for Snippet CRUD.

This is for development/testing only. Not for production use.
"""

from typing import Any

# Third-party imports
from PySide6 import QtWidgets
from PySide6.QtCore import Qt


class SnippetScaffold(QtWidgets.QMainWindow):
    """A development scaffold UI for testing snippet management functionality.

    This class provides a simple UI for adding, editing, deleting, and viewing snippets
    using the snippet_manager. It is intended for development and testing only.
    """

    def __init__(self, snippet_manager: Any) -> None:
        super().__init__()
        self.snippet_manager = snippet_manager
        self.statusBar()  # Create the status bar
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface with all widgets and connections."""
        self.setWindowTitle("Snippet Development Scaffold")
        # Create a central widget to hold the layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Create a label with larger font for better visibility
        title_label = QtWidgets.QLabel("Snippets Manager")
        font = title_label.font()
        font.setPointSize(14)
        font.setBold(True)
        title_label.setFont(font)
        layout.addWidget(title_label)

        # Add a horizontal layout for the list title and refresh button
        list_header = QtWidgets.QHBoxLayout()
        list_label = QtWidgets.QLabel("Available Snippets:")
        font = list_label.font()
        font.setBold(True)
        list_label.setFont(font)
        list_header.addWidget(list_label)

        # Add refresh button
        self.refresh_btn = QtWidgets.QPushButton("Refresh List")
        self.refresh_btn.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload)
        )
        list_header.addWidget(self.refresh_btn)
        layout.addLayout(list_header)

        # Create and configure the snippet list with more height
        self.snippet_list = QtWidgets.QListWidget()
        self.snippet_list.setMinimumHeight(
            150
        )  # Set a minimum height for better visibility
        self.snippet_list.setAlternatingRowColors(
            True
        )  # Alternating colors for better readability
        layout.addWidget(self.snippet_list)

        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("Snippet Name")
        layout.addWidget(self.name_input)

        self.content_input = QtWidgets.QTextEdit()
        self.content_input.setPlaceholderText("Snippet Content")
        layout.addWidget(self.content_input)

        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Add Snippet")
        self.edit_btn = QtWidgets.QPushButton("Edit Selected")
        self.delete_btn = QtWidgets.QPushButton("Delete Selected")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)

        # No need to call setLayout since it's set on the central widget
        self.refresh_snippets()

        # Connect signals to slots
        self.add_btn.clicked.connect(self.add_snippet)
        self.edit_btn.clicked.connect(self.edit_snippet)
        self.delete_btn.clicked.connect(self.delete_snippet)
        self.refresh_btn.clicked.connect(self.refresh_snippets)

        # Connect double-click on list item to load the snippet
        self.snippet_list.itemDoubleClicked.connect(self.load_selected_snippet)

    def refresh_snippets(self) -> None:
        """Refresh the snippet list widget with the latest snippets from the database.

        All snippets are loaded from category ID 1 (for demo purposes).
        """
        self.snippet_list.clear()
        # Display a status message while loading
        self.snippet_list.addItem("Loading snippets...")
        QtWidgets.QApplication.processEvents()  # Process events to update the UI immediately

        # For demo: use category_id=1
        try:
            snippets = self.snippet_manager.list_snippets(1)
            self.snippet_list.clear()  # Clear the loading message

            if not snippets:
                self.snippet_list.addItem("No snippets found. Add one below!")
                return

            for s in snippets:
                # Format with more information
                item = QtWidgets.QListWidgetItem(f"{s.snippet_id}: {s.snippet_name}")
                # Add tooltip with content preview
                preview = s.content[:50] + "..." if len(s.content) > 50 else s.content
                item.setToolTip(f"Content: {preview}")
                # Store the snippet ID as item data for easier access
                item.setData(Qt.ItemDataRole.UserRole, s.snippet_id)
                self.snippet_list.addItem(item)

            # Display status message at the bottom of the window
            self.statusBar().showMessage(f"Loaded {len(snippets)} snippets", 3000)
        except ValueError as e:
            self.snippet_list.clear()
            # Create error item with a special format and make it non-selectable
            error_item = QtWidgets.QListWidgetItem(f"⚠️ Error: {e}")
            error_item.setForeground(Qt.GlobalColor.red)
            error_item.setFlags(error_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.snippet_list.addItem(error_item)
            # Show error in status bar too
            self.statusBar().showMessage(f"Error: {e}", 5000)
        except RuntimeError as e:
            self.snippet_list.clear()
            # Create error item with a special format and make it non-selectable
            error_item = QtWidgets.QListWidgetItem(f"⚠️ Error: {e}")
            error_item.setForeground(Qt.GlobalColor.red)
            error_item.setFlags(error_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.snippet_list.addItem(error_item)
            # Show error in status bar too
            self.statusBar().showMessage(f"Error: {e}", 5000)

        # Highlight the first item if any exist that are valid snippets
        if self.snippet_list.count() > 0:
            for i in range(self.snippet_list.count()):
                item = self.snippet_list.item(i)
                if item.flags() & Qt.ItemFlag.ItemIsSelectable:
                    self.snippet_list.setCurrentItem(item)
                    break

    def add_snippet(self) -> None:
        """Add a new snippet using the values from the input fields.

        Shows an error message if the operation fails.
        """
        name = self.name_input.text().strip()
        content = self.content_input.toPlainText().strip()

        # Validate inputs before attempting to create
        if not name:
            QtWidgets.QMessageBox.warning(
                self, "Validation Error", "Snippet name cannot be empty."
            )
            return

        if not content:
            QtWidgets.QMessageBox.warning(
                self, "Validation Error", "Snippet content cannot be empty."
            )
            return

        try:
            snippet_id = self.snippet_manager.create_snippet(1, name, content)
            self.refresh_snippets()
            # Clear inputs after successful creation
            self.name_input.clear()
            self.content_input.clear()
            # Show success message
            QtWidgets.QMessageBox.information(
                self,
                "Success",
                f"Snippet '{name}' created successfully with ID {snippet_id}",
            )
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Validation Error", str(e))
        except RuntimeError as e:
            QtWidgets.QMessageBox.warning(self, "Database Error", str(e))

    def edit_snippet(self) -> None:
        """Edit the currently selected snippet with values from input fields.

        Shows an error message if no snippet is selected or the operation fails.
        """
        item = self.snippet_list.currentItem()
        if not item:
            QtWidgets.QMessageBox.warning(self, "Error", "No snippet selected.")
            return

        # Get the snippet ID from the item data if available, otherwise parse from text
        snippet_id = item.data(Qt.ItemDataRole.UserRole)
        if snippet_id is None:  # Fallback to parsing from text if data not set
            try:
                snippet_id = int(item.text().split(":")[0])
            except (ValueError, IndexError):
                QtWidgets.QMessageBox.warning(
                    self, "Error", "Invalid snippet selection."
                )
                return

        name = self.name_input.text().strip()
        content = self.content_input.toPlainText().strip()

        if not name or not content:
            QtWidgets.QMessageBox.warning(
                self, "Error", "Name and content cannot be empty."
            )
            return

        try:
            self.snippet_manager.edit_snippet(
                snippet_id, snippet_name=name, content=content
            )
            self.refresh_snippets()
            self.statusBar().showMessage(f"Snippet '{name}' updated successfully", 3000)
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Validation Error", str(e))
        except RuntimeError as e:
            QtWidgets.QMessageBox.warning(self, "Database Error", str(e))

    def delete_snippet(self) -> None:
        """Delete the currently selected snippet.

        Shows an error message if no snippet is selected or the operation fails.
        """
        item = self.snippet_list.currentItem()
        if not item:
            QtWidgets.QMessageBox.warning(self, "Error", "No snippet selected.")
            return

        # Get the snippet ID from the item data if available, otherwise parse from text
        snippet_id = item.data(Qt.ItemDataRole.UserRole)
        if snippet_id is None:  # Fallback to parsing from text if data not set
            try:
                snippet_id = int(item.text().split(":")[0])
            except (ValueError, IndexError):
                QtWidgets.QMessageBox.warning(
                    self, "Error", "Invalid snippet selection."
                )
                return

        # Confirm deletion with the user
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the snippet '{item.text()}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )

        if confirm == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                self.snippet_manager.delete_snippet(snippet_id)
                self.refresh_snippets()
                self.statusBar().showMessage("Snippet deleted successfully", 3000)
            except ValueError as e:
                QtWidgets.QMessageBox.warning(self, "Validation Error", str(e))
            except RuntimeError as e:
                QtWidgets.QMessageBox.warning(self, "Database Error", str(e))

    def load_selected_snippet(self, item: QtWidgets.QListWidgetItem) -> None:
        """Load the selected snippet into the edit fields for viewing or editing.

        Args:
            item: The list widget item that was clicked or selected
        """
        if not item:
            return

        # Get the snippet ID from the item data if available, otherwise parse from text
        snippet_id = item.data(Qt.ItemDataRole.UserRole)
        if snippet_id is None:  # Fallback to parsing from text if data not set
            try:
                snippet_id = int(item.text().split(":")[0])
            except (ValueError, IndexError):
                QtWidgets.QMessageBox.warning(
                    self, "Error", "Invalid snippet selection."
                )
                return

        try:
            snippet = self.snippet_manager.get_snippet(snippet_id)
            if snippet:
                self.name_input.setText(snippet.snippet_name)
                self.content_input.setText(snippet.content)
                self.statusBar().showMessage(
                    f"Loaded snippet {snippet.snippet_id}: {snippet.snippet_name}", 3000
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self, "Error", f"Snippet with ID {snippet_id} not found."
                )
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Could not load snippet: {e}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Unexpected error: {e}")


if __name__ == "__main__":
    import os
    import sys

    # Add the project root directory to the Python path
    # This ensures that imports like 'db.database_manager' work correctly
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, project_root)

    from db.database_manager import DatabaseManager
    from models.snippet_manager import SnippetManager

    # Create the application
    app = QtWidgets.QApplication(sys.argv)

    # Setup database and snippet manager
    try:
        # Use the main database file for the application
        db_manager = DatabaseManager("typing_data.db")

        # Make sure database tables are initialized
        db_manager.init_tables()
        print("Database tables initialized successfully")

        snippet_manager = SnippetManager(db_manager)

        # Create and show the snippet scaffold UI
        scaffold = SnippetScaffold(snippet_manager)
        scaffold.setGeometry(100, 100, 600, 400)  # Set reasonable window size
        scaffold.show()

        # Start the event loop
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error initializing the application: {e}")
        sys.exit(1)
